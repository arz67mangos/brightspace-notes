"""Copy .claude/skills/* to .agents/skills/* (Codex reads the latter). --check: change nothing, exit 1 on drift.
Also checks that AGENTS.md mentions every skill by name."""
import env  # noqa: F401
import shutil, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
src, dst = root / ".claude/skills", root / ".agents/skills"
check = "--check" in sys.argv
bad = []
for d in sorted(p for p in src.iterdir() if (p / "SKILL.md").exists()):
    f, g = d / "SKILL.md", dst / d.name / "SKILL.md"
    if not g.exists() or f.read_bytes() != g.read_bytes():
        bad.append(f"{d.name}: .agents copy {'missing' if not g.exists() else 'differs'}")
        if not check:
            g.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, g)
    if d.name not in (root / "AGENTS.md").read_text(encoding="utf-8"):
        bad.append(f"{d.name}: not listed in AGENTS.md")
for d in dst.iterdir() if dst.exists() else []:
    if not (src / d.name).exists():
        bad.append(f"{d.name}: in .agents but not in .claude (stale)")
print("\n".join(bad) or "in sync")
sys.exit(1 if bad and check else 0)
