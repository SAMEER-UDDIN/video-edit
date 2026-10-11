#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless", "numpy"]
# ///
"""
Fight Club face tracker: where is the face, over time, in each source clip?

Feeds the channel's tight vertical reframe + face-tracked push-in (README § Look). Samples each clip
at --fps (default 10), runs OpenCV YuNet (assets/models/), keeps the most confident face per sample
(optionally the one nearest --prefer-x, e.g. 0.3 for "the left person"), and writes
  {clip: {"w":1920,"h":1080,"samples":[[t, cx, cy, fw, score], ...]}}   (cx/cy/fw normalized 0..1)
Missing detections are simply absent; consumers interpolate.

  uv run presets/youtube/fight-club/face-track.py projects/<job>/raw/*.mp4 --out projects/<job>/assets/faces.json
"""
import argparse, json, os, sys
import cv2, numpy as np
cv2.setLogLevel(0) if hasattr(cv2, "setLogLevel") else None

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "..", "..", "..", "assets", "models", "face_detection_yunet_2023mar.onnx")

def track(path, fps, prefer_x=None):
    cap = cv2.VideoCapture(path)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    scale = 640 / w
    det = cv2.FaceDetectorYN.create(MODEL, "", (640, int(h * scale)), 0.7, 0.3, 50)
    step = max(1, int(round(src_fps / fps)))
    out, i = [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % step == 0:
            ok, f = cap.retrieve()
            if ok:
                sm = cv2.resize(f, (640, int(h * scale)))
                _, faces = det.detect(sm)
                if faces is not None and len(faces):
                    if prefer_x is not None:
                        faces = sorted(faces, key=lambda r: abs((r[0] + r[2] / 2) / 640 - prefer_x) - r[14] * 0.1)
                    else:
                        faces = sorted(faces, key=lambda r: -(r[2] * r[3]) * r[14])
                    x, y, fw, fh, score = faces[0][0], faces[0][1], faces[0][2], faces[0][3], faces[0][14]
                    out.append([round(i / src_fps, 3), round(float((x + fw / 2) / 640), 4),
                                round(float((y + fh / 2) / (h * scale)), 4), round(float(fw / 640), 4), round(float(score), 3)])
        i += 1
    cap.release()
    return {"w": w, "h": h, "fps": round(src_fps, 3), "samples": out}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--fps", type=float, default=10)
    ap.add_argument("--prefer-x", type=float)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = json.load(open(a.out)) if os.path.exists(a.out) else {}
    for c in a.clips:
        r = track(c, a.fps, a.prefer_x)
        res[os.path.basename(c)] = r
        s = r["samples"]
        if s:
            cx = np.median([x[1] for x in s]); fw = np.median([x[3] for x in s])
            print(f"{os.path.basename(c):32s} {len(s):4d} hits  median cx={cx:.3f}  face w={fw:.3f}")
        else:
            print(f"{os.path.basename(c):32s} no face")
    json.dump(res, open(a.out, "w"), indent=0)
