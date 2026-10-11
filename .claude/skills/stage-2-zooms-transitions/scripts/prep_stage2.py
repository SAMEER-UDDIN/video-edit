#!/usr/bin/env python3
"""Prepare a Stage 1 comp for Stage 2 (the flow Sameer called perfect on Seq01, 2026-10-11): writes four After Effects scripts into <job>/ae/.

  python .claude/skills/stage-2-zooms-transitions/scripts/prep_stage2.py projects/<job> --comp "Sequence 01 Headtrack 0915" --video 2.mp4

Context: he renders the Stage 1 comp (AME) to a video (`2.mp4`), drops it in the SAME comp above the Stage 1 layers (which he disables), and puts ONE
plain adjustment layer over it. Run detect_cuts.py on that render first (-> ae/picture-cuts.json). Then, in this order:

  1. ae/split-adjustment.jsx   cut his plain adjustment layer(s) at every PICTURE-change frame (duplicates, names/labels kept, no gaps/overlaps)
                               -> he labels the pieces Green (zoom in) / Purple (zoom out) / Orange (3-key: release then snap back in); he may merge weak cuts
  2. ae/split-video.jsx        cut the render layer (--video) at the in-points of those adjustment layers, so each piece sits under one adjustment layer
  3. ae/morph-remap.jsx        TIME REMAP every piece to remove Premiere's Morph Cut blend at its head and tail (his hand method):
                               key at the piece's in-point = first clean frame of the new clip (S + 0.1), key at its out-point = the value that makes the LAST shown
                               frame the last clean frame of the old clip (L + 0.3), linear. The piece is stretched ~3 % (the cut stays on the same frame, audio stays in sync).
                               First piece: head untouched. Last piece: tail untouched. Pieces that already have a remap (his) are skipped.
  4. ae/read-layers.jsx       returns his labelled adjustment layers as JSON [{"in": frame, "out": frame, "label": n}] -> save as ae/layers.json for plan_zooms.py --layers
Each is idempotent-safe: split-* only act on layers that still span a boundary; morph-remap skips remapped layers.
"""
import argparse, json, os

ap = argparse.ArgumentParser()
ap.add_argument("job"); ap.add_argument("--comp", required=True); ap.add_argument("--video", default="2.mp4")
a = ap.parse_args()
job = os.path.abspath(a.job)
pc = json.load(open(os.path.join(job, "ae", "picture-cuts.json"), encoding="utf-8"))
seq = json.load(open(os.path.join(job, "clips.json"), encoding="utf-8")); FPS = seq["fps"]
pic = sorted({x["picture"] for x in pc})
cutmap = {x["picture"]: {"L": x["L"], "S": x["S"]} for x in pc}

COMMON = r"""
var COMP = %s, F = %d;
var comp = null; for (var i = 1; i <= app.project.numItems; i++) if (app.project.item(i) instanceof CompItem && app.project.item(i).name == COMP) comp = app.project.item(i);
if (!comp) throw new Error('comp not found: ' + COMP);
function fr(t) { return Math.round(t * F); }
"""
hdr = COMMON % (json.dumps(a.comp), FPS)

split_adj = "(function(){" + hdr + r"""
var B = %s; var done = [];
app.beginUndoGroup('Stage 2: split adjustment layers at picture changes');
var todo = [];
for (var i = 1; i <= comp.numLayers; i++) { var l = comp.layer(i);
  if (l.adjustmentLayer && l.property('ADBE Effect Parade').numProperties == 0) todo.push(l); }
for (var q = 0; q < todo.length; q++) {
  var base = todo[q], a0 = fr(base.inPoint), a1 = fr(base.outPoint), inside = [];
  for (var k = 0; k < B.length; k++) if (B[k] > a0 && B[k] < a1) inside.push(B[k]);
  if (!inside.length) continue;
  var END = base.outPoint;
  for (var k = 0; k < inside.length; k++) { var d = base.duplicate(); d.inPoint = inside[k] / F; d.outPoint = (k + 1 < inside.length) ? inside[k + 1] / F : END; }
  base.outPoint = inside[0] / F; done.push(a0 + '-' + a1 + ' -> ' + (inside.length + 1) + ' layers');
}
app.endUndoGroup(); app.project.save();
return 'split ' + (done.length ? done.join(' | ') : 'nothing (no plain adjustment layer spans a cut)');
})()""" % json.dumps(pic)

split_vid = "(function(){" + hdr + r"""
var VID = %s; app.beginUndoGroup('Stage 2: split video at adjustment layers');
var cuts = {}, ends = [];
for (var i = 1; i <= comp.numLayers; i++) { var l = comp.layer(i);
  if (l.adjustmentLayer && !/^(Flash|Dark|Zoom)/.test(l.name)) { cuts[fr(l.inPoint)] = 1; ends.push(fr(l.outPoint)); } }
var B = []; for (var k in cuts) B.push(parseInt(k, 10)); B.sort(function (x, y) { return x - y; });
var base = null; for (var i = 1; i <= comp.numLayers; i++) if (comp.layer(i).name == VID && !comp.layer(i).adjustmentLayer && comp.layer(i).enabled) { var l = comp.layer(i); if (!base || (fr(l.outPoint) - fr(l.inPoint)) > (fr(base.outPoint) - fr(base.inPoint))) base = l; }
if (!base) return 'ERROR no layer named ' + VID;
var a0 = fr(base.inPoint), a1 = fr(base.outPoint), inside = [];
for (var k = 0; k < B.length; k++) if (B[k] > a0 && B[k] < a1) inside.push(B[k]);
if (inside.length) { var END = base.outPoint;
  for (var k = 0; k < inside.length; k++) { var d = base.duplicate(); d.inPoint = inside[k] / F; d.outPoint = (k + 1 < inside.length) ? inside[k + 1] / F : END; }
  base.outPoint = inside[0] / F; }
app.endUndoGroup(); app.project.save();
var n = 0; for (var i = 1; i <= comp.numLayers; i++) if (comp.layer(i).name == VID) n++;
return VID + ': ' + (inside.length + 1) + ' pieces now (' + n + ' layers named ' + VID + ')';
})()""" % json.dumps(a.video)

morph = "(function(){" + hdr + r"""
var VID = %s, M = %s, P = []; app.beginUndoGroup('Stage 2: time remap away the Morph Cut blend');
for (var i = 1; i <= comp.numLayers; i++) { var l = comp.layer(i);
  if (l.name == VID && !l.adjustmentLayer && l.enabled && !l.timeRemapEnabled) P.push(l); }
P.sort(function (x, y) { return x.inPoint - y.inPoint; });
var log = [], last = fr(comp.duration);
for (var q = 0; q < P.length; q++) { var l = P[q], fin = fr(l.inPoint), fout = fr(l.outPoint), N = fout - fin;
  var head = M[fin], tail = M[fout];
  var vin = head ? head.S + 0.1 : fin;
  var vout;
  if (tail) { var Lc = tail.L + 0.3; var sl = (Lc - vin) / (N - 1); vout = vin + N * sl; } else vout = fout >= last - 1 ? fout : fout;
  if (!head && !tail) continue;
  l.timeRemapEnabled = true; var tr = l.property('ADBE Time Remapping');
  tr.setValueAtTime(fin / F, vin / F); tr.setValueAtTime(fout / F, vout / F);
  for (var k = tr.numKeys; k >= 1; k--) { var kt = fr(tr.keyTime(k)); if (kt != fin && kt != fout) tr.removeKey(k); }
  log.push(fin + '-' + fout + ' ' + vin.toFixed(1) + '->' + vout.toFixed(2)); }
app.endUndoGroup(); app.project.save();
return 'remapped ' + log.length + ' pieces: ' + log.slice(0, 3).join(' | ') + (log.length > 3 ? ' ...' : '');
})()""" % (json.dumps(a.video), json.dumps(cutmap))

read_layers = "(function(){" + hdr + r"""
var out = [];
for (var i = 1; i <= comp.numLayers; i++) { var l = comp.layer(i);
  if (l.adjustmentLayer && !/^(Flash|Dark|Zoom)/.test(l.name) && !l.property('ADBE Effect Parade').property('BCC3Brightness-Contrast'))
    out.push('{"in":' + fr(l.inPoint) + ',"out":' + fr(l.outPoint) + ',"label":' + l.label + '}'); }
return '[' + out.join(',') + ']';
})()"""

for name, code in (("split-adjustment.jsx", split_adj), ("split-video.jsx", split_vid), ("morph-remap.jsx", morph), ("read-layers.jsx", read_layers)):
    open(os.path.join(job, "ae", name), "w", encoding="utf-8").write(code)
    print("wrote", os.path.join(job, "ae", name))
print(f"{len(pic)} picture-change frames; run split-adjustment.jsx -> (he labels) -> read-layers.jsx -> split-video.jsx -> morph-remap.jsx -> plan_zooms.py --layers ...")
