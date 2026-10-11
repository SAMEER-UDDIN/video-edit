---
name: stage-1-headtracking
description: "Stage 1 - Headtracking: Sameer's Fight Club head-tracking pass on a Premiere sequence he has already cut. In After Effects, ONE layer per scene (not per cut): the nose is tracked continuously through each camera shot, Time Remap reproduces his cut frame-exactly, Anchor Point follows the nose with Position fixed (nose matched across every cut), scaled just enough (constant per camera shot, burned-in banners kept out), Motion Tile with Mirror Edges, no zooms, no blur; the comp is Dynamic-Linked back onto the sequence above the untouched cut, sync-checked, then QA'd from a real export (frame-exact cut check, contact sheet, low-res preview). Triggers: stage 1, headtracking, head track this sequence, head-track and motion tile, track the faces, reframe sequence NN, do the headtracking."
---

# Stage 1 - Headtracking

Sameer cuts and orders the footage himself. This stage only **reframes**: nose-stabilized head tracking + Motion Tile, built
in **After Effects** (Premiere has no Motion Tile, and BCC isn't visible to Premiere scripting), linked back onto his sequence.

**The method is his** — read [`docs/fight-club/headtracking-method.md`](docs/fight-club/headtracking-method.md) first.
It was learned from his own AE project and **overrides** the style guide's push-in / impact-zoom / blur notes.
First validated on `Sequence 02` (Greg Hardy inhaler, 2026-10-06): job folder `projects/seq02-greg-hardy-inhaler/`.

## Hard rules
- **Never touch the cut.** No cut points, order or audio change. Before anything, duplicate the sequence as `<name> BACKUP`.
  Touch no other sequence.
- **No zoom keys, no push-ins, no blur, no grade, no captions** in this stage.
- **One layer per SCENE, not per cut** (Sameer, 2026-10-06: "dont cut a clip unless the scene is changing"). Consecutive
  clips of one camera shot = ONE AE layer, tracked continuously over its whole source span; **Time Remap** reproduces his
  cut exactly (HOLD into every cut, so the picture stays in sync with his audio and nothing slides across a cut).
  A new layer only where the camera/scene/framing changes. Verify sync: remap value at every clip's first/mid/last frame
  = its source in point (Seq02: 57/57 points, worst 0.01 ms).
- **One constant scale per camera shot** (the face never pops in size on a jump cut). Base = fill × 1.0558 (his 187.7 % on
  1080p); raised only to keep **burned-in banners** (chyrons, broadcast bars, date strips) out of frame.
- **Position is the same nose point for every clip** (default x 540, y 925 on 1080×1920) → every cut is nose-matched.
- **If a clip can't be tracked, say so** (the build prints `NO FACE`) — never guess a framing silently.
- The AE bridge only edits the project set as **Sandbox** in its panel; never work around that guard.

## Procedure

### 0. Read state
`docs/fight-club/headtracking-method.md`, `editing-style-guide.md`, `setup-log.md`; the job's `ANALYSIS.md` if it exists.
Job folder: `projects/<job>/` named after the story (e.g. `seq02-greg-hardy-inhaler`).

### 1. Backup + clip list (Premiere, read-only apart from the backup)
1. Clone the sequence as `<name> BACKUP` (ES `seq.clone()`, rename the new one, compare clip counts) and `app.project.save()`.
2. `python .claude/skills/stage-1-headtracking/scripts/premiere_clips.py "<sequence>" projects/<job>` → `clips.json`
   (size, fps, duration, every V1 clip's media path + sequence in/out + source in/out).
3. Flag sequence settings that aren't 1080×1920 / 29.97 (Sequence 02 was 60 fps: the comp **matches the sequence fps** so
   every cut stays frame-exact; ask before converting anything).

### 2. Inspect the sources → `projects/<job>/headtrack.json`
For each source, grab a frame (`ffmpeg -ss <t> -i <src> -frames:v 1`) and look:
- **Who should be tracked?** If two people share the frame (corner footage, press-conference two-shot), set `prefer_x`
  (0..1 across the source) for the subject.
- **Burned-in graphics?** Measure the source-pixel line where each banner starts → `banners`:
  `["bottom", <first banner row>]` or `["top", <last banner row>]` (Seq02: corner bar bottom 641/720, NESN chyron
  bottom 897/1080, ESPN "OCT 18 FRI" top 24/720).
- **Same source, different framing?** (a wider shot of the same speaker) → put it in its own `groups` entry.
- **B-roll / stills that must not be tracked** → `skip`.
Template: the script docstring in `scripts/build_nose_track.py`. Seq02's real one: `projects/seq02-greg-hardy-inhaler/`.

### 3. Build in After Effects
1. Sameer opens/saves the AE project **inside the job** (`projects/<job>/ae/<job>.aep`) and clicks **Use current** next to
   Sandbox in **Window ▸ Extensions ▸ AE MCP Bridge** (walk him through it step by step; he did it once already).
   Confirm with `ae_project_info` that `projectPath` is that file.
2. `uv run .claude/skills/stage-1-headtracking/scripts/build_nose_track.py projects/<job>` → prints one line per SCENE
   (clips inside, cuts inside, tracked source span, lost frames, scale, Motion Tile) and writes `ae/headtrack.jsx`,
   `ae/sync-check.jsx` and `ae/headtrack-report.json`. Any `NO FACE` line → stop and tell Sameer which clip.
3. `ae_run_jsx {"file": "<repo>/projects/<job>/ae/headtrack.jsx"}` → builds (or rebuilds in place) the comp
   `<sequence> Headtrack` (or the `comp` name in `headtrack.json`) and saves the project. Re-running is safe: it clears
   and rebuilds the same comp, so a Dynamic Link to it survives.
4. `ae_run_jsx {"file": "<repo>/projects/<job>/ae/sync-check.jsx"}` → must say **all in sync** (Time Remap at
   every clip's first / middle / last frame = his source timing). Anything else: fix before going on.

### 4. Link onto the sequence (Premiere)
`app.project.importAEComps("<aep with BACKSLASHES>", ["<comp>"], <bin>)`, then `seq.videoTracks[1].overwriteClip(item, 0.0001)`
— **V2, above the untouched V1**. Read back: V2 = 1 clip spanning 0 → sequence end; V1 / A1 counts unchanged. Save.
(Already linked from an earlier run? Skip — the rebuilt comp updates through the link.)

### 5. QA from a real export, then STOP
1. Export through Premiere (never AME): `seq.exportAsMediaDirect(out, epr, 0)` with **backslash** paths and
   `C:\Program Files\Adobe\Adobe Premiere Pro 2025\CEP\extensions\com.adobe.frameio.v4\assets\epr\Match Source - Adaptive High Bitrate.epr`.
   The bridge call times out ("MCP Bridge is not running") while Premiere renders — **that is normal**: poll the file
   until its size stops changing, don't retry the export.
2. `uv run .claude/skills/stage-1-headtracking/scripts/qa_nose.py <export.mp4> projects/<job> --out "previews/" --name <job>-stage1`
   → `-qa.json`, `-contact-sheet.jpg` (1 frame / 0.5 s, timestamps, red cross = nose target), `-preview-540p.mp4`.
3. Look at the contact sheet yourself (banners at an edge? a face cut off? the wrong person?) — the numbers don't see banners.
4. Report and STOP. Pass marks: nose within ~45 px of target, same-scene cut shift median ≤ ~15 px (frame-exact), 0
   black-edge frames, sync check all in sync. The report, in plain words:
   - a table of the scene layers (which clips each holds, tracked source span, scale and **why**, e.g. a banner);
   - nose deviation per clip, the frame-exact shift at cuts, black frames, face widths, anything off on the sheet;
   - **say it out loud:** the remaining motion at his jump cuts is the head pose changing in his edit, not the tracking
     (he confirmed this himself on Seq02) — options only if he asks: Morph Cut later, or restoring gaps (changes audio).
   Seq02 reference (4 scene layers): dev 14–44 px (one 72 px clip with a cornerman passing), 0 black frames; frame-exact
   nose shift across his jump cuts median 12 px — the rest of any felt "jerk" is the head pose changing at HIS jump cut,
   not tracking. If he wants that gone: Morph Cut (a transition stage) or restoring the removed gaps (changes his audio — ask).
5. Append the result to the job's `ANALYSIS.md`; a new lesson goes in `presets/youtube/fight-club/LESSONS.md`.

## Gotchas (all hit on Seq02)
- **QE `exportFramePNG`/`exportFrameJPEG` throw** on Premiere 25.6 → the repo's `premiere-bridge.mjs frame` fails. Verify
  from the export instead.
- **`exportAsMediaDirect` needs backslash paths** on Windows; forward slashes return "Unknown Error".
- **`ae_render_frame` with ~40 full-res frames killed the AE MCP connection** (AE was at ~14 GB). Keep AE grabs to a few
  frames; do the real QA from the Premiere export.
- `ae_render_frame` returns blobs whose filenames don't sort in render order — map them by the order in the response.
- AE comps may be left at quarter preview resolution; that doesn't affect Dynamic Link output — don't change his setting.
- Stabilized tracks keyed per **source** frame (23.976 / 30 / 59.94) inside a 60 fps comp are fine; keys are linear,
  except the last key before each cut, which is HOLD (one layer per scene would otherwise blend across the cut).
- **"There are too many small blocks" (Seq02)** = the old one-layer-per-clip build mirroring his jump cuts. One layer per
  scene fixed the look of the timeline; the blocks were never extra cuts, so never "fix" it by changing his edit.
- His AE tracker layers were split after tracking, so only the first piece keeps tracker data — read anchor keys / measure
  the render, not `Feature Center`, when inspecting his projects.
