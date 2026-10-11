---
name: stage-1-headtracking
description: "Stage 1 - Headtracking: Sameer's Fight Club head-tracking pass on a Premiere sequence (or the In/Out range of it) he has already cut. In After Effects, ONE layer per cut, NO Time Remap: every clip with a visible face is nose-tracked (Anchor Point keys), Position fixed to ONE nose point for every face so cuts look seamless, one constant scale per source chosen so no Mirror-Edge flipped-head line shows, Motion Tile Output 100x150 with Mirror Edges, no zooms, no blur; fights / B-roll / stills are fill only (except B-roll he names, which is tracked); in split-screen sources the person he framed in Premiere is the one tracked. The comp is Dynamic-Linked onto a visible free track above his untouched cut, sync-checked, then QA'd from a real export (nose deviation, frame-exact cut shift, contact sheet). Triggers: stage 1, headtracking, head track this sequence, head-track and motion tile, track the faces, reframe sequence NN, do the headtracking."
---

# Stage 1 - Headtracking

Sameer cuts and orders the footage himself. This stage only **reframes**: nose-stabilized head tracking + Motion Tile, built
in **After Effects** (Premiere has no Motion Tile), linked back onto his sequence. Method + measurements:
[`docs/fight-club/headtracking-method.md`](docs/fight-club/headtracking-method.md) (read it first; it overrides the style
guide's push-in / zoom / blur notes). Validated on Seq02 (Greg Hardy) and Seq01 (Yan vs Merab, in/out 549.85-587.58,
`projects/seq01-merab-0915/`) - Sameer called the Seq01 result perfect.

## Hard rules
- **Never touch the cut.** No cut points, order, audio change. Duplicate the sequence as `<name> BACKUP` first. Touch no other sequence.
- **NO Time Remap, ever** (Sameer, 2026-10-11). One AE layer per CUT: the source clip slid so its in-point sits on the cut.
- **No zoom keys, no push-ins, no blur, no grade, no captions** in this stage.
- **Track every clip with a visible face** (talking, post-fight, coaching...). **Never fights/action**, and B-roll he doesn't
  name: fill only (`skip`). He may name one B-roll to track ("the 4th B-roll, Merab standing") -> `include`.
- **ONE nose point for every face** (same person = same nose = seamless cut). A drifting nose across a cut is the defect he
  complains about. Different people matter less (`nose_by` only if he asks).
- **One constant scale per source.** The build chooses it (see Auto frame). Range he uses: 154-228 %.
- **Split-screen sources: track the person HE framed**, never whoever the detector likes. His Premiere Position/Scale on
  each clip says which half (x<0 = right person, x>1 = left person). `premiere_clips.py` records it; the build reads it.
- **If a clip can't be tracked, say so** (`NO FACE`) - never guess a framing silently.
- Only the project set as **Sandbox** in the AE MCP Bridge panel is writable; never work around that guard; never build
  into his own hand-made AE project - ask him for a new empty one.
- **A Premiere track may be muted/hidden** (his V4 was) - a linked comp on a muted track never renders. Check
  `track.isMuted()` and use a visible track that is empty in the range.

## Procedure
### 0. Read state
`docs/fight-club/headtracking-method.md`, `editing-style-guide.md`; the job's `ANALYSIS.md`. Job: `projects/<job>/`.
Ask which sequence and whether the **In/Out range** is the work area (Seq01 was just the marked range).

### 1. Backup + clip list (Premiere, read-only apart from the backup)
1. Clone the sequence as `<name> BACKUP` (ES `seq.clone()`, rename the NEW one, compare clip counts, `project.save()`), then
   make the original the active sequence again (the clone steals focus).
2. `python .claude/skills/stage-1-headtracking/scripts/premiere_clips.py "<sequence>" projects/<job> --tracks 1,2`
   -> `clips.json`: V1 + B-roll tracks merged, restricted to the sequence In/Out (times relative to In), with each clip's
   media path, source in/out, track, and his Motion `pos`/`scale`. If the bridge call fails it writes
   `premiere-clips.es.js` - run that with the premiere-pro MCP `execute_extendscript` instead. Never trust an old clips.json.
3. Comp fps = sequence fps (Seq01/02 were 60 fps) so cuts stay frame-exact. Ask before converting anything.

### 2. Look at the sources -> `projects/<job>/headtrack.json`
Make a contact sheet (1 frame per clip, `ffmpeg -ss <t> -i <src> -frames:v 1`, then `tile`) and look:
- **B-roll / fights / stills**: `skip_tracks: [2]` (+ `include: [<clip idx>]` for the B-roll he wants tracked), or `skip: [idx..]`.
- **Split screen / two-shot**: nothing to do if Premiere Position/Scale was recorded (auto prefer); else `prefer_x_clip`
  (left 0.25 / right 0.75) or `prefer_x` per source.
- **Wide shot he wants smaller** (Mirror Edges look): `scale: {basename: pct}`. Banners to keep out only if he asks (`banners`).
Template: the docstring of `scripts/build_nose_track.py`. Seq01's real one: `projects/seq01-merab-0915/headtrack.json`.

### 3. Build in After Effects
1. He makes a NEW empty project (`.aep`, e.g. `merabvsyan.aep`) and clicks **Use current** next to Sandbox in
   **Window > Extensions > AE MCP Bridge**. Confirm with `ae_project_info` that `projectPath` is that file.
2. `uv run .claude/skills/stage-1-headtracking/scripts/build_nose_track.py projects/<job>` prints the **auto frame** line
   (scale + nose y + feasible band) and one line per clip; writes `ae/headtrack.jsx`, `ae/sync-check.jsx`,
   `ae/headtrack-report.json`. Any `NO FACE` line -> stop and tell him which clip.
   *Auto frame*: for the source with the most tracked clips, the smallest scale >= fill x 1.0558 (his 187.7 % on 1080p,
   raised so a face is >= 17 % of the width, cap 230) at which ONE nose height clears BOTH the top and bottom edge for
   every tracked frame (top: `ny <= min_ay*k`, bottom: `ny >= H-(sh-max_ay)*k`, 12 px margin, >= 40 px band); nose x = W/2,
   y = middle of the band. Seq01: 205-207 %, y 669-672. A 1080p source at ~188 % has only ~107 px of vertical slack, so no
   nose height fits at the base scale - that's why it raises the scale rather than just moving the nose.
   If it prints "NO nose height clears both edges", Mirror Edges will show: tell him, don't hide it.
   (Setting `nose` and/or `scale` in headtrack.json turns the auto frame off / overrides it.)
3. `ae_run_jsx {"file": ".../ae/headtrack.jsx"}` builds (or rebuilds in place) the comp `<sequence> Headtrack` and saves.
   Re-running is safe: it clears and rebuilds the same comp, so a Dynamic Link survives.
4. `ae_run_jsx {"file": ".../ae/sync-check.jsx"}` -> must say **all in sync**. Also confirm `timeRemapEnabled` is false on
   every layer.

### 4. Link onto the sequence (Premiere)
`app.project.importAEComps("<aep with BACKSLASHES>", ["<comp>"], <bin>)`, then overwrite it at the **In point**
(`seq.getInPointAsTime().seconds + 0.0001`) on a **visible track that is empty in the range**, above his cut. Read back:
the comp clip spans the range; clip counts of every other track unchanged. `project.save()`. (Already linked? Skip; the
rebuilt comp updates through the link.)

### 5. QA from a real export, then STOP
1. Export through Premiere (never AME): `seq.exportAsMediaDirect(out, epr, 1)` (1 = In to Out) with **backslash** paths and
   `C:\Program Files\Adobe\Adobe Premiere Pro 2025\CEP\extensions\com.adobe.frameio.v4\assets\epr\Match Source - Adaptive High Bitrate.epr`.
   The bridge call errors / times out while Premiere renders - **normal**: poll the file until its size stops changing,
   don't retry. Exports are ~185 MB: check free space on C: and E: first (`ENOSPC` = disk full), delete old test exports.
2. `uv run .claude/skills/stage-1-headtracking/scripts/qa_nose.py <export.mp4> projects/<job> --out "previews/" --name <job>-stage1`
   -> `-qa.json`, `-contact-sheet.jpg` (red cross = nose target), `-preview-540p.mp4`.
3. **Look at the contact sheet yourself**: the right person on every clip (compare with his cut), no flipped-head sliver at
   an edge, no face cut off, no letterboxed clip (= the comp isn't covering: muted track / wrong layer), lower-third strips at
   the bottom (accepted by him, but mention).
4. Pass marks: nose within ~25 px of target on tracked clips, 0 no-face samples, same-person cut shift small (median
   <= ~20 px; cuts between two different people legitimately shift more), black frames only where a source is black (a PNG
   background), sync all in sync. Report in plain words: which clips are tracked / skipped, the auto-frame scale and nose,
   deviation, cut shifts, anything off. STOP.
5. Append the result to the job's `ANALYSIS.md`; a new lesson goes in `presets/youtube/fight-club/LESSONS.md`.

## Gotchas
- **A layer with Time Remap is a bug now.** Remaining motion at his jump cuts is the head pose changing in his edit, not tracking.
- **QE `exportFramePNG` throws** on Premiere 25.6 - verify from the export. **`exportAsMediaDirect` needs backslash paths.**
- **~40 full-res `ae_render_frame` grabs killed the AE connection once** - grab a few only; QA from the Premiere export.
- `ae_render_frame` blobs aren't sorted in render order - map by the order in the response.
- `ae_run_jsx` returns unparseable output if the result contains emoji (layer names): return numbers/ASCII only.
- A still (PNG): fill only, no tracking; OpenCV prints a harmless "codec 61" error for it.
- His own AE tracker layers keep tracker data only on the first split piece - read anchor keys / measure the render.
