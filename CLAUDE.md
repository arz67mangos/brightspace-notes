# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is
A toolkit that lets an agent sign in to a student's own Brightspace (D2L) through a Playwright browser, capture the course material they choose (lecture videos as subtitles + one frame per distinct slide, documents, pages) and write revision notes as `.md` files under `notes/<course>/`. The user drives it by asking in plain language; the workflows live in the skills below, the scripts do the mechanical work.

## Skills (`.claude/skills/`): pick the one that fits
| Skill | Use when |
|---|---|
| `brightspace-setup` | first time on this machine: nothing installed yet, never logged in. Detects, asks per item, installs only what's approved, guides first login |
| `brightspace-check` | an existing install stopped working ("check my setup") |
| `brightspace-notes` | the main workflow: outline, capture videos/docs, write notes, verify coverage, MASTER.md/TIMELINE.md |
| `brightspace-quiz` | quiz help from the notes, self-tests, question bank, weak spots |
| `brightspace-tutorial` | draft answers to a tutorial sheet from the notes |

If a user opens the repo fresh and asks for notes, run `python scripts/doctor.py` first; if most checks fail, follow `brightspace-setup` before anything else.

## Rules that are not negotiable
- **Scope first, never crawl everything.** Run `bs.py toc`, show the modules, ask which modules/topics to capture, process only those. Opening a topic marks it viewed in Brightspace.
- **Never start, attempt or submit a quiz, survey or assignment**, and never click anything that records a result. Quiz help works only from text the user pastes.
- **Unfamiliar page types** (interactive games, multi-page courses, anything not covered in `brightspace-notes` section 3b): stop, describe it, give 2-3 options with a recommendation, wait for the answer.
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
python scripts/bs.py mode    show|headless          visible browser (default) or hidden
python scripts/linkify.py <note.md>                 [mm:ss] cites -> links to slide frames
python scripts/verify.py <ou> notes/<course>        -> notes/<ou>/COVERAGE.md (exit 1 if attention needed)
python scripts/rollup.py notes/<course>             EXAM_FOCUS.md, GLOSSARY.md, per-module CHEATSHEET.md
python scripts/master.py notes/<course> --ou <ou>   MASTER.md (agents read it first when revising)
python scripts/anki.py notes/<course>               -> notes/<course>/anki-cards.tsv
```
`<base>` = `https://<school-host>` (no path); `<ou>` = course id, the number in `/d2l/home/<ou>`; `<aid>` = activity id from `toc.md`. Every script except `doctor.py` prints its usage when run with no arguments.

There is no test suite. Before committing code changes: `python -m py_compile scripts/*.py`, `python scripts/doctor.py`, and one real topic end to end if the change touches capture. Keep scripts small, dependency-light, in the existing terse style.

## Outputs
- `notes/<ou>/`: `toc.md`, `module-intros.md`, `capture-log.jsonl` (every `bs.py video/doc` attempt), `COVERAGE.md`.
- `notes/<course>/<module>/<topic>.md`: one note per topic (front matter with `video:` lines, then Key ideas / Details / Likely exam/test points / Self-check questions as `N. Question? *answer*` / Gaps). Media per topic in `notes/<course>/<module>/assets/<slug>/` (`slides.md`, `sheets/`, `frames/`, `transcript.md`, `frames.txt`).
- `notes/<course>/`: `INDEX.md`, `MASTER.md`, `TIMELINE.md`, `GLOSSARY.md`, `EXAM_FOCUS.md`, `question-bank.md`, `progress.md`.
- `work/`: scratch downloads. `cookies.txt` (repo root): yt-dlp cookies for embedded players; delete after use.

## Architecture (the parts that span files)
- **`scripts/env.py`** is imported first by every script: forces UTF-8 stdout/stderr (Windows pipes default to cp1252 and crash on non-ASCII titles) and on Windows merges the registry PATH so tools installed by winget mid-session are found. New scripts should `import env` too.
- **Login/session (`bs.py`)**: one persistent Chromium profile in `.profile/`; SSO cookies are session-only so they are also saved to `.profile/cookies.json` and re-added on every launch. Visible mode prefers installed Chrome (H.264) and disables occlusion throttling, because hidden or background windows freeze video players.
- **Outline**: students get 403 on the D2L content API, so `toc` loads the Lessons page, captures the bearer token from its `sequences.api` request, and walks the sequence JSON. The sequence host is cached in `.profile/seq.json`; `video`/`doc` need it, so `toc` must run once first.
- **Video capture** is two steps: `bs.py video` opens the topic, waits for the LTI player, then runs the adapters in `scripts/hosts.py` (`ADAPTERS = [yuja, embed, sniff]`, first hit wins) which return `{host, source, subs}`. If the visible window finds no stream it retries headless once. `video.py` then downloads via yt-dlp (URLs other than m3u8) or reads the manifest with ffmpeg, samples a frame every `--step` s, keeps a frame when its dHash (bottom 14% ignored) differs by more than `--sim`, and aligns subtitle lines to slides. No subtitles -> faster-whisper. Only YuJa is tested; adding a host = one function in `hosts.py` (see CONTRIBUTING.md).
- **Notes pipeline**: notes cite `[mm:ss]`; `linkify.py` maps them via `frames.txt` to frame links. `rollup.py`, `master.py` and `anki.py` parse notes by front matter (`---` block) and `## Section` headings, so keep the note template from `brightspace-notes` exactly. `verify.py` joins `toc.md` with `capture-log.jsonl` (and infers older captures from note front matter).

## Known limits
Non-YuJa adapters and `install.sh` are untested; `.pptx` gives text only without LibreOffice; YouTube needs Deno and `yt-dlp[default]`; the outline covers Lessons only (not Assignments, Quizzes, Discussions, Media Library, or unreleased items).
