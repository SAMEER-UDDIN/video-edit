#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless", "numpy", "pillow"]
# ///
"""QA a head-tracking pass from the REAL Premiere export (never from AE preview grabs).

  uv run .claude/skills/stage-1-headtracking/scripts/qa_nose.py <export.mp4> projects/<job> --out "previews/" --name seq02-stage1

Measures on every 6th frame: nose position vs the target, per-clip max deviation, face width; at every cut, the nose on
the exact frame before vs the frame after (same-scene jump cuts vs scene changes); checks EVERY frame for black edges. Writes <name>-qa.json, <name>-contact-sheet.jpg (1 frame / 0.5 s, timestamps,
red cross = nose target) and <name>-preview-540p.mp4 into --out.
Pass marks: nose within ~45 px of target, same-scene cut shift median <= ~15 px (Seq02: 12 px; Sameer's own same-person
cuts: 7-35 px), 0 black frames.
"""
import argparse, glob, json, os, shutil, subprocess
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
cv2.setLogLevel(0) if hasattr(cv2, "setLogLevel") else None

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
MODEL = os.path.join(REPO, "assets", "models", "face_detection_yunet_2023mar.onnx")
FFMPEG = shutil.which("ffmpeg") or next(iter(glob.glob(os.path.expandvars(
    r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe"))), "ffmpeg")

ap = argparse.ArgumentParser()
ap.add_argument("export"); ap.add_argument("job"); ap.add_argument("--out", required=True); ap.add_argument("--name", required=True)
a = ap.parse_args()
seq = json.load(open(os.path.join(a.job, "clips.json"), encoding="utf-8"))
cfg_p = os.path.join(a.job, "headtrack.json")
cfg = json.load(open(cfg_p, encoding="utf-8")) if os.path.exists(cfg_p) else {}
W, H = seq["width"], seq["height"]
NOSE = tuple(cfg.get("nose", [W / 2, H * 925 / 1920])); SKIP = set(cfg.get("skip", []))
clips = seq["clips"]; os.makedirs(a.out, exist_ok=True)

cap = cv2.VideoCapture(a.export); fps = cap.get(cv2.CAP_PROP_FPS); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
det = cv2.FaceDetectorYN.create(MODEL, "", (W // 2, H // 2), 0.6, 0.3, 50)
samples, black, sheet = [], [], {}
for f in range(n):
    ok, fr = cap.read()
    if not ok: break
    t = f / fps
    if fr.shape[1] != W: fr = cv2.resize(fr, (W, H))
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    if min(g[:3].mean(), g[-3:].mean(), g[:, :3].mean(), g[:, -3:].mean()) < 4: black.append(round(t, 3))
    if abs(t * 2 - round(t * 2)) < 0.5 / fps * 2 and round(t * 2) not in sheet: sheet[round(t * 2)] = cv2.resize(fr, (216, 384))
    if f % 6: continue
    _, r = det.detect(cv2.resize(fr, (W // 2, H // 2)))
    if r is None or not len(r): samples.append((t, None)); continue
    r = max(r, key=lambda x: x[2] * x[3]); samples.append((t, (r[8] * 2, r[9] * 2, r[2] * 2)))

def clip_of(t):
    for c in clips:
        if c["seq_start"] <= t < c["seq_end"]: return c["i"]
    return clips[-1]["i"]
per = {}
for t, v in samples:
    if v: per.setdefault(clip_of(t), []).append((t, v))
rep = {"target": NOSE, "clips": [], "cuts": [], "black_frames": black,
       "no_face": [round(t, 2) for t, v in samples if v is None and clip_of(t) not in SKIP]}
for c in clips:
    s = per.get(c["i"], [])
    if not s: rep["clips"].append({"clip": c["i"], "faces": 0}); continue
    dev = max(float(np.hypot(v[0] - NOSE[0], v[1] - NOSE[1])) for _, v in s)
    rep["clips"].append({"clip": c["i"], "nose_median": [round(float(np.median([v[0] for _, v in s]))), round(float(np.median([v[1] for _, v in s])))],
                         "max_dev_px": round(dev), "face_width": round(float(np.median([v[2] for _, v in s])) / W, 3), "skipped": c["i"] in SKIP})
# frame-exact: the nose on the last frame before each cut vs the first frame after it
det_full = cv2.FaceDetectorYN.create(MODEL, "", (W, H), 0.6, 0.3, 50)
def nose_at_frame(f):
    cap.set(cv2.CAP_PROP_POS_FRAMES, f); ok, fr = cap.read()
    if not ok: return None
    if fr.shape[1] != W: fr = cv2.resize(fr, (W, H))
    _, r = det_full.detect(fr)
    if r is None or not len(r): return None
    r = max(r, key=lambda x: x[2] * x[3]); return (float(r[8]), float(r[9]))
for c0, c1 in zip(clips, clips[1:]):
    if c0["i"] in SKIP or c1["i"] in SKIP: continue
    f = int(round(c1["seq_start"] * fps)); A, B = nose_at_frame(f - 1), nose_at_frame(f)
    if A and B:
        same = os.path.basename(c0["path"]) == os.path.basename(c1["path"])
        rep["cuts"].append({"cut": f"{c0['i']}->{c1['i']}", "at": round(c1["seq_start"], 3), "same_source": same,
                            "jump_px": round(float(np.hypot(A[0] - B[0], A[1] - B[1])))})
same_j = [c["jump_px"] for c in rep["cuts"] if c["same_source"]]
rep["cut_jump_median_same_source"] = int(np.median(same_j)) if same_j else None
json.dump(rep, open(os.path.join(a.out, a.name + "-qa.json"), "w"), indent=1)

# contact sheet: 1 frame / 0.5 s, timestamp labels, red cross at the nose target
keys = sorted(sheet); cols, tw, th, lab = 10, 216, 384, 26
img = Image.new("RGB", (cols * tw, ((len(keys) + cols - 1) // cols) * (th + lab)), (16, 16, 16)); d = ImageDraw.Draw(img)
try: font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 18)
except OSError: font = ImageFont.load_default()
cx, cy = NOSE[0] / W * tw, NOSE[1] / H * th
for j, kk in enumerate(keys):
    x, y = (j % cols) * tw, (j // cols) * (th + lab)
    img.paste(Image.fromarray(cv2.cvtColor(sheet[kk], cv2.COLOR_BGR2RGB)), (x, y + lab))
    d.text((x + 6, y + 3), f"{kk / 2:04.1f}s", font=font, fill=(255, 214, 10))
    d.line([(x + cx - 6, y + lab + cy), (x + cx + 6, y + lab + cy)], fill=(255, 0, 0)); d.line([(x + cx, y + lab + cy - 6), (x + cx, y + lab + cy + 6)], fill=(255, 0, 0))
img.save(os.path.join(a.out, a.name + "-contact-sheet.jpg"), quality=88)
subprocess.run([FFMPEG, "-v", "error", "-y", "-i", a.export, "-vf", "scale=540:960,fps=30000/1001", "-c:v", "libx264", "-preset", "medium",
                "-crf", "26", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", os.path.join(a.out, a.name + "-preview-540p.mp4")], check=True)

print(f"target nose {NOSE}")
for r in rep["clips"]:
    if r.get("faces") == 0: print(f"  #{r['clip']:2d}  no face found"); continue
    print(f"  #{r['clip']:2d}  nose {r['nose_median']}  max dev {r['max_dev_px']:4d}px  face {r['face_width']:.0%}{'  (skipped)' if r['skipped'] else ''}")
print("  cuts (frame-exact nose shift): " + ", ".join(f"{c['cut']} {c['jump_px']}px{'' if c['same_source'] else ' [scene change]'}" for c in rep["cuts"]))
print(f"  median shift on same-scene cuts: {rep['cut_jump_median_same_source']}px  (Seq02 reference: 12px)")
print(f"  black-edge frames: {len(black)}   no-face samples: {rep['no_face'][:10]}")
print(f"wrote {a.name}-qa.json, -contact-sheet.jpg, -preview-540p.mp4 in {a.out}")
