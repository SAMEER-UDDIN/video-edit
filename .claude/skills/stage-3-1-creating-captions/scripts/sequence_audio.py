#!/usr/bin/env python3
"""Step 1: the sequence's dialogue audio on the SEQUENCE timeline -> <job>/captions/seq-audio.wav (16 kHz mono).

  python .claude/skills/stage-3-1-creating-captions/scripts/sequence_audio.py "<sequence>" projects/<job> [--track 1] [--from 0 --to 29.783]

Reads the audio track's clips from Premiere (headless bridge, read-only), then mixes each clip's source range at its sequence
position with ffmpeg. Also writes <job>/captions/audio-clips.json. --from/--to limit the range (e.g. only the short, when the
sequence also holds parked material further down the timeline).
"""
import argparse, glob, json, os, shutil, subprocess, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
FFMPEG = shutil.which("ffmpeg") or next(iter(glob.glob(os.path.expandvars(
    r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe"))), "ffmpeg")
ES = r"""(function(){
var NAME = %s, TR = %d, OUT = %s, p = app.project, s = null;
for (var i = 0; i < p.sequences.numSequences; i++) if (p.sequences[i].name == NAME) s = p.sequences[i];
if (!s) return 'ERROR no sequence ' + NAME;
function q(x) { return '"' + String(x).replace(/\\/g, '/').replace(/"/g, '\\"') + '"'; }
var t = s.audioTracks[TR - 1], rows = [];
for (var i = 0; i < t.clips.numItems; i++) { var c = t.clips[i];
  rows.push('{"path":' + q(c.projectItem ? c.projectItem.getMediaPath() : '') + ',"start":' + c.start.seconds + ',"end":' + c.end.seconds + ',"in":' + c.inPoint.seconds + '}'); }
var f = new File(OUT); f.encoding = 'UTF-8'; f.open('w'); f.write('{"duration":' + (Number(s.end) / 254016000000) + ',"clips":[' + rows.join(',') + ']}'); f.close();
return 'ok ' + rows.length;
})()"""

ap = argparse.ArgumentParser()
ap.add_argument("sequence"); ap.add_argument("job"); ap.add_argument("--track", type=int, default=1)
ap.add_argument("--from", dest="t0", type=float, default=0.0); ap.add_argument("--to", dest="t1", type=float)
a = ap.parse_args()
out_dir = os.path.join(os.path.abspath(a.job), "captions"); os.makedirs(out_dir, exist_ok=True)
lst = os.path.join(out_dir, "audio-clips.json").replace("\\", "/")
node = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
subprocess.run([node, os.path.join(REPO, "lanes", "premiere", "premiere-bridge.mjs"), "execute_extendscript",
                json.dumps({"script": ES % (json.dumps(a.sequence), a.track, json.dumps(lst))})], capture_output=True, text=True, cwd=REPO)
if not os.path.exists(lst): sys.exit("bridge did not write audio-clips.json (is the Premiere MCP Bridge panel connected?)")
d = json.load(open(lst, encoding="utf-8"))
t1 = a.t1 if a.t1 is not None else d["duration"]
clips = [c for c in d["clips"] if c["end"] > a.t0 and c["start"] < t1]
ins, fc = [], []
for k, c in enumerate(clips):
    s0 = max(c["start"], a.t0); src = c["in"] + (s0 - c["start"]); dur = min(c["end"], t1) - s0
    ins += ["-ss", f"{src:.4f}", "-t", f"{dur:.4f}", "-i", c["path"]]
    fc.append(f"[{k}:a]aformat=sample_rates=16000:channel_layouts=mono,adelay={int(round((s0 - a.t0) * 1000))}:all=1[a{k}]")
fc.append("".join(f"[a{k}]" for k in range(len(clips))) + f"amix=inputs={len(clips)}:normalize=0,apad,atrim=0:{t1 - a.t0:.4f}[out]")
wav = os.path.join(out_dir, "seq-audio.wav")
subprocess.run([FFMPEG, "-v", "error", "-y", *ins, "-filter_complex", ";".join(fc), "-map", "[out]", "-ar", "16000", "-ac", "1", wav], check=True)
print(f"{len(clips)} clips on A{a.track}, {a.t0:.3f}-{t1:.3f} s -> {wav}")
