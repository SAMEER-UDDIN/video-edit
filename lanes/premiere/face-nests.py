#!/usr/bin/env python3
"""face-nests.py: the Affan Afterhours face grammar on a Premiere timeline (STYLE / PLAYBOOK: "the face shot is never still").

  PYTHONUTF8=1 uv run lanes/premiere/face-nests.py projects/<job> --apply [--sequence "Sequence 20"] [--scratch-audio 5] [--only 9,13]
  PYTHONUTF8=1 uv run lanes/premiere/face-nests.py projects/<job> --verify [--sequence ...]

Reads <job>/transcript/face-zooms.json (written by the job's plan-face-zooms.py): one entry per face run
{block, start, end, clips, zooms: [{start, end, words}], skip}. For every run, in the creator's order:
  1. NEST: V1-only subsequence of [start, end] (createSubsequence with only V1 targeted: no audio inside), overwritten
     back onto V1 at `start`. Premiere gives the placed nest an empty audio item; it is routed to --scratch-audio (0-based,
     a track with nothing in any face run) and deleted. A1 (the voice, its effects, the bleep keys) is never touched.
  2. CUT ZOOM inside the nest: Motion > Scale 100 -> 125 as HOLD keys on the sub-clip under the emphasis word: an
     instant snap, no ramp, back to 100 at the zoom's end (or held to the jump cut).
  3. GRADUAL ZOOM on the nest clip: Motion > Scale 100 -> 110, two linear keys across the run.
Idempotent: a nest already on V1 at its start is reused and its keys rewritten; a subsequence already made is reused.
Proven on a throwaway clone first (2026-09-19, gta6-travis-scott-hired): hold keys read 100 at the frame before the snap
and 125 after; the nest reads 105.01 at its midpoint; A1 kept 209/209.
Every bridge call is short (one run), because a call over ~4 s reads as "Bridge is not running" while Premiere finishes
it (lab-notes 2026-09-19): after such a failure the tool waits for the panel and re-checks the run from the timeline.
"""
import json, os, subprocess, sys, time
from pathlib import Path

BRIDGE = Path(__file__).resolve().parent / 'premiere-bridge.mjs'


def es(script, timeout=170):
    r = subprocess.run(['node', str(BRIDGE), 'execute_extendscript', json.dumps({'script': script})],
                       capture_output=True, text=True, timeout=timeout)
    try:
        j = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None, (r.stdout + r.stderr)[-600:]
    if isinstance(j, dict) and j.get('success') is False:
        return None, j.get('error') or j.get('status') or 'bridge error'
    d = j.get('data', j) if isinstance(j, dict) else j
    if isinstance(d, dict): d = d.get('result', d)
    return d, None


def wait_panel():
    for _ in range(40):
        r = subprocess.run(['node', str(BRIDGE), 'ping'], capture_output=True, text=True)
        if r.returncode == 0 and '"connected": true' in r.stdout: return True
        time.sleep(2)
    return False


PRELUDE = r"""
var F = 1001 / 60000, NUDGE = 0.0001;
function seqByName(n){ for (var i = 0; i < app.project.sequences.numSequences; i++) if (app.project.sequences[i].name === n) return app.project.sequences[i]; return null; }
function scaleProp(c){ for (var k = 0; k < c.components.numItems; k++) { var cm = c.components[k]; if (cm.displayName !== "Motion") continue;
  for (var q = 0; q < cm.properties.numItems; q++) if (cm.properties[q].displayName === "Scale") return cm.properties[q]; } return null; }
function findNest(seq, name, s){ var tr = seq.videoTracks[0]; for (var i = 0; i < tr.clips.numItems; i++) { var c = tr.clips[i];
  if (c.name === name && Math.abs(c.start.seconds - s) < 0.02) return c; } return null; }
function valAt(p, t){ var tt = new Time(); tt.seconds = t; return Number(p.getValueAtTime(tt)); }
"""

APPLY = r"""(function(){
""" + PRELUDE + r"""
  var SEQ = %(seq)s, NAME = %(name)s, S = %(s)r, E = %(e)r, Z = %(z)s, SCR = %(scr)d, BIN = %(bin)s, o = {name: NAME};
  var GRAD0 = %(g0)r, GRAD1 = %(g1)r;   // the run's own push: a RATE, not a constant (LESSONS 2026-09-20)
  var seq = seqByName(SEQ); if (!seq) return "ERROR: no sequence " + SEQ;
  if (app.project.activeSequence.sequenceID !== seq.sequenceID) app.project.openSequence(seq.sequenceID);
  var nest = findNest(seq, NAME, S), sub = seqByName(NAME);
  if (!nest) {
    if (!sub) {
      var tv = [], ta = [], pin = seq.getInPoint(), pout = seq.getOutPoint();
      for (var v = 0; v < seq.videoTracks.numTracks; v++) { tv.push(seq.videoTracks[v].isTargeted()); seq.videoTracks[v].setTargeted(v === 0, true); }
      for (var a = 0; a < seq.audioTracks.numTracks; a++) { ta.push(seq.audioTracks[a].isTargeted()); seq.audioTracks[a].setTargeted(false, true); }
      seq.setInPoint(S + NUDGE); seq.setOutPoint(E + NUDGE);
      sub = seq.createSubsequence(false);
      for (var v = 0; v < seq.videoTracks.numTracks; v++) seq.videoTracks[v].setTargeted(tv[v], true);
      for (var a = 0; a < seq.audioTracks.numTracks; a++) seq.audioTracks[a].setTargeted(ta[a], true);
      try { seq.setInPoint(Number(pin)); } catch (e1) {} try { seq.setOutPoint(Number(pout)); } catch (e2) {}
      if (!sub) return "ERROR: createSubsequence failed for " + NAME;
      sub.name = NAME;
      // file it: <job bin>/Face nests
      var root = app.project.rootItem, jb = null, fb = null;
      for (var i = 0; i < root.children.numItems; i++) if (root.children[i].type === ProjectItemType.BIN && root.children[i].name === BIN) jb = root.children[i];
      if (jb) { for (var i = 0; i < jb.children.numItems; i++) if (jb.children[i].type === ProjectItemType.BIN && jb.children[i].name === "Face nests") fb = jb.children[i];
        if (!fb) { jb.createBin("Face nests"); for (var i = 0; i < jb.children.numItems; i++) if (jb.children[i].type === ProjectItemType.BIN && jb.children[i].name === "Face nests") fb = jb.children[i]; }
        if (fb) sub.projectItem.moveBin(fb); }
    }
    var subDur = sub.videoTracks[0].clips.numItems ? sub.videoTracks[0].clips[sub.videoTracks[0].clips.numItems - 1].end.seconds : 0;
    if (Math.abs(subDur - (E - S)) > 1.5 * F) return "ERROR: " + NAME + " holds " + subDur + " s, the run is " + (E - S);
    try { sub.projectItem.setColorLabel(1); } catch (e3) {}   // Iris: the creator's label for a face run
    var t = new Time(); t.seconds = S + NUDGE;
    seq.overwriteClip(sub.projectItem, t, 0, SCR);
    var at = seq.audioTracks[SCR];
    for (var i = at.clips.numItems - 1; i >= 0; i--) if (at.clips[i].name === NAME) at.clips[i].remove(false, false);
    if (app.project.activeSequence.sequenceID !== seq.sequenceID) app.project.openSequence(seq.sequenceID);
    nest = findNest(seq, NAME, S);
    if (!nest) return "ERROR: " + NAME + " did not land on V1 at " + S;
    // the overwrite at S + NUDGE can leave the replaced clip behind as a ZERO-length item at the run's edge
    // (2026-10-03, Sequence 24 at 60 fps: C1321.MP4 97.65-97.65 after Face nest 06): remove any sub-half-frame V1
    // item touching the run, without ripple, so nothing else moves
    var v1t = seq.videoTracks[0]; o.stubs = 0;
    for (var i = v1t.clips.numItems - 1; i >= 0; i--) { var sc = v1t.clips[i];
      if (sc.name !== NAME && sc.end.seconds - sc.start.seconds < F / 2 && sc.start.seconds >= S - F && sc.start.seconds <= E + F) { sc.remove(false, false); o.stubs++; } }
    o.made = true;
  }
  if (!sub) return "ERROR: nest on V1 but no subsequence named " + NAME;
  // the cut zooms, inside the nest (hold keys = an instant snap)
  var st = sub.videoTracks[0];
  for (var i = 0; i < st.clips.numItems; i++) { var p = scaleProp(st.clips[i]); if (p.isTimeVarying()) p.setTimeVarying(false); p.setValue(100, 1); }
  o.cut = [];
  for (var z = 0; z < Z.length; z++) {
    var zs = Z[z][0] - S, ze = Z[z][1] - S, c = null;
    for (var i = 0; i < st.clips.numItems; i++) if (st.clips[i].start.seconds <= zs + 0.001 && st.clips[i].end.seconds > zs + 0.001) c = st.clips[i];
    if (!c) return "ERROR: no sub-clip under the zoom at " + zs;
    var p = scaleProp(c), off = c.inPoint.seconds - c.start.seconds;
    var head = zs - c.start.seconds >= F / 2, tail = c.end.seconds - ze >= F / 2;
    if (!head && !tail) { p.setValue(125, 1); }
    else {
      p.setTimeVarying(true); var K = [];
      if (head) K.push([c.start.seconds, 100]); K.push([zs, 125]); if (tail) K.push([ze, 100]);
      for (var k = 0; k < K.length; k++) { p.addKey(K[k][0] + off); p.setValueAtKey(K[k][0] + off, K[k][1], 1); }
      var ks = p.getKeys(); for (var k = 0; k < ks.length; k++) p.setInterpolationTypeAtKey(ks[k], 4, 1);
    }
    o.cut.push([valAt(p, zs - F + off).toFixed(1), valAt(p, zs + F + off).toFixed(1), valAt(p, Math.max(zs + F, ze - F) + off).toFixed(1)].join("/"));
  }
  // the gradual zoom, on the nest clip
  var np = scaleProp(nest), nin = nest.inPoint.seconds, dur = nest.end.seconds - nest.start.seconds;
  if (np.isTimeVarying()) np.setTimeVarying(false);
  np.setTimeVarying(true); np.addKey(nin); np.setValueAtKey(nin, GRAD0, 1); np.addKey(nin + dur - F); np.setValueAtKey(nin + dur - F, GRAD1, 1);
  var nk = np.getKeys(); for (var k = 0; k < nk.length; k++) np.setInterpolationTypeAtKey(nk[k], 0, 1);
  o.nest = [nest.start.seconds.toFixed(4), nest.end.seconds.toFixed(4), st.clips.numItems];
  o.ramp = [valAt(np, nin).toFixed(2), valAt(np, nin + dur / 2).toFixed(2), valAt(np, nin + dur - F).toFixed(2)].join("/");
  return JSON.stringify(o);
})()"""

VERIFY = r"""(function(){
""" + PRELUDE + r"""
  var SEQ = %(seq)s, RUNS = %(runs)s, SCR = %(scr)d, out = {bad: [], ok: 0};
  var seq = seqByName(SEQ); if (!seq) return "ERROR: no sequence " + SEQ;
  for (var r = 0; r < RUNS.length; r++) { var R = RUNS[r], nest = findNest(seq, R.name, R.s), sub = seqByName(R.name);
    if (!nest || !sub) { out.bad.push(R.name + ": missing"); continue; }
    if (Math.abs(nest.end.seconds - R.e) > 1.5 * F) { out.bad.push(R.name + ": ends " + nest.end.seconds); continue; }
    var st = sub.videoTracks[0]; if (st.clips.numItems !== R.n) { out.bad.push(R.name + ": " + st.clips.numItems + " clips inside, run has " + R.n); continue; }
    var np = scaleProp(nest), nin = nest.inPoint.seconds, dur = nest.end.seconds - nest.start.seconds;
    var a = valAt(np, nin), b = valAt(np, nin + dur - F);
    if (Math.abs(a - R.g[0]) > 0.05 || Math.abs(b - R.g[1]) > 0.05) { out.bad.push(R.name + ": ramp " + a + " -> " + b + ", wanted " + R.g[0] + " -> " + R.g[1]); continue; }
    var bad = false;
    for (var z = 0; z < R.z.length; z++) { var zs = R.z[z][0] - R.s, c = null;
      for (var i = 0; i < st.clips.numItems; i++) if (st.clips[i].start.seconds <= zs + 0.001 && st.clips[i].end.seconds > zs + 0.001) c = st.clips[i];
      var p = scaleProp(c), off = c.inPoint.seconds - c.start.seconds;
      if (Math.abs(valAt(p, zs + F + off) - 125) > 0.05) { out.bad.push(R.name + ": no 125 at " + zs); bad = true; } }
    if (!bad) out.ok++; }
  out.v1 = seq.videoTracks[0].clips.numItems; out.a1 = seq.audioTracks[0].clips.numItems; out.scratch = seq.audioTracks[SCR].clips.numItems;
  out.v4 = seq.videoTracks.numTracks > 3 ? seq.videoTracks[3].clips.numItems : -1;
  return JSON.stringify(out);
})()"""


def main():
    a = sys.argv[1:]
    if not a or ('--apply' not in a and '--verify' not in a): sys.exit(__doc__)
    job = Path(a[0]).resolve()
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    seqn, scr = opt('--sequence', 'Sequence 20'), int(opt('--scratch-audio', '5'))
    binn = opt('--bin', 'GTA 6 Travis Scott')
    only = {int(x) for x in opt('--only', '').split(',') if x}
    plan = json.load(open(job / 'transcript' / 'face-zooms.json', encoding='utf-8'))
    runs = []
    for k, r in enumerate(plan['runs'], 1):
        m, s = divmod(int(r['start']), 60)
        runs.append(dict(r, name=f'Face nest {k:02d} · {m}:{s:02d}'))
    if '--verify' in a:
        R = [dict(name=r['name'], s=r['start'], e=r['end'], n=r['clips'], g=r.get('gradual') or plan.get('gradual') or [100, 110],
                  z=[[z['start'], z['end']] for z in r['zooms']]) for r in runs]
        d, err = es(VERIFY % dict(seq=json.dumps(seqn), runs=json.dumps(R), scr=scr))
        if err or str(d).startswith('ERROR'): sys.exit(f'verify failed: {err or d}')
        v = d if isinstance(d, dict) else json.loads(d)
        for b in v['bad']: print('✗', b)
        print(f"{v['ok']}/{len(R)} face nests verified · V1 {v['v1']} clips · A1 {v['a1']} · scratch A{scr + 1} {v['scratch']} · V4 {v['v4']}")
        sys.exit(0 if v['ok'] == len(R) else 1)
    for r in runs:
        if only and r['block'] not in only: continue
        g = r.get('gradual') or plan.get('gradual') or [100, 110]
        args = dict(seq=json.dumps(seqn), name=json.dumps(r['name']), s=r['start'], e=r['end'], scr=scr, bin=json.dumps(binn),
                    g0=float(g[0]), g1=float(g[1]), z=json.dumps([[z['start'], z['end']] for z in r['zooms']]))
        for attempt in range(4):
            d, err = es(APPLY % args)
            if err is None and not str(d).startswith('ERROR'):
                print(('+ ' if '"made"' in str(d) else '= ') + str(d)); break
            if err is None: sys.exit(f"{r['name']}: {d}")
            print(f"  … {r['name']}: {err[:80]} (attempt {attempt + 1}); waiting for the panel, then re-checking")
            if not wait_panel(): sys.exit('the bridge panel did not come back')
            time.sleep(3)
        else:
            sys.exit(f"{r['name']}: gave up after 4 attempts")
    d, err = es('(function(){ app.project.save(); return "saved"; })()')
    print(d or err)


if __name__ == '__main__':
    main()
