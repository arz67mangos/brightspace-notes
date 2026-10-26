# brightspace-notes

A Claude Code skill that turns the Brightspace (D2L) course material **you are enrolled in** into revision notes (`notes/<course>/<module>/<topic>.md`) that you, or another Claude agent, can revise from.

It only fetches what you ask for: it lists the course outline, asks which modules/topics you want, and processes just those.

## What it does
- Logs in through a real browser window you sign into yourself (SSO/MFA works). Your password is never seen by the scripts.
- Lists the course outline (modules, topics, IDs).
- For videos: pulls the soft-subtitle transcript, and grabs keyframes at slide changes so Claude can read slides, diagrams and hard-subbed text.
- Claude then writes a dense note per topic: key ideas, details, exam points, self-check questions, gaps.

## Setup
Requires Python 3, ffmpeg on PATH, and [Claude Code](https://claude.com/claude-code).

```bash
pip install yt-dlp playwright webvtt-py faster-whisper
python -m playwright install chromium
```

Open Claude Code in this folder (the skill in `.claude/skills/brightspace-notes/` loads automatically) and say, for example:

> Make revision notes for Topic 2 and 3 of my course at https://YOUR-SCHOOL.brightspace.com/d2l/home/123456

It will run `scripts/bs.py login`, open Chromium for you to sign in, show the outline and ask which topics you want.

## Scripts
- `scripts/bs.py login|toc|video|page|cookies` - login, outline, YuJa video captions + stream URL, page dump, cookie export.
- `scripts/video.py` - transcript from captions + ffmpeg keyframes (scene change, at least one per 45 s).

## Limits
- Video fetching (`bs.py video`) is built for **YuJa** players and tested on one institution (Microsoft SSO). Other players (Panopto, Kaltura, YouTube) work through `video.py` with a URL you find, but need a little manual help; PRs welcome.
- Captions are usually auto-generated: expect small errors in terms and names. Videos with no captions are transcribed locally with faster-whisper (slower, and jargon gets misheard: use `--whisper-model small.en`).
- Opening a topic marks it as viewed in Brightspace.

## Please be responsible
Use only courses you're enrolled in. Notes derive from your institution's material: keep them for personal study (`notes/` is gitignored) and don't redistribute course content. `.profile/` holds your login session: never share or commit it.

MIT licensed.
