"""Video -> transcript + one frame per distinct slide + per-slide narration.

  python scripts/video.py <video-url-or-file> <outdir> [--cookies cookies.txt] [--step 2] [--sim 0.04]

Writes into <outdir>:
  transcript.md   timestamped, deduped subtitles (soft subs next to/under outdir, else faster-whisper speech-to-text)
  frames/         one jpg per distinct slide: f<n>_<mm>m<ss>s.jpg (time = when that slide first appeared; the jpg is
                  its LAST sample, i.e. most built-up version)
  sheets/         sheetNN.jpg contact sheets of 4 frames each (read these first, open single frames for detail)
  frames.txt      file, start s, end s, sheet cell
  slides.md       per slide: frame link + the narration spoken while it was up (start here)

How slides are not missed: the video is sampled every --step seconds (not scene detection), and a new frame is
kept whenever the picture (bottom 14% ignored, so hard subtitles don't count) differs from the slide before by more
than --sim of the hash bits. Lower --sim (0.02) to catch tiny changes such as one bullet appearing.
"""
import argparse, re, shutil, subprocess, sys
from pathlib import Path

import webvtt
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out")
ap.add_argument("--cookies")
ap.add_argument("--step", type=float, default=2.0)
ap.add_argument("--sim", type=float, default=0.04)
ap.add_argument("--keep-video", action="store_true")  # by default a video downloaded by yt-dlp is deleted after its frames are taken
ap.add_argument("--whisper-model", default="base.en")  # only used when no subtitles exist; small.en is more accurate
a = ap.parse_args()

out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
src = a.src
mmss = lambda s: f"{int(s) // 60:02d}:{int(s) % 60:02d}"

if re.match(r"https?://", src) and ".m3u8" not in src:  # m3u8/mp4 manifests: ffmpeg reads them directly
    cmd = [sys.executable, "-m", "yt_dlp", "-f", "best[height<=720]/best", "--write-subs", "--write-auto-subs",
           "--sub-langs", "en.*,en", "--sub-format", "vtt", "-o", str(out / "video.%(ext)s"), src]
    if a.cookies:
        cmd[3:3] = ["--cookies", a.cookies]
    subprocess.run(cmd, check=True)
    vids = [f for f in out.glob("video.*") if f.suffix not in (".vtt", ".part")]
    if not vids:
        sys.exit("yt-dlp produced no video")
    src = str(vids[0])
    downloaded = vids[0]
else:
    downloaded = None

# ---- transcript: [(seconds, text)] ----
subs = sorted([*out.glob("*.vtt"), *out.glob("*.srt")]) or sorted(Path(src).parent.glob(Path(src).stem + "*.vtt"))
rows = []
if subs:
    recent = []  # YouTube-style rolling captions repeat the previous line in every cue: keep each line once
    for cue in (webvtt.from_srt if subs[0].suffix == ".srt" else webvtt.read)(str(subs[0])):
        h, m, s = cue.start.replace(",", ".").split(":")
        for ln in cue.text.split("\n"):
            t = " ".join(ln.split())
            if t and t not in recent:
                rows.append((int(h) * 3600 + int(m) * 60 + float(s), t))
                recent = (recent + [t])[-4:]
    print(f"transcript: {len(rows)} lines from {subs[0].name}")
else:
    print("no soft subtitles: transcribing speech with faster-whisper (first run downloads the model)")
    import numpy as np
    from faster_whisper import WhisperModel

    # raw 16 kHz mono floats via ffmpeg: avoids faster-whisper's PyAV decoder (breaks on av>=19)
    pcm = subprocess.run(["ffmpeg", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = WhisperModel(a.whisper_model, compute_type="int8").transcribe(np.frombuffer(pcm, np.float32), vad_filter=True)
    rows = [(s.start, s.text.strip()) for s in segs]
    print(f"transcript: {len(rows)} lines (whisper, no subs available)")
(out / "transcript.md").write_text("\n".join(f"[{mmss(s)}] {t}" for s, t in rows) + "\n", encoding="utf-8")

# ---- frames: sample densely, keep one per distinct slide ----
cand = out / "_cand"
shutil.rmtree(cand, ignore_errors=True)
cand.mkdir()
subprocess.run(["ffmpeg", "-y", "-i", src, "-vf", f"fps=1/{a.step}", "-q:v", "3", str(cand / "c%05d.jpg")], capture_output=True)
files = sorted(cand.glob("c*.jpg"))
if not files:
    sys.exit("ffmpeg produced no frames (video unreadable or expired URL?)")


def dhash(p):  # 16x16 difference hash of the top 86% of the frame (captions burned in below are ignored)
    g = Image.open(p).convert("L")
    w, h = g.size
    px = list(g.crop((0, 0, w, int(h * 0.86))).resize((17, 16)).getdata())
    return [px[r * 17 + c] > px[r * 17 + c + 1] for r in range(16) for c in range(16)]


runs = []  # {"h": hash of first sample, "first": idx, "last": idx}
for i, f in enumerate(files):
    h = dhash(f)
    if runs and sum(x != y for x, y in zip(h, runs[-1]["h"])) / 256 <= a.sim:
        runs[-1]["last"] = i
    else:
        runs.append({"h": h, "first": i, "last": i})

fr = out / "frames"
sh = out / "sheets"
for d in (fr, sh):
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir()
slides = []  # (n, name, start, end)
for n, r in enumerate(runs, 1):
    start, end = r["first"] * a.step, (r["last"] + 1) * a.step
    name = f"f{n:03d}_{int(start) // 60:02d}m{int(start) % 60:02d}s.jpg"
    shutil.copy(files[r["last"]], fr / name)
    slides.append((n, name, start, end))
shutil.rmtree(cand)

try:
    font = ImageFont.load_default(size=28)
except TypeError:
    font = ImageFont.load_default()
CELL = 640
cells = {}
for k in range(0, len(slides), 4):
    group = slides[k : k + 4]
    ims = []
    for n, name, start, _ in group:
        im = Image.open(fr / name).convert("RGB")
        im = im.resize((CELL, int(im.height * CELL / im.width)))
        cell = Image.new("RGB", (CELL, im.height + 36), "black")  # label strip above the slide, never over it
        ImageDraw.Draw(cell).text((6, 2), f"#{n}  {mmss(start)}", fill="yellow", font=font)
        cell.paste(im, (0, 36))
        ims.append(cell)
    rh = max(i.height for i in ims)
    sheet = Image.new("RGB", (CELL * 2, rh * 2), "white")
    for j, im in enumerate(ims):
        sheet.paste(im, ((j % 2) * CELL, (j // 2) * rh))
        cells[group[j][0]] = f"sheet{k // 4 + 1:02d}.jpg cell {j + 1}"
    sheet.save(sh / f"sheet{k // 4 + 1:02d}.jpg", quality=85)

(out / "frames.txt").write_text("\n".join(f"{nm}\t{s:.0f}\t{e:.0f}\t{cells[n]}" for n, nm, s, e in slides) + "\n")

md = ["# Slides and narration (frame = slide at its most built-up; times in mm:ss)\n"]
for idx, (n, name, start, end) in enumerate(slides):
    nxt = slides[idx + 1][2] if idx + 1 < len(slides) else float("inf")
    brief = " (brief, likely a transition)" if end - start <= a.step else ""
    md.append(f"\n## Slide {n} [{mmss(start)}-{mmss(end)}]{brief} ![](frames/{name})")
    md += [f"[{mmss(s)}] {t}" for s, t in rows if (start if idx else 0) <= s < nxt]
(out / "slides.md").write_text("\n".join(md) + "\n", encoding="utf-8")
if downloaded and not a.keep_video:
    downloaded.unlink()  # frames + transcript are all that's needed; don't leave big video files in the notes
print(f"{len(slides)} distinct slides (from {len(files)} samples) -> frames/, sheets/, slides.md")
