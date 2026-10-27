---
name: brightspace-setup
description: First-time setup of brightspace-notes on a new machine. Detects what is already installed (OS, Python, Python packages, Playwright Chromium, ffmpeg, Deno, LibreOffice, privacy hook), explains it in plain language, asks before downloading or installing each item, installs only what the user approves, re-checks, then guides the Brightspace address and first sign-in. Use when the user has just cloned the repo, says "set this up", "install it", "first time", or runs /brightspace-setup. For an existing install that stopped working, use brightspace-check.
---

# First-time setup

Run everything from the repo root (the folder with `scripts/`). Talk in plain language: the user may not be technical. **Nothing gets downloaded or installed without a yes for that item.**

## 1. Find a working Python
Try `python --version`, then `py --version` (Windows), then `python3 --version` (Mac/Linux). Use the first that prints 3.10 or newer as `<py>` for every command below. On Windows a `python` that opens the Microsoft Store (or prints nothing) does not count.
- None, or older than 3.10: stop here. Tell them to install Python 3.10+ from https://www.python.org/downloads/ (Windows: tick "Add python.exe to PATH"; Mac: or `brew install python`), then restart Claude Code in this folder and say "set it up" again. Don't install Python for them.
- Mac/Linux: if a later `pip install` fails with "externally-managed-environment", offer a virtual environment: `python3 -m venv .venv` then use `.venv/bin/python` as `<py>` from then on (and tell them to run `. .venv/bin/activate` in their own terminal).

## 2. Check what's already there
Run `<py> scripts/doctor.py --json`. It prints `os`, `python` and a `checks` list (`name`, `ok`, `optional`, `fix`, `info`). If it fails before printing (a missing package it imports, unlikely), fall back to `<py> scripts/doctor.py`.

Report in one short list: what's ready, what's missing and what it's for. Don't show the JSON.

## 3. Ask before installing (one question, multi-select)
List only the missing items, each with purpose, rough download size and the exact command. Use AskUserQuestion with multiSelect; required items pre-recommended, optional ones clearly marked optional.

| Item | What it's for | Size (approx.) | Command |
|---|---|---|---|
| Python packages (`requirements.txt`) | everything the scripts use; faster-whisper is the big one (speech-to-text for videos without subtitles) | 300-500 MB | `<py> -m pip install -r requirements.txt` |
| Playwright Chromium | the browser window you sign in with | ~150 MB | `<py> -m playwright install chromium` (Linux: add `--with-deps`, needs sudo) |
| ffmpeg (system program) | reads the videos, takes slide frames | 100-200 MB | Windows `winget install --id Gyan.FFmpeg -e` / Mac `brew install ffmpeg` / Linux `sudo apt-get install -y ffmpeg` |
| Privacy hook (no download) | blocks commits of your notes, login and cookies | 0 | `git config core.hooksPath .githooks` |
| Deno (optional) | needed only for YouTube videos | ~100 MB | Windows `winget install --id DenoLand.Deno -e` / Mac `brew install deno` / Linux see https://deno.com |
| LibreOffice (optional) | slide images from PowerPoint files (text works without it) | ~350 MB | Windows `winget install --id TheDocumentFoundation.LibreOffice -e` / Mac `brew install --cask libreoffice` / Linux `sudo apt-get install -y libreoffice` |

Also say once: the first video with no subtitles downloads a speech model (~150 MB) automatically.

Rules:
- Install only the items they tick, one command at a time, and say what each is doing. If they decline a required item, say what won't work without it and carry on.
- Commands needing admin/sudo, or `winget`/`brew` that isn't installed: show the command and let the user run it themselves; don't try to work around a blocked or failing installer.
- `install.ps1` / `install.sh` install everything in one go without asking per item: mention them only if the user wants "just install everything".
- Windows: the scripts find tools installed by winget straight away; only a direct `ffmpeg`/`deno` command in an already-open terminal needs that terminal reopened.

## 4. Re-check
Run `<py> scripts/doctor.py` again and give the result in plain words ("Everything's ready except the login" is the normal result at this point).

## 5. Brightspace address and first sign-in
1. Ask for the address they use for Brightspace, or a course link (copy it from the browser bar). Keep only the start: `https://<school-host>` (drop `/d2l/...`). If they paste a course link, remember the number after `/d2l/home/`: that's the course id for later.
2. Run `<py> scripts/bs.py login <address>` **in the background** and tell them: "A browser window with an orange bar opened: sign in there as you normally do (including any phone approval), not in your usual browser. It closes by itself when you're in." Never ask for, type or see their password.
3. When it prints `logged in, session saved`, run `<py> scripts/doctor.py` once more to confirm the login line is `[ok]`. If it timed out, offer to run it again.

## 6. Finish
Say it's set up and what to do next, e.g. "Paste a course link and tell me which topics you want notes for." Mention that by default a browser window opens while scripts run, and they can say "switch to headless mode" to hide it. Their notes and login stay on this computer (`notes/`, `.profile/` are never committed).
