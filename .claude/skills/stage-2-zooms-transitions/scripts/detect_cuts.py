#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Where does the PICTURE change at each cut of a RENDERED video, and which frames around it are Premiere's Morph Cut blend?

  uv run .claude/skills/stage-2-zooms-transitions/scripts/detect_cuts.py projects/<job> <render.mp4> [--cuts f1 f2 ...]

<render.mp4> = the Stage 1 render he put in the comp (1.mp4 / 2.mp4). Cut positions come from <job>/clips.json (clip boundaries, comp frames
= seq_start * fps) unless --cuts is given (frame numbers). For every cut it decodes the video (108x192 gray, every frame) and:
  * picture frame p   = the frame with the biggest change within +-3 of the razor frame r (Seq01: always r+1, except where the
                        picture really changes on the razor, e.g. the first cut); weak (static jump cut) cuts take the median offset of the strong ones
  * morph window      = the Morph Cut renders ~5 blended frames: change spikes at p-2, p, p+2 (sometimes p-3..p+2).
                        L = last clean frame of the OLD clip (p-3, or p-4 when the spike starts at p-3)
                        S = first clean frame of the NEW clip (p+2)
                        weak / unreadable cuts fall back to L = p-3, S = p+2 (what he removed by hand on every cut)
Writes <job>/ae/picture-cuts.json: [{"cut": k, "razor": r, "picture": p, "L": .., "S": .., "strength": .., "measured": bool}]
(frame numbers at the render's fps). Feed it to prep_stage2.py.
"""
import json, os, subprocess, sys
import numpy as np

args = sys.argv[1:]
job, video = os.path.abspath(args[0]), args[1]
cuts = [int(x) for x in args[args.index("--cuts") + 1:]] if "--cuts" in args else None
seq = json.load(open(os.path.join(job, "clips.json"), encoding="utf-8"))
fps = seq["fps"]
if cuts is None:
    cuts = [round(c["seq_start"] * fps) for c in seq["clips"][1:]]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "scale=108:192,format=gray", "-fps_mode", "passthrough", "-f", "rawvideo", "-"],
                     capture_output=True).stdout
F = np.frombuffer(raw, np.uint8).reshape(-1, 192, 108).astype(float)
d = np.r_[0, [np.abs(F[i] - F[i - 1]).mean() for i in range(1, len(F))]]
rows = []
for k, r in enumerate(cuts, 1):
    w = range(max(1, r - 3), min(len(d), r + 4)); p = max(w, key=lambda i: d[i])
    rows.append({"cut": k, "razor": int(r), "picture": int(p), "strength": round(float(d[p]), 1), "measured": bool(d[p] >= 3)})
strong = [x["picture"] - x["razor"] for x in rows if x["measured"]]
med = int(np.median(strong)) if strong else 0
for x in rows:
    if not x["measured"]: x["picture"] = x["razor"] + med
    p = x["picture"]; m = max(d[i] for i in range(p - 6, p + 7)); thr = max(4.0, 0.2 * m)
    pre = [i for i in range(p - 4, p) if d[i] > thr]; post = [i for i in range(p, p + 3) if d[i] > thr]
    if m < 4 or len(pre) + len(post) < 2: x["L"], x["S"] = p - 3, p + 2
    else: x["L"], x["S"] = (min(pre) - 1 if pre else p - 3), (max(post) if post else p + 2)
os.makedirs(os.path.join(job, "ae"), exist_ok=True)
json.dump(rows, open(os.path.join(job, "ae", "picture-cuts.json"), "w"), indent=1)
for x in rows:
    print(f"cut {x['cut']:2d} razor {x['razor']:5d} picture {x['picture']:5d} ({x['picture'] - x['razor']:+d})  morph keep <= {x['L']} / >= {x['S']}  strength {x['strength']}{'' if x['measured'] else '  (weak: defaults)'}")
print(f"wrote {os.path.join(job, 'ae', 'picture-cuts.json')}  ({len(rows)} cuts, {len(F)} frames)")
