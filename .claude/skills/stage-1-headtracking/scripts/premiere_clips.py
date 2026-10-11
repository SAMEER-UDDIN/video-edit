#!/usr/bin/env python3
"""Export a Premiere sequence's clip list (one video track) to <job>/clips.json, read-only.

  python .claude/skills/stage-1-headtracking/scripts/premiere_clips.py "Sequence 02" projects/<job> [--track 1]

Runs through the headless bridge (lanes/premiere/premiere-bridge.mjs); Premiere must be open with the MCP Bridge
panel connected. Writes:
  {"sequence", "width", "height", "fps", "frame_ticks", "duration",
   "clips": [{"i", "name", "path", "seq_start", "seq_end", "src_in", "src_out"}, ...]}
"""
import argparse, json, os, shutil, subprocess, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

ES = r"""(function(){
var NAME = %s, TR = %d, OUT = %s;
var p = app.project, s = null;
for (var i = 0; i < p.sequences.numSequences; i++) if (p.sequences[i].name == NAME) s = p.sequences[i];
if (!s) return 'ERROR no sequence named ' + NAME;
function q(x) { return '"' + String(x).replace(/\\/g, '/').replace(/"/g, '\\"') + '"'; }
var st = s.getSettings(), t = s.videoTracks[TR - 1], rows = [];
for (var i = 0; i < t.clips.numItems; i++) {
  var c = t.clips[i], path = c.projectItem ? c.projectItem.getMediaPath() : '';
  rows.push('{"i":' + i + ',"name":' + q(c.name) + ',"path":' + q(path) + ',"seq_start":' + c.start.seconds + ',"seq_end":' + c.end.seconds +
            ',"src_in":' + c.inPoint.seconds + ',"src_out":' + c.outPoint.seconds + '}');
}
var o = '{"sequence":' + q(s.name) + ',"width":' + st.videoFrameWidth + ',"height":' + st.videoFrameHeight + ',"fps":' + (1 / st.videoFrameRate.seconds) +
        ',"frame_ticks":' + q(st.videoFrameRate.ticks) + ',"duration":' + (Number(s.end) / 254016000000) + ',"clips":[' + rows.join(',') + ']}';
var f = new File(OUT); f.encoding = 'UTF-8'; f.open('w'); f.write(o); f.close();
return 'ok ' + rows.length + ' clips';
})()"""

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("sequence"); ap.add_argument("job"); ap.add_argument("--track", type=int, default=1)
    a = ap.parse_args()
    job = os.path.abspath(a.job); os.makedirs(job, exist_ok=True)
    out = os.path.join(job, "clips.json").replace("\\", "/")
    node = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    code = ES % (json.dumps(a.sequence), a.track, json.dumps(out))
    r = subprocess.run([node, os.path.join(REPO, "lanes", "premiere", "premiere-bridge.mjs"), "execute_extendscript",
                        json.dumps({"script": code})], capture_output=True, text=True, cwd=REPO)
    if not os.path.exists(out):
        sys.exit("bridge did not write clips.json:\n" + r.stdout[-1500:] + r.stderr[-1500:])
    d = json.load(open(out, encoding="utf-8"))
    print(f"{d['sequence']}: {d['width']}x{d['height']} @ {d['fps']:.3f} fps, {d['duration']:.3f}s, {len(d['clips'])} clips -> {out}")
    for c in d["clips"]:
        print(f"  #{c['i']:2d} {c['seq_start']:7.3f}-{c['seq_end']:7.3f}  in {c['src_in']:8.3f}  {os.path.basename(c['path'])[:60]}")
