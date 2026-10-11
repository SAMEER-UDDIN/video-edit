#!/usr/bin/env python3
"""Step 5: <job>/stage2-plan.json -> <job>/ae/stage2.jsx (run with the after-effects MCP: ae_run_jsx {"file": ...}).

  python .claude/skills/stage-2-zooms-transitions/scripts/build_zooms.py projects/<job>

Adds INTO his cut comp (from make_cut_comp.py), never touching his "Cut N" layers; re-running replaces only layers named
"Zoom ..." / "Dark @..." / "Flash @...". Method: docs/fight-club/blurmo-transitions-method.md (his D:/1.aep Comp 09).
  * zoom = one adjustment layer per cut, exactly spanning it, labelled like the cut: Sapphire S_BlurMoCurves at defaults,
    Center XY + Z Dist keyed on the first and last frame, Bezier with his curve: fast at the cut, slow in the middle
    (end speeds 7x / 6x the average slope, influence 4 % / 6 %, as measured on Comp 09)
  * transition = its own adjustment layer: BCC Brightness-Contrast, Brightness LINEAR 0 -> peak ON the cut frame -> 0
    (10 frames up, 5 down at the comp rate scaled from 60 fps), layer from cut-0.467 s to cut+0.417 s
"""
import json, os, sys

job = os.path.abspath(sys.argv[1])
plan = json.load(open(os.path.join(job, "stage2-plan.json"), encoding="utf-8"))
FD = 1.0 / plan["fps"]; F60 = plan["fps"] / 60.0
segs = []
for s in plan["segments"]:
    t0 = round(s["t0"] / FD) * FD; t1 = round(s["t1"] / FD) * FD; last = t1 - FD
    avg = (s["z1"] - s["z0"]) / (last - t0)
    segs.append({"cut": s["cut"], "t0": t0, "t1": t1, "kl": last, "z0": s["z0"], "z1": s["z1"], "sOut": 7 * avg, "iOut": 4,
                 "sIn": 6 * avg, "iIn": 6, "lbl": {"Green": 9, "Purple": 10}.get(s.get("label"), 0)})
trans = []
for t in plan["transitions"]:
    c = round(t["cut"] / FD) * FD
    trans.append({"cut": c, "type": t["type"], "peak": plan["dark"] if t["type"] == "dark" else plan["flash"],
                  "k0": c - round(10 * F60) * FD, "k2": c + round(5 * F60) * FD,
                  "lin": max(0, c - 0.467), "lout": min(plan["duration"], c + 0.417)})

jsx = r"""(function(){
var P = %s, S = %s, T = %s;
app.beginUndoGroup('Stage 2 zooms + transitions');
var proj = app.project, comp = null;
for (var i = 1; i <= proj.numItems; i++) if (proj.item(i) instanceof CompItem && proj.item(i).name == P.comp) comp = proj.item(i);
if (!comp) return 'ERROR comp not found: ' + P.comp + ' (run ae/cuts.jsx first)';
for (var l = comp.numLayers; l >= 1; l--) if (/^(Zoom |Dark @|Flash @)/.test(comp.layer(l).name)) comp.layer(l).remove();
function adj(name, tin, tout) { var l = comp.layers.addSolid([1, 1, 1], name, comp.width, comp.height, 1, comp.duration);
  l.adjustmentLayer = true; l.inPoint = tin; l.outPoint = tout; return l; }
for (var n = 0; n < S.length; n++) {
  var s = S[n], L = adj('Zoom ' + s.cut + (s.z1 < s.z0 ? ' in' : ' out'), s.t0, s.t1); if (s.lbl) L.label = s.lbl;
  var fx = L.Effects.addProperty('S_BlurMoCurves');
  var C = fx.property('S_BlurMoCurves-0050'), Z = fx.property('S_BlurMoCurves-0051');
  C.setValueAtTime(s.t0, P.center); C.setValueAtTime(s.kl, P.center);
  Z.setValueAtTime(s.t0, s.z0); Z.setValueAtTime(s.kl, s.z1);
  for (var k = 1; k <= 2; k++) { Z.setInterpolationTypeAtKey(k, KeyframeInterpolationType.BEZIER); C.setInterpolationTypeAtKey(k, KeyframeInterpolationType.BEZIER); }
  Z.setTemporalEaseAtKey(1, [new KeyframeEase(0, 33.33)], [new KeyframeEase(s.sOut, s.iOut)]);
  Z.setTemporalEaseAtKey(2, [new KeyframeEase(s.sIn, s.iIn)], [new KeyframeEase(0, 33.33)]);
  for (var k = 1; k <= 2; k++) C.setTemporalEaseAtKey(k, [new KeyframeEase(0, 33.33)], [new KeyframeEase(0, 33.33)]);
}
for (var n = 0; n < T.length; n++) {
  var t = T[n], L = adj((t.type == 'dark' ? 'Dark' : 'Flash') + ' @' + t.cut.toFixed(3), t.lin, t.lout);
  var B = L.Effects.addProperty('BCC3Brightness-Contrast').property('BCC3Brightness-Contrast-0002');
  B.setValueAtTime(t.k0, 0); B.setValueAtTime(t.cut, t.peak); B.setValueAtTime(t.k2, 0);
  for (var k = 1; k <= B.numKeys; k++) B.setInterpolationTypeAtKey(k, KeyframeInterpolationType.LINEAR);
}
app.endUndoGroup(); app.project.save(); comp.openInViewer();
var cuts = 0; for (var l = 1; l <= comp.numLayers; l++) if (/^Cut \d+$/.test(comp.layer(l).name)) cuts++;
return '"' + P.comp + '": ' + S.length + ' zoom + ' + T.length + ' transition layers added over ' + cuts + ' cut layers (untouched), saved';
})()""" % (json.dumps({k: plan[k] for k in ("comp", "center")}), json.dumps(segs), json.dumps(trans))
os.makedirs(os.path.join(job, "ae"), exist_ok=True)
open(os.path.join(job, "ae", "stage2.jsx"), "w", encoding="utf-8").write(jsx)
for s in segs: print(f"zoom cut {s['cut']}: {s['t0']:.3f}-{s['t1']:.3f}  Z {s['z0']:.2f} -> {s['z1']:.2f}  (end speeds {s['sOut']:+.2f} / {s['sIn']:+.2f})")
for t in trans: print(f"{t['type']:5s} {t['peak']:+.0f} peak on {t['cut']:.3f}")
print("wrote ae/stage2.jsx")
