"""Video host adapters for `bs.py video`.

An adapter takes a Ctx `x` (x.pg page, x.c browser context, x.net list of (url, response) seen so far)
and returns None if the page isn't its host, else
    {"host": name, "source": url-for-video.py, "subs": {filename: text}}
Adapters run in ADAPTERS order; the first hit wins. To add a host see CONTRIBUTING.md.
"""
import re
import time


def safe_json(r):
    try:
        return r.json()
    except Exception:
        return None


def yuja(x):
    """YuJa: the player's own VideoSource JSON lists the HLS stream and the caption file. TESTED."""
    fr = next((f for f in x.pg.frames if "yuja.com/V/Video" in f.url), None)
    if not fr:
        return None
    urls = [u for u, _ in x.net if "/P/Data/VideoSource" in u]
    j = {}
    for u in reversed(urls):  # newest first: earlier ones belong to a frame navigation that was replaced
        try:
            j = fr.evaluate("u => fetch(u).then(r => r.json())", u)  # re-fetched in the player's own frame (bodies of seen responses are gone)
            break
        except Exception:
            continue
    cap = [v for v in j.get("captionURL", {}).values() if isinstance(v, str) and v.endswith(".srt")][:1]
    hls = next(iter((j.get("streams") or [{}])[0].get("typeAndVideoSourceMap", {}).values()), {})
    subs = {"video.en.srt": fr.evaluate("u => fetch(u).then(r => r.text())", cap[0])} if cap else {}
    return {"host": "yuja", "source": hls.get("fileURL", ""), "subs": subs}


EMBED = re.compile(r"youtube(-nocookie)?\.com/embed|player\.vimeo\.com|panopto\.(com|eu)|kaltura\.com|echo360\.", re.I)


def embed(x):
    """Known embeddable players: hand the frame URL to yt-dlp (it fetches video + subs). UNTESTED."""
    f = next((f for f in x.pg.frames if EMBED.search(f.url)), None)
    return {"host": "embed", "source": f.url, "subs": {}} if f else None


def sniff(x):
    """Last resort: press play, then take the first manifest/mp4 and caption files the page requested. UNTESTED."""
    for f in x.pg.frames:
        try:
            f.evaluate("() => document.querySelectorAll('video').forEach(v => { v.muted = true; v.play().catch(() => {}); })")
        except Exception:
            pass
    time.sleep(5)
    media = [u for u, _ in x.net if re.search(r"\.(m3u8|mpd|mp4)(\?|$)", u)]
    if not media:
        return None
    caps = [u for u, _ in x.net if re.search(r"\.(vtt|srt)(\?|$)", u)]
    subs = {}
    for i, u in enumerate(caps[:3]):
        r = x.c.request.get(u)
        if r.ok:
            subs[f"video.{i}{'.srt' if '.srt' in u else '.vtt'}"] = r.text()
    return {"host": "sniffed", "source": media[0], "subs": subs}


ADAPTERS = [yuja, embed, sniff]
