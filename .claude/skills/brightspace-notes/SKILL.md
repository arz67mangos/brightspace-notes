---
name: brightspace-notes
description: Read and navigate a Brightspace (D2L) course, watch its videos via subtitles + scene-change keyframes, and write revision notes as .md files per module. Use when the user asks to capture, summarise, or make revision notes from Brightspace/e-learning material or lecture videos.
---

# Brightspace -> revision notes

Repo root = the folder containing `scripts/` and `notes/`. Run all commands from it. Notes go to `notes/<course>/<module>/<topic>.md`.

## 0. Setup (once)
- `pip install yt-dlp playwright webvtt-py faster-whisper && python -m playwright install chromium`; `ffmpeg` on PATH.
- `python scripts/bs.py login <base-url>` — opens Chromium; the user logs in manually (SSO/MFA). The script detects the Brightspace home page, saves the session to `.profile/` (gitignored) and exits by itself. Run it in the background; re-run when the session expires.

## 1. Navigate
**Scope first, never crawl everything.** Ask the user for the Brightspace base URL (e.g. `https://school.brightspace.com`) and course, or the topic/module they want (a pasted course URL contains the orgUnitId: `/d2l/home/<id>`). Run `toc` (cheap, one request), show the module list, and ask which modules or topics they want (AskUserQuestion, multi-select). Process only those. Skip quizzes, surveys, assignment dropboxes, group lists, external links and anything not asked for. Re-use existing `notes/*/toc.md` instead of re-fetching.
- **Scripted (fast, bulk):** `python scripts/bs.py toc <base> <ou>` writes `notes/<ou>/toc.md`: every module and topic with its activity ID and kind (`link-activity` = usually a YuJa video or quiz, `file-activity` = document). The `/d2l/api/le/.../content/toc` API is 403 for students, so this uses the Lessons sequence API the page itself calls.
- **Session expired / redirected to login.microsoftonline.com?** Re-run `python scripts/bs.py login <base>`: a Chromium window opens, the user signs in (MFA), the script saves cookies to `.profile/cookies.json` and exits by itself. Always run it in the background and tell the user to sign in.
- **Claude in Chrome (interactive):** use the `chrome-browser` skill for one-off pages or when the scripted route breaks.

Documents (`file-activity`): open `{base}/d2l/le/enhancedSequenceViewer/<ou>?url=https%3A%2F%2F<host>%2F<ou>%2Factivity%2F<id>%3FfilterOnDatesAndDepth%3D1` (host is in `.profile/seq.json`) or use Chrome, download, then read with the PDF skill. Save originals under `work/`, not `notes/`.

## 2. Videos
`bs.py video` is written for **YuJa** players (tested at one institution). Other hosts (Panopto, Kaltura, YouTube...): find the video/caption URL with the generic route in step 5, then run `video.py` on it.
1. `python scripts/bs.py video <base> <ou> <activityId> work/<slug>` → `video.en.srt` (YuJa's soft-subtitle file, usually auto-generated, so expect small errors in terms; this works for videos with no hard subs) + `source.txt` (signed HLS .m3u8, expires in about an hour). Opening a topic marks it viewed in Brightspace.
2. `python scripts/video.py "$(cat work/<slug>/source.txt)" work/<slug>` → `transcript.md` (timestamped) + `frames/*.jpg` at scene changes + `frames.txt` (times). Raise `--scene` (0.15) if too many frames, lower (0.05) if slides are missed. Other hosts: pass any URL/file; `--cookies cookies.txt` (from `bs.py cookies`) for auth-gated hosts.
3. **Read `transcript.md` first**, then **view the frames** (Read tool on the jpgs) for slide text, diagrams, code, formulas, and hard-sub text the transcript lacks. Match frames to transcript by timestamp.
4. No subtitle file at all: `video.py` automatically transcribes the audio with faster-whisper (CPU, `base.en`; first run downloads the model). It mishears jargon ("demand" -> "D-man"), so pass `--whisper-model small.en` for coursework and cross-check terms against the slide frames.
5. Host not supported by yt-dlp (custom player): in Chrome, `read_network_requests` for `.m3u8/.mp4/.vtt` URLs and feed those to `video.py`. Soft subs often appear as a `.vtt` request when captions are toggled on.

## 3. Write the note
One file per topic, this shape (keep it dense; the note is for revision and for other agents to consume):

```
---
course: <name>
module: <name>
topic: <title>
source: <brightspace url> (+ video url)
captured: <YYYY-MM-DD>
---
# <Topic>
## Key ideas        (bullets, definitions in own words)
## Details          (formulas, code, diagrams-as-text, worked examples; cite [mm:ss] for video claims)
## Likely exam/test points
## Self-check questions (5-10 Q&A)
## Gaps              (what was unreadable/missing: no subs, blurry frame, etc.)
```

Then update `notes/<course>/INDEX.md` (one line per note: link + 1-sentence summary). Never invent content not in the transcript/frames/pages; put unknowns under Gaps.

## 4. Revision
Point an agent at `notes/<course>/<module>/` and ask it to quiz from "Self-check questions" or explain from "Key ideas".

## Rules
- Only access courses the user is enrolled in; don't bulk-redistribute material. `.profile/` and `cookies.txt` are credentials — never commit or print them.
- Ask before downloading large files in bulk; work module by module.
