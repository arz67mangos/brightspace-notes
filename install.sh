#!/bin/sh
# One-shot setup for macOS/Linux. Run from the repo folder:  sh install.sh
set -e
command -v python3 >/dev/null || { echo "Install Python 3.10+ first (https://www.python.org/downloads/)"; exit 1; }
if ! command -v ffmpeg >/dev/null; then
  if command -v brew >/dev/null; then brew install ffmpeg
  elif command -v apt-get >/dev/null; then sudo apt-get install -y ffmpeg
  else echo "Install ffmpeg manually, then re-run"; exit 1; fi
fi
if ! command -v deno >/dev/null; then  # YouTube downloads need a JS runtime
  if command -v brew >/dev/null; then brew install deno; else echo "Optional: install Deno (https://deno.com) for YouTube videos"; fi
fi
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
python3 scripts/doctor.py
echo
echo "Next: python3 scripts/bs.py login https://YOUR-SCHOOL.brightspace.com   (or just ask Claude Code in this folder)"
