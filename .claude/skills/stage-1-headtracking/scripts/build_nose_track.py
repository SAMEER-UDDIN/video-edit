#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless", "numpy"]
# ///
"""Sameer's head-tracking method, built in After Effects (see ../SKILL.md and docs/fight-club/headtracking-method.md).

  uv run .claude/skills/stage-1-headtracking/scripts/build_nose_track.py projects/<job>

Reads <job>/clips.json (premiere_clips.py) and optional <job>/headtrack.json, writes <job>/ae/headtrack.jsx (run it with
the after-effects MCP: ae_run_jsx {"file": ...}), <job>/ae/sync-check.jsx and <job>/ae/headtrack-report.json.

ONE AE LAYER PER CUT, NO TIME REMAP (Sameer, 2026-10-11 - his own comp's way). Each layer is the source clip, slid in time
so its source in-point sits on the cut (startTime = cut start - src_in); in/out = the cut. Per layer:
  * the nose is tracked per source frame (53x50 patch, pyramidal Lucas-Kanade, gentle YuNet drift correction / re-seed),
    seeded on the person he framed (see "prefer" below); Anchor Point keys = the nose on screen (AE Stabilize-Position)
  * Position CONSTANT = ONE nose point for every face in the job (same person = same nose = seamless cuts)
  * Scale CONSTANT per source. AUTO FRAME (default, when neither "nose" nor "scale" is given): for the source with the most
    tracked clips, find the smallest scale >= fill x 1.0558 (his 187.7 % on 1080p, raised so a face is >= min_face of the
    width, cap max_scale) at which ONE nose height clears BOTH the top and bottom edge for every tracked frame (no Mirror
    Edges flipped-head line), then put the nose x = W/2, y = middle of that band (Seq01: 205 %, y 672). Other sources
    (B-roll) use that nose and fill x 1.0558 / min_face. Banners are only kept out if listed; "scale": {basename: pct}
    overrides (a WIDE shot may go below fill - Mirror Edges covers the rest)
  * Motion Tile on tracked layers: Output >= 100 W x 150 H (his value, raised only if the motion needs it), Mirror Edges on
  * skipped clips (fights / B-roll / stills): fill only, centred, no tracking; stills have no remap at all
  * "prefer" = which face to lock onto in a split screen / two-shot. Default: read from his Premiere framing (clips.json
    "pos"/"scale": the source column his Position+Scale centre on); override with prefer_x / prefer_x_clip.

headtrack.json (all optional):
  {"comp": "Seq Headtrack",
   "skip": [1, 4, 15],                                  # clip indexes NOT to track (fights, B-roll, stills)
   "skip_tracks": [2], "include": [18],                 # skip every clip on these Premiere tracks, except these indexes
   "prefer_x": {"<source basename>": 0.42},             # which person (0..1 across the source)
   "prefer_x_clip": {"22": 0.25},                       # per clip (split screen: left 0.25 / right 0.75)
   "nose": [540, 672], "scale": {"<source basename>": 205},   # manual override of the auto frame
   "nose_by": {"<source basename>": [540, 925]},        # a different person may sit elsewhere (optional)
   "banners": {"<source basename>": ["bottom", 897]},   # burned-in graphics to keep out (opt-in)
   "min_face": 0.17, "max_scale": 230, "margin": 12, "min_band": 40, "fill_ratio": 1.0558, "patch": [53, 50]}
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
AUTO_FRAME = "nose" not in cfg
FILL_RATIO = cfg.get("fill_ratio", 187.7 / (100 * 1920 / 1080))
PATCH = cfg.get("patch", [53, 50])
PREFER_X, BANNER = cfg.get("prefer_x", {}), cfg.get("banners", {})
GROUPS, SKIP = {int(k): v for k, v in cfg.get("groups", {}).items()}, set(cfg.get("skip", []))
MARGIN, MIN_BAND = cfg.get("margin", 12), cfg.get("min_band", 40)   # px safety at each edge / min width of the feasible nose band
LAYER_MODE, MIN_FACE, MAX_SCALE = "cut", cfg.get("min_face", 0.17), cfg.get("max_scale", 230)   # one layer per cut, NO Time Remap (2026-10-11)
PREFER_CLIP = {int(k): v for k, v in cfg.get("prefer_x_clip", {}).items()}   # clip index -> which person (split screens)
NOSE_BY, SCALE_BY = cfg.get("nose_by", {}), cfg.get("scale", {})
STILL_EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp")   # stills: no Time Remap, fill only
COMP = cfg.get("comp", seq["sequence"] + " Headtrack")
clips = seq["clips"]
SKIP |= {c["i"] for c in clips if c.get("track", 1) in cfg.get("skip_tracks", []) and c["i"] not in cfg.get("include", [])}
def src_w(path):
    cap = cv2.VideoCapture(path); w = int(cap.get(3)); cap.release(); return w
def auto_prefer(c):
    """which source column his Premiere framing centres on (0..1), from clips.json pos/scale; 0.5 = no preference."""
    if not c.get("pos") or not c.get("scale") or os.path.splitext(c["path"])[1].lower() in STILL_EXT: return 0.5
    sw = src_w(c["path"])
    if not sw: return 0.5
    f = 0.5 + (0.5 * W - c["pos"][0] * W) / (sw * c["scale"] / 100)
    return round(f, 3) if abs(f - 0.5) > 0.1 and 0.05 < f < 0.95 else 0.5

def yunet(det, frame, prefer_x, prev=None):
    _, fs = det.detect(frame)
    if fs is None or not len(fs): return None
    h, w = frame.shape[:2]
    if prev is not None:
        f = min(fs, key=lambda r: math.hypot(r[8] - prev[0], r[9] - prev[1]))
        if math.hypot(f[8] - prev[0], f[9] - prev[1]) > 0.12 * w: return None
    else:
        if prefer_x != 0.5:   # a chosen side (split screen / two-shot): only faces near it may seed the track
            fs = [r for r in fs if abs((r[0] + r[2] / 2) / w - prefer_x) <= 0.2]
            if not len(fs): return None
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
    pts, prev_g, p, reseeds, lost, fw = [], None, None, 0, 0, None
    for fi in range(f0, f1 + 1):
        ok, fr = cap.read()
        if not ok: break
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        y = yunet(det, fr, prefer_x, p)
        if p is None:
            if y is not None: p = np.array(y[:2], np.float32); fw = y[2]
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
    if not good: return sw, sh, fps, None, None, None, reseeds, lost, fw
    ts = np.array([t for t, _ in pts])
    xs = np.interp(range(len(pts)), good, [pts[i][1][0] for i in good])
    ys = np.interp(range(len(pts)), good, [pts[i][1][1] for i in good])
    if len(xs) > 3:   # light 3-tap smooth: AE's tracker is sub-pixel, LK + detector jitter is not
        k = np.array([0.25, 0.5, 0.25])
        xs = np.convolve(np.pad(xs, 1, mode="edge"), k, "valid"); ys = np.convolve(np.pad(ys, 1, mode="edge"), k, "valid")
    return sw, sh, fps, ts, xs, ys, reseeds, lost, fw

def key(c): return os.path.basename(c["path"])
def group(c): return GROUPS.get(c["i"], key(c))

# ---- one scene (= one AE layer) per cut; a skipped clip is a fill-only layer
scenes = [{"clips": [c], "path": c["path"], "group": GROUPS.get(c["i"], key(c)), "skip": c["i"] in SKIP} for c in clips]

for sc in scenes:
    c = sc["clips"][0]
    if sc["skip"]:
        cap = cv2.VideoCapture(sc["path"]); sc["sw"], sc["sh"] = int(cap.get(3)), int(cap.get(4)); cap.release()
        sc["tracks"] = None; continue
    px = PREFER_CLIP.get(c["i"], PREFER_X.get(key(c), auto_prefer(c)))
    sc["prefer"] = px
    sc["tracks"] = [track(sc["path"], c["src_in"], c["src_out"], px)]; sc["span"] = [(c["src_in"], c["src_out"])]
    sc["sw"], sc["sh"] = sc["tracks"][0][0], sc["tracks"][0][1]

def nose_at(sc, t):
    """nose (source px) at source time t, linear between tracked source frames."""
    for (lo, hi), r in zip(sc["span"], sc["tracks"]):
        if lo - 1e-6 <= t <= hi + 1e-6 and r[3] is not None:
            return float(np.interp(t, r[3], r[4])), float(np.interp(t, r[3], r[5]))
    return None

# ---- anchor keys per cut, in COMP time (no Time Remap)
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
        fw = sc["tracks"][0][8]
        if fw: sc_need = min(MAX_SCALE, max(sc_need, 100 * MIN_FACE * W / fw))   # tiny face -> raise (his 228 %)
        if key(sc["clips"][0]) in SCALE_BY: sc_need = SCALE_BY[key(sc["clips"][0])]
        ays = [k[3] for seg in seg_keys for k in seg]
        side, edge = (BANNER.get(key(sc["clips"][0])) or [None, None])
        if side == "bottom": sc_need = max(sc_need, 100 * 1.02 * (H - NOSE[1]) / (edge - max(ays)))
        elif side == "top": sc_need = max(sc_need, 100 * 1.02 * NOSE[1] / (min(ays) - edge))
        need[sc["group"]] = sc_need if key(sc["clips"][0]) in SCALE_BY else max(need.get(sc["group"], 0), sc_need)

# ---- AUTO FRAME: one nose height that clears BOTH edges (no Mirror-Edge flipped-head line) for the main source
auto_note = ""
tracked = [sc for sc in scenes if not sc["skip"] and sc["segs"][0]]
if AUTO_FRAME and tracked:
    by_src = {}
    for sc in tracked: by_src.setdefault(key(sc["clips"][0]), []).append(sc)
    main = max(by_src, key=lambda k: len(by_src[k]))
    ms = by_src[main]; sh = ms[0]["sh"]
    lo_ay = min(k[3] for sc in ms for k in sc["segs"][0]); hi_ay = max(k[3] for sc in ms for k in sc["segs"][0])
    base = max(need[sc["group"]] for sc in ms)
    cand = [SCALE_BY[main]] if main in SCALE_BY else [base + 0.5 * i for i in range(0, int((MAX_SCALE - base) / 0.5) + 1)]
    for pct in cand:
        k = pct / 100; top, bot = lo_ay * k - MARGIN, H - (sh - hi_ay) * k + MARGIN     # ny <= top and ny >= bot
        if bot + MIN_BAND <= top:
            NOSE = (W / 2, round((top + bot) / 2))
            for sc in ms: need[sc["group"]] = pct
            auto_note = f"auto frame: {main[:40]} scale {pct:.1f}%  nose y {NOSE[1]:.0f} (band {bot:.0f}..{top:.0f})"; break
    else:
        auto_note = f"auto frame: NO nose height clears both edges for {main[:40]} up to {MAX_SCALE}% - kept default nose {NOSE}; Mirror Edges will show"
    print(auto_note)

layers, report = [], []
for n, sc in enumerate(scenes):
    sw, sh = sc["sw"], sc["sh"]
    if sc["skip"]: scale = round(100 * max(W / sw, H / sh) * FILL_RATIO, 1); pos = [W / 2, H / 2]
    else: scale = round(need[sc["group"]], 1); pos = list(NOSE_BY.get(key(sc["clips"][0]), NOSE))
    k = scale / 100
    need_w, need_h = 100.0, 150.0
    for seg in sc["segs"]:
        for _, _, ax, ay in seg:
            left, right, top, bottom = pos[0] - ax * k, pos[0] + (sw - ax) * k, pos[1] - ay * k, pos[1] + (sh - ay) * k
            need_w = max(need_w, 100 + 200 * max(0, left, W - right) / (sw * k) + 4)
            need_h = max(need_h, 100 + 200 * max(0, top, H - bottom) / (sh * k) + 4)
    ow, oh = (100 if need_w <= 104 else math.ceil(need_w)), math.ceil(need_h)
    cs = sc["clips"]
    layers.append({"n": n, "name": f"cut {cs[0]['i']:02d}", "path": sc["path"],
                   "tin": cs[0]["seq_start"], "tout": cs[-1]["seq_end"], "scale": scale, "pos": pos, "ow": ow, "oh": oh,
                   "segs": [[list(k) for k in seg] for seg in sc["segs"]], "fixed": sc["skip"],
                   "still": os.path.splitext(sc["path"])[1].lower() in STILL_EXT})
    lost = sum(r[7] for r in sc["tracks"]) if sc["tracks"] else 0
    reseeds = sum(r[6] for r in sc["tracks"]) if sc["tracks"] else 0
    report.append({"scene": n + 1, "clips": f"{cs[0]['i']}-{cs[-1]['i']}", "cuts_inside": len(cs) - 1,
                   "time": f"{cs[0]['seq_start']:.3f}-{cs[-1]['seq_end']:.3f}", "source": key(cs[0])[:50], "group": sc["group"],
                   "tracked_span": [f"{a:.2f}-{b:.2f}" for a, b in sc.get("span", [])], "lost_frames": lost, "reseeds": reseeds,
                   "skipped": sc["skip"], "scale": scale, "motion_tile": f"{ow}x{oh}",
                   "anchor_keys": sum(len(s) for s in sc["segs"])})

os.makedirs(os.path.join(job, "ae"), exist_ok=True)
json.dump(report, open(os.path.join(job, "ae", "headtrack-report.json"), "w"), indent=1)
json.dump({"nose": [float(NOSE[0]), float(NOSE[1])], "scale": {k: round(v, 1) for k, v in need.items()}}, open(os.path.join(job, "ae", "frame.json"), "w"), indent=1)   # Stage 2 reads the nose as the zoom centre
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
  if (c.still) {            // still image: fill + Motion Tile only (no Time Remap / tracking)
    ly.inPoint = c.tin; ly.outPoint = c.tout;
    var t0 = ly.Effects.addProperty('ADBE Tile');
    t0.property('ADBE Tile-0004').setValue(c.ow); t0.property('ADBE Tile-0005').setValue(c.oh); t0.property('ADBE Tile-0006').setValue(1);
    ly.transform.scale.setValue([c.scale, c.scale]); ly.transform.position.setValue(c.pos);
    report.push(c.name + ': still'); continue;
  }
  // NO Time Remap (Sameer, 2026-10-11): the layer is the source clip, slid so its source in-point sits on the cut
  ly.startTime = c.tin - c.segs[0][0][1];
  var A = ly.transform.anchorPoint, at = [], av = [];
  for (var s = 0; s < c.segs.length; s++) {
    var seg = c.segs[s];
    for (var k = 0; k < seg.length; k++) { at.push(seg[k][0]); av.push([seg[k][2], seg[k][3]]); }
  }
  ly.inPoint = c.tin; ly.outPoint = c.tout;
  var tile = ly.Effects.addProperty('ADBE Tile');
  tile.property('ADBE Tile-0002').setValue(100); tile.property('ADBE Tile-0003').setValue(100);
  tile.property('ADBE Tile-0004').setValue(c.ow); tile.property('ADBE Tile-0005').setValue(c.oh);
  tile.property('ADBE Tile-0006').setValue(1);
  ly.transform.scale.setValue([c.scale, c.scale]);
  ly.transform.position.setValue(c.pos);
  if (at.length > 1) {
    A.setValuesAtTimes(at, av);
    for (var k = 1; k <= A.numKeys; k++) A.setInterpolationTypeAtKey(k, LIN, LIN);
  } else if (av.length) A.setValue(av[0]);
  report.push(c.name + ': anchor ' + A.numKeys + ' keys, ' + ly.inPoint.toFixed(3) + '-' + ly.outPoint.toFixed(3));
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
})()""" % (json.dumps([[c["i"], c["seq_start"], c["seq_end"], c["src_in"]] for c in clips if os.path.splitext(c["path"])[1].lower() not in STILL_EXT]), json.dumps(COMP))
open(os.path.join(job, "ae", "sync-check.jsx"), "w", encoding="utf-8").write(sync)
print(f'wrote {os.path.join(job, "ae", "headtrack.jsx")}  (comp "{COMP}", {len(layers)} scene layers, nose target {NOSE})')
print(f'wrote {os.path.join(job, "ae", "sync-check.jsx")}  (run after the build: must say "all in sync")')
