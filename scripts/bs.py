"""Brightspace helper using a saved login profile (.profile/).

  python scripts/bs.py login   <base>                 one-time, manual login in a visible browser
  python scripts/bs.py toc     <base> <orgUnitId>     write notes/<ou>/toc.md (modules/topics tree)
  python scripts/bs.py page    <base> <ou> <topicId>  dump page text + video/iframe/track URLs as JSON
  python scripts/bs.py cookies <base>                 write cookies.txt (Netscape) for yt-dlp

<base> e.g. https://brightspace.myuni.edu
"""
import json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / ".profile"


STATE = PROFILE / "cookies.json"  # SSO cookies are session-only, so the profile dir alone forgets them


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
        elif cmd == "video":  # video <base> <ou> <activityId> <outdir>: YuJa captions (.srt) + HLS url
            ou, aid, outdir = a
            host = json.loads((PROFILE / "seq.json").read_text())["host"]
            pg = c.new_page()
            src = {}
            pg.on("response", lambda r: src.update(j=r.json()) if "/P/Data/VideoSource" in r.url and "j" not in src else None)
            pg.goto(f"{base}/d2l/le/enhancedSequenceViewer/{ou}?url=https%3A%2F%2F{host}%2F{ou}%2Factivity%2F{aid}%3FfilterOnDatesAndDepth%3D1",
                    wait_until="networkidle")
            time.sleep(6)
            fr = next((f for f in pg.frames if "yuja.com/V/Video" in f.url), None)
            if not fr:
                sys.exit("no YuJa player on this topic (not a video?)")
            for label in ("Play from beginning", "Resume from"):  # resume prompt (only if partly watched) blocks playback
                try:
                    fr.get_by_text(label).first.click(timeout=1500)
                    break
                except Exception:
                    pass
            # VideoSource JSON lists the caption file path (e.g. /P/DataPage/CaptionFile/4691_English.srt)
            t = [v for k, v in src.get("j", {}).get("captionURL", {}).items() if v.endswith(".srt")][:1]
            o = Path(outdir)
            o.mkdir(parents=True, exist_ok=True)
            if t:
                (o / "video.en.srt").write_text(fr.evaluate("u => fetch(u).then(r => r.text())", t[0]), encoding="utf-8")
            else:
                print("no caption file listed (no soft subs?)")
            hls = next(iter(src.get("j", {}).get("streams", [{}])[0].get("typeAndVideoSourceMap", {}).values()), {})
            m3u8 = hls.get("fileURL", "")
            (o / "source.txt").write_text(m3u8)
            print(json.dumps({"title": pg.title(), "srt": bool(t), "m3u8": bool(m3u8), "dir": str(o)}))
        elif cmd == "page":
            ou, tid = a
            pg = c.new_page()
            pg.goto(f"{base}/d2l/le/content/{ou}/viewContent/{tid}/View", wait_until="networkidle")
            time.sleep(3)  # players inject late
            js = """() => ({
              title: document.title,
              text: document.body.innerText.slice(0, 20000),
              iframes: [...document.querySelectorAll('iframe')].map(f => f.src),
              videos: [...document.querySelectorAll('video,source')].map(v => v.currentSrc || v.src),
              tracks: [...document.querySelectorAll('track')].map(t => ({src: t.src, label: t.label, lang: t.srclang})),
              links: [...document.querySelectorAll('a[href]')].map(a => [a.innerText.trim(), a.href]).filter(x => x[0]).slice(0, 80)
            })"""
            print(json.dumps(pg.evaluate(js), indent=1))
        elif cmd == "cookies":
            api_version(c, base)  # fail early if logged out
            lines = ["# Netscape HTTP Cookie File"]
            for k in c.cookies():
                lines.append("\t".join([k["domain"], str(k["domain"].startswith(".")).upper(), k["path"],
                                        str(k["secure"]).upper(), str(int(k["expires"])) if k["expires"] > 0 else "0",
                                        k["name"], k["value"]]))
            (ROOT / "cookies.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
            print("wrote cookies.txt (gitignored)")
        else:
            sys.exit(__doc__)
        c.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
