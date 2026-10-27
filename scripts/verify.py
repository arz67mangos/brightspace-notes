"""Coverage + health check: did the capture miss anything?

  python scripts/verify.py <ou> [<notes-course-folder>]       e.g. verify.py 123456 notes/ECON101

Reads notes/<ou>/toc.md (everything the course outline lists) and notes/<ou>/capture-log.jsonl (every video/doc
capture attempt, written by bs.py) and writes notes/<ou>/COVERAGE.md:
  1. every topic in the outline with its status: captured / FAILED / not captured (quiz-like) / not captured
  2. per captured video: duration vs transcript range, slide count, silent gaps, missing frame files
  3. per captured document: converted to markdown? PDF pages that came out empty?
  4. (with a notes folder) broken links, citations not yet linked, self-check questions without an answer
Exit code 1 if anything needs attention. Limits: the outline lists Lessons content only; Assignments, Quizzes,
Discussions, Announcements and Media Library are separate tools, and items hidden by release conditions or dates
are not visible to your account until released.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ou = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
course = Path(sys.argv[2]) if len(sys.argv) > 2 else None
base = ROOT / "notes" / ou
toc = base / "toc.md"
if not toc.exists():
    sys.exit(f"no {toc}: run bs.py toc first")

mmss = lambda s: f"{int(s) // 60:02d}:{int(s) % 60:02d}"
QUIZ = re.compile(r"quiz|survey|test\b|submission|checker|declaration", re.I)

log = {}
if (base / "capture-log.jsonl").exists():
    for line in (base / "capture-log.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        log[e["aid"]] = e  # newest attempt wins

if course and course.exists():  # captures from before the log existed: infer them from the notes (source: ... activity <id> + video: lines)
    for note in course.rglob("*.md"):
        head = note.read_text(encoding="utf-8").split("\n---\n")[0]
        m = re.search(r"^source: .*?activity (\d+)", head, re.M)
        vids = [l.split("|")[-1].strip() for l in head.splitlines() if l.startswith("video:")]
        if m and vids and m.group(1) not in log:
            log[m.group(1)] = {"aid": m.group(1), "kind": "video", "ok": True, "dir": str(note.parent / vids[0]), "inferred": True}

problems, out = [], [f"# Coverage: course {ou}\n"]


def video_health(d):
    d = Path(d)
    fl, notes = d / "frames.txt", []
    if not fl.exists():
        return ["video.py has not been run on this capture (no frames.txt)"]
    rows = [l.split("\t") for l in fl.read_text().splitlines() if l.strip()]
    dur = max(int(r[2]) for r in rows) if rows else 0
    missing = [r[0] for r in rows if not (d / "frames" / r[0]).exists()]
    tr = d / "transcript.md"
    ts = [int(m.group(1)) * 60 + int(m.group(2)) for m in re.finditer(r"^\[(\d+):(\d\d)\]", tr.read_text(encoding="utf-8"), re.M)] if tr.exists() else []
    info = f"{len(rows)} slides, video ~{mmss(dur)}, " + (f"transcript {len(ts)} lines {mmss(ts[0])}-{mmss(ts[-1])}" if ts else "NO transcript")
    if not rows:
        notes.append("no slide frames")
    if not ts:
        notes.append("no transcript")
    elif dur - ts[-1] > 90:
        notes.append(f"transcript stops {mmss(dur - ts[-1])} before the video ends (captions truncated?)")
    gaps = [(a, b) for a, b in zip(ts, ts[1:]) if b - a > 120]
    if gaps:
        notes.append("silent gaps >2 min (check slides there): " + ", ".join(f"{mmss(a)}-{mmss(b)}" for a, b in gaps[:5]))
    if missing:
        notes.append(f"{len(missing)} frame file(s) missing: {missing[:3]}")
    return [info] + notes


def doc_health(entry):
    f = Path(entry.get("file", ""))
    if not f.exists() or f.stat().st_size == 0:
        return ["downloaded file missing or empty"]
    notes = [f"{f.name}, {f.stat().st_size // 1024} KB"]
    stems = {f.stem.lower()}
    mds = [p for root in filter(None, [course, Path(entry.get("dir", "."))]) if root.exists() for p in root.rglob("*.md") if p.stem.lower() in stems]
    if f.suffix.lower() in (".zip",):
        notes.append("zip: check each inner document was converted (docs.py prints one line per file)")
    elif not mds:
        notes.append("NOT converted/read yet (run docs.py)")
    elif f.suffix.lower() == ".pdf":
        try:
            import fitz

            pages = len(fitz.open(f))
            got = len(re.findall(r"^## Page \d+", mds[0].read_text(encoding="utf-8"), re.M))
            if got != pages:
                notes.append(f"PDF has {pages} pages but markdown has {got}")
        except Exception:
            pass
    return notes


stats, tbl = {}, []
module = "(top)"
for line in toc.read_text(encoding="utf-8").splitlines():
    m = re.match(r"^(\s*)- \*\*(.+?)\*\* \((\d+|\?)\)\s*$", line)
    if m:
        module = m.group(2)
        tbl.append(f"\n## {module}\n\n| Topic | Kind | Status | Evidence |\n|---|---|---|---|")
        continue
    m = re.match(r"^\s*- (.+?) \((\d+|\?), ([\w-]*)\)\s*$", line)
    if not m:
        continue
    title, aid, kind = m.groups()
    e = log.get(aid)
    if e and e["ok"]:
        status = "captured"
        ev = "; ".join(video_health(e["dir"]) if e["kind"] == "video" else doc_health(e))
    elif e:
        status, ev = "FAILED", e.get("reason", "capture did not produce a stream/file")
        problems.append(f"{module} / {title}: FAILED")
    elif QUIZ.search(title):
        status, ev = "not captured (quiz/assessment-like)", "skipped on purpose"
    else:
        status, ev = "not captured", "not requested yet"
    st = stats.setdefault(module, [0, 0])
    st[1] += 1
    st[0] += status == "captured"
    for flag in re.findall(r"(NOT converted[^;]*|no transcript|no slide frames|transcript stops[^;]*|frame file\(s\) missing[^;]*|PDF has[^;]*|missing or empty|has not been run[^;]*)", ev):
        problems.append(f"{module} / {title}: {flag}")
    tbl.append(f"| {title} | {kind} | {status} | {ev} |")

total = [sum(v[0] for v in stats.values()), sum(v[1] for v in stats.values())]
out.append(f"**{total[0]} of {total[1]} topics captured.**\n")
out.append("| Module | Captured |\n|---|---|\n" + "\n".join(f"| {k} | {a}/{b} |" for k, (a, b) in stats.items()))
out += tbl

if course and course.exists():
    out.append("\n## Notes health\n")
    nh = []
    for note in sorted(course.rglob("*.md")):
        if "assets" in note.relative_to(course).parts:  # raw transcripts/slides, not notes
            continue
        t = note.read_text(encoding="utf-8")
        for target in re.findall(r"\]\((?!https?:)([^)#]+)\)", t):
            if not (note.parent / target).exists():
                nh.append(f"{note.name}: broken link {target}")
        loose = len(re.findall(r"(?<![\[\(])\[\d{1,2}:\d{2}(?:-\d{1,2}:\d{2})?\](?!\()", t))
        if loose:
            nh.append(f"{note.name}: {loose} citation(s) not linked yet (run linkify.py)")
        sec = re.search(r"## Self-check questions[^\n]*\n(.*?)(?=\n## |\Z)", t, re.S)
        bad = [l for l in (sec.group(1).splitlines() if sec else []) if re.match(r"\s*\d+\.", l) and not re.search(r"\*[^*]+\*\s*$", l)]
        if bad:
            nh.append(f"{note.name}: {len(bad)} self-check question(s) without an *answer*")
    out += [f"- {x}" for x in nh] or ["- no problems found"]
    problems += nh

out.append("\n## What this check cannot see\n- Only Lessons content (the outline). Assignments, Quizzes, Discussions, Announcements, Media Library are separate tools.\n"
           "- Items hidden by release conditions or dates are not visible to your account until released.\n"
           "- It checks completeness and signs of truncation, not whether a note's wording is right (read the Gaps section of each note).")
(base / "COVERAGE.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"{total[0]}/{total[1]} topics captured. wrote {base / 'COVERAGE.md'}")
if problems:
    print(f"{len(problems)} thing(s) need attention:")
    print("\n".join(f"  - {p}" for p in problems[:25]))
sys.exit(1 if problems else 0)
