# One-shot setup for Windows. Run from the repo folder:
#   powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
$py = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } elseif (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { $null }
if (-not $py) { Write-Host "Install Python 3.10+ from https://www.python.org/downloads/ (tick 'Add to PATH'), then re-run." -ForegroundColor Red; exit 1 }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "Installing ffmpeg..."; winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
    Write-Host "ffmpeg installed: open a NEW terminal after this script so PATH updates." -ForegroundColor Yellow
}
& $py -m pip install -r requirements.txt
& $py -m playwright install chromium
git config core.hooksPath .githooks
& $py scripts/doctor.py
Write-Host "`nNext: python scripts/bs.py login https://YOUR-SCHOOL.brightspace.com   (or just ask Claude Code in this folder)"
