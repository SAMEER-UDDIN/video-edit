#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Find where a B-roll's sharp band starts/ends in a rendered video (its blurred strips have almost no horizontal detail).

  uv run .claude/skills/stage-2-zooms-transitions/scripts/band_edges.py <video.mp4> <t1> [<t2> ...]

Prints the top / bottom row of the sharp band at each time (frame 1920 high). Use the top edge that repeats across times; the bottom edge can be
under-read when the picture is dark at the bottom. Look at a crop to confirm (ffmpeg -vf crop). Then: plan_zooms.py --lines "<cut>:<top>-<bottom>".
"""
import subprocess, sys
import numpy as np
v = sys.argv[1]
for t in map(float, sys.argv[2:]):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", v, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8)
    h = f.size // 1080; f = f.reshape(h, 1080).astype(float)
    g = np.convolve(np.abs(np.diff(f, axis=1)).mean(axis=1), np.ones(15) / 15, "same")
    rows = np.where(g > g[h // 2 - 100:h // 2 + 100].mean() * 0.5)[0]; rows = rows[(rows > 50) & (rows < h - 50)]
    d = np.diff(g)
    print(f"{t:7.2f}s  detail rows {rows.min()}..{rows.max()}   top edge ~{int(np.argmax(d[:h // 3]))}  bottom edge ~{int(2 * h // 3 + np.argmin(d[2 * h // 3:]))}")
