# Contributing

Thanks for helping. The most useful contribution is **a video host adapter** for the player your school uses.

## Adding a video host adapter

`bs.py video` opens a topic in a logged-in headless browser, then runs the functions in `ADAPTERS` (`scripts/hosts.py`) in order. The first one that recognises the page wins.

An adapter is one function:

```python
def myhost(x):
    # x.pg  = Playwright page (x.pg.frames lists every iframe, with .url)
    # x.c   = browser context (x.c.request.get(url) is an authenticated HTTP client)
    # x.net = [(url, response), ...] of everything the page requested so far
    frame = next((f for f in x.pg.frames if "myhost.com/player" in f.url), None)
    if not frame:
        return None                      # not my host
    ...                                  # find the stream URL and the caption text
    return {"host": "myhost",
            "source": "https://.../index.m3u8",          # anything ffmpeg or yt-dlp can open
            "subs": {"video.en.srt": "<srt or vtt text>"}}   # {} if the host has no captions
```

then add it to `ADAPTERS` **before** `sniff` (the generic last resort).

How to find the URLs for a new host: open the topic in Chrome, DevTools > Network, press play, turn captions on, and look for `.m3u8` / `.mp4` (stream) and `.vtt` / `.srt` / `caption` (subtitles). The caption URL often appears in a JSON response next to the stream URL, which is how the YuJa adapter works.

Rules for a good adapter:
- Return `None` quickly when the page isn't yours.
- Don't download the video yourself; `video.py` does that from `source`.
- Mark it `TESTED` or `UNTESTED` in its docstring, and say which school/version you tested on.
- Never print or store cookies/tokens anywhere except the existing gitignored files.

## Other changes
- Keep scripts small and dependency-light; no new package unless a few lines can't do it.
- Run `python scripts/doctor.py` and a real topic end to end before opening a PR.
- **Never commit** anything from `notes/`, `.profile/`, `work/` or `cookies.*`. The pre-commit hook (`.githooks/`) blocks it; don't bypass it. Screenshots or sample output in PRs must be from material you're allowed to share.
