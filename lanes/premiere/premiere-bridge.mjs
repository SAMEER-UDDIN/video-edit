// Headless CLI driver for the Premiere MCP bridge — calls tool handlers directly,
// no MCP session needed. Works from any session as long as the MCP Bridge (CEP)
// panel is running in Premiere (Window > Extensions > MCP Bridge (CEP), temp dir
// /tmp/premiere-mcp-bridge on macOS, %TEMP%\premiere-mcp-bridge on Windows).
//
// Engine: vendor/premiere-mcp — our pinned local clone of
// github.com/hetpatel-11/Adobe_Premiere_Pro_MCP (the original project; the old
// premiere-pro-mcp npm package was a knockoff republish with a broken CEP shim).
// Pinned by clone: update ONLY via deliberate `git pull` + re-test, record the
// new commit hash in the premiere-pro skill.
//
// Usage:
//   node lanes/premiere/premiere-bridge.mjs --list [filter]        # list tools
//   node lanes/premiere/premiere-bridge.mjs --desc <tool>          # show a tool's params
//   node lanes/premiere/premiere-bridge.mjs <tool> ['<json-args>'] # call one tool
//   node lanes/premiere/premiere-bridge.mjs replay <cuts.json> <clipName>
//     # premiere-pro step 2: replay the EDL onto V1 of the ACTIVE sequence as
//     # individual overwrite edits via one batched ExtendScript (per-segment
//     # in/out + overwriteClip with position read-back — the your-job
//     # pattern; append position is read back after every overwrite because
//     # Premiere quantizes boundaries to the frame grid).
//   node lanes/premiere/premiere-bridge.mjs frame '{"time":17.0,"out":"<path-no-ext>"}'
//     # A relative `out` resolves against YOUR cwd (never Premiere's), the parent folder is
//     # created, a trailing .png is stripped, and the command FAILS if the PNG did not land.
//     # Program-monitor-accurate frame grab from the ACTIVE sequence at `time` seconds —
//     # full render: keyframed effects + all video tracks/alpha overlays composited.
//     # Calls QE exportFramePNG with a proper NON-DROP TIMECODE STRING built from the
//     # sequence fps. That arg form is the ONLY correct one: numeric seconds THROW
//     # ("Illegal Parameter type") and the vendored export_frame tool's fallback passes
//     # String(seconds), which QE parses as a FRAMES timecode — it silently exports the
//     # frame at ~t/fps seconds (measured 2026-07-18: "18" → frame 18 ≈ 0.75s). A ticks
//     # string is equally wrong. Writes <out>.png and prints the timecode used.
//     # It ALSO prints any video track whose Toggle Track Output is OFF: such a track is
//     # silently missing from the composite, so a grade or graphic on it measures delta 0
//     # exactly like a dead effect — and the Exposure control is muted too, so it cannot
//     # tell them apart. Read that line before concluding anything rendered nothing.
//   node lanes/premiere/premiere-bridge.mjs diff-edl <cuts.json> [more cuts.json...]
//     # The rough-cut learning loop (skill Step 5): diff the ACTIVE sequence's
//     # V1 against the authored EDL(s) after the creator hand-edits. Matches
//     # timeline clips to EDL segments by source-range overlap (clips matched to
//     # EDLs by clip filename), then prints: deleted segments (with their
//     # transcript), boundary moves > 1 frame with the WORDS around each moved
//     # boundary (needs <job>/transcript/words.json next to each cuts.json),
//     # graft pairs (OUT-extension + IN-trim at one joint), new material, and
//     # timeline gaps. Read-only; never writes. The hand-edited timeline is the
//     # source of truth — this command exists to LEARN from it, not to sync it.
//   node lanes/premiere/premiere-bridge.mjs zoom ['<json-opts>']
//     # Opening zoom preset (re-dialled 2026-09-10): applies Transform (with
//     # Shutter Angle 360 motion blur) to a clip on V1 of the active sequence and
//     # bakes a per-frame scale ramp — the only way to script ease shapes, since
//     # Premiere's ease presets aren't reachable via the API. The scale defaults
//     # ARE the lock — 115 → 100 over 18 frames, quart ease-out; verify frame 9
//     # reads 100.94 (a cubic bake reads 101.88). Numbers:
//     # presets/youtube/default/README.md § Opening zoom-out. ALWAYS pass fps — it
//     # is the sequence's own rate, not part of the lock. All keys land at the
//     # clip's in point (source-time domain).
//     # Opts: {"clip":0,"from":115,"to":100,"frames":18,"ease":"quart","fps":"30000/1001"}
//     #   clip: 0-based clip index on V1 · ease: quart (the opening zoom-out's lock) | inout (the push-in's S) | cubic | quint | overshoot | linear
//     #   fps: the SEQUENCE rate as a rational string (e.g. "30000/1001") — key
//     #   spacing is 1/fps, so a wrong rate stretches/squeezes the ramp
//     #   WHERE the ramp starts (default = the clip's in point, the opening zoom-out):
//     #     "at": <sequence seconds>  — e.g. a word timestamp from the transcript
//     #     "offset": <frames>        — frames past the clip's in point
//     #   With a start past the in point, keys BEFORE it are preserved (a clip can hold the
//     #   opening zoom-out and a later push-in in the same property). Errors if the ramp
//     #   would start before the clip or run past its end.
//     # Emphasis push-in (youtube/default move 5), synced to a word:
//     #   zoom '{"clip":8,"from":100,"to":115,"frames":18,"ease":"inout","fps":"30000/1001","at":28.3}'
//   node lanes/premiere/premiere-bridge.mjs grade-layer ['<json-opts>']
//     # Pipeline step 4, the layer half in ONE command: mints an adjustment layer AT THE ACTIVE
//     # SEQUENCE'S OWN FRAME SIZE (read off the sequence, never typed — a 16:9 layer on a
//     # vertical timeline can be scaled to fit and leave the top and bottom ungraded), imports
//     # it, provisions tracks up to the V1/V2/V3/V4 map, places it spanning V1's full extent on
//     # the grade track, names the clip GRADE, adds Lumetri, and saves. Idempotent: it refuses
//     # if that track already holds a GRADE clip, and reuses a same-size layer already in the
//     # project instead of stacking duplicate bin items. Reports any track whose output is off.
//     # Opts: {"track":2,"minTracks":4,"lumetri":true}
//     # The LOOK is the separate headless step that follows (project must be CLOSED):
//     #   premiere-up.sh --quit -> grade-lut.py apply <job>.prproj -> premiere-up.sh <job>.prproj
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

// Bridge dir must match the CEP panel's default: /tmp on macOS, %TEMP% on Windows.
// (URL.href, not .pathname, for the imports — pathname yields /C:/... on Windows.)
const { tmpdir } = await import("node:os");
process.env.PREMIERE_TEMP_DIR = process.env.PREMIERE_TEMP_DIR ||
  (process.platform === "win32" ? `${tmpdir()}\\premiere-mcp-bridge` : "/tmp/premiere-mcp-bridge");
const V = new URL("../../vendor/premiere-mcp/", import.meta.url);
const { PremiereProBridge } = await import(new URL("dist/bridge/index.js", V).href);
const { PremiereProTools } = await import(new URL("dist/tools/index.js", V).href);

const bridge = new PremiereProBridge();
await bridge.initialize();
const tools = new PremiereProTools(bridge);

const call = async (name, args = {}) => {
  const r = await tools.executeTool(name, args);
  if (r && r.success === false) throw new Error(`${name} failed: ${r.error}`);
  return r && r.data !== undefined ? r.data : r;
};
const es = async (code) => call("execute_extendscript", { script: code });

const [cmd, a1, a2] = process.argv.slice(2);

if (!cmd || cmd === "--list") {
  const filter = a1?.toLowerCase();
  console.log(tools.getAvailableTools().map(t => t.name)
    .filter(n => !filter || n.includes(filter)).join("\n"));
} else if (cmd === "--desc") {
  const t = tools.getAvailableTools().find(x => x.name === a1);
  console.log(JSON.stringify({ description: t?.description, parameters: t?.inputSchema }, null, 2));
} else if (cmd === "replay") {
  const segs = JSON.parse(readFileSync(a1, "utf-8")).segments;
  // +1e-4s on every boundary: frame-grid times are repeating decimals, and a double
  // that lands a hair BELOW the exact tick value gets FLOORED by Premiere into the
  // previous frame (measured: one out-point a full frame short). The nudge is 0.24%
  // of a frame — floor now always resolves to the intended frame, and off-grid EDLs
  // are unaffected.
  // Carry each segment's SOURCE CLIP. rough-cut explicitly allows cuts to cross clips
  // ("segments CAN cross clips in any order — that's the whole point"), so a multi-file EDL
  // must resolve one project item PER SEGMENT. Falls back to the CLI <clipName> when a
  // segment has no `clip` (single-file EDLs, and the older hand-written ones).
  const segJson = JSON.stringify(segs.map(s => [
    s.start + 1e-4, s.end + 1e-4, s.clip ? String(s.clip).split("/").pop() : null,
  ]));
  const r = await es(`
(function(){
var SEGS = ${segJson};
var NAME = ${JSON.stringify(a2)};
function find(bin, name){
  for (var i = 0; i < bin.children.numItems; i++) {
    var c = bin.children[i];
    if (c.name === name) return c;
    if (c.type === ProjectItemType.BIN) { var f = find(c, name); if (f) return f; }
  }
  return null;
}
var cache = {}, used = [];
function resolve(name){
  if (cache[name] !== undefined) return cache[name];
  var it = find(app.project.rootItem, name);
  cache[name] = it;
  if (it) used.push(name);
  return it;
}
var seq = app.project.activeSequence;
if (!seq) return "ERROR: no active sequence";
var vt = seq.videoTracks[0];
var pos = vt.clips.numItems ? vt.clips[vt.clips.numItems - 1].end.seconds : 0;
for (var s = 0; s < SEGS.length; s++) {
  var want = SEGS[s][2] || NAME;                 // per-segment clip, else the CLI name
  var item = resolve(want);
  if (!item) return "ERROR: project item not found for segment " + s + ": " + want;
  item.setInPoint(SEGS[s][0], 4);
  item.setOutPoint(SEGS[s][1], 4);
  vt.overwriteClip(item, pos);
  pos = vt.clips[vt.clips.numItems - 1].end.seconds;
}
for (var u = 0; u < used.length; u++) {
  var ci = cache[used[u]];
  if (ci) { ci.clearInPoint(4); ci.clearOutPoint(4); }
}
return "laid " + SEGS.length + " segments from " + used.length + " source clip(s) [" +
       used.join(", ") + "], timeline ends " + pos.toFixed(3) + "s";
})()
`);
  console.log(JSON.stringify(r));
  console.log(JSON.stringify(await call("save_project")));
} else if (cmd === "diff-edl") {
  const { dirname, basename, join } = await import("node:path");
  const edlPaths = process.argv.slice(3);
  if (!edlPaths.length) throw new Error("diff-edl needs at least one cuts.json path");

  // segments from every EDL, keyed by clip basename; word lists for boundary context
  const segs = [];
  const wordsByClip = {};
  for (const p of edlPaths) {
    for (const [i, s] of JSON.parse(readFileSync(p, "utf-8")).segments.entries())
      segs.push({ edl: basename(dirname(dirname(p))) || p, i, clip: basename(s.clip), ...s, used: false });
    // transcript/words.json sits next to transcript/cuts.json
    try {
      const w = JSON.parse(readFileSync(join(dirname(p), "words.json"), "utf-8"));
      for (const c of w.clips || []) wordsByClip[basename(c.clip)] = c.words || [];
    } catch { /* words optional — boundary context just goes quiet */ }
  }
  const wordsAt = (clip, t) => {
    const ws = wordsByClip[clip];
    if (!ws) return "";
    const near = ws.filter(w => w.end > t - 0.8 && w.start < t + 0.8).map(w => w.w).join(" ");
    return near ? `  [“${near}”]` : "";
  };

  const dump = await es(`
(function(){
var s = app.project.activeSequence;
if (!s) return "ERROR: no active sequence";
var fps = 1 / s.getSettings().videoFrameRate.seconds;
var v = [];
for (var t = 0; t < s.videoTracks.numTracks; t++) {
  var vt = s.videoTracks[t];
  for (var i = 0; i < vt.clips.numItems; i++) {
    var c = vt.clips[i];
    v.push({ trk: t, name: c.name,
      tlIn: c.start.seconds, tlOut: c.end.seconds,
      srcIn: c.inPoint.seconds, srcOut: c.outPoint.seconds });
  }
}
return JSON.stringify({ fps: fps, clips: v });
})()`);
  const tl = JSON.parse(typeof dump === "string" ? dump : dump.result || JSON.stringify(dump));
  if (tl.ERROR) throw new Error(tl.ERROR);
  const FRAME = 1 / (tl.fps || 30);
  const fmt = (x) => x.toFixed(2);

  const lines = [];
  let grafts = 0, moves = 0;
  const clipRows = [];
  for (const c of tl.clips) {
    let best = null, bo = 0;
    for (const s of segs) {
      if (c.name !== s.clip) continue;
      const o = Math.min(c.srcOut, s.end) - Math.max(c.srcIn, s.start);
      if (o > bo) { bo = o; best = s; }
    }
    if (!best) { lines.push(`NEW      ${c.name} src ${fmt(c.srcIn)}-${fmt(c.srcOut)} — not from any EDL segment`); continue; }
    best.used = true;
    clipRows.push({ c, s: best, dIn: c.srcIn - best.start, dOut: c.srcOut - best.end });
  }
  for (let k = 0; k < clipRows.length; k++) {
    const { c, s, dIn, dOut } = clipRows[k];
    if (Math.abs(dIn) > FRAME) {
      moves++;
      lines.push(`IN  ${dIn > 0 ? "trimmed " : "extended"} ${Math.abs(dIn).toFixed(2)}s  ${s.edl}#${s.i} @src ${fmt(s.start)}→${fmt(c.srcIn)}${wordsAt(c.name, c.srcIn)}`);
    }
    if (Math.abs(dOut) > FRAME) {
      moves++;
      lines.push(`OUT ${dOut > 0 ? "extended" : "trimmed "} ${Math.abs(dOut).toFixed(2)}s  ${s.edl}#${s.i} @src ${fmt(s.end)}→${fmt(c.srcOut)}${wordsAt(c.name, c.srcOut)}`);
    }
    // graft signature: this clip's OUT extended into words + next clip's IN trimmed past its start
    const nxt = clipRows[k + 1];
    if (nxt && dOut > FRAME && nxt.dIn > FRAME) {
      grafts++;
      lines.push(`  ↳ GRAFT at joint: kept take-1 through ${fmt(c.srcOut)}, re-entered take 2 at ${fmt(nxt.c.srcIn)} — mid-sentence splice around a restart`);
    }
  }
  for (const s of segs.filter(x => !x.used))
    lines.push(`DELETED  ${s.edl}#${s.i} ${fmt(s.start)}-${fmt(s.end)}  “${(s.transcript || "").slice(0, 90)}”`);
  const v1 = tl.clips.filter(c => c.trk === 0);
  for (let k = 1; k < v1.length; k++) {
    const g = v1[k].tlIn - v1[k - 1].tlOut;
    if (Math.abs(g) > 0.001) lines.push(`GAP      ${g > 0 ? "+" : ""}${g.toFixed(3)}s on the timeline at ${fmt(v1[k - 1].tlOut)}`);
  }
  console.log(lines.length ? lines.join("\n") : "timeline matches the EDL(s) exactly — no hand edits detected");
  console.log(`— ${tl.clips.length} timeline clips vs ${segs.length} EDL segments · ${segs.filter(x => !x.used).length} deleted · ${moves} boundary moves · ${grafts} graft(s) · end ${fmt(v1.length ? v1[v1.length - 1].tlOut : 0)}s`);
} else if (cmd === "frame") {
  const opts = JSON.parse(a1);
  if (!(opts.time >= 0) || !opts.out) throw new Error('frame needs {"time":<seconds>,"out":"<path-no-ext>"}');
  // `<out>.png` is the ONE filename this command promises, so strip a trailing .png: otherwise QE
  // writes g5.png and the landed-check below looks for g5.png.png and throws on a good grab.
  opts.out = String(opts.out).replace(/\.png$/i, "");
  // The ExtendScript runs INSIDE Premiere, whose cwd is its own app folder, so a relative `out`
  // handed straight through writes nothing while the command still reports success: that is how
  // 184 review grabs landed nowhere (2026-09-07). Resolve against the CALLER's cwd first.
  const ABS = /^([a-zA-Z]:[\\/]|\/)/;
  if (!ABS.test(opts.out)) opts.out = resolve(process.cwd(), opts.out);
  // Premiere on Windows wants C:/... — a Git Bash /c/... path is the one path here that comes from outside.
  if (process.platform === "win32") opts.out = String(opts.out).replace(/\\/g, "/").replace(/^\/([a-zA-Z])\//, "$1:/");
  mkdirSync(dirname(opts.out), { recursive: true });
  const r = await es(`
(function(){
var seq = app.project.activeSequence;
if (!seq) return "ERROR: no active sequence";
var frameDur = seq.getSettings().videoFrameRate.seconds;
var nominal = Math.round(1 / frameDur);
var f = Math.round(${opts.time} / frameDur);
var ff = f % nominal, s = (f - ff) / nominal;
var ss = s % 60, mm = ((s - ss) / 60) % 60, hh = Math.floor(s / 3600);
function p(n){ return (n < 10 ? "0" : "") + n; }
var tc = p(hh) + ":" + p(mm) + ":" + p(ss) + ":" + p(ff);
app.enableQE();
var qs = qe.project.getActiveSequence();
if (!qs) return "ERROR: no QE sequence";
qs.exportFramePNG(tc, ${JSON.stringify(opts.out)});
// Toggle Track Output state, reported on EVERY grab. A muted track is silently absent from the
// composite, so a grade/graphic on it measures delta 0 — indistinguishable from a dead effect,
// and the Exposure control cannot tell them apart either (it is muted too). Cost a whole
// diagnosis on a real job, 2026-09-02. Only tracks that actually hold clips are worth naming.
var off = [];
for (var t = 0; t < seq.videoTracks.numTracks; t++) {
  var trk = seq.videoTracks[t];
  if (trk.isMuted() && trk.clips.numItems > 0)
    off.push("V" + (t + 1) + "(" + trk.clips.numItems + " clip" + (trk.clips.numItems === 1 ? "" : "s") + ")");
}
return "exported " + seq.name + " @ " + tc + " (frame " + f + ") -> " + ${JSON.stringify(opts.out)} + ".png"
  + (off.length ? "  |  ⚠ TRACK OUTPUT OFF, NOT IN THIS FRAME: " + off.join(", ")
                  + " — anything on those tracks measures delta 0; setMute(0) to include it, and restore what the creator had"
                : "");
})()
`);
  // Premiere's return string is built from ExtendScript state alone: it says "exported" whether or
  // not a file landed. Check the PNG, or a whole review round reads as good grabs (2026-09-07).
  if (!existsSync(`${opts.out}.png`))
    throw new Error(`frame: Premiere reported ${r} but ${opts.out}.png does not exist`);
  console.log(JSON.stringify(r));
} else if (cmd === "zoom") {
  const opts = { clip: 0, from: 115, to: 100, frames: 18, ease: "quart", fps: "24000/1001",
                 offset: 0, at: null, ...(a1 ? JSON.parse(a1) : {}) };
  const [fpsNum, fpsDen = 1] = String(opts.fps).split("/").map(Number);
  if (!fpsNum || !fpsDen) throw new Error(`bad fps: ${opts.fps} (rational string like "30000/1001")`);
  const EASE = {
    linear: t => t,
    cubic: t => 1 - Math.pow(1 - t, 3),
    quart: t => 1 - Math.pow(1 - t, 4),    // sharper ease-out: 94% of the travel by the midpoint (2026-09-10)
    quint: t => 1 - Math.pow(1 - t, 5),    // sharper still: 97% by the midpoint
    inout: t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,   // the S: cubic ease-in-out, 50% at the midpoint, eased on both ends (the push-in, the user 2026-09-10)
    overshoot: t => { const s = 1.70158; return 1 + (s + 1) * Math.pow(t - 1, 3) + s * Math.pow(t - 1, 2); },
  };
  const fn = EASE[opts.ease];
  if (!fn) throw new Error(`unknown ease: ${opts.ease} (use ${Object.keys(EASE).join("/")})`);
  const vals = [];
  for (let f = 0; f <= opts.frames; f++) vals.push(opts.from + (opts.to - opts.from) * fn(f / opts.frames));
  const r = await es(`
(function(){
var TRACK = 0, CLIP = ${opts.clip}, VALS = ${JSON.stringify(vals)};
var frameDur = ${fpsDen} / ${fpsNum};
var AT = ${opts.at === null ? "null" : Number(opts.at)}, OFFSET_F = ${Number(opts.offset)};
var seq = app.project.activeSequence;
if (!seq) return "ERROR: no active sequence";
var clip = seq.videoTracks[TRACK].clips[CLIP];
if (!clip) return "ERROR: no clip " + CLIP + " on V" + (TRACK + 1);
var hasTransform = false;
for (var i = 0; i < clip.components.numItems; i++) {
  if (clip.components[i].displayName === "Transform") hasTransform = true;
}
if (!hasTransform) {
  app.enableQE();
  var qtrack = qe.project.getActiveSequence().getVideoTrackAt(TRACK);
  var nth = -1;
  for (var q = 0; q < qtrack.numItems; q++) {
    var it = qtrack.getItemAt(q);
    if (it && it.type === "Clip") {
      nth++;
      if (nth === CLIP) { it.addVideoEffect(qe.project.getVideoEffectByName("Transform")); break; }
    }
  }
  clip = seq.videoTracks[TRACK].clips[CLIP];
}
var inPt = clip.inPoint.seconds;
// WHERE THE RAMP STARTS. Default = the clip's in point (the opening zoom-out). "at" is a
// SEQUENCE time in seconds (use a word timestamp straight from the transcript); "offset" is
// frames from the in point. Keys live in SOURCE time, so both resolve through inPoint.
var startSrc = (AT !== null) ? (inPt + (AT - clip.start.seconds)) : (inPt + OFFSET_F * frameDur);
if (startSrc < inPt - 1e-6) return "ERROR: ramp starts before the clip (" + startSrc.toFixed(4) + " < " + inPt.toFixed(4) + ")";
var clipEndSrc = inPt + (clip.end.seconds - clip.start.seconds);
if (startSrc + (VALS.length - 1) * frameDur > clipEndSrc + 1e-6)
  return "ERROR: not enough clip left — ramp needs " + (VALS.length - 1) + " frames past " + startSrc.toFixed(4) + "s, clip ends at " + clipEndSrc.toFixed(4) + "s";
var baked = 0;
for (var i = 0; i < clip.components.numItems; i++) {
  var comp = clip.components[i];
  if (comp.displayName !== "Transform") continue;
  for (var p = 0; p < comp.properties.numItems; p++) {
    var prop = comp.properties[p];
    var dn = prop.displayName;
    if (dn === "Scale Height" || dn === "Scale Width") {
      // Clear only from the ramp start ONWARD. At the default offset that is every key
      // (unchanged behaviour); with an offset it preserves anything earlier — clip 1 carries
      // the opening zoom-out AND a push-in in this same property, and a blanket clear would
      // silently destroy the opening move.
      var keys = prop.getKeys();
      if (keys) {
        for (var k = keys.length - 1; k >= 0; k--)
          if (keys[k].seconds >= startSrc - 1e-6) prop.removeKey(keys[k], 1);
      }
      if (!prop.isTimeVarying()) prop.setTimeVarying(true);
      for (var f = 0; f < VALS.length; f++) {
        var kt = startSrc + f * frameDur;
        prop.addKey(kt);
        prop.setValueAtKey(kt, VALS[f], 1);
      }
      var check = prop.getKeys();
      for (var c = 0; c < check.length; c++) {
        if (check[c].seconds < startSrc - 1e-6) continue;   // leave earlier ramps alone
        try { prop.setInterpolationTypeAtKey(check[c], 0, 1); } catch (e) {}
      }
      baked++;
    } else if (dn === "Shutter Angle") {
      prop.setValue(360, 1);
    }
  }
}
if (baked !== 2) return "ERROR: baked " + baked + " scale props, expected 2";
return "zoom baked: clip " + CLIP + ", " + VALS.length + " keys/prop, first key " + startSrc.toFixed(4) + "s (source time)";
})()
`);
  console.log(JSON.stringify(r));
  console.log(JSON.stringify(await call("save_project")));
} else if (cmd === "grade-layer") {
  // Pipeline step 4, the whole layer half in ONE command: mint an adjustment layer at the
  // ACTIVE SEQUENCE'S OWN FRAME SIZE, import it, place it spanning the timeline on the grade
  // track, name it GRADE, add Lumetri. The size is READ, never typed — that is the point of
  // the command (2026-09-02). The Look is the separate headless step that follows:
  //   premiere-up.sh --quit -> grade-lut.py apply <job>.prproj -> premiere-up.sh <job>.prproj
  const opts = { track: 2, minTracks: 4, lumetri: true, ...(a1 ? JSON.parse(a1) : {}) };
  const { execFileSync } = await import("node:child_process");

  // 1. Read what the sequence actually is. Never assume 16:9, and never trust a job's format
  //    tag over the sequence in front of you.
  const probe = await es(`
(function(){
var seq = app.project.activeSequence;
if (!seq) return "ERROR: no active sequence";
var v1 = seq.videoTracks[0], end = 0;
for (var c = 0; c < v1.clips.numItems; c++)
  if (v1.clips[c].end.seconds > end) end = v1.clips[c].end.seconds;
// ☠️ The grade track must be EMPTY or already ours. overwriteClip REPLACES whatever occupies
// the range without asking (the vendored engine's own source records a case of it silently
// destroying audio), so anything here that is not our GRADE clip is a stop, not a fall-through.
// The real scenario: a timeline that got graphics before the grade ran. CLAUDE.md's documented
// recovery for that is a QE addTracks INSERT at index 1, which shifts the old V2 up to V3 with
// its effects intact — never an overwrite.
var existing = "";
if (seq.videoTracks.numTracks >= ${opts.track}) {
  var gt = seq.videoTracks[${opts.track - 1}], mine = 0, other = 0;
  for (var g = 0; g < gt.clips.numItems; g++)
    if (gt.clips[g].name === "GRADE") mine++; else other++;
  if (mine) existing = "V${opts.track} already holds a GRADE clip";
  else if (other) existing = "V${opts.track} holds " + other + " non-GRADE clip(s) — refusing to overwrite. "
    + "If graphics are already on this track, INSERT a grade track instead "
    + "(QE addTracks(1, 1, 0,0,0,0,0) shifts them up intact) — see CLAUDE.md, the grade-under-graphics note.";
}
return [seq.name, seq.frameSizeHorizontal, seq.frameSizeVertical, end,
        seq.videoTracks.numTracks, v1.clips.numItems, existing].join("\\u0001");
})()
`);
  if (String(probe).startsWith("ERROR")) throw new Error(probe);
  const [seqName, W, H, endStr, nTracks, v1Clips, existing] = String(probe).split("\u0001");
  if (existing) { console.log(JSON.stringify({ skipped: existing })); process.exit(0); }
  if (Number(v1Clips) === 0) throw new Error(`V1 of "${seqName}" is empty — lay the footage before the grade layer`);
  const end = Number(endStr);

  // 2. Mint a template at exactly that size. Deterministic: same size => byte-identical file,
  //    so re-running is idempotent and a second job at the same size re-imports the same item.
  // fileURLToPath, never .pathname — pathname yields /C:/... on Windows (same trap the imports
  // at the top of this file avoid). And probe for python: Windows ships a fake `python3` Store
  // stub that `command -v` trusts, so fall back to `python` the way every .sh here does.
  const { fileURLToPath } = await import("node:url");
  const mint = fileURLToPath(new URL("premiere-templates/mint-adjustment-layer.py", import.meta.url));
  let PY = "python3";
  try { execFileSync(PY, ["-c", ""], { stdio: "ignore" }); } catch { PY = "python"; }
  const [tplPath, tplUuid] = execFileSync(PY, [mint, `${W}x${H}`], { encoding: "utf-8" })
    .trim().split(/\r?\n/);

  // 3. Import, provision tracks, place, name, Lumetri — all read back before reporting.
  const r = await es(`
(function(){
var seq = app.project.activeSequence, root = app.project.rootItem;
var ITEM = "Adjustment Layer ${W}x${H}", JUNK = "adj-template-${W}x${H}";

// Recursive, like this file's own find() in the replay command: the editor is free to file
// into a bin, and a flat scan would miss it and re-import a duplicate.
function findItem(name, bin){
  bin = bin || root;
  for (var i = 0; i < bin.children.numItems; i++) {
    var c = bin.children[i];
    if (c.name === name) return c;
    if (c.type === ProjectItemType.BIN) { var f = findItem(name, c); if (f) return f; }
  }
  return null;
}

// A project that already holds a layer at this size (a second sequence of the same shape,
// or a re-run) reuses it — importing again would just stack duplicate bin items.
var al = findItem(ITEM), imported = "reused";
if (!al) {
  if (!app.project.importSequences(${JSON.stringify(tplPath)}, [${JSON.stringify(tplUuid)}]))
    return "ERROR: importSequences returned false";
  al = findItem(ITEM);
  imported = "minted";
}
if (!al) return "ERROR: '" + ITEM + "' not found after import";
var junk = findItem(JUNK);
// The donor drags a throwaway sequence in with it. deleteBin on a fresh bin is the only
// removal that works on a clip item (deleteItem/deleteBin no-op directly).
if (junk) { var b = root.createBin("__trash"); junk.moveBin(b); b.deleteBin(); }

// A fresh sequence has too few tracks for V1 footage / V2 grade / V3 graphics / V4 accents.
// addTracks APPENDS, so nothing already placed moves.
app.enableQE();
var added = 0;
while (seq.videoTracks.numTracks < Math.max(${opts.track}, ${opts.minTracks})) {
  qe.project.getActiveSequence().addTracks(1, seq.videoTracks.numTracks, 0, 0, 0, 0, 0);
  added++;
  if (added > 8) return "ERROR: addTracks did not grow the sequence";
}

var gt = seq.videoTracks[${opts.track - 1}];
gt.overwriteClip(al, 0);
var g = null;
for (var c = 0; c < gt.clips.numItems; c++) if (gt.clips[c].start.seconds < 1e-6) g = gt.clips[c];
if (!g) return "ERROR: layer did not land on V${opts.track}";
var t = new Time(); t.seconds = ${end};
g.end = t;
try { g.name = "GRADE"; } catch (e) {}

var lum = "none";
if (${opts.lumetri}) {
  var qt = qe.project.getActiveSequence().getVideoTrackAt(${opts.track - 1}), target = null;
  for (var q = 0; q < qt.numItems; q++) { var it = qt.getItemAt(q); if (it.type === "Clip") { target = it; break; } }
  if (!target) return "ERROR: no QE clip on V${opts.track}";
  var eff = qe.project.getVideoEffectByName("Lumetri Color");
  if (!eff) return "ERROR: 'Lumetri Color' effect not found";
  target.addVideoEffect(eff);
  var names = [];
  for (var k = 0; k < g.components.numItems; k++) names.push(g.components[k].displayName);
  lum = names.join("/");
}

// Toggle Track Output: a muted grade track measures delta 0 on every later verification and
// is indistinguishable from a dead effect, so say so now rather than at diagnosis time.
var muted = [];
for (var m = 0; m < seq.videoTracks.numTracks; m++)
  if (seq.videoTracks[m].isMuted() && seq.videoTracks[m].clips.numItems > 0) muted.push("V" + (m + 1));

return ["ok", seq.name, "${W}x${H} (" + imported + ")", g.name,
        g.start.seconds.toFixed(3) + "-" + g.end.seconds.toFixed(3),
        seq.videoTracks.numTracks + " video tracks (+" + added + ")", lum,
        muted.length ? "\\u26a0 TRACK OUTPUT OFF: " + muted.join(",") : "all track output on"].join("  |  ");
})()
`);
  if (String(r).startsWith("ERROR")) throw new Error(r);
  console.log(String(r));
  console.log(JSON.stringify(await call("save_project")));
} else {
  const t = tools.getAvailableTools().find(x => x.name === cmd);
  if (!t) { console.error(`Unknown tool: ${cmd}`); process.exit(1); }
  console.log(JSON.stringify(await tools.executeTool(cmd, a1 ? JSON.parse(a1) : {}), null, 2));
}
process.exit(0);
