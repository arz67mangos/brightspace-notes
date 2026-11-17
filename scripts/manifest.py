"""Reference manifest: what a complete course set contains, so another install can check itself against it.

  python scripts/manifest.py make  notes/ out.json     per course: module folders, topic titles, video/doc/page-image counts
  python scripts/manifest.py check notes/ out.json     compare this install to a manifest; exit 1 if anything is missing

Titles are read from each note's front matter (`topic:`), so folder naming can differ. The manifest holds course and
topic titles only (no note text, no URLs): share it privately, don't commit it.
"""
import env  # noqa: F401
import json, re, sys
from pathlib import Path

norm = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
SKIP = {"assets", "_raw", "sheets", "frames"}


def scan(root):
    out = {}
    for c in sorted(p for p in Path(root).iterdir() if p.is_dir() and not p.name.isdigit()):
        topics, videos, docs = [], 0, 0
        for f in c.rglob("*.md"):
            if "assets" in f.parts or "_raw" in f.parts:
                continue
            m = re.search(r"^topic: (.*)$", f.read_text(encoding="utf-8", errors="replace")[:1500], re.M)
            if m:
                topics.append(m.group(1).strip())
        for a in c.rglob("assets"):
            for d in (x for x in a.iterdir() if x.is_dir()):
                if (d / "slides.md").exists():
                    videos += 1
                else:
                    docs += sum(1 for _ in d.glob("*.md"))
        out[c.name] = {"topics": sorted(set(topics)), "videos": videos, "docs": docs,
                       "has": [n for n in ("MASTER.md", "TIMELINE.md", "INDEX.md", "GLOSSARY.md", "EXAM_FOCUS.md") if (c / n).exists()]}
    return out


def main(cmd, root, ref):
    cur = scan(root)
    if cmd == "make":
        Path(ref).write_text(json.dumps(cur, indent=1, ensure_ascii=False), encoding="utf-8")
        for k, v in cur.items():
            print(f'{k}: {len(v["topics"])} topic notes, {v["videos"]} videos, {v["docs"]} converted documents')
        return 0
    want, bad = json.loads(Path(ref).read_text(encoding="utf-8")), 0
    for k, w in want.items():
        have = cur.get(k)
        if not have:
            print(f"[MISSING COURSE] {k}")
            bad += 1
            continue
        got = {norm(t) for t in have["topics"]}
        miss = [t for t in w["topics"] if norm(t) not in got]
        short = [f"{n} {have[n]}/{w[n]}" for n in ("videos", "docs") if have[n] < w[n]]
        gaps = [f"no {n}" for n in w["has"] if n not in have["has"]]
        if miss or short or gaps:
            bad += 1
            print(f"[GAPS] {k}: {len(miss)} topic notes missing; {', '.join(short + gaps) or 'counts ok'}")
            for t in miss:
                print(f"   - {t}")
        else:
            print(f"[OK] {k}: {len(w['topics'])} topics, {w['videos']} videos, {w['docs']} documents")
    print("\nA topic that is missing may be named differently or not released to you; list those under Gaps, don't invent notes.")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] not in ("make", "check"):
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
