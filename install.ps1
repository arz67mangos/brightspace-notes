# One-shot setup for Windows. Run from the repo folder:
#   powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
$py = $null  # "python" can be the Microsoft Store stub that only opens the Store: accept a command only if it runs
foreach ($c in "py", "python") { try { & $c --version *> $null; if ($LASTEXITCODE -eq 0) { $py = $c; break } } catch {} }
if (-not $py) { Write-Host "Install Python 3.10+ from https://www.python.org/downloads/ (tick 'Add to PATH'), then re-run." -ForegroundColor Red; exit 1 }
$winget = [bool](Get-Command winget -ErrorAction SilentlyContinue)
foreach ($t in @(@("ffmpeg", "Gyan.FFmpeg", "reads the videos"), @("deno", "DenoLand.Deno", "YouTube videos"))) {
    if (Get-Command $t[0] -ErrorAction SilentlyContinue) { continue }
    if (-not $winget) { Write-Host "Install $($t[0]) ($($t[2])) yourself: winget is not available on this PC." -ForegroundColor Yellow; continue }
    Write-Host "Installing $($t[0]) ($($t[2]))..."; winget install --id $t[1] -e --accept-package-agreements --accept-source-agreements
}
# winget updates the saved PATH, not this window's: reload it so the checks below see the new tools
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
& $py -m pip install -r requirements.txt
if ($LASTEXITCODE) { Write-Host "pip install failed (see above)." -ForegroundColor Red; exit 1 }
& $py -m playwright install chromium
if ($LASTEXITCODE) { Write-Host "Chromium download failed (see above)." -ForegroundColor Red; exit 1 }
git config core.hooksPath .githooks
& $py scripts/doctor.py
Write-Host "`nOpen a NEW terminal if ffmpeg/Deno were just installed. Next: $py scripts/bs.py login https://YOUR-SCHOOL.brightspace.com   (or just ask Claude Code in this folder)"
