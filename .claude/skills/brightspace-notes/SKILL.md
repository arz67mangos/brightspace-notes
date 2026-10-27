---
name: brightspace-notes
description: Read and navigate a Brightspace (D2L) course, capture its lecture videos (subtitles + one frame per slide) and documents, and write revision notes as .md files per topic with timestamp-linked slide references. Use when the user asks to capture, summarise, or make revision notes from Brightspace/e-learning material or lecture videos.
---

# Brightspace -> revision notes

Repo root = the folder containing `scripts/` and `notes/`. Run everything from it. Notes: `notes/<course>/<module>/<topic>.md`; each topic's captured media: `notes/<course>/<module>/assets/<slug>/` (all gitignored).
Related skills: `brightspace-tutorial` (answer tutorial sheets from the notes), `brightspace-quiz` (quiz the user from the notes).

## 0. Setup
- First time on this machine: follow the `brightspace-setup` skill (checks what's installed, asks before installing anything). Something broken later: `brightspace-check`. Both use `python scripts/doctor.py`, which prints exactly what's missing and the fix.
- `python scripts/bs.py login <base-url>`: opens Chromium, the user signs in (SSO/MFA), the script saves the session and exits by itself. Run it in the background and tell the user to sign in. Re-run when the session expires (symptom: redirect to a login page).

**Browser window:** by default the scripts open a visible Chromium window so the user can watch. The first time you run a browser script in a session, tell the user once: "A browser window will open so you can watch; if you'd rather it ran hidden, say 'switch to headless mode'." When they ask to hide it run `python scripts/bs.py mode headless`; to show it again run `python scripts/bs.py mode show`. Don't touch the window while a script runs. The login window is always visible.

## 1. Scope first: never crawl everything
Ask for the base URL and course (or topic). A pasted course URL contains the orgUnitId (`/d2l/home/<id>`). Run `python scripts/bs.py toc <base> <ou>` (one request, writes `notes/<ou>/toc.md` with every module/topic, its activity ID, and kind), show the modules, and ask which ones they want (AskUserQuestion, multi-select). Process only those.
- **Only capture what was asked for.** Skip quizzes, surveys, assignment dropboxes, group lists and external links unless the user asks (quizzes: they may want help with participation/pre-class quizzes or self-tests; see `brightspace-quiz`). Never submit, start a timed attempt, or click anything that records a result on the user's behalf.
- Reuse an existing `toc.md` instead of re-fetching. `link-activity` = usually a video (or a quiz: check the title), `file-activity` = a document.
- Interactive alternative or when scripts break: Claude in Chrome, if the user has it connected.

## 2. Videos
1. `python scripts/bs.py video <base> <ou> <activityId> notes/<course>/<module>/assets/<slug>`: finds the player through the adapters in `scripts/hosts.py` (YuJa is tested; YouTube/Vimeo/Panopto/Kaltura embeds and generic sniffing are untested), writes the caption file and `source.txt` (signed stream URL, expires in about an hour).
2. `python scripts/video.py "$(cat <dir>/source.txt)" <dir>` then delete `source.txt`. If step 1 printed `"host": "embed"`, add `--cookies cookies.txt` (written by step 1, gitignored; delete it when done). Produces:
   - `slides.md`: one section per distinct slide: frame link + the narration said while it was on screen. **Start here.**
   - `sheets/sheetNN.jpg`: contact sheets of 4 slides each, labelled `#n mm:ss`. **Read these to see every slide cheaply**, then open single `frames/` jpgs for small print, graphs and tables.
   - `transcript.md`, `frames.txt` (file, start, end, sheet cell).
   - Slides are not missed: the video is sampled every 2 s and a frame kept whenever the picture changes (captions at the bottom are ignored). If bullets appearing one at a time are being missed, rerun with `--sim 0.02`; if too many near-duplicates, `--sim 0.06`. Topics with 2+ videos: one asset folder each.
3. Subtitles: soft subs are used when they exist. If a video has none, `video.py` transcribes the audio with faster-whisper (`--whisper-model small.en` is better for coursework).
4. **Fix transcript errors**: captions are ASR. Cross-check every term against the slide text in the frames (and the lecture-notes document if captured). Correct the term in the note and list the correction under Gaps (e.g. "demand" misheard as "D-man"). Treat lines that contradict the slide as ASR errors.
5. Other hosts: if `bs.py video` finds nothing, see CONTRIBUTING.md (add an adapter) or in Chrome use `read_network_requests` to find the `.m3u8/.mp4/.vtt` URLs and pass them to `video.py`.

## 3. Documents (`file-activity`)
`python scripts/bs.py doc <base> <ou> <activityId> work/<slug>` downloads the file; then `python scripts/docs.py <file> notes/<course>/<module>/assets/<slug>` converts pdf/docx/pptx/zip to markdown (+ page images for scanned/diagram pages, or all pages with `--images`). Read the `.md`; view page images for diagrams. Lecture-notes documents are the authority for terminology and model diagrams.

## 3b. Topic types and how to handle each
**Slide decks (PDF/PowerPoint shown in Brightspace's viewer): never screenshot pages.** Download the file with `bs.py doc`, then `docs.py <file> <dir> --images` (text + page images; for `.pptx` without LibreOffice you get text only: say so, offer to install LibreOffice or to use the PDF version if one exists). Work from the text and look at page images only for diagrams.
**YouTube/Vimeo links** (a page that just lists video links): get the page's links (`docs.py` on the downloaded page, or `bs.py page`), then run `video.py <youtube-url> <dir>` per video: same transcript + slide-frame method (yt-dlp fetches the captions).
**Interactive games / activities** (drag-and-drop, simulations): the learning is in doing, so don't try to "scrape" a game. Read its instructions/text, note the concept it teaches, and ask the user how they'd like it handled (options: they play it and tell you what they saw; you open it visibly and screenshot the states; you only summarise the intro text). Never press submit/grade.
**Multi-page interactive courses** (navigate page by page with videos, slide notes and short self-test questions): **new situation: stop and ask first.** Describe what you see and give 2-3 options with your recommendation, for example: (a) step through each page with the browser and record text, embedded videos and self-test questions; (b) check whether the course package can be downloaded; (c) the user pages through while you read each page as they go.
**Any page type you don't recognise:** don't improvise. Tell the user what it is, give 2-3 options with your pick, and wait for the answer.

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

## 4b. Verify coverage (do this after every capture session)
`python scripts/verify.py <ou> notes/<course>` writes `notes/<ou>/COVERAGE.md`: every topic in the outline with its status (captured / FAILED / not captured, quiz-like ones labelled), and per capture the evidence: slide count, video length vs transcript range (flags transcripts that stop early or have long silent gaps), missing frames, documents downloaded but not converted, PDFs whose page count doesn't match, plus broken links, unlinked citations and self-check questions without answers in the notes. Fix whatever it flags, then tell the user the headline ("12 of 16 topics captured; 3 not requested; 1 failed: ...") and anything it can't see (other Brightspace tools; items not yet released). Every `bs.py video/doc` attempt is logged to `notes/<ou>/capture-log.jsonl` for this.

## 5. Revision outputs (on request)
- `python scripts/rollup.py notes/<course>` -> `EXAM_FOCUS.md` (all exam points), `GLOSSARY.md` (all bold terms), per-module `CHEATSHEET.md`. Offer to tighten a cheat sheet into a one-page summary.
- `python scripts/anki.py notes/<course>` -> `notes/<course>/anki-cards.tsv`, import in Anki (File > Import).
- Quizzes, self-tests and tutorial help: skills `brightspace-quiz` and `brightspace-tutorial`.

## 6. After every capture session: refresh the agent context
1. `python scripts/verify.py <ou> notes/<course>` (coverage), `python scripts/rollup.py notes/<course>` (exam focus, glossary, cheat sheets).
2. `python scripts/master.py notes/<course> --ou <ou>` writes `MASTER.md`: the file any agent reads first when revising (rules: answer only from the notes, cite them, say "not covered" instead of inventing; a topic map saying which note, key terms and source files hold each topic; a file tree).
3. Write or update `notes/<course>/TIMELINE.md` from the captured schedule, assessment and reminder pages (not the lecture notes): a table of **When | What | Type (lesson F2F/SDL, quiz, CA, presentation, submission, exam, other) | Weight | Source (link to the captured file) | What to prepare with (links to notes)**, plus a "Not stated / to confirm" list. Use only dates and weightings stated in those documents; if only a week number is given, show it as given (and the term start date if the schedule has it). Never guess a date. Mention the source file for every row. Reminder pages are read for dates only; never open or answer the quizzes they point to unless the user asks.
4. Tell the user what changed and where `MASTER.md` and `TIMELINE.md` are.

## Rules
- Only courses the user is enrolled in. Don't redistribute course material; `notes/`, `.profile/`, `cookies.*` and `work/` are personal and gitignored. Never print or commit credentials; don't bypass the pre-commit hook.
- Ask before downloading in bulk; work module by module. Opening a topic marks it viewed in Brightspace.
