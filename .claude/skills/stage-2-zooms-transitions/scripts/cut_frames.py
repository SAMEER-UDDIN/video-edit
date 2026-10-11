#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Step 3: where does the PICTURE actually change at each cut? (Razor marks and picture changes can differ.)

  uv run .claude/skills/stage-2-zooms-transitions/scripts/cut_frames.py projects/<job> [--adobe-offset 1]

For every boundary between consecutive clips in <job>/clips.json, decodes 13 frames around it (ffmpeg, in decode order) and
takes the frame with the biggest change. Weak changes (a static jump cut, diff < 3) take the median offset of the strong
ones. --adobe-offset = how many frames LATER Adobe shows the same picture than ffmpeg decodes it (Seq02's 2_2.mp4: 1;
VERIFY it on the strongest cut with ae_render_frame on the two frames around it before trusting it).
Writes <job>/ae/cut-frames.json: [{"cut": n, "razor": s, "picture": s, "offset_frames": k, "strength": d, "measured": bool}]
"""
import argparse, glob, json, os, shutil, subprocess
import numpy as np

FFMPEG = shutil.which("ffmpeg") or next(iter(glob.glob(os.path.expandvars(
    r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe"))), "ffmpeg")
ap = argparse.ArgumentParser(); ap.add_argument("job"); ap.add_argument("--adobe-offset", type=int, default=0)
a = ap.parse_args()
seq = json.load(open(os.path.join(a.job, "clips.json"), encoding="utf-8"))
fps = seq["fps"]; clips = seq["clips"]; rows = []
for k in range(1, len(clips)):
    c = clips[k]; razor = c["seq_start"]; src_t = c["src_in"]           # picture change happens in THIS clip's source
    rf = round(src_t * fps); f0 = rf - 6
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", c["path"], "-vf", f"select='between(n\\,{f0}\\,{f0 + 12})',scale=108:192,format=gray",
                          "-fps_mode", "passthrough", "-f", "rawvideo", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 192, 108).astype(float)
    d = [np.abs(fr[i] - fr[i - 1]).mean() for i in range(1, len(fr))]
    j = int(np.argmax(d)) + 1
    rows.append({"cut": k + 1, "razor": round(razor, 5), "razor_src_frame": int(rf), "change_src_frame": int(f0 + j), "strength": round(float(max(d)), 1)})
strong = [r["change_src_frame"] - r["razor_src_frame"] for r in rows if r["strength"] >= 3]
med = int(np.median(strong)) if strong else 0
for r in rows:
    r["measured"] = bool(r["strength"] >= 3); r["strength"] = float(r["strength"])
    off = (r["change_src_frame"] - r["razor_src_frame"]) if r["measured"] else med
    r["offset_frames"] = int(off + a.adobe_offset)
    r["picture"] = round(r["razor"] + r["offset_frames"] / fps, 5)
json.dump(rows, open(os.path.join(a.job, "ae", "cut-frames.json"), "w"), indent=1)
for r in rows:
    print(f"cut {r['cut']}: razor {r['razor']:.4f}  picture {r['picture']:.4f}  ({r['offset_frames']:+d} frames, "
          f"{'measured' if r['measured'] else 'weak change, median offset'}, strength {r['strength']})")
