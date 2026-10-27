"""Check that everything brightspace-notes needs is installed, and say exactly how to fix what isn't.

  python scripts/doctor.py           human-readable report
  python scripts/doctor.py --json    same checks as JSON (used by the brightspace-setup skill)
"""
import importlib.util, json, platform, shutil, subprocess, sys
from pathlib import Path

import env  # noqa: F401  (UTF-8 output, PATH refresh)

ROOT = Path(__file__).resolve().parent.parent
AS_JSON = "--json" in sys.argv
results = []


def check(name, ok, fix, info="", optional=False):
    results.append({"name": name, "ok": bool(ok), "optional": optional, "fix": fix, "info": info})
    if AS_JSON:
        return
    print(f"[{'ok' if ok else '--' if optional else '!!'}] {name}{(': ' + info) if info else ''}")
    if not ok and optional:
        print(f"     optional: {fix}")


check("Python >= 3.10", sys.version_info >= (3, 10), "install Python 3.10+ from python.org", sys.version.split()[0])
check("ffmpeg on PATH", bool(shutil.which("ffmpeg")), "Windows: winget install Gyan.FFmpeg | Mac: brew install ffmpeg | Linux: sudo apt-get install ffmpeg")
check("git", bool(shutil.which("git")), "install git (https://git-scm.com)")
for mod, pkg in [("playwright", "playwright"), ("yt_dlp", "yt-dlp"), ("webvtt", "webvtt-py"), ("faster_whisper", "faster-whisper"),
                 ("numpy", "numpy"), ("PIL", "pillow"), ("fitz", "pymupdf"), ("docx", "python-docx"), ("pptx", "python-pptx")]:
    check(f"python package {pkg}", importlib.util.find_spec(mod) is not None, f"python -m pip install {pkg}  (or: python -m pip install -r requirements.txt)")

try:  # is Chromium downloaded for Playwright?
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        check("Playwright Chromium", Path(p.chromium.executable_path).exists(), "python -m playwright install chromium")
except Exception as e:
    check("Playwright Chromium", False, "python -m pip install playwright && python -m playwright install chromium", str(e)[:60])

check("Deno (YouTube videos need a JavaScript runtime)", bool(shutil.which("deno")), "Windows: winget install DenoLand.Deno | Mac: brew install deno | Linux: https://deno.com", optional=True)
check("yt-dlp YouTube extras (yt-dlp-ejs)", importlib.util.find_spec("yt_dlp_ejs") is not None, 'python -m pip install -U "yt-dlp[default]"', optional=True)
hook = subprocess.run(["git", "config", "core.hooksPath"], capture_output=True, text=True, cwd=ROOT).stdout.strip() if shutil.which("git") else ""
check("privacy pre-commit hook", hook == ".githooks", "git config core.hooksPath .githooks")
soffice = shutil.which("soffice") or next((c for c in (r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                                                       "/Applications/LibreOffice.app/Contents/MacOS/soffice") if Path(c).exists()), None)
check("LibreOffice (renders .pptx slides)", bool(soffice), "Windows: winget install TheDocumentFoundation.LibreOffice | Mac: brew install --cask libreoffice | Linux: sudo apt-get install libreoffice", optional=True)

cfg = ROOT / ".profile" / "config.json"
base = json.loads(cfg.read_text()).get("base") if cfg.exists() else None
if not (ROOT / ".profile" / "cookies.json").exists() or not base:
    check("Brightspace login", False, "python scripts/bs.py login https://YOUR-SCHOOL.brightspace.com")
else:
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import bs

        with sync_playwright() as p:
            c = bs.ctx(p, headless=True)  # a health check shouldn't pop a window
            pg = c.new_page()
            pg.goto(f"{base}/d2l/home", wait_until="domcontentloaded")
            pg.wait_for_timeout(3000)
            ok = base.split("//")[1] in pg.url and "login" not in pg.url
            c.close()
        check("Brightspace login", ok, f"session expired: python scripts/bs.py login {base}", base)
    except Exception as e:
        check("Brightspace login", False, f"python scripts/bs.py login {base}", str(e)[:60])

bad = [r for r in results if not r["ok"] and not r["optional"]]
if AS_JSON:
    print(json.dumps({"os": f"{platform.system()} {platform.release()} ({platform.machine()})", "python": sys.executable,
                      "base": base, "checks": results}, indent=1))
else:
    print("\nAll good." if not bad else "\nFix these:\n  - " + "\n  - ".join(f"{r['name']}: {r['fix']}" for r in bad))
sys.exit(1 if bad else 0)
