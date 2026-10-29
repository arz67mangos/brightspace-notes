"""Brightspace helper using a saved login profile (.profile/).

  python scripts/bs.py login   <base>                          one-time manual login in a visible browser
  python scripts/bs.py toc     <base> <ou>                     write notes/<ou>/toc.md (modules/topics + activity IDs)
  python scripts/bs.py video   <base> <ou> <activityId> <dir>  captions + stream URL (hosts.py adapters)
  python scripts/bs.py doc     <base> <ou> <activityId> <dir>  download a file topic (pdf/docx/pptx/zip...)
  python scripts/bs.py page    <base> <ou> <topicId>           dump page text + iframes/links as JSON
  python scripts/bs.py course  <base> <ou> <activityId> <dir>  multi-lesson course (SCORM/Rise): lessons.json with each lesson's text + video URL
  python scripts/bs.py yuja    <base> <video-url> <dir>        captions + source.txt for a direct YuJa link
  python scripts/bs.py cookies <base>                          write cookies.txt (Netscape) for yt-dlp
  python scripts/bs.py mode    show|headless                   watch the browser work (default) or hide it

<base> e.g. https://brightspace.myuni.edu ; <ou> = orgUnitId, the number in /d2l/home/<id>
"""
import json, re, sys, time
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env  # noqa: F401  (UTF-8 output, PATH refresh)
import hosts

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / ".profile"
STATE = PROFILE / "cookies.json"  # SSO cookies are session-only, so the profile dir alone forgets them
CONFIG = PROFILE / "config.json"  # {"base": ...}, written by login, read by doctor.py


def settings():
    return json.loads(CONFIG.read_text()) if CONFIG.exists() else {}


def save_settings(**kw):
    PROFILE.mkdir(exist_ok=True)
    CONFIG.write_text(json.dumps({**settings(), **kw}))


def ctx(p, headless=None):
    """Browser context with the saved login. Visible window by default; `bs.py mode headless` hides it."""
    if headless is None:
        headless = settings().get("headless", False)
    args = [  # a visible window behind other apps is throttled as "occluded", which freezes video players' JavaScript
        "--disable-features=CalculateNativeWinOcclusion", "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding", "--disable-background-timer-throttling"]
    try:  # visible windows: prefer the real Chrome if installed (has the H.264 codec video players check for)
        c = p.chromium.launch_persistent_context(str(PROFILE), headless=headless, args=args, **({} if headless else {"channel": "chrome"}))
    except Exception:
        c = p.chromium.launch_persistent_context(str(PROFILE), headless=headless, args=args)
    if STATE.exists():
        c.add_cookies(json.loads(STATE.read_text()))
    return c


def log_capture(ou, aid, kind, ok, **detail):
    """One line per capture attempt in notes/<ou>/capture-log.jsonl: verify.py compares it with toc.md to show what was NOT captured."""
    d = ROOT / "notes" / ou
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "capture-log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "aid": aid, "kind": kind, "ok": ok, **detail}) + "\n")


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


def html_to_md(h):
    """Module descriptions are HTML: keep text, lists and links ([text](url)), drop the rest."""
    import html as _h, re as _re

    h = _re.sub(r"(?is)<(script|style).*?</\1>", "", h)
    h = _re.sub(r'(?is)<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', lambda m: f"[{_re.sub('<[^>]+>', '', m.group(2)).strip()}]({m.group(1)})", h)
    h = _re.sub(r"(?i)<li[^>]*>", "\n- ", h)
    h = _re.sub(r"(?i)</p>|<br\s*/?>|</div>|</h\d>|</tr>", "\n", h)
    return _re.sub(r"\n{3,}", "\n\n", _h.unescape(_re.sub(r"<[^>]+>", "", h))).strip()


def module_intros(e, out=None):
    """(module title, aid, description as markdown) for every module whose description isn't empty."""
    out = [] if out is None else out
    for s in e.get("entities", []):
        if "sequence" in s.get("class", []):
            d = html_to_md(s.get("properties", {}).get("description") or "")
            aid = next((l["href"].split("/activity/")[1].split("?")[0] for l in s.get("links", [])
                        if "self" in l.get("rel", []) and "/activity/" in l["href"]), "?")
            if d:
                out.append((s["properties"]["title"].strip(), aid, d))
            module_intros(s, out)
    return out


def open_activity(c, base, ou, aid, player=False):
    """Load one topic in the sequence viewer. Returns (page, [(url, response)], activity JSON).
    Response bodies are NOT usable (Playwright drops them when the LTI launch navigates the frame): adapters
    re-fetch the URLs they need from inside the right frame instead. The activity JSON is fetched with the
    page's own bearer token. player=True also waits for an embedded video player (iframe on another site)."""
    if not (PROFILE / "seq.json").exists():
        sys.exit(f"run first: python scripts/bs.py toc {base} {ou}")
    host = json.loads((PROFILE / "seq.json").read_text())["host"]
    pg, net, auth = c.new_page(), [], {}
    seen = lambda: bool(auth)

    def grab(r):
        if "sequences.api" in r.url and "auth" not in auth and "authorization" in r.all_headers():
            auth["auth"] = r.all_headers()["authorization"]

    pg.on("request", grab)
    pg.on("response", lambda r: net.append((r.url, r)))
    try:  # a window that isn't in front reads as "hidden" and some players then refuse to start
        pg.bring_to_front()
        c.new_cdp_session(pg).send("Emulation.setFocusEmulationEnabled", {"enabled": True})
    except Exception:
        pass
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
    if player:
        site = base.split("//")[1]
        for _ in range(60):  # up to 30 s for the LTI launch to land on the video site
            if any(f.url.startswith("http") and site not in f.url for f in pg.frames):
                break
            time.sleep(0.5)
        for _ in range(40):  # then up to 20 s for the player to ask for its media (YuJa: VideoSource)
            if any("/P/Data/VideoSource" in u or re.search(r"\.(m3u8|mpd)", u) for u, _ in net):
                break
            time.sleep(0.5)
    time.sleep(6)  # players inject late
    if "login.microsoftonline" in pg.url or "/d2l/login" in pg.url:
        sys.exit(f"session expired: python scripts/bs.py login {base}")
    act = {}
    if auth:
        r = c.request.get(f"https://{host}/{ou}/activity/{aid}?filterOnDatesAndDepth=1", headers={"Authorization": auth["auth"]})
        act = hosts.safe_json(r) or {}
    return pg, net, act


def course_lessons(c, base, ou, aid):
    """Walk a SCORM/Rise course ("Video 1..N" lessons + a Review Quiz): click each lesson, collect its text and
    embedded video URL. Never touches quizzes. Returns [{lesson, text, video, iframes}]."""
    pg, _, _ = open_activity(c, base, ou, aid)
    fr = next((f for f in pg.frames if "content/index.html" in f.url), None)
    if not fr:
        sys.exit("no course player found on this topic (not a SCORM/Rise course?)")
    names = fr.evaluate("() => [...document.querySelectorAll('a[href*=\"#/lessons/\"]')].map(a => a.innerText.trim().split('\\n')[0])")
    names = [n for n in names if n and not re.match(r"Lesson \d+ ?-|START COURSE$", n, re.I)]  # skip the "continue: Lesson N - title" link and the cover page's START COURSE button
    if not names:  # older layout: lessons are named "Video 1", "Part 2" ...
        names = [n for n in fr.evaluate("() => [...document.querySelectorAll('a, button')].map(e => e.innerText.trim())")
                 if re.fullmatch(r"(Video|Lesson|Part) ?\d+.*", n or "")]
    out, seen = [], set()
    for k, n in enumerate(dict.fromkeys(names), 1):
        fr.get_by_text(n, exact=True).first.click()
        vid, txt, quiet = "", "", 0
        for _ in range(80):  # up to 40 s: the lesson heading changes, then its player iframe is added (lazy, below the fold)
            time.sleep(0.5)
            try:
                fr.evaluate("() => { const m = document.querySelector('main, [role=main]') || document.scrollingElement; m.scrollTo(0, 1e5); window.scrollTo(0, 1e5); }")
                txt = fr.evaluate("() => document.body.innerText")
                srcs = fr.evaluate("() => [...document.querySelectorAll('iframe')].map(i => i.src || i.dataset.src || '')")
            except Exception:
                continue
            ys = [x.split("&preload")[0] for x in srcs if "yuja.com/V/Video" in x]
            ys = [x for x in ys if x not in seen]  # a previous lesson's player can linger in the DOM: only a new video counts
            if re.search(rf"LESSON {k} OF", txt, re.I) and ys:
                vid = ys[-1]
                break
            if re.search(rf"LESSON {k} OF", txt, re.I) and not srcs:  # text-only lesson: no player is coming
                quiet += 1
                if quiet >= 6:
                    break
        seen.add(vid)
        try:  # diagrams and templates are images (the lesson text alone loses them): keep the URL and alt text of each real picture
            imgs = fr.evaluate("() => [...document.querySelectorAll('main img, [role=main] img')].filter(i => i.naturalWidth >= 120).map(i => [i.currentSrc || i.src, i.alt || ''])")
        except Exception:
            imgs = []
        try:  # templates and references are links inside the lesson (not the menu's #/lessons/ ones)
            links = fr.evaluate("() => [...document.querySelectorAll('main a[href], [role=main] a[href]')].map(a => [a.innerText.trim() || a.getAttribute('aria-label') || '', a.href]).filter(x => !x[1].includes('#/') && !x[1].startsWith('javascript'))")
        except Exception:
            links = []
        out.append({"lesson": n, "text": txt, "video": vid, "images": imgs, "links": links})
    return out


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
    if cmd == "mode":  # mode show|headless: not tied to a school, `base` holds the setting here
        if base not in ("show", "headless"):
            sys.exit("usage: bs.py mode show|headless")
        save_settings(headless=(base == "headless"))
        return print("browser windows will be " + ("hidden (headless)" if base == "headless" else "shown while scripts run"))
    with sync_playwright() as p:
        if cmd == "login":
            c = ctx(p, headless=False)
            # the script's window looks like normal Chrome: label it so people sign in HERE, not in their own Chrome
            c.add_init_script("document.addEventListener('DOMContentLoaded',()=>{const b=document.createElement('div');"
                              "b.textContent='brightspace-notes: sign in in THIS window (not your normal Chrome). It closes by itself when done.';"
                              "b.style.cssText='position:fixed;top:0;left:0;right:0;z-index:2147483647;background:#e67e22;color:#fff;"
                              "font:600 15px sans-serif;padding:8px;text-align:center';document.documentElement.appendChild(b)})")
            pg = c.new_page()
            pg.goto(base)
            print("Log in (incl. MFA) in the browser window; waiting up to 10 min...", flush=True)
            host = base.split("//")[1]
            def urls():  # live address of every tab (x.url alone goes stale unless Playwright is pumped)
                out = []
                for x in c.pages:
                    try:
                        out.append(x.evaluate("location.href"))
                    except Exception:
                        pass
                return out

            for _ in range(300):  # no stdin under agents: wait until SSO lands back on Brightspace's home
                pg.wait_for_timeout(2000)  # not time.sleep: it blocks Playwright's event loop
                # any tab: sign-in may finish in another one. /d2l/login (schools with a local login form) is not "in" yet
                if any(host in u and "/d2l/" in u and "login" not in u.lower() for u in urls()):
                    STATE.write_text(json.dumps(c.cookies()))
                    save_settings(base=base)
                    print("logged in, session saved", flush=True)
                    break
            else:
                print(f"not signed in after 10 minutes; run again: python scripts/bs.py login {base}", flush=True)
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
            intros = module_intros(root)
            (out / "module-intros.md").write_text(f"# Module introduction pages: {root['properties']['title']}\n\n" + "\n\n".join(
                f"## {t} ({a})\n\n{d}" for t, a, d in intros) + "\n", encoding="utf-8")
            print(f"wrote {out / 'toc.md'} and module-intros.md ({len(intros)} module descriptions)")
        elif cmd == "video":
            ou, aid, outdir = a
            def find(c):
                pg, net, _ = open_activity(c, base, ou, aid, player=True)
                x = type("Ctx", (), {"pg": pg, "c": c, "net": net})()
                return pg, next((h for ad in hosts.ADAPTERS if (h := ad(x))), None)

            pg, hit = find(c)
            title = pg.title()
            if not (hit and hit["source"]) and not settings().get("headless", False):
                # some players never start in a visible window (seen with YuJa): retry hidden once
                print("no stream found in the visible window; retrying hidden (headless)...", flush=True)
                c.close()
                c = ctx(p, headless=True)
                pg, hit = find(c)
            if not hit:
                log_capture(ou, aid, "video", False, reason="no video found", dir=outdir)
                sys.exit("no video found on this topic (is it a file/quiz/link?)")
            o = Path(outdir)
            o.mkdir(parents=True, exist_ok=True)
            for name, text in hit["subs"].items():
                if text.strip():  # an empty caption file would stop video.py: no subs means it transcribes the audio instead
                    (o / name).write_text(text, encoding="utf-8")
            (o / "source.txt").write_text(hit["source"])
            if hit["host"] == "embed":  # yt-dlp needs the login cookies to open these
                write_cookies(c)
            log_capture(ou, aid, "video", bool(hit["source"]), title=title, host=hit["host"], subs=list(hit["subs"]), dir=str(o))
            print(json.dumps({"title": title, "host": hit["host"], "subs": list(hit["subs"]), "source": bool(hit["source"]), "dir": str(o)}))
        elif cmd == "course":
            ou, aid, outdir = a
            les = course_lessons(c, base, ou, aid)
            o = Path(outdir)
            o.mkdir(parents=True, exist_ok=True)
            for k, l in enumerate(les, 1):  # save each lesson's pictures beside lessons.json: images/<lesson no>-<n>.<ext>
                for j, (u, _alt) in enumerate(l.get("images", []), 1):
                    r = c.request.get(u)
                    if r.ok:
                        (o / "images").mkdir(exist_ok=True)
                        ext = (r.headers.get("content-type", "image/png").split("/")[-1].split(";")[0] or "png").replace("jpeg", "jpg").replace("svg+xml", "svg")
                        (o / "images" / f"{k:02d}-{j}.{ext}").write_bytes(r.body())
                        l["images"][j - 1].append(f"images/{k:02d}-{j}.{ext}")
            (o / "lessons.json").write_text(json.dumps(les, indent=1), encoding="utf-8")
            log_capture(ou, aid, "course", bool(les), lessons=len(les), videos=sum(bool(l["video"]) for l in les), dir=str(o))
            print(json.dumps([{"lesson": l["lesson"], "video": l["video"]} for l in les], indent=1))
        elif cmd == "yuja":  # a direct sp.video.yuja.com link (e.g. listed on a page), no Brightspace launch needed
            url, outdir = a
            pg, net = c.new_page(), []
            pg.on("response", lambda r: net.append((r.url, r)))
            pg.goto(url.split("&preload")[0], wait_until="domcontentloaded")
            time.sleep(5)
            vs = pg.viewport_size or {"width": 1280, "height": 720}
            for i in range(60):  # a direct link doesn't autoplay: the player only asks for its stream after the big play button is clicked
                if any("/P/Data/VideoSource" in u or "youtube.com/embed/" in u for u, _ in net):
                    break
                if i % 10 == 0:
                    pg.mouse.click(vs["width"] / 2, vs["height"] / 2)
                time.sleep(0.5)
            x = type("Ctx", (), {"pg": pg, "c": c, "net": net})()
            hit = hosts.yuja(x)
            yt = next((re.search(r"youtube\.com/embed/([\w-]{11})", u) for u, _ in net if "youtube.com/embed/" in u), None)
            if (not hit or not hit["source"]) and yt:  # YuJa page wrapping a YouTube video: video.py hands it to yt-dlp
                hit = {"host": "yuja-youtube", "source": f"https://www.youtube.com/watch?v={yt.group(1)}", "subs": {}}
            if not hit or not hit["source"]:
                sys.exit("no stream found at that link")
            o = Path(outdir)
            o.mkdir(parents=True, exist_ok=True)
            for name, text in hit["subs"].items():
                if text.strip():  # an empty caption file would stop video.py: no subs means it transcribes the audio instead
                    (o / name).write_text(text, encoding="utf-8")
            (o / "source.txt").write_text(hit["source"])
            print(json.dumps({"title": pg.title(), "subs": list(hit["subs"]), "dir": str(o)}))
        elif cmd == "doc":
            ou, aid, outdir = a
            pg, _, act = open_activity(c, base, ou, aid)
            links = file_links(act)
            if not links:
                log_capture(ou, aid, "doc", False, reason="no downloadable file", dir=outdir)
                sys.exit("no downloadable file on this topic (not a file-activity?)")
            href, name = links[0]
            r = c.request.get(href)
            if not r.ok:
                sys.exit(f"download failed: HTTP {r.status}")
            o = Path(outdir)
            o.mkdir(parents=True, exist_ok=True)
            # the name comes from the server: keep a plain file name (no folders, no characters Windows forbids)
            f = o / (re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name or unquote(href.split("?")[0].rsplit("/", 1)[-1])).strip(" .") or "download")
            f.write_bytes(r.body())
            log_capture(ou, aid, "doc", True, file=str(f), bytes=f.stat().st_size, dir=str(o))
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


ARGS = {"login": 0, "toc": 1, "video": 3, "doc": 3, "page": 2, "course": 3, "yuja": 2, "cookies": 0, "mode": 0}  # arguments after <base>

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) - 3 != ARGS.get(sys.argv[1]):
        sys.exit(__doc__)
    main(*sys.argv[1:])
