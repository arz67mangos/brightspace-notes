"""Turn [mm:ss] / [mm:ss-mm:ss] / [KEY mm:ss] citations in a note into links to the slide frame on screen at that time.

  python scripts/linkify.py <note.md> [more notes...]

The note's front matter declares its videos (one line each; KEY is only needed when a note has 2+ videos):
    video: P1 | Part 1 Law of Demand | assets/part1
`assets/part1` is the folder produced by video.py (relative to the note). Idempotent: re-run after editing.
Result: [Part 1 @02:10](assets/part1/frames/f003_02m05s.jpg)
"""
import re, sys
from pathlib import Path

import env  # noqa: F401  (UTF-8 output, PATH refresh)

CITE = re.compile(r"\[(?:([A-Za-z0-9]+)\s+)?(\d{1,2}):(\d{2})(?:\s*-\s*\d{1,2}:\d{2})?\](?!\()")


def frame_at(assets: Path, t: int):
    best = None
    for line in (assets / "frames.txt").read_text().splitlines():
        name, start, *_ = line.split("\t")
        if best is None or int(start) <= t:
            best = name
    return best


def linkify(note: Path):
    text = note.read_text(encoding="utf-8")
    head, sep, body = text.partition("\n---\n")  # front matter ends at the first "\n---\n" after the opening ---
    vids = [[x.strip() for x in l.split(":", 1)[1].split("|")] for l in head.splitlines() if l.startswith("video:")]
    if not vids:
        return print(f"{note.name}: no 'video:' lines in front matter, skipped")
    by_key = {v[0]: v for v in vids} if len(vids) > 1 else {None: vids[0]}
    if len(vids) == 1:
        by_key[vids[0][0]] = vids[0]

    def sub(m):
        v = by_key.get(m.group(1)) or by_key.get(None)
        if not v or (len(vids) > 1 and m.group(1) is None):
            return m.group(0)  # ambiguous cite in a multi-video note: leave as is
        _, label, folder = (v + [""] * 3)[:3]
        t = int(m.group(2)) * 60 + int(m.group(3))
        f = frame_at(note.parent / folder, t)
        shown = m.group(0)[1:-1].split(" ", 1)[-1] if m.group(1) else m.group(0)[1:-1]
        return f"[{label} @{shown}]({folder}/frames/{f})"

    in_code, out = False, []
    for line in body.split("\n"):
        if line.startswith("```"):
            in_code = not in_code
        out.append(line if in_code else CITE.sub(sub, line))
    note.write_text(head + sep + "\n".join(out), encoding="utf-8")
    print(f"{note.name}: linked {sum(1 for l in out if '](' in l and '@' in l)} line(s)")


for n in sys.argv[1:] or sys.exit(__doc__):
    linkify(Path(n)) if Path(n).is_file() else print(f"{n}: no such note, skipped")
