---
name: brightspace-check
description: Check that the brightspace-notes setup is healthy (Python, ffmpeg, packages, browser, privacy hook, Brightspace login) and fix what's missing, explained in plain language. Use when the user says "check my setup", "is everything ok", "it's not working", or runs /brightspace-check. For a first install on a new machine use brightspace-setup instead.
---

# Setup check (for non-technical users)

If nothing has been installed yet (most packages and Chromium missing, never logged in), switch to the `brightspace-setup` skill: it walks through a first install item by item.

1. Run `python scripts/doctor.py` from the repo folder (try `py` if `python` isn't found) and read the output. `[ok]` fine, `[--]` optional, `[!!]` problem. (`--json` gives the same checks machine-readable.)
2. Reply in **plain language**, no jargon: one short list, e.g. "Everything is ready" or "2 things need fixing: ...". Explain what each missing piece is for in half a sentence (ffmpeg = reads the video; Chromium = the window you sign in with).
3. If something is missing, **offer to fix it and ask first**, then run the fix the doctor printed (pip installs, `python -m playwright install chromium`, `git config core.hooksPath .githooks`). For ffmpeg or Python itself, say what to install and from where (Windows: `winget install Gyan.FFmpeg`; Mac: `brew install ffmpeg`); installing system software needs the user's OK. The scripts pick up newly installed Windows tools by themselves; the user's own terminal needs reopening. Re-run the doctor after fixing and report the result.
4. **Login:** if the login line is `[!!]`, ask for their Brightspace address (e.g. `https://school.brightspace.com`) if you don't know it, run `python scripts/bs.py login <address>` in the background, and tell them: "A browser window opened: sign in there as you normally do (including any phone approval). I'll carry on when you're in." Never ask for or handle their password.
5. Finish with one line on what they can do next ("Ask me to make notes for a topic, e.g. 'make notes for Topic 2'").
