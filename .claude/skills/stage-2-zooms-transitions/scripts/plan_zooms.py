#!/usr/bin/env python3
"""Step 4: Sameer's labels + picture-change frames -> <job>/stage2-plan.json.

  python .claude/skills/stage-2-zooms-transitions/scripts/plan_zooms.py projects/<job> --labels labels.json \
      [--transitions "9:solid:the slam" "5:none:no flash here" ...] [--bands 3 8] [--center-cut "4:540,960"]

  --labels       file with the JSON that ae/read-labels.jsx returned (AE label 9 = Green = ZOOM IN, 10 = Purple = ZOOM OUT;
                 any other label = no zoom on that cut, reported)
  --layers       (alternative to --labels) JSON [{"in": frame, "out": frame, "label": 9|10}, ...] = HIS labelled adjustment layers already
                 in the comp (one zoom segment each, time order). Zooms are written onto those layers (names/labels kept), a flash goes on
                 every segment start but the first. "cut numbers" below are then segment numbers 1..N. Layers running past the comp end
                 are clamped.
  --transitions  per-cut overrides "<cut number>:<flash|solid|dark|none>[:<why>]". DEFAULT (his Linked Comp 01, 2026-10-11):
                 EVERY cut after the first gets a brightness FLASH (BCC Brightness +25, peak on the cut). `solid` = the white-solid
                 camera flash for a hard impact cut he names; `none` = no transition; `dark` (-30) only if he asks.
                 Peak per cut: "<cut>:flash=30". Transition sits on the START of that cut.
  --bands        cut numbers that get the wide-B-roll band look (sharp band + blurred copy + two white lines) - he names them.
  --curve        per-cut curve type "<cut>:drop" or "<cut>:drop3[@0.77]" (his other BlurMo curves, 2026-10-11):
                   drop  = INTENSE DROP: out speed +/-14.4 with 1 % influence (snaps most of the move in the first few frames), then a
                           long soft settle (in influence ~55 %). He uses it mostly on the FIRST clip (hook zoom-out 0.64 -> 1), so cut 1
                           Purple is `drop` by default.
                   drop3 = 3 KEYS in one layer: slow release 0.74 -> 1.0 over the first ~77 % of the cut, then at that point a drop-curve
                           zoom-IN to 0.755 that lands on the cut (his Linked Comp 01 layer 6: keys 0 / 202 / 264 f).
  --lines        "<cut>:<top>-<bottom>" for a B-roll whose blurred-background band is ALREADY in the render (Premiere baked it): only the two thin white
                 lines on the band edges are added (24 px, top edge+3 / bottom edge-7, under the zoom adjustment so they zoom with the picture).
                 Measure the edges with band_edges.py. (Sameer, 31 s fight B-roll: band 257-1658.)
  --center x,y   S_BlurMoCurves Center XY for every zoom. Default = the Stage 1 nose point (projects/<job>/ae/frame.json,
                 else 540,672); he clicks the FACE (his Center XY sat at the face, e.g. 537,590). --center-cut "<cut>:x,y"
                 overrides one cut (B-roll without a face: 540,960).

SUBTLE ON SHORT SEGMENTS (Sameer, 2026-10-11): "longer adjustment layers are perfect; shorter ones need subtle curves - the scene changes quickly and an
intense zoom feels unpleasant". Segment length < 1.8 s scales the zoom depth by k = clamp((len-0.6)/1.2, 0.35, 1) (so 0.83 s -> 35 % of the
move, 1.35 s -> 63 %, >= 1.8 s -> full) and softens the ease (more influence). The first-clip hook and drop3 layers stay intense.
SMOOTH FLASHES: "keep the value lower when they occur back to back - I want a smooth transition, not a flash". Peak = 25 x clamp((gap-0.5)/2, 0.35, 1)
where gap = seconds to the nearest neighbouring transition (>= 2.5 s apart -> full +25, 1.25 s -> ~+9). A per-cut "<cut>:flash=N" still wins.
LABELS: Green 9 = zoom in, Purple 10 = zoom out, ORANGE 11 = 3-KEY zoom-out (release, then snap back in before the cut = drop3).

Zoom depths (his Linked Comp 01, 20 zooms): zoom-in ends 0.715-0.77 (default 0.74), zoom-out starts 0.715-0.79 (default 0.75);
the first cut's zoom-out is the hook (0.64, whip start). Zoom-ins that follow a deep zoom-out start at 1.0 as he keyed them
(no forced continuity). Override any one with --depth "<cut>:<z>".
"""
import argparse, json, os

ap = argparse.ArgumentParser()
ap.add_argument("job"); ap.add_argument("--labels"); ap.add_argument("--layers"); ap.add_argument("--transitions", nargs="*", default=[])
ap.add_argument("--center"); ap.add_argument("--center-cut", nargs="*", default=[]); ap.add_argument("--bands", nargs="*", type=int, default=[])
ap.add_argument("--depth", nargs="*", default=[]); ap.add_argument("--curve", nargs="*", default=[]); ap.add_argument("--comp")
ap.add_argument("--lines", nargs="*", default=[]); ap.add_argument("--no-subtle", action="store_true"); ap.add_argument("--no-smooth", action="store_true")
ap.add_argument("--dark", type=float, default=-30); ap.add_argument("--flash", type=float, default=25)
ap.add_argument("--in-depth", type=float, default=0.74); ap.add_argument("--out-depth", type=float, default=0.75); ap.add_argument("--hook", type=float, default=0.64)
a = ap.parse_args()
job = os.path.abspath(a.job)
seq = json.load(open(os.path.join(job, "clips.json"), encoding="utf-8"))
if a.layers:
    L = sorted(json.load(open(a.layers, encoding="utf-8")), key=lambda r: r["in"])
    labels = {i + 1: r["label"] for i, r in enumerate(L)}
else:
    L = None
    labels = {int(x["name"].split()[1]): x["label"] for x in json.load(open(a.labels, encoding="utf-8"))}
cf_p = os.path.join(job, "ae", "cut-frames.json")
pic = {r["cut"]: r["picture"] for r in json.load(open(cf_p))} if os.path.exists(cf_p) else {}
fr_p = os.path.join(job, "ae", "frame.json")
center = [float(v) for v in a.center.split(",")] if a.center else (json.load(open(fr_p))["nose"] if os.path.exists(fr_p) else [540.0, 672.0])
ccut = {int(d.split(":")[0]): [float(v) for v in d.split(":")[1].split(",")] for d in a.center_cut}
depth = {int(d.split(":")[0]): float(d.split(":")[1]) for d in a.depth}
curves = {}
for d in a.curve:
    k, t = d.split(":"); frac = float(t.split("@")[1]) if "@" in t else 0.77; curves[int(k)] = (t.split("@")[0], frac)
n = len(seq["clips"]); dur = seq["duration"]
bounds = [0.0] + [pic.get(k, seq["clips"][k - 1]["seq_start"]) for k in range(2, n + 1)] + [dur]
if L:
    n = len(L); fps = seq["fps"]
    bounds = [r["in"] / fps for r in L] + [dur]; bounds[0] = 0.0

segs, skipped = [], []
for k in range(1, n + 1):
    lab = labels.get(k)
    t0, t1 = bounds[k - 1], bounds[k]
    if lab == 9:      # Green: zoom in
        seg = {"z0": 1.0, "z1": depth.get(k, a.in_depth)}
    elif lab in (10, 11):   # Purple: zoom out (cut 1 = the hook); Orange: 3-key zoom-out (drop3)
        seg = {"z0": depth.get(k, a.hook if k == 1 else a.out_depth), "z1": 1.0, "hook": k == 1}
    else:
        skipped.append(k); continue
    if k in curves: seg["curve"], seg["frac"] = curves[k]
    if seg.get("curve") == "drop3":      # his 3-key layer starts at the normal zoom-out depth, not the hook depth
        if lab not in (10, 11): print(f"note: cut {k} is not Purple - drop3 (zoom-out then late zoom-in) ignored"); seg.pop("curve"); seg.pop("frac")
        else: seg["z0"] = depth.get(k, a.out_depth); seg["hook"] = False
    elif seg.get("hook"): seg["curve"] = "drop"
    dur_k = t1 - t0
    if not seg.get("hook") and seg.get("curve") not in ("drop", "drop3") and k not in depth and dur_k < 1.8 and not a.no_subtle:
        kk = max(0.35, min(1.0, (dur_k - 0.6) / 1.2))
        if lab == 9: seg["z1"] = round(1 - (1 - a.in_depth) * kk, 3)
        else: seg["z0"] = round(1 - (1 - a.out_depth) * kk, 3)
        seg["subtle"] = round(kk, 2)
    if L: seg["layer_in"] = L[k - 1]["in"]
    if lab == 11 and "curve" not in seg: seg["curve"], seg["frac"] = "drop3", 0.77
    seg.update({"cut": k, "label": {9: "Green", 10: "Purple", 11: "Orange"}[lab], "t0": round(t0, 5), "t1": round(t1, 5)})
    if k in ccut: seg["center"] = ccut[k]
    segs.append(seg)

over = {}
for t in a.transitions:
    parts = t.split(":", 2); k = int(parts[0]); typ = parts[1] if len(parts) > 1 else "flash"
    peak = None
    if "=" in typ: typ, pk = typ.split("="); peak = float(pk)
    over[k] = (typ, peak, parts[2] if len(parts) > 2 else "")
trans = []
times = [bounds[k - 1] for k in range(2, n + 1) if over.get(k, ("flash",))[0] != "none"]
def smooth_peak(t):
    others = [abs(t - u) for u in times if u != t]
    gap = min(others) if others else 9.0
    return round(a.flash * max(0.35, min(1.0, (gap - 0.5) / 2.0)), 1)
for k in range(2, n + 1):
    typ, peak, why = over.get(k, ("flash", None, "every cut"))
    if typ == "none": continue
    if typ == "flash" and peak is None and not a.no_smooth: peak = smooth_peak(bounds[k - 1])
    row = {"cut": round(bounds[k - 1], 5), "cut_number": k, "type": typ, "why": why}
    if peak is not None: row["peak"] = peak
    trans.append(row)
plan = {"comp": a.comp or seq["sequence"] + " Cuts", "into_existing": True, "fps": seq["fps"], "duration": dur,
        "center": center, "segments": segs, "transitions": trans, "dark": a.dark, "flash": a.flash, "bands": a.bands,
        "lines": [{"cut": int(d.split(":")[0]), "top": int(d.split(":")[1].split("-")[0]), "bottom": int(d.split(":")[1].split("-")[1]),
                   "t0": round(bounds[int(d.split(":")[0]) - 1], 5), "t1": round(bounds[int(d.split(":")[0])], 5)} for d in a.lines]}
json.dump(plan, open(os.path.join(job, "stage2-plan.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
for s in segs: print(f"cut {s['cut']} {s['label']:6s} {s['t0']:7.3f}-{s['t1']:7.3f}  Z {s['z0']:.2f} -> {s['z1']:.2f}" + ("  (hook)" if s.get("hook") else "") + (f"  subtle x{s['subtle']}" if s.get("subtle") else "") + (f"  curve {s['curve']}" + (f"@{s['frac']}" if s.get('frac') and s['curve'] == 'drop3' else "") if s.get("curve") else ""))
for t in trans: print(f"transition {t['type']:5s} on cut {t['cut_number']} @ {t['cut']:.3f}" + (f"  peak {t['peak']:+.1f}" if "peak" in t else "") + f"  ({t['why']})")
if a.bands: print(f"band look on cuts {a.bands}")
if skipped: print(f"NO ZOOM (no Green/Purple label): cuts {skipped}  <- tell Sameer")
print("wrote stage2-plan.json")
