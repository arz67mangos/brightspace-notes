"""Check that everything brightspace-notes needs is installed, and say exactly how to fix what isn't.

  python scripts/doctor.py
"""
import importlib.util, json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
bad = []


def check(name, ok, fix, info="", optional=False):
    print(f"[{'ok' if ok else '--' if optional else '!!'}] {name}{(': ' + info) if info else ''}")
    if not ok and not optional:
        bad.append(f"{name}: {fix}")
    elif not ok:
        print(f"     optional: {fix}")


check("Python >= 3.10", sys.version_info >= (3, 10), "install Python 3.10+ from python.org", sys.version.split()[0])
check("ffmpeg on PATH", bool(shutil.which("ffmpeg")), "Windows: winget install Gyan.FFmpeg | Mac: brew install ffmpeg")
check("git", bool(shutil.which("git")), "install git")
for mod, pkg in [("playwright", "playwright"), ("yt_dlp", "yt-dlp"), ("webvtt", "webvtt-py"), ("faster_whisper", "faster-whisper"),
                 ("numpy", "numpy"), ("PIL", "pillow"), ("fitz", "pymupdf"), ("docx", "python-docx"), ("pptx", "python-pptx")]:
    check(f"python package {pkg}", importlib.util.find_spec(mod) is not None, f"pip install {pkg}  (or: pip install -r requirements.txt)")

try:  # is Chromium downloaded for Playwright?
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        check("Playwright Chromium", Path(p.chromium.executable_path).exists(), "python -m playwright install chromium")
except Exception as e:
    check("Playwright Chromium", False, "pip install playwright && python -m playwright install chromium", str(e)[:60])

check("Deno (YouTube videos need a JavaScript runtime)", bool(shutil.which("deno")), "Windows: winget install DenoLand.Deno | Mac: brew install deno (then open a new terminal)", optional=True)
hook = subprocess.run(["git", "config", "core.hooksPath"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
check("privacy pre-commit hook", hook == ".githooks", "git config core.hooksPath .githooks")
soffice = shutil.which("soffice") or next((c for c in (r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                                                       "/Applications/LibreOffice.app/Contents/MacOS/soffice") if Path(c).exists()), None)
check("LibreOffice (renders .pptx slides)", bool(soffice), "install LibreOffice for slide images from .pptx", optional=True)

cfg = ROOT / ".profile" / "config.json"
if not (ROOT / ".profile" / "cookies.json").exists() or not cfg.exists():
    check("Brightspace login", False, "python scripts/bs.py login https://YOUR-SCHOOL.brightspace.com")
else:
    base = json.loads(cfg.read_text())["base"]
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

print("\nAll good." if not bad else "\nFix these:\n  - " + "\n  - ".join(bad))
sys.exit(1 if bad else 0)
