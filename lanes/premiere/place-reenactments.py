#!/usr/bin/env python3
"""place-reenactments.py: owns broll/reenact/placement.json and the Premiere REENACTMENT track (V2).

  uv run lanes/premiere/place-reenactments.py projects/<job> --verify   # readback vs placement.json
  uv run lanes/premiere/place-reenactments.py projects/<job> --apply    # place every row not yet laid
  uv run lanes/premiere/place-reenactments.py projects/<job> --remove   # clear V2 (nothing else)

Why (2026-09-16, gta-san-andreas-hot-coffee): this channel has a LAYER the pipeline had no owner for.
`place-graphics.py` owns V3/V4 alpha overlays and full-screen punch-cuts; the Affan Afterhours preset
adds a second picture layer under them - opaque AI reenactment clips on V2, over the face on V1 -
and those need the same discipline: one file that is the truth, placement by overwriteClip at
start + 1e-4, the out point pinned, and every write read back before it is believed.

Rows: {"id", "file", "start", "end", "track": 1, "block"}
  `block` is the creator's Violet block number, carried so a re-derive can regroup without re-reading
  the timeline. `track` is 0-based like Premiere's own API: 1 = V2.

TWO LOCKS THIS LANE ADDS:
  - **A HOLE ON V2 FLASHES THE FACE.** V1 is the talking head, so any gap inside a Violet block shows
    it for those frames. The deriver lays EQUAL slots wall to wall and `--verify` fails on a gap
    larger than one frame.
  - **THE 96 % INSET IS THE LOOK. NEVER "FIX" IT.** Kling renders 1928x1076 into a 1920x1080
    sequence, so setScaleToFrameSize() FITS and lands Scale at 96, insetting the clip a few px on
    every side. The creator built on that: a colour mat with film grain sits under the overlay
    track and reads as a dark red drop shadow around every Higgsfield shot. Fit, and leave the edge.
"""
import json, os, subprocess, sys
for _s in (sys.stdout, sys.stderr):        # Windows pipes default to cp1252
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

BRIDGE = Path(__file__).resolve().parent / 'premiere-bridge.mjs'
NUDGE = 1e-4          # the same nudge as the EDL replay: a double a hair below a frame tick FLOORS


def sh(*cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"{' '.join(cmd[:3])} failed:\n{r.stderr or r.stdout}")
    return r.stdout


def es(script):
    out = sh('node', str(BRIDGE), 'execute_extendscript', json.dumps({'script': script}))
    try:
        j = json.loads(out)
    except json.JSONDecodeError:
        sys.exit(f'bridge returned non-JSON:\n{out[:800]}')
    if isinstance(j, dict) and j.get('success') is False:
        sys.exit(f"bridge error: {j.get('error')}")
    d = j.get('data', j) if isinstance(j, dict) else j
    if isinstance(d, dict):
        d = d.get('result', d)
    return d if isinstance(d, str) else json.dumps(d)


class Placer:
    TRACK = 1          # the DEFAULT only. Each row may carry its own 0-based `track`: the creator
                       # re-laid this job onto V4/V5/V6 by hand, and the lane follows their layout
                       # rather than imposing one (2026-09-17).

    def __init__(self, job):
        self.job = Path(job).resolve()
        import os as _os
        name = _os.environ.get('VE_PLACEMENT', 'placement.json')
        self.pj = self.job / 'broll' / 'reenact' / name
        self.rows = json.load(open(self.pj))
        self.fps = None

    def F(self):
        if self.fps is None:
            raw = sorted((self.job / 'raw').glob('*.mp4'))
            f = str(raw[0]) if raw else self.rows[0]['file']
            r = sh('ffprobe', '-v', 'error', '-select_streams', 'v:0',
                   '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', f)
            n, _, d = r.strip().split('\n')[0].strip(',').partition('/')
            self.fps = float(n) / float(d or 1)
        return 1.0 / self.fps

    def tracks(self):
        return sorted({int(r.get('track', self.TRACK)) for r in self.rows})

    def readback(self, track=None):
        r = es(r"""
(function(){
  var seq = app.project.activeSequence; if (!seq) return "ERROR: no active sequence";
  // a track the plan needs may not exist yet (place() provisions it): report empty, never throw
  if (seq.videoTracks.numTracks <= %d) return "[]";
  var tr = seq.videoTracks[%d]; var out = [];
  for (var i = 0; i < tr.clips.numItems; i++) { var c = tr.clips[i];
    out.push({name: c.name, start: c.start.seconds, end: c.end.seconds,
              path: c.projectItem ? c.projectItem.getMediaPath() : ""}); }
  return JSON.stringify(out);
})()""" % (((self.TRACK if track is None else track),) * 2))
        if str(r).startswith('ERROR'):
            sys.exit(r)
        out = json.loads(r)
        for c in out:
            c['track'] = self.TRACK if track is None else track
        return out

    def verify(self, quiet=False):
        F, ok = self.F(), True
        tl = [c for t in self.tracks() for c in self.readback(t)]
        by_start = sorted(tl, key=lambda c: c['start'])
        for row in self.rows:
            m = [c for c in tl
                 if os.path.basename(c['path']) == os.path.basename(row['file'])
                 and c['track'] == int(row.get('track', self.TRACK))
                 and abs(c['start'] - row['start']) <= 1.5 * F]
            if not m:
                ok = False
                print(f"✗ {row['id']}: {os.path.basename(row['file'])} not on V2 at {row['start']:.4f}")
                continue
            c = m[0]
            if abs(c['end'] - row['end']) > 1.5 * F:
                ok = False
                print(f"✗ {row['id']}: ends {c['end']:.4f}, placement says {row['end']:.4f} "
                      f"({(c['end'] - row['end']) / F:+.1f} frames)")
            elif not quiet:
                print(f"✓ {row['id']:<8} {c['start']:8.3f} → {c['end']:8.3f}  {os.path.basename(c['path'])}")
        # THE HOLE CHECK: a gap inside a block shows the face on V1 for those frames
        blocks = {}
        for row in self.rows:
            blocks.setdefault(row['block'], []).append(row)
        for b, rs in sorted(blocks.items()):
            rs.sort(key=lambda r: r['start'])
            for a, z in zip(rs, rs[1:]):
                if z['start'] - a['end'] > 1.05 * F:
                    ok = False
                    print(f"✗ block {b}: {(z['start'] - a['end']) * 1000:.0f} ms hole between "
                          f"{a['id']} and {z['id']} — the face flashes through")
        print(f"{'ALL PLACED' if ok else 'DRIFT'}: {len(self.rows)} rows, {len(by_start)} clips on V2")
        return ok

    def remove_all(self):
        r = es(r"""
(function(){
  var seq = app.project.activeSequence; var tr = seq.videoTracks[%d]; var n = 0;
  for (var i = tr.clips.numItems - 1; i >= 0; i--) { var c = tr.clips[i]; var ok = false;
    try { ok = c.remove(false, false); } catch (e) { ok = false; }
    if (!ok) { app.enableQE(); var qt = qe.project.getActiveSequence().getVideoTrackAt(%d);
      for (var q = qt.numItems - 1; q >= 0; q--) { var it = qt.getItemAt(q);
        if (it.type === "Clip" && Math.abs(it.start.secs - c.start.seconds) < 0.002) {
          it.remove(false, false); ok = true; break; } } }
    if (ok) n++; }
  return JSON.stringify(n);
})()""" % (self.TRACK, self.TRACK))
        return json.loads(r)

    def place(self, row):
        F = self.F()
        TRK = int(row.get('track', self.TRACK))
        out = es(r"""
(function(){
  var seq = app.project.activeSequence, root = app.project.rootItem;
  var PATH = %s, START = %s, END = %s, TRACK = %d, BIN = %s;
  function findBin(b, name){ for (var i = 0; i < b.children.numItems; i++) { var c = b.children[i];
    if (c.type === ProjectItemType.BIN) { if (c.name === name) return c; var f = findBin(c, name); if (f) return f; } }
    return null; }
  // Premiere returns Windows paths with backslashes; placement.json carries forward slashes.
  // Comparing them raw made every findByPath miss and every import look like a failure (2026-09-16).
  var BS = String.fromCharCode(92);   // no backslash literal: an escaped one does not survive
  function norm(p){ var o = String(p), r = "";
    for (var i = 0; i < o.length; i++) { var ch = o.charAt(i); r += (ch === BS ? "/" : ch); }
    return r.toLowerCase(); }
  var WANT = norm(PATH);
  function findByPath(bin){ for (var i = 0; i < bin.children.numItems; i++) { var c = bin.children[i];
    if (c.type === ProjectItemType.BIN) { var f = findByPath(c); if (f) return f; }
    else if (c.getMediaPath && norm(c.getMediaPath()) === WANT) return c; } return null; }
  var item = findByPath(root);
  if (!item) { var target = findBin(root, BIN) || root;
               app.project.importFiles([PATH], true, target, false); item = findByPath(root); }
  if (!item) return "ERROR: import failed for " + PATH;
  if (seq.videoTracks.numTracks <= TRACK) {
    app.enableQE();
    qe.project.getActiveSequence().addTracks(TRACK + 1 - seq.videoTracks.numTracks, seq.videoTracks.numTracks, 0, 0, 0, 0, 0);
    if (seq.videoTracks.numTracks <= TRACK) return "ERROR: could not add video track V" + (TRACK + 1);
  }
  var tr = seq.videoTracks[TRACK];
  // The source is 24 fps in a 59.94 sequence, so setOutPoint QUANTISES to the SOURCE frame grid and
  // lands up to 3 timeline frames short (2026-09-16). So over-trim by 0.2 s and pin the end back
  // down afterwards: the overhang is either overwritten by the next clip laid on this track or
  // removed by the pin, and the slot is never left short.
  item.setInPoint(0, 4); item.setOutPoint(END - START + 0.2, 4);
  tr.overwriteClip(item, START + %s);
  item.clearInPoint(4); item.clearOutPoint(4);
  var clip = null;
  for (var i = 0; i < tr.clips.numItems; i++) { var c = tr.clips[i];
    if (Math.abs(c.start.seconds - START) < 0.02 && c.projectItem && norm(c.projectItem.getMediaPath()) === WANT) clip = c; }
  if (!clip) return "ERROR: clip did not land on V" + (TRACK + 1) + " at " + START;
  var t = new Time(); t.seconds = END + %s; clip.end = t;      // ALWAYS pin, both directions
  // THE EDGE IS THE LOOK. setScaleToFrameSize() fits 1928x1076 into 1920x1080 and lands Scale at
  // 96, leaving a few px of the track below showing on every side - the creator's colour mat and
  // film grain, reading as a drop shadow. On 2026-09-17 I measured that inset, called it a bleed,
  // filled to 101.5 and wiped the look off 59 clips. Fit. Never scale a reenactment clip up.
  try { if (clip.projectItem) clip.projectItem.setScaleToFrameSize(); } catch (e) {}
  return JSON.stringify({start: clip.start.seconds, end: clip.end.seconds, name: clip.name});
})()""" % (json.dumps(row['file']), row['start'], row['end'], TRK,
           json.dumps(os.environ.get('VE_BIN', 'GTA SAN ANDRES')), NUDGE, NUDGE))
        if str(out).startswith('ERROR'):
            sys.exit(f"{row['id']}: {out}")
        got = json.loads(out)
        if abs(got['start'] - row['start']) > 1.5 * F or abs(got['end'] - row['end']) > 1.5 * F:
            sys.exit(f"{row['id']}: placed {got['start']:.4f} → {got['end']:.4f} but wanted "
                     f"{row['start']:.4f} → {row['end']:.4f} (readback mismatch, stopping)")
        return got

    def apply(self):
        F = self.F()
        tl = [c for t in self.tracks() for c in self.readback(t)]
        done = {(os.path.basename(c['path']), round(c['start'], 3), c['track']) for c in tl}
        laid = 0
        for row in self.rows:
            key = (os.path.basename(row['file']), round(row['start'], 3), int(row.get('track', self.TRACK)))
            if any(k[0] == key[0] and k[2] == key[2] and abs(k[1] - key[1]) <= 1.5 * F for k in done):
                continue
            got = self.place(row)
            laid += 1
            print(f"+ {row['id']:<8} V{int(row.get('track', self.TRACK))+1} {got['start']:8.3f} → {got['end']:8.3f}  {os.path.basename(row['file'])}")
        print(f"placed {laid} clip(s) on V2")
        return laid


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    p = Placer(a[0])
    if '--remove' in a:
        print('removed', p.remove_all(), 'clip(s) from V2')
        return
    if '--apply' in a:
        p.apply()
    sys.exit(0 if p.verify(quiet='--apply' in a) else 1)


if __name__ == '__main__':
    main()
