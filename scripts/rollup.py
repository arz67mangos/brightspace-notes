"""Roll the per-topic notes of a course up into revision sheets.

  python scripts/rollup.py <course-notes-folder>        e.g. notes/ECON101

Writes into that folder (overwrites; don't hand-edit these):
  EXAM_FOCUS.md      every note's "## Likely exam/test points", grouped by module
  GLOSSARY.md        every **bold term** from "## Key ideas" with its sentence, alphabetical, linked to its note
  <module>/CHEATSHEET.md   each note's "## Key ideas" concatenated for one module (ask Claude to tighten it)
Notes are the .md files two levels down (<course>/<module>/<topic>.md) that have the standard sections.
"""
import re, sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))


def section(text, title):
    m = re.search(rf"## {title}[^\n]*\n(.*?)(?=\n## |\Z)", text, re.S)
    return m.group(1).strip() if m else ""


def fm(text, key):
    m = re.search(rf"^{key}: (.+)$", text.split("\n---\n")[0], re.M)
    return m.group(1).strip() if m else ""


exam, gloss, per_module = [], {}, {}
for note in sorted(root.glob("*/*.md")):
    if note.name in ("CHEATSHEET.md",):
        continue
    t = note.read_text(encoding="utf-8")
    mod, topic = fm(t, "module") or note.parent.name, fm(t, "topic") or note.stem
    rel = note.relative_to(root).as_posix()
    if pts := section(t, "Likely exam/test points"):
        exam.append(f"## {mod}\n### [{topic}]({rel})\n{pts}\n")
    key = section(t, "Key ideas")
    if key:
        per_module.setdefault(note.parent, []).append(f"### [{topic}]({note.name})\n{key}\n")
    for line in key.splitlines():
        for term in re.findall(r"\*\*([^*]+)\*\*", line)[:1]:  # first bold term of a bullet = the term it defines
            gloss.setdefault(term.strip(" :").lower(), (term.strip(" :"), re.sub(r"^[-\s]*", "", line), rel))

(root / "EXAM_FOCUS.md").write_text("# Exam focus\n\n" + "\n".join(exam), encoding="utf-8")
(root / "GLOSSARY.md").write_text(
    "# Glossary\n\n" + "\n".join(f"- **{t}**: {l}  ([note]({r}))" for _, (t, l, r) in sorted(gloss.items())) + "\n", encoding="utf-8")
for folder, parts in per_module.items():
    (folder / "CHEATSHEET.md").write_text(f"# {folder.name}: cheat sheet\n\n" + "\n".join(parts), encoding="utf-8")
print(f"EXAM_FOCUS.md ({len(exam)} notes), GLOSSARY.md ({len(gloss)} terms), {len(per_module)} CHEATSHEET.md")
