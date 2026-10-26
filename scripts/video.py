"""Video -> transcript + scene-change keyframes.

  python scripts/video.py <video-url-or-file> <outdir> [--cookies cookies.txt] [--scene 0.3] [--max-frames 60]

Writes <outdir>/transcript.md (timestamped, deduped) and <outdir>/frames/*.jpg (+ frames.txt with times).
Soft subs come from yt-dlp. No soft subs -> transcript.md is skipped and you're told; hard subs / slide
text are read from the keyframes by Claude (view the images). Speech-to-text fallback: see SKILL.md.
"""
import argparse, re, subprocess, sys
from pathlib import Path

import webvtt

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out")
ap.add_argument("--cookies")
ap.add_argument("--scene", default="0.08")  # slide decks change little between frames; 0.3 missed most of them
ap.add_argument("--max-frames", type=int, default=60)
ap.add_argument("--whisper-model", default="base.en")  # used only when no subtitles exist; try small.en for accuracy
a = ap.parse_args()

out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
src = a.src

if re.match(r"https?://", src) and ".m3u8" not in src:  # m3u8: ffmpeg reads HLS directly
    cmd = [sys.executable, "-m", "yt_dlp", "-f", "best[height<=720]/best", "--write-subs", "--write-auto-subs",
           "--sub-langs", "en.*,en", "--sub-format", "vtt", "-o", str(out / "video.%(ext)s"), src]
    if a.cookies:
        cmd[3:3] = ["--cookies", a.cookies]
    subprocess.run(cmd, check=True)
    vids = [f for f in out.glob("video.*") if f.suffix not in (".vtt", ".part")]
    if not vids:
        sys.exit("yt-dlp produced no video")
    src = str(vids[0])

# transcript from first .vtt found (prefer manual subs over auto: sorted puts 'en.vtt' before 'en-orig' etc.)
vtts = sorted([*out.glob("*.vtt"), *out.glob("*.srt")]) or sorted(Path(src).parent.glob(Path(src).stem + "*.vtt"))
if vtts:
    last, rows = "", []
    for cue in (webvtt.from_srt if vtts[0].suffix == ".srt" else webvtt.read)(str(vtts[0])):
        t = " ".join(cue.text.split())
        if t and t != last:
            rows.append(f"[{cue.start.split('.')[0]}] {t}")
            last = t
    (out / "transcript.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"transcript: {len(rows)} lines from {vtts[0].name}")
else:
    print("no soft subtitles: transcribing speech with faster-whisper (first run downloads the model)")
    from faster_whisper import WhisperModel

    import numpy as np

    # raw 16 kHz mono floats via ffmpeg: avoids faster-whisper's PyAV decoder (breaks on av>=19)
    pcm = subprocess.run(["ffmpeg", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = WhisperModel(a.whisper_model, compute_type="int8").transcribe(np.frombuffer(pcm, np.float32), vad_filter=True)
    rows = [f"[{int(s.start) // 3600:02d}:{int(s.start) // 60 % 60:02d}:{int(s.start) % 60:02d}] {s.text.strip()}" for s in segs]
    (out / "transcript.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"transcript: {len(rows)} lines (whisper, no subs available)")

# keyframes on scene change; showinfo gives timestamps on stderr
fr = out / "frames"
fr.mkdir(exist_ok=True)
for old in fr.glob("*.jpg"):
    old.unlink()
r = subprocess.run(["ffmpeg", "-y", "-i", src, "-vf", f"select='gt(scene,{a.scene})+isnan(prev_selected_t)+gte(t-prev_selected_t,45)',showinfo", "-fps_mode", "vfr",
                    "-q:v", "3", str(fr / "f%04d.jpg")], capture_output=True, text=True)
times = re.findall(r"pts_time:([\d.]+)", r.stderr)
shots = sorted(fr.glob("f*.jpg"))
# cap frames: keep an evenly spaced subset
if len(shots) > a.max_frames:
    keep = {shots[int(i * len(shots) / a.max_frames)] for i in range(a.max_frames)}
    for s in shots:
        if s not in keep:
            s.unlink()
shots = sorted(fr.glob("f*.jpg"))
if not shots:  # static slides / low motion: fall back to one frame per 30s
    subprocess.run(["ffmpeg", "-y", "-i", src, "-vf", "fps=1/30", "-q:v", "3", str(fr / "f%04d.jpg")],
                   capture_output=True)
    shots = sorted(fr.glob("f*.jpg"))
    times = [str(i * 30) for i in range(len(shots))]
by_idx = {f"f{i + 1:04d}.jpg": t for i, t in enumerate(times)}
(out / "frames.txt").write_text("\n".join(f"{s.name}\t{float(by_idx.get(s.name, 0)):.1f}s" for s in shots) + "\n")
print(f"{len(shots)} keyframes in {fr}")
