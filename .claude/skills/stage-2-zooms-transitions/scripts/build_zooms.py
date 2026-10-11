#!/usr/bin/env python3
"""Step 5: <job>/stage2-plan.json -> <job>/ae/stage2.jsx (run with the after-effects MCP: ae_run_jsx {"file": ...}).

  python .claude/skills/stage-2-zooms-transitions/scripts/build_zooms.py projects/<job>

Adds INTO his cut comp (from make_cut_comp.py), never touching his "Cut N" layers; re-running replaces only layers named
"Zoom ..." / "Flash @..." / "Dark @..." / "Solid flash @..." / "Band ...". Method: docs/fight-club/blurmo-transitions-method.md
(his Comp 09 and, 2026-10-11, "fightclubtestingphase Linked Comp 01").
  * zoom = one adjustment layer per cut, exactly spanning it, labelled like the cut: Sapphire S_BlurMoCurves at defaults,
    Center XY + Z Dist keyed on the first and last frame, Bezier with his curve measured on 20 zooms (Linked Comp 01):
      zoom IN  (1 -> ~0.74): out speed 4.5x avg slope / influence 9 %, in speed 2.6x / 15 %   (fast start, softer landing)
      zoom OUT (~0.75 -> 1): out speed 3.8x avg slope / influence 10.5 %, in speed 3.5x / 12 %
      hook (cut 1 zoom out): starts 0.64 with a whip (influence 1 %) and an easy landing (influence 56 %)
  * flash = its own adjustment layer: BCC Brightness-Contrast, Brightness LINEAR 0 -> peak ON the cut frame -> 0
    (14 frames up, 15 down @60 fps), layer from cut-52 to cut+93 frames. Peak +19..+30 (default +25). ("dark" still works.)
  * solid flash (a hard impact cut instead of the brightness flash): white solid, Opacity 100 on the cut -> 0 over 25 frames
    (easy ease), layer from cut-1 to cut+75 frames
  * band (a wide B-roll that doesn't fit vertical): duplicates of that Cut layer - sharp copy masked to a horizontal band
    (y 18 % - 82 % of the height), a copy behind it at 163.8 % with Gaussian Blur 25, two thin white lines on the band edges
"""
import json, os, sys

job = os.path.abspath(sys.argv[1])
plan = json.load(open(os.path.join(job, "stage2-plan.json"), encoding="utf-8"))
FD = 1.0 / plan["fps"]; F60 = plan["fps"] / 60.0
segs = []
for s in plan["segments"]:
    t0 = round(s["t0"] / FD) * FD; t1 = round(s["t1"] / FD) * FD; last = t1 - FD
    avg = (s["z1"] - s["z0"]) / max(last - t0, FD)
    zin = s["z1"] < s["z0"]
    cur = s.get("curve", "")
    if cur == "drop":      # intense drop: snap in the first frames, long soft settle (his first-clip curve)
        sg = 1 if s["z1"] > s["z0"] else -1
        sOut, iOut, sIn, iIn = 14.4 * sg, 1, 0, 55
    elif zin:
        sub = 1 - s.get("subtle", 1.0)          # short segment: softer ease (more influence), the depth is already shallower
        sOut, iOut, sIn, iIn = 4.5 * avg, 9 + 14 * sub, 2.6 * avg, 15 + 10 * sub
    else:
        sub = 1 - s.get("subtle", 1.0)
        sOut, iOut, sIn, iIn = 3.8 * avg, 10.5 + 14 * sub, 3.5 * avg, 12 + 10 * sub
    segs.append({"cut": s["cut"], "t0": t0, "t1": t1, "kl": last, "z0": s["z0"], "z1": s["z1"], "sOut": sOut, "iOut": iOut,
                 "sIn": sIn, "iIn": iIn, "lbl": {"Green": 9, "Purple": 10}.get(s.get("label"), 0),
                 "center": s.get("center") or plan["center"], "layer_in": s.get("layer_in")})
    if cur == "drop3":     # 3 keys: slow release z0 -> 1.0, then a drop-curve zoom-in that lands on the cut
        km = t0 + max(1, round(s.get("frac", 0.77) * (last - t0) / FD)) * FD
        a1 = (1.0 - s["z0"]) / (km - t0)
        segs[-1].update({"three": True, "km": km, "z0": s["z0"], "z1": 1.0, "z3": 0.755,
                         "sOut": 4.3 * a1, "iOut": 11.7, "sIn": 4.0 * a1, "iIn": 12.7})
trans = []
for t in plan["transitions"]:
    c = round(t["cut"] / FD) * FD; typ = t["type"]
    if typ == "solid":
        trans.append({"cut": c, "type": "solid", "lin": max(0, c - FD), "lout": min(plan["duration"], c + round(76 * F60) * FD),
                      "fade": c + round(25 * F60) * FD})
    else:
        trans.append({"cut": c, "type": typ, "peak": plan["dark"] if typ == "dark" else t.get("peak", plan["flash"]),
                      "k0": c - round(14 * F60) * FD, "k2": c + round(15 * F60) * FD,
                      "lin": max(0, c - round(52 * F60) * FD), "lout": min(plan["duration"], c + round(93 * F60) * FD)})
bands = plan.get("bands", [])
lines = plan.get("lines", [])

jsx = r"""(function(){
var P = %s, S = %s, T = %s, BANDS = %s, LINES = %s;
app.beginUndoGroup('Stage 2 zooms + transitions');
var proj = app.project, comp = null;
for (var i = 1; i <= proj.numItems; i++) if (proj.item(i) instanceof CompItem && proj.item(i).name == P.comp) comp = proj.item(i);
if (!comp) return 'ERROR comp not found: ' + P.comp + ' (run ae/cuts.jsx first)';
function layerAt(fin) { for (var l = 1; l <= comp.numLayers; l++) { var q = comp.layer(l); if (q.adjustmentLayer && Math.abs(Math.round(q.inPoint * comp.frameRate) - fin) <= 0) return q; } return null; }
for (var l = comp.numLayers; l >= 1; l--) if (/^(Zoom |Dark @|Flash @|Solid flash @|Band |White Solid 1 \(band)/.test(comp.layer(l).name)) comp.layer(l).remove();
function adj(name, tin, tout) { var l = comp.layers.addSolid([1, 1, 1], name, comp.width, comp.height, 1, comp.duration);
  l.adjustmentLayer = true; l.inPoint = tin; l.outPoint = tout; return l; }
var BEZ = KeyframeInterpolationType.BEZIER, LIN = KeyframeInterpolationType.LINEAR;
for (var n = 0; n < S.length; n++) {
  var s = S[n], L = null;
  if (s.layer_in !== null) {    // HIS labelled adjustment layer: put the zoom on it, keep its name / label / span
    L = layerAt(s.layer_in); if (!L) return 'ERROR no adjustment layer starting at frame ' + s.layer_in;
    var oldfx = L.property('ADBE Effect Parade').property('S_BlurMoCurves'); if (oldfx) oldfx.remove();
  } else { L = adj('Zoom ' + s.cut + (s.z1 < s.z0 ? ' in' : ' out'), s.t0, s.t1); if (s.lbl) L.label = s.lbl; }
  var fx = L.Effects.addProperty('S_BlurMoCurves');
  var C = fx.property('S_BlurMoCurves-0050'), Z = fx.property('S_BlurMoCurves-0051');
  if (s.three) {
    C.setValueAtTime(s.t0, s.center); C.setValueAtTime(s.km, s.center); C.setValueAtTime(s.kl, s.center);
    Z.setValueAtTime(s.t0, s.z0); Z.setValueAtTime(s.km, 1.0); Z.setValueAtTime(s.kl, s.z3);
    for (var k = 1; k <= 3; k++) { Z.setInterpolationTypeAtKey(k, BEZ); C.setInterpolationTypeAtKey(k, BEZ); C.setTemporalEaseAtKey(k, [new KeyframeEase(0, 33.33)], [new KeyframeEase(0, 33.33)]); }
    Z.setTemporalEaseAtKey(1, [new KeyframeEase(0, 33.33)], [new KeyframeEase(s.sOut, s.iOut)]);
    Z.setTemporalEaseAtKey(2, [new KeyframeEase(s.sIn, s.iIn)], [new KeyframeEase(-14.4, 1)]);
    Z.setTemporalEaseAtKey(3, [new KeyframeEase(0, 50)], [new KeyframeEase(0, 16.7)]);
    continue;
  }
  C.setValueAtTime(s.t0, s.center); C.setValueAtTime(s.kl, s.center);
  Z.setValueAtTime(s.t0, s.z0); Z.setValueAtTime(s.kl, s.z1);
  for (var k = 1; k <= 2; k++) { Z.setInterpolationTypeAtKey(k, BEZ); C.setInterpolationTypeAtKey(k, BEZ); }
  Z.setTemporalEaseAtKey(1, [new KeyframeEase(0, 33.33)], [new KeyframeEase(s.sOut, s.iOut)]);
  Z.setTemporalEaseAtKey(2, [new KeyframeEase(s.sIn, s.iIn)], [new KeyframeEase(0, 33.33)]);
  for (var k = 1; k <= 2; k++) C.setTemporalEaseAtKey(k, [new KeyframeEase(0, 33.33)], [new KeyframeEase(0, 33.33)]);
}
for (var n = 0; n < T.length; n++) {
  var t = T[n];
  if (t.type == 'solid') {
    var W = comp.layers.addSolid([1, 1, 1], 'Solid flash @' + t.cut.toFixed(3), comp.width, comp.height, 1, comp.duration);
    W.inPoint = t.lin; W.outPoint = t.lout;
    var O = W.transform.opacity; O.setValueAtTime(t.cut, 100); O.setValueAtTime(t.fade, 0);
    // his camera-flash decay (edited by hand at 6 s): white on the cut, 64 pct next frame, 27 pct at +5, 11 pct at +10, 0 by +24
    for (var k = 1; k <= 2; k++) O.setInterpolationTypeAtKey(k, BEZ);
    O.setTemporalEaseAtKey(1, [new KeyframeEase(0, 33.33)], [new KeyframeEase(-5485.5, 3.1)]);
    O.setTemporalEaseAtKey(2, [new KeyframeEase(0, 73.8)], [new KeyframeEase(0, 16.7)]);
    continue;
  }
  var L = adj((t.type == 'dark' ? 'Dark' : 'Flash') + ' @' + t.cut.toFixed(3), t.lin, t.lout);
  var B = L.Effects.addProperty('BCC3Brightness-Contrast').property('BCC3Brightness-Contrast-0002');
  B.setValueAtTime(t.k0, 0); B.setValueAtTime(t.cut, t.peak); B.setValueAtTime(t.k2, 0);
  for (var k = 1; k <= B.numKeys; k++) B.setInterpolationTypeAtKey(k, LIN);
}
function findCut(k) { for (var l = 1; l <= comp.numLayers; l++) if (comp.layer(l).name == 'Cut ' + k) return comp.layer(l); return null; }
var H = comp.height, bandTop = Math.round(0.18 * H), bandBot = Math.round(0.818 * H);
for (var n = 0; n < BANDS.length; n++) {
  var src = findCut(BANDS[n]); if (!src) continue;
  var bg = src.duplicate(); bg.name = 'Band bg ' + BANDS[n]; bg.transform.scale.setValue([163.8, 163.8]);
  bg.Effects.addProperty('ADBE Gaussian Blur 2').property('ADBE Gaussian Blur 2-0001').setValue(25);
  var sh = src.duplicate(); sh.name = 'Band sharp ' + BANDS[n];
  var ms = sh.property('ADBE Mask Parade').addProperty('ADBE Mask Atom'), shp = new Shape();
  shp.vertices = [[-60, bandTop], [comp.width + 60, bandTop], [comp.width + 60, bandBot], [-60, bandBot]]; shp.closed = true;
  ms.property('ADBE Mask Shape').setValue(shp);
  bg.moveBefore(src); sh.moveBefore(src);
  for (var q = 0; q < 2; q++) {
    var ln = comp.layers.addSolid([1, 1, 1], 'Band line ' + BANDS[n] + (q ? ' bottom' : ' top'), comp.width, comp.height, 1, comp.duration);
    ln.inPoint = src.inPoint; ln.outPoint = src.outPoint;
    ln.transform.scale.setValue([100, 1.26 * H / 1920]); ln.transform.position.setValue([comp.width / 2, q ? bandBot - 7 : bandTop + 3]);
    ln.moveBefore(src);
  }
}
function findPiece(t0) { for (var l = 1; l <= comp.numLayers; l++) { var q = comp.layer(l); if (!q.adjustmentLayer && q.enabled && Math.abs(q.inPoint - t0) < 0.5 / comp.frameRate && !/^White Solid|^Band|^Solid/.test(q.name)) return q; } return null; }
for (var n = 0; n < LINES.length; n++) {   // blurred band already baked into the render: just the two white edge lines (24 px)
  var Ln = LINES[n], pc = findPiece(Ln.t0); if (!pc) continue;
  var ys = [Ln.top + 3, Ln.bottom - 7], nm = ['top', 'bottom'];
  for (var q = 0; q < 2; q++) {
    var sl = comp.layers.addSolid([1, 1, 1], 'White Solid 1 (band ' + nm[q] + ' ' + Ln.cut + ')', comp.width, comp.height, 1, comp.duration);
    sl.inPoint = pc.inPoint; sl.outPoint = pc.outPoint; sl.transform.scale.setValue([100, 1.26126126126125 * comp.height / 1920]);
    sl.transform.position.setValue([comp.width / 2, ys[q]]); sl.moveBefore(pc);
  }
}
app.endUndoGroup(); app.project.save(); comp.openInViewer();
var cuts = 0; for (var l = 1; l <= comp.numLayers; l++) if (/^Cut \d+$/.test(comp.layer(l).name)) cuts++;
return '"' + P.comp + '": ' + S.length + ' zoom + ' + T.length + ' transition layers + ' + BANDS.length + ' band(s) over ' + cuts + ' cut layers (untouched), saved';
})()""" % (json.dumps({k: plan[k] for k in ("comp", "center")}), json.dumps(segs), json.dumps(trans), json.dumps(bands), json.dumps(lines))
os.makedirs(os.path.join(job, "ae"), exist_ok=True)
open(os.path.join(job, "ae", "stage2.jsx"), "w", encoding="utf-8").write(jsx)
for s in segs: print(("3-key " if s.get("three") else "") + f"zoom cut {s['cut']}: {s['t0']:.3f}-{s['t1']:.3f}  Z {s['z0']:.2f} -> {s['z1']:.2f}  center {s['center']}  (end speeds {s['sOut']:+.2f}/{s['iOut']:.0f}% , {s['sIn']:+.2f}/{s['iIn']:.0f}%)")
for t in trans: print(f"{t['type']:5s} " + (f"{t['peak']:+.0f} peak " if 'peak' in t else "") + f"on {t['cut']:.3f}")
if bands: print(f"band look on cuts {bands}")
print("wrote ae/stage2.jsx")
