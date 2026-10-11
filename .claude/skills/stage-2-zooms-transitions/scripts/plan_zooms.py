#!/usr/bin/env python3
"""Step 4: Sameer's labels + picture-change frames + the mood picks -> <job>/stage2-plan.json.

  python .claude/skills/stage-2-zooms-transitions/scripts/plan_zooms.py projects/<job> --labels labels.json \
      --transitions "2:dark:from the act to the fallout" "3:flash:the outburst" ...

  --labels       file with the JSON that ae/read-labels.jsx returned (AE label 9 = Green = ZOOM IN, 10 = Purple = ZOOM OUT;
                 confirm the names in his AE prefs; any other label = no zoom on that cut, reported)
  --transitions  one per transition, "<cut number>:<dark|flash>:<why>" — the transition sits on the START of that cut.
                 Picked by MOOD (dark = tension, negative, a deflating twist, the act -> the fallout; flash = an outburst, a
                 reveal, the camera turning to someone, the receipt). Not every cut needs one.
  --center x,y   S_BlurMoCurves Center XY (default 540,925 = the Stage 1 nose point)

Zoom depths (his Comp 09): a zoom-out on cut 1 starts at 0.70 (the hook); any other zoom-out starts ~0.02 wider than the
zoom-in before it ended (the zoom flows through the cut), else 0.82; a zoom-in ends at 0.80, the LAST cut (payoff) at 0.66.
Override any one with --depth "<cut>:<z>".
"""
import argparse, json, os

ap = argparse.ArgumentParser()
ap.add_argument("job"); ap.add_argument("--labels", required=True); ap.add_argument("--transitions", nargs="*", default=[])
ap.add_argument("--center", default="540,925"); ap.add_argument("--depth", nargs="*", default=[])
ap.add_argument("--comp"); ap.add_argument("--dark", type=float, default=-30); ap.add_argument("--flash", type=float, default=25)
a = ap.parse_args()
job = os.path.abspath(a.job)
seq = json.load(open(os.path.join(job, "clips.json"), encoding="utf-8"))
labels = {int(x["name"].split()[1]): x["label"] for x in json.load(open(a.labels, encoding="utf-8"))}
cf_p = os.path.join(job, "ae", "cut-frames.json")
pic = {r["cut"]: r["picture"] for r in json.load(open(cf_p))} if os.path.exists(cf_p) else {}
depth = {int(d.split(":")[0]): float(d.split(":")[1]) for d in a.depth}
n = len(seq["clips"]); dur = seq["duration"]
bounds = [0.0] + [pic.get(k, seq["clips"][k - 1]["seq_start"]) for k in range(2, n + 1)] + [dur]

segs, prev_end, skipped = [], None, []
for k in range(1, n + 1):
    lab = labels.get(k)
    t0, t1 = bounds[k - 1], bounds[k]
    if lab == 9:      # Green: zoom in
        z0, z1 = 1.0, depth.get(k, 0.66 if k == n else 0.80)
    elif lab == 10:   # Purple: zoom out
        z0 = depth.get(k, 0.70 if k == 1 else (round(prev_end + 0.02, 2) if prev_end and prev_end < 1 else 0.82)); z1 = 1.0
    else:
        skipped.append(k); prev_end = None; continue
    segs.append({"cut": k, "label": "Green" if lab == 9 else "Purple", "t0": round(t0, 5), "t1": round(t1, 5), "z0": z0, "z1": z1})
    prev_end = z1
trans = []
for t in a.transitions:
    k, typ, why = t.split(":", 2)
    trans.append({"cut": round(bounds[int(k) - 1], 5), "cut_number": int(k), "type": typ, "why": why})
plan = {"comp": a.comp or seq["sequence"] + " Cuts", "into_existing": True, "fps": seq["fps"], "duration": dur,
        "center": [float(v) for v in a.center.split(",")], "segments": segs, "transitions": trans, "dark": a.dark, "flash": a.flash}
json.dump(plan, open(os.path.join(job, "stage2-plan.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
for s in segs: print(f"cut {s['cut']} {s['label']:6s} {s['t0']:7.3f}-{s['t1']:7.3f}  Z {s['z0']:.2f} -> {s['z1']:.2f}")
for t in trans: print(f"transition {t['type']:5s} on cut {t['cut_number']} @ {t['cut']:.3f}  ({t['why']})")
if skipped: print(f"NO ZOOM (no Green/Purple label): cuts {skipped}  <- tell Sameer")
print("wrote stage2-plan.json")
