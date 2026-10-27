"""Generate MASTER.md: the file an agent reads FIRST when revising a course, so it finds knowledge instead of inventing it.

  python scripts/master.py <course-notes-folder> [--ou <orgUnitId>]       e.g. master.py notes/ECON101 --ou 123456

Writes <folder>/MASTER.md (overwritten; don't hand-edit): rules for agents, where the cross-cutting files are,
a topic map (note, key terms, source files per topic) and a file tree. Re-run after every capture session.
"""
import re, sys
from pathlib import Path
from urllib.parse import quote

args = sys.argv[1:]
if not args:
    sys.exit(__doc__)
root = Path(args[0])
ou = args[args.index("--ou") + 1] if "--ou" in args else None
IMG = {".jpg", ".jpeg", ".png", ".webp"}


def fm(text, key):
    m = re.search(rf"^{key}: (.+)$", text.split("\n---\n")[0], re.M)
    return m.group(1).strip() if m else ""


def sect(text, title):
    m = re.search(rf"## {title}[^\n]*\n(.*?)(?=\n## |\Z)", text, re.S)
    return m.group(1) if m else ""


index = {}
if (root / "INDEX.md").exists():  # one-line summaries written by whoever made the notes
    for m in re.finditer(r"^- \[[^\]]*\]\(([^)]+)\)[:\s-]*(.*)$", (root / "INDEX.md").read_text(encoding="utf-8"), re.M):
        index[m.group(1)] = m.group(2).strip()

rows = []
for note in sorted(root.glob("*/*.md")):
    if note.name in ("CHEATSHEET.md",):
        continue
    t = note.read_text(encoding="utf-8")
    if not fm(t, "topic"):
        continue  # not a standard note (e.g. answers file): listed in the tree only
    rel = note.relative_to(root).as_posix()
    terms = [x for x in dict.fromkeys(re.findall(r"\*\*([^*]+)\*\*", sect(t, "Key ideas"))) if len(x) > 4 and "(" not in x.split(" ")[0] and "(down)" not in x][:7]
    srcs = []
    for l in t.split("\n---\n")[0].splitlines():
        if l.startswith("video:"):
            d = l.split("|")[-1].strip()
            srcs += [f"{(note.parent / d).relative_to(root).as_posix()}/slides.md", f"{(note.parent / d).relative_to(root).as_posix()}/transcript.md"]
    assets = note.parent / "assets"
    if assets.exists():
        srcs += [p.relative_to(root).as_posix() for p in sorted(assets.rglob("*.md")) if p.name not in ("slides.md", "transcript.md")]
    rows.append((fm(t, "module") or note.parent.name, fm(t, "topic"), rel, index.get(rel) or index.get(note.relative_to(root).as_posix(), ""), terms, srcs))


def tree(d, prefix=""):
    out = []
    kids = sorted(d.iterdir(), key=lambda p: (p.is_file(), p.name))
    dirs = [k for k in kids if k.is_dir()]
    files = [k for k in kids if k.is_file()]
    imgs = [f for f in files if f.suffix.lower() in IMG]
    shown = [f for f in files if f.suffix.lower() not in IMG]
    entries = [(k, True) for k in dirs] + [(k, False) for k in shown]
    for i, (k, isdir) in enumerate(entries):
        last = i == len(entries) - 1 and not imgs
        out.append(f"{prefix}{'└── ' if last else '├── '}{k.name}{'/' if isdir else ''}")
        if isdir:
            out += tree(k, prefix + ("    " if last else "│   "))
    if imgs:
        out.append(f"{prefix}└── ({len(imgs)} image files)")
    return out


def exists(name):
    return (root / name).exists()


L = [f"# {root.name}: master context (agents: read this first)\n",
     "This file tells an agent where the course knowledge is, so it answers from the notes instead of inventing.\n",
     "## Rules for agents",
     "1. **Answer from the files below only.** Find the topic in the *Topic map*, open its note, and cite it (note path, plus the slide link if the note has one).",
     "2. If a topic isn't in the map, or a note's **Gaps** section says it wasn't captured, say \"not covered in the notes\" and offer to capture it. Don't fill the gap from general knowledge unless the user asks, and then label it as outside the notes.",
     "3. Transcripts are auto-generated: if a term looks odd, check the slide text in `slides.md` and the note's Gaps (corrections are listed there).",
     "4. Quizzes and tutorials: follow the mode the user states. By default give the answer with its reasoning and note reference; if they say it matters and they want to work it out, point to the note sections and guide them instead (skills `brightspace-quiz`, `brightspace-tutorial`).",
     "5. For dates and deadlines read `TIMELINE.md`, not the notes.",
     "6. Notes are the user's personal study material: don't copy them into public places.\n",
     "## Where things are",
     "| Need | File |", "|---|---|",
     f"| One-line summary per note | {'[INDEX.md](INDEX.md)' if exists('INDEX.md') else '(not created)'} |",
     f"| Dates, deadlines, assessments | {'[TIMELINE.md](TIMELINE.md)' if exists('TIMELINE.md') else '(not created yet: ask for it)'} |",
     f"| All key terms | {'[GLOSSARY.md](GLOSSARY.md)' if exists('GLOSSARY.md') else '(run rollup.py)'} |",
     f"| All exam/test points | {'[EXAM_FOCUS.md](EXAM_FOCUS.md)' if exists('EXAM_FOCUS.md') else '(run rollup.py)'} |",
     f"| Past quiz question types | {'[question-bank.md](question-bank.md)' if exists('question-bank.md') else '(none yet)'} |",
     f"| Weak spots from quizzes | {'[progress.md](progress.md)' if exists('progress.md') else '(none yet)'} |",
     f"| What was and wasn't captured | {'`notes/' + ou + '/COVERAGE.md` (run verify.py)' if ou else '(run verify.py)'} |",
     "| Per-module cheat sheets | `CHEATSHEET.md` inside each module folder |\n",
     "## Topic map"]
last = None
for mod, topic, rel, summ, terms, srcs in rows:
    if mod != last:
        L += [f"\n### {mod}", "| Topic | Note | Key terms | Sources (narration/slides/documents) |", "|---|---|---|---|"]
        last = mod
    L.append(f"| {topic}{(' - ' + summ) if summ else ''} | [{rel}]({quote(rel)}) | {', '.join(terms)} | {'<br>'.join(f'[{s}]({quote(s)})' for s in srcs)} |")
if not rows:
    L.append("(no notes yet)")
L += ["\n## File tree", "```", f"{root.name}/"] + tree(root) + ["```"]
(root / "MASTER.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"wrote {root / 'MASTER.md'}: {len(rows)} topics")
