"""Export "Self-check questions" from notes to an Anki-importable file.

  python scripts/anki.py <notes-folder-or-note.md> [out.tsv]

Reads each note's "## Self-check questions" section; a card is a numbered line `N. Question? *Answer*`
(answer in italics at the end). Lines without an italic answer are skipped with a warning.
Anki: File > Import, pick the .tsv; fields = Front, Back, Tags (course::module::topic).
"""
import re, sys
from pathlib import Path

import env  # noqa: F401  (UTF-8 output, PATH refresh)

CARD = re.compile(r"^\s*\d+\.\s+(.*?)\s+\*([^*]+)\*\s*$")
target = Path(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))
if not target.exists():
    sys.exit(__doc__)
# default next to the notes (gitignored), not in the repo root where `git add .` would pick the cards up
dest = Path(sys.argv[2]) if len(sys.argv) > 2 else (target if target.is_dir() else target.parent) / "anki-cards.tsv"
notes = [target] if target.is_file() else sorted(target.rglob("*.md"))
rows, skipped = [], 0
for n in notes:
    text = n.read_text(encoding="utf-8")
    fm = dict(l.split(": ", 1) for l in text.split("\n---\n")[0].splitlines() if ": " in l and not l.startswith("video:"))
    tag = "::".join(re.sub(r"\W+", "_", fm.get(k, "").strip()) for k in ("course", "module", "topic") if fm.get(k))
    sec = re.search(r"## Self-check questions[^\n]*\n(.*?)(?=\n## |\Z)", text, re.S)
    for line in (sec.group(1).splitlines() if sec else []):
        if not line.strip():
            continue
        m = CARD.match(line)
        if m:
            rows.append(f"{m.group(1)}\t{m.group(2)}\t{tag}")
        else:
            skipped += 1
            print(f"skipped (no *answer*): {n.name}: {line.strip()[:70]}")
dest.write_text("\n".join(rows) + "\n", encoding="utf-8")
print(f"wrote {len(rows)} cards to {dest} ({skipped} skipped)")
