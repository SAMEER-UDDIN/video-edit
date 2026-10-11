#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless", "numpy"]
# ///
"""Sameer's head-tracking method, built in After Effects (see ../SKILL.md and docs/fight-club/headtracking-method.md).

  uv run .claude/skills/stage-1-headtracking/scripts/build_nose_track.py projects/<job>

Reads <job>/clips.json (premiere_clips.py) and optional <job>/headtrack.json, writes <job>/ae/headtrack.jsx (run it with
the after-effects MCP: ae_run_jsx {"file": ...}) and <job>/ae/headtrack-report.json.

ONE LAYER PER SCENE (2026-10-06, Sameer: "dont cut a clip unless the scene is changing"). A scene = consecutive clips
of the same camera shot (same source + same scale group). Each scene is one AE layer:
  * the nose is tracked CONTINUOUSLY over the scene's whole source span (53x50 patch, pyramidal Lucas-Kanade per
    source frame, gentle YuNet drift correction / re-seed) — no restart at the editor's cuts
  * Time Remap reproduces the editor's cut exactly (segment keys linear at speed 1, HOLD into each cut), so the
    picture stays in sync with his audio in Premiere
  * Anchor Point keys = the nose of the frame on screen; HOLD into each cut so nothing slides across a cut
  * Position CONSTANT = the shared nose point (every cut nose-matched); Scale CONSTANT per scale group
    = max(fill x 1.0558 [his 187.7 % on 1080p], smallest scale keeping burned-in banners out); no zoom, no blur
  * Motion Tile: Output >= 100 W x 120 H (raised only if the motion needs it), Mirror Edges on

headtrack.json (all optional):
  {"comp": "Seq Headtrack", "nose": [540, 925], "fill_ratio": 1.0558, "patch": [53, 50],
   "prefer_x": {"<source basename>": 0.42},          # which person to lock onto (0..1 across the source)
   "banners":  {"<source basename>": ["bottom", 897]},  # burned-in graphics to keep out: edge + source-px line
   "groups":   {"4": "dana-wide"},                    # clip index -> scale group (a different framing = a new scene)
   "skip":     [7],                                   # clips NOT to track (B-roll/stills): fill + Motion Tile only
   "max_span": 180}                                   # longest source span tracked in one pass (s); else per clip + 1 s pre-roll
"""
import json, math, os, sys
import cv2, numpy as np
cv2.setLogLevel(0) if hasattr(cv2, "setLogLevel") else None

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
MODEL = os.path.join(REPO, "assets", "models", "face_detection_yunet_2023mar.onnx")

job = os.path.abspath(sys.argv[1])
seq = json.load(open(os.path.join(job, "clips.json"), encoding="utf-8"))
cfg_p = os.path.join(job, "headtrack.json")
cfg = json.load(open(cfg_p, encoding="utf-8")) if os.path.exists(cfg_p) else {}
W, H, FPS, DUR = seq["width"], seq["height"], seq["fps"], seq["duration"]
FD = 1.0 / FPS
NOSE = tuple(cfg.get("nose", [W / 2, H * 925 / 1920]))
FILL_RATIO = cfg.get("fill_ratio", 187.7 / (100 * 1920 / 1080))
PATCH = cfg.get("patch", [53, 50])
PREFER_X, BANNER = cfg.get("prefer_x", {}), cfg.get("banners", {})
GROUPS, SKIP = {int(k): v for k, v in cfg.get("groups", {}).items()}, set(cfg.get("skip", []))
MAX_SPAN = cfg.get("max_span", 180)
COMP = cfg.get("comp", seq["sequence"] + " Headtrack")
clips = seq["clips"]

def yunet(det, frame, prefer_x, prev=None):
    _, fs = det.detect(frame)
    if fs is None or not len(fs): return None
    h, w = frame.shape[:2]
    if prev is not None:
        f = min(fs, key=lambda r: math.hypot(r[8] - prev[0], r[9] - prev[1]))
        if math.hypot(f[8] - prev[0], f[9] - prev[1]) > 0.12 * w: return None
    else:
        f = max(fs, key=lambda r: r[2] * r[3] * r[14] - 0.006 * w * h * abs((r[0] + r[2] / 2) / w - prefer_x))
    return (float(f[8]), float(f[9]), float(f[2]))

def track(path, t0, t1, prefer_x):
    """nose per source frame over [t0, t1], continuous. Returns (sw, sh, fps, times[], xs[], ys[], reseeds, lost)."""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS); sw, sh = int(cap.get(3)), int(cap.get(4))
    det = cv2.FaceDetectorYN.create(MODEL, "", (sw, sh), 0.6, 0.3, 50)
    f0, f1 = max(0, int(math.floor(t0 * fps))), int(math.ceil(t1 * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, f0)
    pw, ph = int(PATCH[0] * sh / 1080), int(PATCH[1] * sh / 1080)
    lk = dict(winSize=(max(15, pw | 1), max(15, ph | 1)), maxLevel=3,
              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    pts, prev_g, p, reseeds, lost = [], None, None, 0, 0
    for fi in range(f0, f1 + 1):
        ok, fr = cap.read()
        if not ok: break
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        y = yunet(det, fr, prefer_x, p)
        if p is None:
            if y is not None: p = np.array(y[:2], np.float32)
            else: lost += 1
        else:
            nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev_g, g, p.reshape(1, 1, 2), None, **lk)
            if st[0][0] == 1:
                p = nxt.reshape(2)
                if y is not None:
                    if math.hypot(y[0] - p[0], y[1] - p[1]) > 0.35 * y[2]: p = np.array(y[:2], np.float32); reseeds += 1
                    else: p = p + 0.08 * (np.array(y[:2], np.float32) - p)
            elif y is not None:
                p = np.array(y[:2], np.float32); reseeds += 1
            else:
                lost += 1
        pts.append((fi / fps, None if p is None else (float(p[0]), float(p[1]))))
        prev_g = g
    cap.release()
    good = [i for i, (_, v) in enumerate(pts) if v]
    if not good: return sw, sh, fps, None, None, None, reseeds, lost
    ts = np.array([t for t, _ in pts])
    xs = np.interp(range(len(pts)), good, [pts[i][1][0] for i in good])
    ys = np.interp(range(len(pts)), good, [pts[i][1][1] for i in good])
    if len(xs) > 3:   # light 3-tap smooth: AE's tracker is sub-pixel, LK + detector jitter is not
        k = np.array([0.25, 0.5, 0.25])
        xs = np.convolve(np.pad(xs, 1, mode="edge"), k, "valid"); ys = np.convolve(np.pad(ys, 1, mode="edge"), k, "valid")
    return sw, sh, fps, ts, xs, ys, reseeds, lost

def key(c): return os.path.basename(c["path"])
def group(c): return GROUPS.get(c["i"], key(c))

# ---- scenes: consecutive clips of one camera shot (same source + scale group); a skipped clip is its own scene
scenes = []
for c in clips:
    if scenes and c["i"] not in SKIP and scenes[-1]["clips"][-1]["i"] not in SKIP and \
            key(scenes[-1]["clips"][-1]) == key(c) and group(scenes[-1]["clips"][-1]) == group(c):
        scenes[-1]["clips"].append(c)
    else:
        scenes.append({"clips": [c], "path": c["path"], "group": group(c), "skip": c["i"] in SKIP})

for sc in scenes:
    cs = sc["clips"]
    if sc["skip"]:
        cap = cv2.VideoCapture(sc["path"]); sc["sw"], sc["sh"] = int(cap.get(3)), int(cap.get(4)); cap.release()
        sc["tracks"] = None; continue
    lo, hi = min(c["src_in"] for c in cs), max(c["src_out"] for c in cs)
    if hi - lo <= MAX_SPAN:       # one continuous pass over the whole span (gaps included): no restart at cuts
        r = track(sc["path"], lo, hi, PREFER_X.get(key(cs[0]), 0.5)); sc["tracks"] = [r]; sc["span"] = [(lo, hi)]
    else:                         # very long span: per clip, each with a 1 s pre-roll so it is settled at the cut
        sc["tracks"] = [track(sc["path"], max(0, c["src_in"] - 1), c["src_out"], PREFER_X.get(key(c), 0.5)) for c in cs]
        sc["span"] = [(max(0, c["src_in"] - 1), c["src_out"]) for c in cs]
    sc["sw"], sc["sh"] = sc["tracks"][0][0], sc["tracks"][0][1]

def nose_at(sc, t):
    """nose (source px) at source time t, linear between tracked source frames."""
    for (lo, hi), r in zip(sc["span"], sc["tracks"]):
        if lo - 1e-6 <= t <= hi + 1e-6 and r[3] is not None:
            return float(np.interp(t, r[3], r[4])), float(np.interp(t, r[3], r[5]))
    return None

# ---- keys per scene, in COMP time: anchor + time remap; HOLD into every cut
need = {}
for sc in scenes:
    sw, sh = sc["sw"], sc["sh"]
    seg_keys = []
    for c in sc["clips"]:
        ts, te, i0 = c["seq_start"], c["seq_end"], c["src_in"]
        if sc["skip"]: seg_keys.append([(ts, i0, sw / 2, sh / 2), (te - FD, i0 + (te - FD - ts), sw / 2, sh / 2)]); continue
        fps_src = sc["tracks"][0][2]
        times = [ts] + [ts + (k / fps_src - i0) for k in range(int(math.ceil(i0 * fps_src)), int(math.floor((i0 + te - ts - FD) * fps_src)) + 1)
                        if ts < ts + (k / fps_src - i0) < te - FD - 1e-6] + [te - FD]
        keys = []
        for t in times:
            s = i0 + (t - ts); n = nose_at(sc, s)
            if n: keys.append((round(t, 5), round(s, 5), round(n[0], 2), round(n[1], 2)))
        seg_keys.append(keys)
    sc["segs"] = seg_keys
    if not sc["skip"]:
        sc_need = 100 * max(W / sw, H / sh) * FILL_RATIO
        ays = [k[3] for seg in seg_keys for k in seg]
        side, edge = (BANNER.get(key(sc["clips"][0])) or [None, None])
        if side == "bottom": sc_need = max(sc_need, 100 * 1.02 * (H - NOSE[1]) / (edge - max(ays)))
        elif side == "top": sc_need = max(sc_need, 100 * 1.02 * NOSE[1] / (min(ays) - edge))
        need[sc["group"]] = max(need.get(sc["group"], 0), sc_need)

layers, report = [], []
for n, sc in enumerate(scenes):
    sw, sh = sc["sw"], sc["sh"]
    if sc["skip"]: scale = round(100 * max(W / sw, H / sh) * FILL_RATIO, 1); pos = [W / 2, H / 2]
    else: scale = round(need[sc["group"]], 1); pos = list(NOSE)
    k = scale / 100
    need_w, need_h = 100.0, 120.0
    for seg in sc["segs"]:
        for _, _, ax, ay in seg:
            left, right, top, bottom = pos[0] - ax * k, pos[0] + (sw - ax) * k, pos[1] - ay * k, pos[1] + (sh - ay) * k
            need_w = max(need_w, 100 + 200 * max(0, left, W - right) / (sw * k) + 4)
            need_h = max(need_h, 100 + 200 * max(0, top, H - bottom) / (sh * k) + 4)
    ow, oh = (100 if need_w <= 104 else math.ceil(need_w)), math.ceil(need_h)
    cs = sc["clips"]
    layers.append({"n": n, "name": f"scene {n + 1:02d} clips {cs[0]['i']}-{cs[-1]['i']}", "path": sc["path"],
                   "tin": cs[0]["seq_start"], "tout": cs[-1]["seq_end"], "scale": scale, "pos": pos, "ow": ow, "oh": oh,
                   "segs": [[list(k) for k in seg] for seg in sc["segs"]], "fixed": sc["skip"]})
    lost = sum(r[7] for r in sc["tracks"]) if sc["tracks"] else 0
    reseeds = sum(r[6] for r in sc["tracks"]) if sc["tracks"] else 0
    report.append({"scene": n + 1, "clips": f"{cs[0]['i']}-{cs[-1]['i']}", "cuts_inside": len(cs) - 1,
                   "time": f"{cs[0]['seq_start']:.3f}-{cs[-1]['seq_end']:.3f}", "source": key(cs[0])[:50], "group": sc["group"],
                   "tracked_span": [f"{a:.2f}-{b:.2f}" for a, b in sc.get("span", [])], "lost_frames": lost, "reseeds": reseeds,
                   "skipped": sc["skip"], "scale": scale, "motion_tile": f"{ow}x{oh}",
                   "anchor_keys": sum(len(s) for s in sc["segs"])})

os.makedirs(os.path.join(job, "ae"), exist_ok=True)
json.dump(report, open(os.path.join(job, "ae", "headtrack-report.json"), "w"), indent=1)
for r in report:
    flag = "  (skipped: fill only)" if r["skipped"] else ("" if r["anchor_keys"] else "   <-- NO FACE: not tracked, tell the user")
    print(f"scene {r['scene']:2d}  clips {r['clips']:>6s} ({r['cuts_inside']} cuts inside)  {r['time']:>15s}  tracked {','.join(r['tracked_span'])}"
          f"  lost {r['lost_frames']}  scale {r['scale']:.1f}%  tile {r['motion_tile']}{flag}")

jsx = r"""(function(){
var L = %s, W = %d, H = %d, FPS = %f, DUR = %f, NAME = %s;
app.beginUndoGroup('Stage 1 headtracking');
var proj = app.project, comp = null;
for (var i = 1; i <= proj.numItems; i++) if (proj.item(i) instanceof CompItem && proj.item(i).name == NAME) comp = proj.item(i);
if (!comp) comp = proj.items.addComp(NAME, W, H, 1, DUR, FPS);
while (comp.numLayers) comp.layer(1).remove();
comp.duration = DUR; comp.frameRate = FPS;
var foot = {};
function footage(p) {
  if (foot[p]) return foot[p];
  var want = new File(p).fsName.toLowerCase();
  for (var i = 1; i <= proj.numItems; i++) { var it = proj.item(i); if (it instanceof FootageItem && it.file && it.file.fsName.toLowerCase() == want) return (foot[p] = it); }
  return (foot[p] = proj.importFile(new ImportOptions(new File(p))));
}
var LIN = KeyframeInterpolationType.LINEAR, HOLD = KeyframeInterpolationType.HOLD, report = [];
for (var n = L.length - 1; n >= 0; n--) {
  var c = L[n], ly = comp.layers.add(footage(c.path));
  ly.name = c.name; ly.startTime = 0;
  if (ly.hasAudio) ly.audioEnabled = false;
  ly.timeRemapEnabled = true;
  var TR = ly.property('ADBE Time Remapping'), A = ly.transform.anchorPoint;
  var tt = [], tv = [], at = [], av = [], holdT = {};
  for (var s = 0; s < c.segs.length; s++) {
    var seg = c.segs[s];
    for (var k = 0; k < seg.length; k++) { at.push(seg[k][0]); av.push([seg[k][2], seg[k][3]]); }
    tt.push(seg[0][0]); tv.push(seg[0][1]); tt.push(seg[seg.length - 1][0]); tv.push(seg[seg.length - 1][1]);
    if (s < c.segs.length - 1) holdT[seg[seg.length - 1][0].toFixed(4)] = 1;      // hold into the cut
  }
  TR.setValuesAtTimes(tt, tv);
  for (var k = TR.numKeys; k >= 1; k--) { var kt = TR.keyTime(k), keep = false;     // drop AE's default remap keys
    for (var j = 0; j < tt.length; j++) if (Math.abs(tt[j] - kt) < 1e-4) keep = true;
    if (!keep) TR.removeKey(k); }
  for (var k = 1; k <= TR.numKeys; k++) TR.setInterpolationTypeAtKey(k, LIN, holdT[TR.keyTime(k).toFixed(4)] ? HOLD : LIN);
  ly.inPoint = c.tin; ly.outPoint = c.tout;
  var tile = ly.Effects.addProperty('ADBE Tile');
  tile.property('ADBE Tile-0002').setValue(100); tile.property('ADBE Tile-0003').setValue(100);
  tile.property('ADBE Tile-0004').setValue(c.ow); tile.property('ADBE Tile-0005').setValue(c.oh);
  tile.property('ADBE Tile-0006').setValue(1);
  ly.transform.scale.setValue([c.scale, c.scale]);
  ly.transform.position.setValue(c.pos);
  if (at.length > 1) {
    A.setValuesAtTimes(at, av);
    for (var k = 1; k <= A.numKeys; k++) A.setInterpolationTypeAtKey(k, LIN, holdT[A.keyTime(k).toFixed(4)] ? HOLD : LIN);
  } else if (av.length) A.setValue(av[0]);
  report.push(c.name + ': remap ' + TR.numKeys + ' keys, anchor ' + A.numKeys + ' keys, ' + ly.inPoint.toFixed(3) + '-' + ly.outPoint.toFixed(3));
}
app.endUndoGroup();
app.project.save();
return 'built ' + comp.numLayers + ' scene layers in "' + NAME + '" @' + comp.frameRate + ' fps, ' + comp.duration.toFixed(4) + 's (saved) | ' + report.reverse().join(' | ');
})()""" % (json.dumps(layers), W, H, FPS, DUR, json.dumps(COMP))
open(os.path.join(job, "ae", "headtrack.jsx"), "w", encoding="utf-8").write(jsx)

# sync check: Time Remap at every clip's first / middle / last frame must equal his source timing (picture = audio)
sync = r"""(function(){
var C = %s, NAME = %s, comp = null;
for (var i = 1; i <= app.project.numItems; i++) if (app.project.item(i) instanceof CompItem && app.project.item(i).name == NAME) comp = app.project.item(i);
if (!comp) return 'ERROR no comp ' + NAME;
var fd = comp.frameDuration, worst = 0, bad = [];
function layerAt(t) { for (var l = 1; l <= comp.numLayers; l++) { var L = comp.layer(l); if (t >= L.inPoint - 1e-6 && t < L.outPoint - 1e-6) return L; } return null; }
for (var j = 0; j < C.length; j++) {
  var c = C[j], pts = [c[1], (c[1] + c[2]) / 2, c[2] - fd];
  for (var q = 0; q < 3; q++) {
    var t = Math.round(pts[q] / fd) * fd; if (t < c[1] - 1e-6) t += fd;
    var L = layerAt(t); if (!L) { bad.push('no layer @' + t.toFixed(3)); continue; }
    var tr = L.property('ADBE Time Remapping'), v = tr.numKeys ? tr.valueAtTime(t, false) : (t - L.startTime);
    var d = Math.abs(v - (c[3] + (t - c[1]))); if (d > worst) worst = d;
    if (d > 0.5 * fd) bad.push('clip ' + c[0] + ' @' + t.toFixed(3) + ' shows ' + v.toFixed(4) + ' expected ' + (c[3] + (t - c[1])).toFixed(4));
  }
}
return 'sync: ' + (C.length * 3) + ' points, worst ' + (worst * 1000).toFixed(2) + ' ms' + (bad.length ? ' | OUT OF SYNC: ' + bad.join('; ') : ' | all in sync');
})()""" % (json.dumps([[c["i"], c["seq_start"], c["seq_end"], c["src_in"]] for c in clips]), json.dumps(COMP))
open(os.path.join(job, "ae", "sync-check.jsx"), "w", encoding="utf-8").write(sync)
print(f'wrote {os.path.join(job, "ae", "headtrack.jsx")}  (comp "{COMP}", {len(layers)} scene layers, nose target {NOSE})')
print(f'wrote {os.path.join(job, "ae", "sync-check.jsx")}  (run after the build: must say "all in sync")')
