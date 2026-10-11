#!/usr/bin/env python3
"""Export a Premiere sequence's clips (V1 + any B-roll tracks, inside the sequence In/Out if set) to <job>/clips.json, read-only.

  python .claude/skills/stage-1-headtracking/scripts/premiere_clips.py "Sequence 01" projects/<job> [--tracks 1,2] [--no-inout]

Runs through the headless bridge (lanes/premiere/premiere-bridge.mjs); Premiere must be open with the MCP Bridge panel
connected (or paste the ES from this file into the premiere-pro MCP execute_extendscript tool). Times are RELATIVE to the
In point (comp time 0 = In). Clips from all listed tracks are merged and sorted by start; they must not overlap.
Writes:
  {"sequence", "width", "height", "fps", "frame_ticks", "duration", "seq_in",
   "clips": [{"i", "track", "idx", "name", "path", "seq_start", "seq_end", "src_in", "src_out",
              "pos": [x, y] (his Motion Position, 0..1), "scale": pct (his Motion Scale)}, ...]}
pos/scale let build_nose_track.py see WHICH face he framed in a split-screen source.
"""
import argparse, json, os, shutil, subprocess, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

ES = r"""(function(){
var NAME = %s, TRK = %s, OUT = %s, USEIO = %s;
var p = app.project, s = null;
for (var i = 0; i < p.sequences.numSequences; i++) if (p.sequences[i].name == NAME) s = p.sequences[i];
if (!s) return 'ERROR no sequence named ' + NAME;
function q(x) { return '"' + String(x).replace(/\\/g, '/').replace(/"/g, '\\"') + '"'; }
var st = s.getSettings(), END = Number(s.end) / 254016000000, IN = 0, OUTT = END;
if (USEIO) { var a = s.getInPointAsTime().seconds, b = s.getOutPointAsTime().seconds; if (b > a && (a > 0 || b < END - 0.01)) { IN = a; OUTT = b; } }
var rows = [];
for (var k = 0; k < TRK.length; k++) {
  var t = s.videoTracks[TRK[k] - 1];
  for (var i = 0; i < t.clips.numItems; i++) {
    var c = t.clips[i];
    if (!(c.end.seconds > IN + 1e-6 && c.start.seconds < OUTT - 1e-6)) continue;
    var path = c.projectItem ? c.projectItem.getMediaPath() : '', pos = '', sc = '';
    for (var m = 0; m < c.components.numItems; m++) if (c.components[m].displayName == 'Motion') {
      for (var n = 0; n < c.components[m].properties.numItems; n++) {
        var pr = c.components[m].properties[n];
        if (pr.displayName == 'Position') { var v = pr.getValue(); pos = ',"pos":[' + v[0] + ',' + v[1] + ']'; }
        if (pr.displayName == 'Scale') sc = ',"scale":' + pr.getValue();
      } }
    rows.push({s: c.start.seconds, t: '"track":' + TRK[k] + ',"idx":' + i + ',"name":' + q(c.name) + ',"path":' + q(path) + ',"seq_start":' + (c.start.seconds - IN) +
              ',"seq_end":' + (c.end.seconds - IN) + ',"src_in":' + c.inPoint.seconds + ',"src_out":' + c.outPoint.seconds + pos + sc});
  }
}
rows.sort(function (a, b) { return a.s - b.s; });
var parts = [];
for (var j = 0; j < rows.length; j++) parts.push('{"i":' + j + ',' + rows[j].t + '}');
var o = '{"sequence":' + q(s.name) + ',"width":' + st.videoFrameWidth + ',"height":' + st.videoFrameHeight + ',"fps":' + (1 / st.videoFrameRate.seconds) +
        ',"frame_ticks":' + q(st.videoFrameRate.ticks) + ',"duration":' + (OUTT - IN) + ',"seq_in":' + IN + ',"clips":[' + parts.join(',') + ']}';
var f = new File(OUT); f.parent.create(); f.encoding = 'UTF-8'; f.open('w'); f.write(o); f.close();
return 'ok ' + rows.length + ' clips, in ' + IN + ' out ' + OUTT;
})()"""

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("sequence"); ap.add_argument("job"); ap.add_argument("--tracks", default="1"); ap.add_argument("--no-inout", action="store_true")
    a = ap.parse_args()
    job = os.path.abspath(a.job); os.makedirs(job, exist_ok=True)
    out = os.path.join(job, "clips.json").replace("\\", "/")
    node = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    if os.path.exists(out): os.remove(out)      # never trust a stale clips.json
    code = ES % (json.dumps(a.sequence), json.dumps([int(x) for x in a.tracks.split(",")]), json.dumps(out), "false" if a.no_inout else "true")
    r = subprocess.run([node, os.path.join(REPO, "lanes", "premiere", "premiere-bridge.mjs"), "execute_extendscript",
                        json.dumps({"script": code})], capture_output=True, text=True, cwd=REPO)
    if not os.path.exists(out):
        es = os.path.join(job, "premiere-clips.es.js"); open(es, "w", encoding="utf-8").write(code)
        sys.exit("bridge did not write clips.json:\n" + r.stdout[-800:] + r.stderr[-800:] +
                 f"\nFallback: run the script in {es} with the premiere-pro MCP execute_extendscript tool (it writes clips.json itself).")
    d = json.load(open(out, encoding="utf-8"))
    print(f"{d['sequence']}: {d['width']}x{d['height']} @ {d['fps']:.3f} fps, {d['duration']:.3f}s, {len(d['clips'])} clips -> {out}")
    for c in d["clips"]:
        print(f"  #{c['i']:2d} V{c['track']} {c['seq_start']:7.3f}-{c['seq_end']:7.3f}  in {c['src_in']:8.3f}  {os.path.basename(c['path'])[:50]}")
