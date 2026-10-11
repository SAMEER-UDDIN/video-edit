#!/usr/bin/env python3
"""audio-polish.py: pipeline step 3 on the Premiere lane, the house chain on every A1 clip.

  uv run lanes/premiere/audio-polish.py projects/<job> --apply             # gain from voice-gain.py, chain on every A1 clip, read back, save
  uv run lanes/premiere/audio-polish.py projects/<job> --apply --gain 15   # a named gain instead of the measured one
  uv run lanes/premiere/audio-polish.py projects/<job> --verify            # read every A1 clip's chain back, exit 1 on a miss
  uv run lanes/premiere/audio-polish.py projects/<job>/sections/<s> --apply --range FROM TO
        # multi-section job: the gain measured on that section's own cuts.json, applied only to the
        # A1 clips starting in [FROM, TO) timeline seconds (every section shoots at its own level)

The WHAT: Amplify +GAIN (measured, workflows/voice-gain.py: the raw's kept speech to -17 LUFS)
into a Hard Limiter at -6 dBFS, one static pass, never loudnorm. The HOW, all read back:

  - every A1 clip gets Amplify + Hard Limiter as CLIP effects (QE addAudioEffect when missing,
    matched to the DOM clip by start time, so an existing chain is updated in place, not doubled)
  - Amplify Left/Right v = (dB + 96) / 144 · Hard Limiter Maximum Amplitude v = (dB + 100) / 100
    (both ranges verified in the UI 2026-07-30; a 0 dB check cannot tell the ranges apart)
  - a MONO clip exposes one Amplify "Gain" slider (same range) and plays under Premiere's -3 dB centre pan law
    on a stereo master, so it gets gain + 3 dB (proved by voice-only bounces, your-job 2026-09-07)
  - a timeline rebuild (re-replay) drops clip effects: run --apply again after one
"""
import json, os, subprocess, sys
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

BRIDGE = Path(__file__).resolve().parent / 'premiere-bridge.mjs'
VOICE_GAIN = Path(__file__).resolve().parent.parent.parent / 'workflows' / 'voice-gain.py'
LIMIT_DB = -6
PAN_LAW_DB = 3   # a MONO clip on a stereo sequence plays at -3 dB per channel (Premiere's centre pan law); its Gain gets this back


def sh(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: sys.exit(f"{' '.join(cmd[:3])} failed:\n{r.stderr or r.stdout}")
    return r.stdout


def es(script):
    out = sh('node', str(BRIDGE), 'execute_extendscript', json.dumps({'script': script}))
    lines = out.splitlines(); j = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i][:1] in '{["':
            try: j = json.loads('\n'.join(lines[i:])); break
            except json.JSONDecodeError: continue
    if j is None: sys.exit(f'bridge returned non-JSON:\n{out[-800:]}')
    if isinstance(j, dict) and j.get('success') is False: sys.exit(f"bridge error: {j.get('error')}")
    d = j.get('data', j) if isinstance(j, dict) else j
    if isinstance(d, dict): d = d.get('result', d)
    return d if isinstance(d, str) else json.dumps(d)


amp_v = lambda db: (db + 96) / 144
lim_v = lambda db: (db + 100) / 100


def run(gain, apply, rng=None):
    lo, hi = rng if rng else (-1, 1e9)
    r = es(r"""
(function(){
  var seq = app.project.activeSequence; if (!seq) return "ERROR: no active sequence";
  var AMP = %s, AMP_MONO = %s, LIM = %s, APPLY = %s, LO = %s, HI = %s;
  var tr = seq.audioTracks[0], out = {clips: 0, added: 0, ok: 0, bad: []};
  var qtr = null;
  if (APPLY) { app.enableQE(); qtr = qe.project.getActiveSequence().getAudioTrackAt(0); }
  function qItemAt(t){ for (var q = 0; q < qtr.numItems; q++) { var it = qtr.getItemAt(q);
    if (it.type === "Clip" && Math.abs(it.start.secs - t) < 0.002) return it; } return null; }
  function comp(c, name){ for (var k = 0; k < c.components.numItems; k++) if (c.components[k].displayName === name) return c.components[k]; return null; }
  function prop(cm, name){ for (var q = 0; q < cm.properties.numItems; q++) if (cm.properties[q].displayName === name) return cm.properties[q]; return null; }
  for (var i = 0; i < tr.clips.numItems; i++) {
    var c = tr.clips[i];
    if (c.start.seconds < LO || c.start.seconds >= HI) continue;   // --range: this section's clips only
    out.clips++;
    if (APPLY) {
      var need = []; if (!comp(c, "Amplify")) need.push("Amplify"); if (!comp(c, "Hard Limiter")) need.push("Hard Limiter");
      if (need.length) { var qi = qItemAt(c.start.seconds); if (!qi) { out.bad.push(i + ": no QE item"); continue; }
        for (var n = 0; n < need.length; n++) { qi.addAudioEffect(qe.project.getAudioEffectByName(need[n])); out.added++; } }
      var a = comp(c, "Amplify"), l = comp(c, "Hard Limiter");
      if (!a || !l) { out.bad.push(i + ": chain missing after add"); continue; }
      // stereo source: Amplify exposes Left + Right; MONO source: one "Gain" slider on the same -96..+48
      // range (proved by voice-only bounces on your-job 2026-09-07: stereo intro -21.0 LUFS at the
      // -6 ceiling, mono outro -22.5 LUFS with peaks -8.9 = the -3 dB centre pan law a mono clip gets on a
      // stereo master), so a mono clip takes gain + PAN_LAW so the master hears the same level
      var L = prop(a, "Left"), R = prop(a, "Right"), G = prop(a, "Gain"), M = prop(l, "Maximum Amplitude");
      if (!((L && R) || G) || !M) { out.bad.push(i + ": property not found"); continue; }
      if (G && !(L && R)) G.setValue(AMP_MONO, true); else { L.setValue(AMP, true); R.setValue(AMP, true); }
      M.setValue(LIM, true);
    }
    var a2 = comp(c, "Amplify"), l2 = comp(c, "Hard Limiter");
    if (!a2 || !l2) { out.bad.push(i + ": no chain"); continue; }
    var L2 = prop(a2, "Left"), R2 = prop(a2, "Right"), G2 = prop(a2, "Gain"), M2 = prop(l2, "Maximum Amplitude");
    if (!((L2 && R2) || G2) || !M2) { out.bad.push(i + ": property not found"); continue; }
    var mono = !(L2 && R2);
    var want = mono ? AMP_MONO : AMP;
    var gl = mono ? G2.getValue() : L2.getValue(), gr = mono ? gl : R2.getValue(), gm = M2.getValue();
    if (Math.abs(gl - want) > 1e-4 || Math.abs(gr - want) > 1e-4 || Math.abs(gm - LIM) > 1e-4) out.bad.push(i + (mono ? ": Gain=" : ": L=") + gl + (mono ? "" : " R=" + gr) + " lim=" + gm);
    else { out.ok++; if (mono) out.mono = (out.mono || 0) + 1; }
  }
  if (APPLY && !out.bad.length) app.project.save();
  return JSON.stringify(out);
})()""" % (amp_v(gain), amp_v(gain + PAN_LAW_DB), lim_v(LIMIT_DB), 'true' if apply else 'false', repr(float(lo)), repr(float(hi))))
    if str(r).startswith('ERROR'): sys.exit(r)
    return json.loads(r)


def main():
    a = sys.argv[1:]
    if len(a) < 2: sys.exit(__doc__)
    job = a[0]
    if '--gain' in a:
        gain = int(a[a.index('--gain') + 1]); src = 'named'
    else:
        m = json.loads(sh('uv', 'run', str(VOICE_GAIN), job, '--json'))
        gain = m['gain_db']; src = f"measured: kept speech {m['lufs']} LUFS -> target {m['target_lufs']}"
        if m.get('warn'): print('⚠ ' + m['warn'])
    apply = '--apply' in a
    rng = None
    if '--range' in a:   # multi-section jobs: only A1 clips starting in [FROM, TO) seconds get this gain
        i = a.index('--range'); rng = (float(a[i + 1]), float(a[i + 2]))
    got = run(gain, apply, rng)
    scope = f" · range {rng[0]:.3f}–{rng[1]:.3f}s" if rng else ''
    print(f"gain {gain:+d} dB ({src}) · limiter {LIMIT_DB} dBFS · A1 clips {got['clips']}{scope} · chain added on {got['added']} effect slot(s) · {got['ok']} verified" + (f" ({got['mono']} mono: Gain slider at {gain + PAN_LAW_DB:+d} dB, the -3 dB centre pan law given back)" if got.get('mono') else ''))
    for b in got['bad']: print('✗ ' + b)
    if got['bad']: sys.exit(1)
    if apply: print('saved')


if __name__ == '__main__':
    main()
