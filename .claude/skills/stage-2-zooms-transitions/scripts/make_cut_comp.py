#!/usr/bin/env python3
"""Step 1: Sameer's Premiere V1 cuts -> an AE comp with ONE layer per cut (exact in/out), ready for him to label.

  python .claude/skills/stage-2-zooms-transitions/scripts/make_cut_comp.py projects/<job> [--comp "<name>"]

Reads <job>/clips.json (from stage-1's premiere_clips.py, run on the sequence he wants zoomed) and writes:
  <job>/ae/cuts.jsx         builds/refreshes the comp: layer "Cut N" per V1 clip, source timing preserved, NO effects,
                            audio off, unlabelled — EXCEPT a refresh keeps any label he already gave "Cut N" (by name).
                            Re-running only touches layers named "Cut N".
  <job>/ae/read-labels.jsx  returns JSON of every "Cut N" layer: name, label index, in, out (run after he labels)
"""
import argparse, json, os

ap = argparse.ArgumentParser(); ap.add_argument("job"); ap.add_argument("--comp")
a = ap.parse_args()
job = os.path.abspath(a.job)
seq = json.load(open(os.path.join(job, "clips.json"), encoding="utf-8"))
comp = a.comp or seq["sequence"] + " Cuts"
cuts = [{"n": k + 1, "path": c["path"], "ts": c["seq_start"], "te": c["seq_end"], "i0": c["src_in"]} for k, c in enumerate(seq["clips"])]

cuts_jsx = r"""(function(){
var C = %s, NAME = %s, W = %d, H = %d, FPS = %f, DUR = %f;
app.beginUndoGroup('Stage 2 cut comp');
var proj = app.project, comp = null, foot = {};
for (var i = 1; i <= proj.numItems; i++) if (proj.item(i) instanceof CompItem && proj.item(i).name == NAME) comp = proj.item(i);
if (!comp) comp = proj.items.addComp(NAME, W, H, 1, DUR, FPS);
var kept = {}, keptN = 0;                                   // never lose his labels on a refresh
for (var l = comp.numLayers; l >= 1; l--) { var Lx = comp.layer(l);
  if (/^Cut \d+$/.test(Lx.name)) { if (Lx.label) { kept[Lx.name] = Lx.label; keptN++; } Lx.remove(); } }
comp.duration = DUR; comp.frameRate = FPS;
function footage(p) {
  if (foot[p]) return foot[p];
  var want = new File(p).fsName.toLowerCase();
  for (var i = 1; i <= proj.numItems; i++) { var it = proj.item(i); if (it instanceof FootageItem && it.file && it.file.fsName.toLowerCase() == want) return (foot[p] = it); }
  return (foot[p] = proj.importFile(new ImportOptions(new File(p))));
}
for (var n = C.length - 1; n >= 0; n--) {
  var c = C[n], L = comp.layers.add(footage(c.path));
  L.name = 'Cut ' + c.n; L.startTime = c.ts - c.i0; L.inPoint = c.ts; L.outPoint = c.te; L.label = kept[L.name] || 0;
  if (L.hasAudio) L.audioEnabled = false;
  L.moveToEnd();
}
for (var n = 0; n < C.length; n++) { var L = comp.layer('Cut ' + C[n].n); if (L) L.moveToEnd(); }   // Cut 1 .. Cut N top-down, at the bottom
app.endUndoGroup(); app.project.save(); comp.openInViewer();
return 'comp "' + NAME + '": ' + C.length + ' cut layers (' + keptN + ' existing labels kept), saved and opened';
})()""" % (json.dumps(cuts), json.dumps(comp), seq["width"], seq["height"], seq["fps"], seq["duration"])

read_jsx = r"""(function(){
var NAME = %s, comp = null;
for (var i = 1; i <= app.project.numItems; i++) if (app.project.item(i) instanceof CompItem && app.project.item(i).name == NAME) comp = app.project.item(i);
if (!comp) return 'ERROR no comp ' + NAME;
var o = [];
for (var l = 1; l <= comp.numLayers; l++) { var L = comp.layer(l); if (!/^Cut \d+$/.test(L.name)) continue;
  o.push('{"name":"' + L.name + '","label":' + L.label + ',"in":' + L.inPoint + ',"out":' + L.outPoint + '}'); }
return '[' + o.join(',') + ']';
})()""" % json.dumps(comp)

os.makedirs(os.path.join(job, "ae"), exist_ok=True)
open(os.path.join(job, "ae", "cuts.jsx"), "w", encoding="utf-8").write(cuts_jsx)
open(os.path.join(job, "ae", "read-labels.jsx"), "w", encoding="utf-8").write(read_jsx)
print(f'comp "{comp}": {len(cuts)} cuts -> ae/cuts.jsx, ae/read-labels.jsx')
for c in cuts: print(f"  Cut {c['n']}: {c['ts']:.4f}-{c['te']:.4f}  {os.path.basename(c['path'])}")
