#!/usr/bin/env python3
"""place-sfx.py: put a job's sfx-plan.json on the Premiere SFX tracks (pipeline step 6, Premiere lane).

  uv run lanes/premiere/place-sfx.py projects/<job> --apply     # place every row not yet on the timeline, set levels, read back, save
  uv run lanes/premiere/place-sfx.py projects/<job> --verify    # timeline readback vs sfx-plan.json (exit 1 on drift)
  uv run lanes/premiere/place-sfx.py projects/<job> --remove    # clear ALL library SFX clips, only for a deliberate full replacement
  uv run lanes/premiere/place-sfx.py projects/<job> --diff      # the timeline vs the plan: the user's hand edits, the input for the next rule
  uv run lanes/premiere/place-sfx.py projects/<job> --plan <f> --apply   # a SECOND cue sheet from another library folder

The plan is universal (workflows/sfx-plan.py); this is the HOW for Premiere. Rows carry
{at, file, src_in, src_out, level_db, track}. Mechanics, all read back before they are believed:

  - the library file is imported ONCE into an `sfx` bin (found by media path on later runs)
  - audio tracks are provisioned with QE addTracks so the plan's track index exists (appends, so
    nothing already placed moves)
  - each slice is placed by setting the project item's in/out and DOM overwriteClip at
    at + 1e-4 (the replay's floor-nudge), then the in/out are cleared again
  - the level is the clip's intrinsic Volume > Level: v = 10^((dB - 15) / 20), which is the
    encoding read off eleven distinct whole-dB values on the your-job timeline
"""
import json, math, os, subprocess, sys
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

BRIDGE = Path(__file__).resolve().parent / 'premiere-bridge.mjs'
NUDGE = 1e-4


def sh(*cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"{' '.join(cmd[:3])} failed:\n{r.stderr or r.stdout}")
    return r.stdout


def es(script, _retry=True):
    out = sh('node', str(BRIDGE), 'execute_extendscript', json.dumps({'script': script}))
    # the bridge logs to stdout too (multi-line when the script is long): the result is the LAST
    # top-level JSON value, which starts at the last unindented '{' or '[' line
    lines = out.splitlines(); j = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i][:1] in '{[' or lines[i][:1] == '"':
            try: j = json.loads('\n'.join(lines[i:])); break
            except json.JSONDecodeError: continue
    if j is None:
        if _retry and not out.strip(): return es(script, False)    # an empty answer right after a relaunch: once more
        sys.exit(f'bridge returned non-JSON:\n{out[-800:]}')
    if isinstance(j, dict) and j.get('success') is False: sys.exit(f"bridge error: {j.get('error')}")
    d = j.get('data', j) if isinstance(j, dict) else j
    if isinstance(d, dict): d = d.get('result', d)
    return d if isinstance(d, str) else json.dumps(d)


def probe_fps(path):
    r = sh('ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', path)
    n, _, d = r.strip().split('\n')[0].strip(',').partition('/')
    return float(n) / float(d or 1)


def lvl_v(db): return 10 ** ((db - 15) / 20)
def v_lvl(v): return 20 * math.log10(max(v, 1e-9)) + 15


class Placer:
    def __init__(self, job, plan=None):
        self.job = Path(job).resolve()
        self.hf = self.job / 'hf-graphics'
        # `--plan <file>` lets a second cue sheet share these mechanics. readback() filters by the
        # LIBRARY FOLDER of row 0, so two sheets drawing on two folders never see each other's clips
        # and each stays independently verifiable (2026-09-16: the reenactment layer's diegetic sound
        # lives in the job's own assets/sfx, not the house library).
        self.rows = json.load(open(Path(plan) if plan else self.hf / 'sfx-plan.json'))
        if not self.rows: sys.exit('sfx-plan.json has no rows: nothing to place, verify or remove (an empty plan must never mean "every clip")')
        self.lib = str(Path(self.rows[0]['file']).parent)
        gfx = json.load(open(self.hf / 'placement.json'))
        self.F = 1 / probe_fps(next(r['file'] for r in gfx if os.path.exists(r['file'])))
        self.tracks = sorted({r['track'] for r in self.rows})

    def readback(self):
        r = es(r"""
(function(){
  var seq = app.project.activeSequence; if (!seq) return "ERROR: no active sequence";
  var LIB = %s, out = [];
  for (var t = 1; t < seq.audioTracks.numTracks; t++) {
    var tr = seq.audioTracks[t];
    for (var i = 0; i < tr.clips.numItems; i++) { var c = tr.clips[i];
      var p = c.projectItem ? c.projectItem.getMediaPath() : "";
      if (p.indexOf(LIB) !== 0) continue;
      var lvl = null;
      for (var k = 0; k < c.components.numItems; k++) { var cm = c.components[k];
        if (cm.displayName !== "Volume") continue;
        for (var q = 0; q < cm.properties.numItems; q++) if (cm.properties[q].displayName === "Level") lvl = cm.properties[q].getValue(); }
      out.push({track: t, start: c.start.seconds, end: c.end.seconds, srcIn: c.inPoint.seconds, srcOut: c.outPoint.seconds, path: p, v: lvl}); }
  }
  return JSON.stringify(out);
})()""" % json.dumps(self.lib))
        if str(r).startswith('ERROR'): sys.exit(r)
        return json.loads(r)

    def match(self, r, tl):
        return [c for c in tl if c['path'] == r['file'] and c['track'] == r['track'] and abs(c['start'] - r['at']) <= 1.5 * self.F]

    def verify(self, quiet=False):
        tl = self.readback(); ok = True; seen = set()
        for r in self.rows:
            m = [c for c in self.match(r, tl) if id(c) not in seen]      # a clip answers for ONE row
            if not m:
                ok = False; print(f"✗ {r['id']} {r['event']:<8} A{r['track'] + 1} {r['at']:.3f} {os.path.basename(r['file'])}: not on the timeline"); continue
            c = m[0]; seen.add(id(c))
            got = v_lvl(c['v']) if c['v'] is not None else None
            # overwriteClip truncates a repeated sound when the next cue occupies its track.
            # Verify that intended tail, not the untrimmed source slice or just its in-point.
            end = r['at'] + r['src_out'] - r['src_in']
            next_at = [n['at'] for n in self.rows if n['track'] == r['track'] and n['at'] > r['at']]
            if next_at: end = min(end, min(next_at))
            src_out = r['src_in'] + end - r['at']
            if got is None or abs(got - r['level_db']) > 0.2:
                ok = False; print(f"✗ {r['id']}: level {got} dB, plan {r['level_db']:+d}")
            elif abs(c['srcIn'] - r['src_in']) > 1.5 * self.F:
                ok = False; print(f"✗ {r['id']}: source in {c['srcIn']:.3f}, plan {r['src_in']:.3f}")
            elif abs(c['srcOut'] - src_out) > 1.5 * self.F or abs(c['end'] - end) > 1.5 * self.F:
                ok = False; print(f"✗ {r['id']}: tail {c['end']:.3f} / source out {c['srcOut']:.3f}, plan {end:.3f} / {src_out:.3f}")
            elif not quiet:
                print(f"✓ {r['id']} A{c['track'] + 1} {c['start']:.3f} → {c['end']:.3f} {r['level_db']:+d} dB {os.path.basename(c['path'])}")
        extra = [c for c in tl if id(c) not in seen]
        if extra: ok = False
        for c in extra: print(f"⚠ extra SFX clip on A{c['track'] + 1} at {c['start']:.3f}: {os.path.basename(c['path'])}, not in sfx-plan.json")
        print(f"{'ALL PLACED' if ok else 'DRIFT'}: {len(self.rows)} rows, {len(extra)} extra")
        return ok

    def diff(self):
        """the user's hand edits, read off the timeline against the plan: the input for the next rule."""
        tl = self.readback(); F = self.F; used = set(); n = 0
        lv = lambda v: round(v_lvl(v), 1) if v is not None else None
        for r in self.rows:
            c = next((c for i, c in enumerate(tl) if id(c) not in used and c['path'] == r['file'] and c['track'] == r['track'] and abs(c['start'] - r['at']) <= 1.5 * F), None)
            if c is None:
                near = [(i, c) for i, c in enumerate(tl) if id(c) not in used and c['path'] == r['file'] and abs(c['start'] - r['at']) <= 1.0]
                if near:
                    i, c = min(near, key=lambda ic: abs(ic[1]['start'] - r['at'])); used.add(id(c)); n += 1
                    print(f"MOVED    {r['id']} {r['event']:<9} {os.path.basename(r['file'])[:22]:22} {r['at']:8.3f} -> {c['start']:.3f} ({(c['start'] - r['at']) / F:+.1f} fr)" + (f" A{r['track'] + 1}->A{c['track'] + 1}" if c['track'] != r['track'] else '') + f"  [{r['gid']} {r['note'][:24]}]")
                else:
                    print(f"REMOVED  {r['id']} {r['event']:<9} {os.path.basename(r['file'])[:22]:22} {r['at']:8.3f}  [{r['gid']} {r['note'][:24]}]"); n += 1; continue
            else: used.add(id(c))
            if c['v'] is not None and abs(lv(c['v']) - r['level_db']) > 0.2:
                print(f"LEVEL    {r['id']} {r['event']:<9} {os.path.basename(r['file'])[:22]:22} {r['at']:8.3f}  {r['level_db']:+d} -> {lv(c['v']):+.1f} dB  [{r['gid']} {r['note'][:24]}]"); n += 1
            if abs(c['srcIn'] - r['src_in']) > 1.5 * F:
                print(f"SLICE    {r['id']} {r['event']:<9} {os.path.basename(r['file'])[:22]:22} {r['at']:8.3f}  src {r['src_in']:.2f} -> {c['srcIn']:.2f}  [{r['gid']} {r['note'][:24]}]"); n += 1
        for c in tl:
            if id(c) not in used:
                print(f"ADDED    A{c['track'] + 1} {c['start']:8.3f}-{c['end']:.3f} {os.path.basename(c['path'])[:26]:26} src {c['srcIn']:.2f}-{c['srcOut']:.2f} {lv(c['v'])!s:>6} dB"); n += 1
        print(f"{n} difference(s) between the timeline and sfx-plan.json")
        return n

    def provision(self):
        need = max(self.tracks) + 1
        r = es(r"""
(function(){
  var seq = app.project.activeSequence; var NEED = %d; app.enableQE();
  var before = seq.audioTracks.numTracks, tries = 0;
  while (seq.audioTracks.numTracks < NEED && tries++ < 8)
    qe.project.getActiveSequence().addTracks(0, 0, 1, 1, seq.audioTracks.numTracks, 0, 0);
  return JSON.stringify({before: before, after: seq.audioTracks.numTracks});
})()""" % need)
        got = json.loads(r)
        if got['after'] < need: sys.exit(f"could not provision audio tracks: have {got['after']}, need {need}")
        if got['after'] != got['before']: print(f"audio tracks {got['before']} → {got['after']}")

    def place(self, r):
        out = es(r"""
(function(){
  var seq = app.project.activeSequence, root = app.project.rootItem;
  var PATH = %s, AT = %s, SIN = %s, SOUT = %s, TRACK = %d, V = %s;
  function findByPath(bin){ for (var i = 0; i < bin.children.numItems; i++) { var c = bin.children[i];
    if (c.type === ProjectItemType.BIN) { var f = findByPath(c); if (f) return f; }
    else if (c.getMediaPath && c.getMediaPath() === PATH) return c; } return null; }
  function findBin(name){ for (var i = 0; i < root.children.numItems; i++) { var c = root.children[i];
    if (c.type === ProjectItemType.BIN && c.name === name) return c; } return null; }
  var item = findByPath(root);
  if (!item) { var bin = findBin("sfx") || root.createBin("sfx"); app.project.importFiles([PATH], true, bin, false); item = findByPath(root); }
  if (!item) return "ERROR: import failed for " + PATH;
  item.setInPoint(SIN + 1e-4, 4); item.setOutPoint(SOUT + 1e-4, 4);
  var tr = seq.audioTracks[TRACK];
  tr.overwriteClip(item, AT + 1e-4);
  item.clearInPoint(4); item.clearOutPoint(4);
  var clip = null;
  for (var i = 0; i < tr.clips.numItems; i++) { var c = tr.clips[i];
    if (Math.abs(c.start.seconds - AT) < 0.03 && c.projectItem && c.projectItem.getMediaPath() === PATH) clip = c; }
  if (!clip) return "ERROR: clip did not land on A" + (TRACK + 1) + " at " + AT;
  var got = null;
  for (var k = 0; k < clip.components.numItems; k++) { var cm = clip.components[k];
    if (cm.displayName !== "Volume") continue;
    for (var q = 0; q < cm.properties.numItems; q++) { var pr = cm.properties[q];
      if (pr.displayName === "Level") { pr.setValue(V, true); got = pr.getValue(); } } }
  return JSON.stringify({start: clip.start.seconds, end: clip.end.seconds, srcIn: clip.inPoint.seconds, v: got});
})()""" % (json.dumps(r['file']), r['at'], r['src_in'], r['src_out'], r['track'], lvl_v(r['level_db'])))
        if str(out).startswith('ERROR'): sys.exit(f"{r['id']}: {out}")
        got = json.loads(out)
        if abs(got['start'] - r['at']) > 1.5 * self.F:
            sys.exit(f"{r['id']}: landed at {got['start']:.4f}, wanted {r['at']:.4f} (readback mismatch, stopping)")
        if got['v'] is None or abs(v_lvl(got['v']) - r['level_db']) > 0.2:
            sys.exit(f"{r['id']}: level read back {got['v']} ({v_lvl(got['v']) if got['v'] else None} dB), wanted {r['level_db']:+d}")
        return got

    def apply(self):
        self.provision()
        tl = self.readback()
        placed, kept = [], 0
        for r in self.rows:
            if self.match(r, tl): kept += 1; continue
            g = self.place(r)
            placed.append(f"{r['id']} {r['event']:<8} A{r['track'] + 1} {g['start']:.3f} → {g['end']:.3f} {r['level_db']:+d} dB {os.path.basename(r['file'])} [{r['gid']} {r['note']}]")
        for p in placed: print('+ ' + p)
        print(f"{kept} already placed · {len(placed)} placed")
        if not self.verify(quiet=True):
            print(f"{len(placed)} clip(s) placed, project NOT saved: resolve the drift (--diff for hand edits, remove the exact stale clips), then re-apply")
            return False
        if placed:
            sh('node', str(BRIDGE), 'save_project'); print('saved')
        return True

    def remove(self):
        r = es(r"""
(function(){
  var seq = app.project.activeSequence; var LIB = %s, n = 0;
  for (var t = 1; t < seq.audioTracks.numTracks; t++) { var tr = seq.audioTracks[t];
    for (var i = tr.clips.numItems - 1; i >= 0; i--) { var c = tr.clips[i];
      var p = c.projectItem ? c.projectItem.getMediaPath() : "";
      if (p.indexOf(LIB) !== 0) continue;
      var ok = false; try { ok = c.remove(false, false); } catch (e) {}
      if (!ok) { app.enableQE(); var qt = qe.project.getActiveSequence().getAudioTrackAt(t);
        for (var q = qt.numItems - 1; q >= 0; q--) { var it = qt.getItemAt(q);
          if (it.type === "Clip" && Math.abs(it.start.secs - c.start.seconds) < 0.002) { it.remove(false, false); ok = true; break; } } }
      if (ok) n++; } }
  return JSON.stringify({removed: n, left: (function(){ var k = 0; for (var t = 1; t < seq.audioTracks.numTracks; t++) { var tr = seq.audioTracks[t];
    for (var i = 0; i < tr.clips.numItems; i++) { var c = tr.clips[i]; if ((c.projectItem ? c.projectItem.getMediaPath() : "").indexOf(LIB) === 0) k++; } } return k; })()});
})()""" % json.dumps(self.lib))
        got = json.loads(r)
        print(f"removed {got['removed']} SFX clip(s), {got['left']} left")
        if got['removed']: sh('node', str(BRIDGE), 'save_project'); print('saved')


def main():
    a = sys.argv[1:]
    if len(a) < 2: sys.exit(__doc__)
    plan = a[a.index('--plan') + 1] if '--plan' in a else None
    p = Placer(a[0], plan)
    if '--apply' in a: sys.exit(0 if p.apply() else 1)
    elif '--verify' in a: sys.exit(0 if p.verify() else 1)
    elif '--remove' in a: p.remove()
    elif '--diff' in a: p.diff()
    else: sys.exit(__doc__)


if __name__ == '__main__':
    main()
