---
name: brightspace-notes
description: Read and navigate a Brightspace (D2L) course, capture its lecture videos (subtitles + one frame per slide) and documents, and write revision notes as .md files per topic with timestamp-linked slide references. Use when the user asks to capture, summarise, or make revision notes from Brightspace/e-learning material or lecture videos.
---

# Brightspace -> revision notes

Repo root = the folder containing `scripts/` and `notes/`. Run everything from it. Notes: `notes/<course>/<module>/<topic>.md`; each topic's captured media: `notes/<course>/<module>/assets/<slug>/` (all gitignored).
Related skills: `brightspace-tutorial` (answer tutorial sheets from the notes), `brightspace-quiz` (quiz the user from the notes).

## 0. Setup
- First time / something broken: `python scripts/doctor.py` prints exactly what's missing and the fix. `install.ps1` (Windows) / `install.sh` (Mac/Linux) set everything up.
- `python scripts/bs.py login <base-url>`: opens Chromium, the user signs in (SSO/MFA), the script saves the session and exits by itself. Run it in the background and tell the user to sign in. Re-run when the session expires (symptom: redirect to a login page).

**Browser window:** by default the scripts open a visible Chromium window so the user can watch. The first time you run a browser script in a session, tell the user once: "A browser window will open so you can watch; if you'd rather it ran hidden, say 'switch to headless mode'." When they ask to hide it run `python scripts/bs.py mode headless`; to show it again run `python scripts/bs.py mode show`. Don't touch the window while a script runs. The login window is always visible.

## 1. Scope first: never crawl everything
Ask for the base URL and course (or topic). A pasted course URL contains the orgUnitId (`/d2l/home/<id>`). Run `python scripts/bs.py toc <base> <ou>` (one request, writes `notes/<ou>/toc.md` with every module/topic, its activity ID, and kind), show the modules, and ask which ones they want (AskUserQuestion, multi-select). Process only those.
- **Never open, fetch or answer anything quiz-like**: quizzes, prep quizzes, surveys, assignment dropboxes. The user does those themselves. Also skip group lists, external links, anything not asked for.
- Reuse an existing `toc.md` instead of re-fetching. `link-activity` = usually a video (or a quiz: check the title), `file-activity` = a document.
- Interactive alternative or when scripts break: Claude in Chrome (`chrome-browser` skill).

## 2. Videos
1. `python scripts/bs.py video <base> <ou> <activityId> notes/<course>/<module>/assets/<slug>`: finds the player through the adapters in `scripts/hosts.py` (YuJa is tested; YouTube/Vimeo/Panopto/Kaltura embeds and generic sniffing are untested), writes the caption file and `source.txt` (signed stream URL, expires in about an hour).
2. `python scripts/video.py "$(cat <dir>/source.txt)" <dir>` then delete `source.txt`. Produces:
   - `slides.md`: one section per distinct slide: frame link + the narration said while it was on screen. **Start here.**
   - `sheets/sheetNN.jpg`: contact sheets of 4 slides each, labelled `#n mm:ss`. **Read these to see every slide cheaply**, then open single `frames/` jpgs for small print, graphs and tables.
   - `transcript.md`, `frames.txt` (file, start, end, sheet cell).
   - Slides are not missed: the video is sampled every 2 s and a frame kept whenever the picture changes (captions at the bottom are ignored). If bullets appearing one at a time are being missed, rerun with `--sim 0.02`; if too many near-duplicates, `--sim 0.06`. Topics with 2+ videos: one asset folder each.
3. Subtitles: soft subs are used when they exist. If a video has none, `video.py` transcribes the audio with faster-whisper (`--whisper-model small.en` is better for coursework).
4. **Fix transcript errors**: captions are ASR. Cross-check every term against the slide text in the frames (and the lecture-notes document if captured). Correct the term in the note and list the correction under Gaps (e.g. "demand" misheard as "D-man"). Treat lines that contradict the slide as ASR errors.
5. Other hosts: if `bs.py video` finds nothing, see CONTRIBUTING.md (add an adapter) or in Chrome use `read_network_requests` to find the `.m3u8/.mp4/.vtt` URLs and pass them to `video.py`.

## 3. Documents (`file-activity`)
`python scripts/bs.py doc <base> <ou> <activityId> work/<slug>` downloads the file; then `python scripts/docs.py <file> notes/<course>/<module>/assets/<slug>` converts pdf/docx/pptx/zip to markdown (+ page images for scanned/diagram pages, or all pages with `--images`). Read the `.md`; view page images for diagrams. Lecture-notes documents are the authority for terminology and model diagrams. Don't answer assessed/quiz-like material.

## 4. Write the note
One file per topic. Front matter lists the videos so citations can be turned into frame links:

```
---
course: <name>
module: <name>
topic: <title>
source: Brightspace activity <id>
captured: <YYYY-MM-DD>
video: P1 | Part 1 Law of Demand | assets/part1
---
# <Topic>
## Key ideas        (bullets; **bold** each key term: they feed GLOSSARY.md)
## Details          (formulas, worked examples, diagrams as text; cite the video time: [02:10] or [02:10-02:40])
## Likely exam/test points
## Self-check questions
1. Question? *Short answer*
## Gaps              (ASR corrections, unreadable frames, anything not captured)
```
- Cite video times as `[mm:ss]` / `[mm:ss-mm:ss]`; with 2+ videos in the note write `[P2 02:10]`. Then run `python scripts/linkify.py <note.md>`: each cite becomes a link to the slide on screen at that time (`[Part 1 @02:10](assets/part1/frames/f003_...jpg)`), so the user can jump back to the slide.
- Self-check questions MUST be `N. Question? *answer*` (answer in italics, last): that is what `anki.py` exports.
- Never invent content that isn't in the transcript/frames/documents. Unknowns go under Gaps.
- Update `notes/<course>/INDEX.md` (one line per note).

## 5. Revision outputs (on request)
- `python scripts/rollup.py notes/<course>` -> `EXAM_FOCUS.md` (all exam points), `GLOSSARY.md` (all bold terms), per-module `CHEATSHEET.md`. Offer to tighten a cheat sheet into a one-page summary.
- `python scripts/anki.py notes/<course> anki-cards.tsv` -> import in Anki (File > Import).
- Quizzing and tutorial help: skills `brightspace-quiz` and `brightspace-tutorial`.

## Rules
- Only courses the user is enrolled in. Don't redistribute course material; `notes/`, `.profile/`, `cookies.*` and `work/` are personal and gitignored. Never print or commit credentials; don't bypass the pre-commit hook.
- Ask before downloading in bulk; work module by module. Opening a topic marks it viewed in Brightspace.
