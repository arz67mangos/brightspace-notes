"""Brightspace helper using a saved login profile (.profile/).

  python scripts/bs.py login   <base>                          one-time manual login in a visible browser
  python scripts/bs.py toc     <base> <ou>                     write notes/<ou>/toc.md (modules/topics + activity IDs)
  python scripts/bs.py video   <base> <ou> <activityId> <dir>  captions + stream URL (hosts.py adapters)
  python scripts/bs.py doc     <base> <ou> <activityId> <dir>  download a file topic (pdf/docx/pptx/zip...)
  python scripts/bs.py page    <base> <ou> <topicId>           dump page text + iframes/links as JSON
  python scripts/bs.py cookies <base>                          write cookies.txt (Netscape) for yt-dlp

<base> e.g. https://brightspace.myuni.edu ; <ou> = orgUnitId, the number in /d2l/home/<id>
"""
import json, sys, time
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hosts

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / ".profile"
STATE = PROFILE / "cookies.json"  # SSO cookies are session-only, so the profile dir alone forgets them
CONFIG = PROFILE / "config.json"  # {"base": ...}, written by login, read by doctor.py


def ctx(p, headless=True):
    c = p.chromium.launch_persistent_context(str(PROFILE), headless=headless)
    if STATE.exists():
        c.add_cookies(json.loads(STATE.read_text()))
    return c


def api_version(c, base):
    r = c.request.get(f"{base}/d2l/api/versions/")
    if not r.ok:
        sys.exit(f"not logged in or bad base URL (HTTP {r.status}); run: bs.py login {base}")
    return next(v["LatestVersion"] for v in r.json() if v["ProductCode"] == "le")


def write_cookies(c):
    lines = ["# Netscape HTTP Cookie File"]
    for k in c.cookies():
        lines.append("\t".join([k["domain"], str(k["domain"].startswith(".")).upper(), k["path"],
                                str(k["secure"]).upper(), str(int(k["expires"])) if k["expires"] > 0 else "0",
                                k["name"], k["value"]]))
    (ROOT / "cookies.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote cookies.txt (gitignored)")


def walk_seq(e, depth=0, out=None):
    """Lessons sequence JSON -> markdown lines: modules as bold, topics as `title (activity ID, kind)`."""
    out = [] if out is None else out
    for s in e.get("entities", []):
        c = s.get("class", [])
        if "sequence" not in c and "sequenced-activity" not in c:
            continue
        aid = next((l["href"].split("/activity/")[1].split("?")[0] for l in s.get("links", [])
                    if "self" in l.get("rel", []) and "/activity/" in l["href"]), "?")
        kind = next((x for sub in s.get("entities", []) if "about" in sub.get("rel", []) for x in sub["class"] if x != "activity"), "")
        title = s["properties"]["title"].strip()
        out.append(f"{'  ' * depth}- **{title}** ({aid})" if "sequence" in c else f"{'  ' * depth}- {title} ({aid}, {kind})")
        walk_seq(s, depth + 1, out)
    return out


def open_activity(c, base, ou, aid):
    """Load one topic in the sequence viewer. Returns (page, [(url, response)], activity JSON)."""
    if not (PROFILE / "seq.json").exists():
        sys.exit(f"run first: python scripts/bs.py toc {base} {ou}")
    host = json.loads((PROFILE / "seq.json").read_text())["host"]
    pg, net = c.new_page(), []
    seen = lambda: any(f"/activity/{aid}?" in u and "sequences.api" in u for u, _ in net)
    pg.on("response", lambda r: net.append((r.url, r)))  # bodies are read later: reading inside the handler fails
    pg.goto(f"{base}/d2l/le/enhancedSequenceViewer/{ou}?url=https%3A%2F%2F{host}%2F{ou}%2Factivity%2F{aid}%3FfilterOnDatesAndDepth%3D1",
            wait_until="domcontentloaded")  # not networkidle: some topic pages (zip previews) never go idle
    for attempt in range(2):  # the activity response is occasionally missed on the first load: reload once
        for _ in range(30):
            if seen() or "login" in pg.url:
                break
            time.sleep(0.5)
        if seen() or "login" in pg.url:
            break
        pg.reload(wait_until="domcontentloaded")
    time.sleep(6)  # players inject late
    if "login.microsoftonline" in pg.url or "/d2l/login" in pg.url:
        sys.exit(f"session expired: python scripts/bs.py login {base}")
    act = next((j for u, r in net if f"/activity/{aid}?" in u and "sequences.api" in u and (j := hosts.safe_json(r))), {})
    return pg, net, act


def file_links(e, out=None):
    """All (href, filename) download links under a file entity of an activity JSON; enforced-content link first."""
    out = [] if out is None else out
    if "file" in e.get("class", []):
        ls = sorted(e.get("links", []), key=lambda l: "embed" not in l.get("class", []))
        out += [(l["href"], e.get("properties", {}).get("name")) for l in ls if "alternate" in l.get("rel", []) and l["href"].startswith("http")]
    for s in e.get("entities", []):
        file_links(s, out)
    return out


def main(cmd, base, *a):
    base = base.rstrip("/")
    with sync_playwright() as p:
        if cmd == "login":
            c = ctx(p, headless=False)
            pg = c.new_page()
            pg.goto(base)
            print("Log in (incl. MFA) in the browser window; waiting up to 10 min...", flush=True)
            host = base.split("//")[1]
            for _ in range(300):  # no stdin under agents: wait until SSO lands back on Brightspace's home
                time.sleep(2)
                if host in pg.url and "/d2l/" in pg.url:
                    STATE.write_text(json.dumps(c.cookies()))
                    CONFIG.write_text(json.dumps({"base": base}))
                    print("logged in, session saved", flush=True)
                    break
            return c.close()
        c = ctx(p)
        if cmd == "toc":  # student accounts get 403 on /d2l/api/le/.../content/toc, so use the Lessons sequence API
            ou = a[0]
            pg = c.new_page()
            hdr = {}

            def grab(r):
                if "sequences.api" in r.url and "auth" not in hdr and "authorization" in r.all_headers():
                    hdr["auth"] = r.all_headers()["authorization"]
                    hdr["host"] = r.url.split("/")[2]

            pg.on("request", grab)
            pg.goto(f"{base}/d2l/le/sequenceLauncher/{ou}/View", wait_until="networkidle")
            time.sleep(4)
            if "auth" not in hdr:
                sys.exit(f"no sequence API call seen (logged out?). Run: bs.py login {base}")
            root = c.request.get(f"https://{hdr['host']}/{ou}", headers={"Authorization": hdr["auth"]}).json()
            (PROFILE / "seq.json").write_text(json.dumps({"host": hdr["host"]}))
            out = ROOT / "notes" / ou
            out.mkdir(parents=True, exist_ok=True)
            (out / "toc.md").write_text(f"# {root['properties']['title']}\n\n" + "\n".join(walk_seq(root)) + "\n", encoding="utf-8")
            print(f"wrote {out / 'toc.md'}")
        elif cmd == "video":
            ou, aid, outdir = a
            pg, net, _ = open_activity(c, base, ou, aid)
            x = type("Ctx", (), {"pg": pg, "c": c, "net": net})()
            hit = next((h for ad in hosts.ADAPTERS if (h := ad(x))), None)
            if not hit:
                sys.exit("no video found on this topic (is it a file/quiz/link?)")
            o = Path(outdir)
            o.mkdir(parents=True, exist_ok=True)
            for name, text in hit["subs"].items():
                (o / name).write_text(text, encoding="utf-8")
            (o / "source.txt").write_text(hit["source"])
            if hit["host"] == "embed":  # yt-dlp needs the login cookies to open these
                write_cookies(c)
            print(json.dumps({"title": pg.title(), "host": hit["host"], "subs": list(hit["subs"]), "source": bool(hit["source"]), "dir": str(o)}))
        elif cmd == "doc":
            ou, aid, outdir = a
            pg, _, act = open_activity(c, base, ou, aid)
            links = file_links(act)
            if not links:
                sys.exit("no downloadable file on this topic (not a file-activity?)")
            href, name = links[0]
            r = c.request.get(href)
            if not r.ok:
                sys.exit(f"download failed: HTTP {r.status}")
            o = Path(outdir)
            o.mkdir(parents=True, exist_ok=True)
            f = o / (name or unquote(href.split("?")[0].rsplit("/", 1)[-1]))
            f.write_bytes(r.body())
            print(json.dumps({"file": str(f), "bytes": f.stat().st_size}))
        elif cmd == "page":
            ou, tid = a
            pg = c.new_page()
            pg.goto(f"{base}/d2l/le/content/{ou}/viewContent/{tid}/View", wait_until="networkidle")
            time.sleep(3)
            js = """() => ({
              title: document.title,
              text: document.body.innerText.slice(0, 20000),
              iframes: [...document.querySelectorAll('iframe')].map(f => f.src),
              links: [...document.querySelectorAll('a[href]')].map(a => [a.innerText.trim(), a.href]).filter(x => x[0]).slice(0, 80)
            })"""
            print(json.dumps(pg.evaluate(js), indent=1))
        elif cmd == "cookies":
            api_version(c, base)
            write_cookies(c)
        else:
            sys.exit(__doc__)
        c.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
