# AGENTS.md

Source of truth for any coding agent (Codex, Claude Code, others) working in this repo. `CLAUDE.md` only imports this file. Skills are authored in `.claude/skills/` and copied to `.agents/skills/` by `python scripts/sync_agents.py`.

## What this is
**course-capture-agent**: a toolkit that lets an agent sign in to a student's own Brightspace (D2L) through a Playwright browser, capture the course material they choose (lecture videos as subtitles + one frame per distinct slide, documents, pages) and build a private per-course study set under `notes/<course>/` (notes, `MASTER.md`, `TIMELINE.md`, quizzes, tutorial drafts). The user drives it in plain language; the skills hold the workflows, the scripts do the mechanical work.

## Skills (`.agents/skills/`, same files in `.claude/skills/`): pick the one that fits
| Skill | Use when |
|---|---|
| `brightspace-setup` | first time on this machine: nothing installed yet, never logged in |
| `brightspace-check` | an existing install stopped working ("check my setup") |
| `course-capture` | the main workflow: outline, capture videos/docs, write notes, verify coverage, MASTER.md/TIMELINE.md |
| `course-audit` | "check everything for new or missed content": diff the outline, capture gaps, fix failures |
| `study-hub` | "what's due, what do I need to do by when, remind me": deadlines across all courses |
| `brightspace-quiz` | quiz help from the notes, self-tests, question bank, weak spots |
| `brightspace-tutorial` | draft answers to a tutorial sheet from the notes |

If the repo is freshly cloned and the user asks for anything, run `python scripts/doctor.py` first; if most checks fail, follow `brightspace-setup`.

## The standard workflow (do not shortcut it)
The output must be the full study set, not a chat summary of what you found. A capture is not done until every item below exists on disk.
1. **Scope**: `bs.py toc`, show the modules, ask which to capture.
2. **One thread per course.** Each course gets its own agent thread/session that starts from `docs/course-session-kickoff.md` and reads that course's `notes/<course>/MASTER.md` first. Never mix courses in one thread. Claude Code can start these sessions itself; in Codex the user opens one thread per course and pastes the kickoff prompt.
3. **One folder per scrape.** Each video/document/page gets its own folder: downloads in `work/<slug>/`, converted output in `notes/<course>/<module>/assets/<slug>/` (`slides.md`, `sheets/`, `frames/`, `transcript.md`, `frames.txt` for video). Never summarise from memory or from the page text alone; the files are the evidence.
4. **One note per topic** from the template in `course-capture`, with `[mm:ss]` cites linked by `linkify.py`.
5. **Verify**: `verify.py` -> `COVERAGE.md`; fix every flagged item or list it under Gaps; report the headline numbers.
6. **Refresh the course context**: `rollup.py`, `master.py`, then `TIMELINE.md`. `master.py` writes the Parked / Reminders rule into `MASTER.md`.
7. **Report** what was captured, what failed or was skipped, and where `MASTER.md` and `TIMELINE.md` are. A final answer that is only a summary of findings, with no files written, means the workflow was not followed.

**Parked / Reminders (every thread):** when the user says to hold something off or to remind them, add it to a running "Parked / Reminders" list (per course in a course thread) and repeat the whole list at the end of every reply until they finish or drop it.

## Rules that are not negotiable
- **Scope first, never crawl everything.** Process only the modules/topics the user picked. Opening a topic marks it viewed in Brightspace.
- **Never start, attempt or submit a quiz, survey or assignment**, and never click anything that records a result. Quiz help works only from text the user pastes.
- **Unfamiliar page types** (interactive games, multi-page courses, anything not covered in `course-capture` section 3b): stop, describe it, give 2-3 options with a recommendation, wait for the answer.
- **Never ask for, type or handle the user's password.** `bs.py login` opens a window and the user signs in themselves.
- **Private data stays local:** `notes/`, `.profile/` (login session, cookies, config), `work/`, `cookies.txt`, `*.tsv` are gitignored and the pre-commit hook (`.githooks/pre-commit`, enabled by `git config core.hooksPath .githooks`) blocks them. Never commit, publish or upload notes or course material, never use `--no-verify`, never `git add -f` those paths.
- Never put a real school URL, course id, name or email in committed files; use placeholders like `https://YOUR-SCHOOL.brightspace.com` and `123456`.

## Commands (run from the repo root; `py`/`python3` if `python` isn't found; `.venv/bin/python` if a `.venv/` exists)
```
python scripts/doctor.py [--json]                   setup check (exit 1 if a required item is missing)
python scripts/bs.py login   <base>                 user signs in; saves .profile/cookies.json + config.json
python scripts/bs.py toc     <base> <ou>            outline -> notes/<ou>/toc.md, module-intros.md
python scripts/bs.py video   <base> <ou> <aid> <dir>   captions + source.txt (signed stream URL, ~1 h)
python scripts/video.py "$(cat <dir>/source.txt)" <dir> [--cookies cookies.txt] [--sim 0.02]
python scripts/bs.py doc     <base> <ou> <aid> work/<slug>
python scripts/docs.py <file> <dir> [--images]      pdf/docx/pptx/html/zip -> markdown (+ page images)
python scripts/bs.py page    <base> <ou> <topicId>  page text/iframes/links as JSON
python scripts/bs.py course  <base> <ou> <aid> <dir> multi-lesson SCORM/Rise course -> lessons.json (text + video URL per lesson)
python scripts/bs.py yuja    <base> <url> <dir>      captions + source.txt for a direct YuJa link
python scripts/bs.py mode    show|headless          visible browser (default) or hidden
powershell -File scripts/ocr.ps1 <pages-dir> <out.md>  Windows OCR over page images (scanned/garbled PDFs)
python scripts/linkify.py <note.md>                 [mm:ss] cites -> links to slide frames
python scripts/verify.py <ou> notes/<course>        -> notes/<ou>/COVERAGE.md (exit 1 if attention needed)
python scripts/rollup.py notes/<course>             EXAM_FOCUS.md, GLOSSARY.md, per-module CHEATSHEET.md
python scripts/master.py notes/<course> --ou <ou>   MASTER.md (agents read it first when revising)
python scripts/anki.py notes/<course>               -> notes/<course>/anki-cards.tsv
python scripts/mdtodocx.py <filled.md>              filled course-book .md -> .docx (answers in blue)
python scripts/graph.py <preset>                    text graph (supply/demand shifts, PPC, AD-AS) for tutorial answers
python scripts/sync_agents.py [--check]             copy .claude/skills -> .agents/skills; --check exits 1 on drift
```
`<base>` = `https://<school-host>` (no path); `<ou>` = course id, the number in `/d2l/home/<ou>`; `<aid>` = activity id from `toc.md`. Every script except `doctor.py` prints its usage when run with no arguments.

There is no test suite. Before committing code changes: `python -m py_compile scripts/*.py`, `python scripts/doctor.py`, `python scripts/sync_agents.py --check`, and one real topic end to end if the change touches capture. Keep scripts small, dependency-light, in the existing terse style.

## Outputs
- `notes/<ou>/`: `toc.md`, `module-intros.md`, `capture-log.jsonl` (every `bs.py video/doc` attempt), `COVERAGE.md`.
- `notes/<course>/<module>/<topic>.md`: one note per topic (front matter with `video:` lines, then Key ideas / Details / Likely exam/test points / Self-check questions as `N. Question? *answer*` / Gaps). Media per topic in `notes/<course>/<module>/assets/<slug>/`.
- `notes/<course>/`: `INDEX.md`, `MASTER.md`, `TIMELINE.md`, `GLOSSARY.md`, `EXAM_FOCUS.md`, `question-bank.md`, `progress.md`.
- `work/`: scratch downloads. `cookies.txt` (repo root): yt-dlp cookies for embedded players; delete after use.

## Architecture (the parts that span files)
- **`scripts/env.py`** is imported first by every script: forces UTF-8 stdout/stderr (Windows pipes default to cp1252 and crash on non-ASCII titles) and on Windows merges the registry PATH so tools installed by winget mid-session are found. New scripts should `import env` too.
- **Login/session (`bs.py`)**: one persistent Chromium profile in `.profile/` (only one browser script at a time); SSO cookies are session-only so they are also saved to `.profile/cookies.json` and re-added on every launch. Visible mode prefers installed Chrome (H.264) and disables occlusion throttling, because hidden or background windows freeze video players. The login window shows an orange "Course Capture Agent" bar so the user signs in there and not in their normal Chrome.
- **Outline**: students get 403 on the D2L content API, so `toc` loads the Lessons page, captures the bearer token from its `sequences.api` request, and walks the sequence JSON. The sequence host is cached in `.profile/seq.json`; `video`/`doc` need it, so `toc` must run once first.
- **Video capture** is two steps: `bs.py video` opens the topic, waits for the LTI player, then runs the adapters in `scripts/hosts.py` (`ADAPTERS = [yuja, embed, sniff]`, first hit wins) which return `{host, source, subs}`. If the visible window finds no stream it retries headless once. `video.py` then downloads via yt-dlp (URLs other than m3u8) or reads the manifest with ffmpeg, samples a frame every `--step` s, keeps a frame when its dHash (bottom 14% ignored) differs by more than `--sim`, and aligns subtitle lines to slides. No subtitles -> faster-whisper. Only YuJa is tested; adding a host = one function in `hosts.py` (see CONTRIBUTING.md).
- **Notes pipeline**: notes cite `[mm:ss]`; `linkify.py` maps them via `frames.txt` to frame links. `rollup.py`, `master.py` and `anki.py` parse notes by front matter (`---` block) and `## Section` headings, so keep the note template from `course-capture` exactly. `verify.py` joins `toc.md` with `capture-log.jsonl` (and infers older captures from note front matter).

## Known limits
Non-YuJa adapters and `install.sh` are untested; `.pptx` gives text only without LibreOffice; YouTube needs Deno and `yt-dlp[default]`; the outline covers Lessons only (not Assignments, Quizzes, Discussions, Media Library, or unreleased items).
