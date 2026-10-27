# brightspace-notes

A [Claude Code](https://claude.com/claude-code) skill that turns the Brightspace (D2L) course material **you are enrolled in** into revision notes you can study from, quiz yourself on, or hand to another Claude agent.

It is **scoped on purpose**: it lists the course outline, asks which modules/topics you want, and processes only those. It never starts or submits a quiz attempt for you.

## What you get
| Capture | Result |
|---|---|
| Lecture videos | Transcript from the video's own subtitles (speech-to-text if there are none), **one frame per distinct slide** (including each step of a diagram being drawn), contact sheets, and `slides.md`: each slide next to the narration spoken over it |
| Documents (PDF, Word, PowerPoint, zip) | Converted to markdown; scanned/diagram pages saved as images |
| Notes | One `.md` per topic: key ideas, details, exam points, self-check Q&A, gaps. Every `[mm:ss]` reference links to the slide on screen at that moment, labelled with the video it came from |
| Revision extras | Anki flashcards, exam-focus sheet, glossary, per-module cheat sheets, quiz mode, tutorial-sheet helper |

Everything lands in `notes/` on your machine (gitignored: it is your institution's material, keep it personal).

## Install
### 1. Install the basics (once per computer, Windows)
- **Python 3.10 or newer** from https://www.python.org/downloads/. In the installer, **tick "Add python.exe to PATH"** before clicking Install.
- **Git** from https://git-scm.com/download/win (the default options are fine).
- **Claude Code**: the Claude desktop app (https://claude.com/download, then the **Code** tab) or the terminal version (https://claude.com/claude-code).

(If you're comfortable with a terminal: `winget install Python.Python.3.13` and `winget install Git.Git` do the first two.)

### 2. Download this repo
Open **PowerShell** (Start menu, type "PowerShell"), then copy-paste these two lines. They put the folder in your Documents:

```bash
cd $HOME\Documents
git clone https://github.com/arz67mangos/brightspace-notes.git
```
You now have a folder `Documents\brightspace-notes`. To get updates later, run `git pull` inside that folder.

*No git?* On the GitHub page click the green **Code** button > **Download ZIP**, then right-click the file > **Extract All**. This works, but you won't get updates with `git pull`, and the privacy guard (below) needs git, so cloning is better.

### 3. Open the folder in Claude Code
- Desktop app: in the **Code** tab, choose the `brightspace-notes` folder as the project folder.
- Terminal: `cd $HOME\Documents\brightspace-notes`, then run `claude`.

Always open Claude Code **in this folder**: that's how it finds the skills below.

### 4. Set it up
**Easiest:** open Claude Code in this folder and type **`/brightspace-setup`** (or say "set this up"). Claude checks what you already have, tells you what's missing with sizes and the exact commands, installs only what you approve, then helps you sign in to Brightspace.

Or install everything in one go, from this folder:

```bash
# Windows
powershell -ExecutionPolicy Bypass -File install.ps1
# macOS / Linux
sh install.sh
```
This installs the Python packages, Chromium (for the login window), ffmpeg, Deno (for YouTube), switches on the privacy hook, and runs the doctor. It is safe to run again. Tested on Windows; `install.sh` for macOS/Linux is provided but untested. On macOS/Linux, if pip refuses ("externally managed environment"), the script tells you how to use a virtual environment (`.venv/`, gitignored).

## Use it
Open Claude Code **in this folder** (the skills in `.claude/skills/` load automatically) and just ask, e.g.:

> Make revision notes for Topic 2 of my course: https://YOUR-SCHOOL.brightspace.com/d2l/home/123456

Claude will:
1. run `scripts/bs.py login`: a Chromium window opens, **you sign in yourself** (SSO/MFA fine). Your password never touches the scripts; the session is saved to `.profile/` (gitignored). Re-login when it expires.
2. list the modules and **ask which topics you want**. Anything you don't pick is never opened.
3. fetch the videos/documents of those topics, read the slides and narration, and write the notes.

**Quizzes:** paste questions and ask for help. By default you get the answer with the reasoning and note references; if a quiz matters and you want to work it out yourself, say so ("don't give me the answer, point me to the notes") and it will guide you instead. Pasted questions are kept in a personal question bank so it can later set you self-tests in the same question types.

**Slide decks, YouTube lists, interactive pages:** slide decks (PDF/PowerPoint) are downloaded and read as files rather than screenshotted; pages of YouTube links are handled like lecture videos; for interactive games and multi-page courses, or anything it doesn't recognise, the agent stops and asks you first with recommended options.

Other things you can ask: *"quiz me on Topic 2"* (skill `brightspace-quiz`, tracks what you get wrong), *"attempt this tutorial sheet from my notes"* (skill `brightspace-tutorial`, shows which note each answer came from and lists its assumptions), *"make an exam-focus sheet / glossary / cheat sheet"*, *"export Anki cards"*.

## For revising with an agent: `MASTER.md` and `TIMELINE.md`
After each capture session the course folder gets two files meant for agents (and you):
- **`MASTER.md`**: the file to point an agent at first. It has rules (answer only from your notes, cite them, say "not covered" instead of inventing), a **topic map** (which note, key terms and source files hold each topic), and a file tree. Generated by `python scripts/master.py notes/<course> --ou <course-id>`.
- **`TIMELINE.md`**: all lessons, quizzes, CAs, presentations, submissions and exams with dates and weightings, taken from the course schedule and assessment pages, each row linking to its source. Dates not stated in the documents are listed under "to confirm", never guessed.

Revising? Tell your agent: *"Read notes/<course>/MASTER.md first, then help me revise <topic>."*

## Did it miss anything? `verify`
After a capture session, ask *"verify the capture"* (or run `python scripts/verify.py <course-id> notes/<course folder>`). It writes `notes/<course-id>/COVERAGE.md`: every topic in the course outline with a status (captured / failed / not captured, with quiz-like items labelled), and evidence per capture: slide count, whether the transcript covers the whole video (flags transcripts that stop early or have long silent gaps), missing frames, documents not yet converted, plus broken links and self-check questions without answers in your notes. It can't see Brightspace tools outside Lessons (Assignments, Discussions, Media Library...) or items not yet released to you; it checks completeness, not whether a note's wording is right (read each note's "Gaps").

## Watch it work, or hide it
By default a Chromium window **opens and you can watch** the scripts browse Brightspace. If you'd rather it work invisibly in the background, just tell your agent: *"switch to headless mode"* (and *"show the browser again"* to undo it). It remembers your choice. The sign-in window is always shown, because you have to sign in yourself.

(Or run it yourself: `python scripts/bs.py mode headless` / `python scripts/bs.py mode show`.)

## Check your setup: `doctor`
**Easiest:** open Claude Code in this folder and type **`/brightspace-check`** (or just say "check my setup"). Claude runs the check, explains the result in plain language, and offers to fix anything missing, including signing you back in to Brightspace.

Or run it yourself:
```bash
python scripts/doctor.py
```
Checks Python, ffmpeg, git, every Python package, Playwright's Chromium, the privacy hook, and your Brightspace login, and prints the exact command to fix anything missing.

## Privacy guard
`.githooks/pre-commit` (enabled by the installer; or `git config core.hooksPath .githooks`) **refuses any commit containing** `notes/`, `.profile/`, `work/` or cookie files, so you can't push your login session or course material by accident. `.gitignore` covers the same paths. Please don't bypass it with `--no-verify`.

## Commands (what Claude runs for you)
| Command | Does |
|---|---|
| `bs.py login <base>` | manual sign-in window, saves session |
| `bs.py toc <base> <ou>` | course outline with activity IDs -> `notes/<ou>/toc.md` |
| `bs.py video <base> <ou> <id> <dir>` | finds the player (host adapters), saves captions + stream URL |
| `bs.py doc <base> <ou> <id> <dir>` | downloads a file topic |
| `bs.py page <base> <ou> <topicId>` | page text, iframes and links as JSON (for unfamiliar topic types) |
| `bs.py cookies <base>` | `cookies.txt` for yt-dlp (gitignored) |
| `bs.py mode show\|headless` | watch the browser work, or hide it |
| `video.py <url\|file> <dir>` | transcript + slide frames + `slides.md` (+ speech-to-text if no subs) |
| `docs.py <file> <dir>` | pdf/docx/pptx/zip -> markdown (+ page images) |
| `linkify.py <note.md>` | turns `[mm:ss]` / `[P2 mm:ss]` into links to the slide frame |
| `anki.py <course notes> [out.tsv]` | self-check questions -> Anki import file (default `anki-cards.tsv` in the notes folder) |
| `rollup.py <course notes>` | `EXAM_FOCUS.md`, `GLOSSARY.md`, per-module `CHEATSHEET.md` |
| `master.py <course notes> --ou <ou>` | `MASTER.md`, the file an agent reads first |
| `verify.py <ou> [<course notes>]` | coverage check -> `notes/<ou>/COVERAGE.md` |
| `doctor.py [--json]` | setup check |

`<ou>` = the number in your course URL `/d2l/home/<ou>`.

## Not missing slides
Videos are sampled every 2 s (not "scene detection") and a frame is kept whenever the picture changes by more than a small threshold, ignoring the bottom strip where burned-in subtitles sit. Result: every slide, and each step of an animation, gets a frame. Tune with `video.py --sim 0.02` (catch tinier changes) or `--sim 0.06` (fewer near-duplicates), `--step 1` for fast-moving videos.

## Limits (please read)
- **Video hosts:** `bs.py video` is **tested on YuJa** at one institution (Microsoft SSO). Adapters for YouTube/Vimeo/Panopto/Kaltura embeds (via yt-dlp) and a generic network sniffer exist but are **untested**; if yours fails, see [CONTRIBUTING.md](CONTRIBUTING.md): adding a host is one small function, and PRs are very welcome.
- Captions are usually auto-generated: expect small errors in terms and names. The skill cross-checks terms against the slides, and notes list corrections under "Gaps". Speech-to-text (no-subtitle videos) is weaker on jargon: use `--whisper-model small.en`.
- `.pptx` files give text only unless LibreOffice is installed (then slides are rendered); symbol-font arrows in Word handouts can come through blank.
- Opening a topic marks it as viewed in Brightspace. Students can't use Brightspace's content API (403), so the outline comes from the same Lessons data the web page loads.
- Written for students: it only reads what your account can already see.

## Be responsible
Use only courses you're enrolled in, for your own study. Don't share the generated notes or media beyond what your institution allows. `.profile/` is your login session: never share it.

MIT licensed. Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).
