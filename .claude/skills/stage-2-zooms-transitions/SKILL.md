---
name: stage-2-zooms-transitions
description: "Stage 2 - Zooms and Transitions: Sameer's BlurMo Curves zooms + brightness-flash transitions on his Stage 1 render, in After Effects (Sandbox project), after he has cut the sequence. The Stage 1 render (2.mp4) goes in the Stage 1 comp under ONE plain adjustment layer; Claude cuts that layer at every picture-change frame, HE labels the pieces Green (zoom in) / Purple (zoom out) / Orange (3-key: release then snap back in); the render is cut at the same boundaries and TIME-REMAPPED to remove Premiere's Morph Cut blend at each cut; then one S_BlurMoCurves zoom per labelled layer (depth ~0.74, his measured ease; intense drop curve on the first clip; SUBTLE on short layers), a smooth BCC brightness flash on every cut (+25, lower when back to back), the hand-tuned white-solid camera flash on cuts he names, white edge lines on baked-blur B-roll he names; linked back and QA'd from a real export. Triggers: stage 2, zooms and transitions, blurmo curves, add zooms, add transitions, do the zooms."
---

# Stage 2 - Zooms and Transitions

Sameer's cut, order and audio are never touched. This stage adds **one zoom per segment he labels**, **smooth brightness flashes** and a few
**camera-flash / B-roll line accents**, in **After Effects**, exactly the way he builds them himself. He called the Seq01 result **perfect**
(2026-10-11: `projects/seq01-merab-0915/`, comp "Sequence 01 Headtrack 0915", `merabvsyan.aep`).

**The method is his** - read [`docs/fight-club/blurmo-transitions-method.md`](docs/fight-club/blurmo-transitions-method.md) first
(Comp 09, Linked Comp 01 measurements, the smoothing rules, the camera flash, the curve types).

## Hard rules
- **One zoom per labelled adjustment layer. No extra "mini zooms".** Labels are HIS: **Green (9) = zoom in, Purple (10) = zoom out, Orange (11) = 3-key
  zoom-out (the zoom releases, then snaps back in before the cut).** Never invent a direction; unlabelled = no zoom (tell him). He may merge weak cuts
  into one layer - respect his layers, spans, names and labels (zooms go ON them).
- **Transitions:** a brightness **flash on every segment start after the first**, bright only (never dark unless he asks). **Smooth, not flashy:** peak
  +25 for an isolated cut, **lower when they occur back to back** (about +9 when ~1 s apart). A **white-solid camera flash** replaces it only on a cut he
  names (`solid`). He can drop one (`none`).
- **Short layers get SUBTLE zooms** (< 1.8 s: shallower depth + softer ease - the scene changes quickly, an intense zoom feels unpleasant). Long layers keep
  the full curve. The **first clip is the hook: his intense DROP curve** (0.64 -> 1, snap then long settle).
- **Time Remap is part of Stage 2 (step 3):** removes Premiere's Morph Cut blend at every cut. Never touch a piece that already has a remap (his).
  Stage 1 itself never uses Time Remap.
- **B-roll looks only where he points:** `--lines` (white edge lines on a band whose blur is already baked into the render) / `--bands` (full band + blurred
  copy + lines, for B-roll whose blur is NOT in the render) / `solid` flash. Ask which cuts; never choose them.
- Everything is added **in the AE Sandbox project** (never his own hand-made .aep; if the open project isn't the Sandbox one, say so - `ae_project_info` first).
  His layers/labels are never changed except what the steps below do to the plain adjustment layer and the render.

## Procedure (Variant A - validated on Seq01: the Stage 1 comp itself)
### 0. Read state
`blurmo-transitions-method.md`, the job's `ANALYSIS.md` (`projects/<job>/`), `ae_project_info` (which project/comp is open, is it the Sandbox?).
Prerequisite: the Stage 1 comp is built and linked (stage-1-headtracking) and **he rendered it to a video** (AME) and dropped it in the SAME comp above the
Stage 1 layers (which he disables), with one plain adjustment layer over it. If the comp has the render (`2.mp4` here) and the adjustment layer, go on.
`clips.json` (`premiere_clips.py ... --tracks 1,2`, In/Out range) gives the razor frames.

### 1. Find the real cut frames + Morph Cut windows
`uv run .claude/skills/stage-2-zooms-transitions/scripts/detect_cuts.py projects/<job> "<path to the render>"` -> `ae/picture-cuts.json`: per cut the PICTURE frame
(Seq01: razor + 1 on every cut except the first) and the Morph Cut blend (keep frames <= L of the old clip / >= S of the new, normally p-3 / p+2).
Check the strongest cut with `ae_render_frame` (max ~4 frames) if the offset looks odd. A picture change >= 2 frames off the razor = a lip-sync offset: flag it.

### 2. Cut the adjustment layer -> STOP for his labels
`python .../prep_stage2.py projects/<job> --comp "<comp>" --video "<render name>"` writes `ae/split-adjustment.jsx`, `split-video.jsx`, `morph-remap.jsx`, `read-layers.jsx`.
Run `split-adjustment.jsx` (`ae_run_jsx {"file": ...}`): his plain adjustment layer is cut into one layer per cut at the picture frames (read back: contiguous,
no gaps/overlaps). Tell him to label them (Green / Purple / **Orange** for a 3-key), merge any weak cuts he wants merged, and say "labelled". Ask in the same message which
cut (if any) gets the white-solid camera flash and which B-roll clips get the lines/band look.

### 3. Cut the render + remove the morph (Time Remap)
1. Read his labelled layers: `ae_run_jsx {"file": ".../ae/read-layers.jsx"}` returns `[{"in": frame, "out": frame, "label": n}, ...]` -> save the JSON as
   `projects/<job>/ae/layers.json` (`out` past the comp end is fine).
2. `split-video.jsx` cuts the render at every adjustment layer's in-point (one piece under each). Then `morph-remap.jsx`: Time Remap on every piece
   (key at the in-point = first clean frame of the new clip, key at the out-point so the last shown frame is the last clean frame of the old clip; the piece is
   stretched ~3 %). Boundaries he merged have no morph handling (the blend stays inside that piece). Pieces with a remap already (his) are skipped.
   Read back: piece count = adjustment layer count, remap keys 2 per piece, every `timeRemapEnabled` true.

### 4. Plan -> build -> read back
1. `python .../plan_zooms.py projects/<job> --layers projects/<job>/ae/layers.json --comp "<comp>" [--transitions "5:solid:<why>" "9:none"] [--curve "<n>:drop3"] [--lines "<n>:<top>-<bottom>"] [--bands <n>] --center-cut "<n>:540,960" ...`
   (segment numbers = his layers in time order). Defaults: zoom-in 1 -> 0.74, zoom-out 0.75 -> 1, first segment the hook, Orange = drop3, short segments subtle
   (`--no-subtle`), flashes +25 smoothed by neighbour gap (`--no-smooth`, or `"<n>:flash=30"` for one), Center XY = the Stage 1 nose point (`ae/frame.json`; the
   non-face B-roll segments get `--center-cut "<n>:540,960"`).
   - **White edge lines** on a B-roll whose blurred band is already in the render: measure it with `band_edges.py "<render>" <t1> <t2> ...` (top edge is stable,
     the bottom can under-read on dark frames - confirm on a crop), then `--lines "<segment>:<top>-<bottom>"` (24 px lines, top = edge + 3, bottom = edge - 7,
     above that render piece, below the zoom layers).
   - **3-key** (`drop3`) only on Orange layers he labelled (or `--curve "<n>:drop3@0.77"` on a cut he names).
2. `python .../build_zooms.py projects/<job>` -> `ae/stage2.jsx`; `ae_run_jsx {"file": ".../ae/stage2.jsx"}`. It writes the zoom (S_BlurMoCurves, defaults, Center XY + Z Dist
   on his layers' first/last frame), the brightness flashes (own adjustment layers, 3 linear keys 14 up / 15 down, peak ON the cut), the solid flash (his decay
   curve) and the lines. Re-running is safe: it replaces only Zoom / Flash / Solid flash / Band / "White Solid 1 (band" layers and rebuilds the zoom effect on his layers.
3. Read back: every zoom layer's direction matches its label, Z keys on the first/last frame, 3 keys on Orange (0 / 77 % / end), peaks on the cut frames and lower
   when back to back, solid flash = 100 on the cut -> 0 at +25 with out -5485/3.1 % and in 0/73.8 %. Render <= 4 frames at a time to look (hook, a flash, a mid zoom,
   the solid flash cut, the line B-roll).

### 5. Link + QA from a real export, then STOP
1. Premiere: link the comp onto a visible, empty-in-range video track above his cut at the In point (stage-1-headtracking § 4: muted tracks never render;
   remove an older Stage 2/Stage 1 comp clip on that track first), read back counts, save.
2. Export through Premiere (`exportAsMediaDirect(out, epr, 1)`, backslash paths, "Match Source - Adaptive High Bitrate" .epr; the bridge errors while it renders -
   poll the file; check disk space first). Measure at each zoom's first/last frame (YuNet face width: zoom-in grows it) and at each flash peak (mean
   brightness up, smaller when back to back). Make the 540p preview into `previews/`.
3. Report: a table of segment -> label -> zoom (depth, subtle?), the flashes (peaks), the solid flash / lines, the Time Remap result, flags (lip-sync offset,
   unlabelled layers). Then STOP. Append to `ANALYSIS.md`; new lessons -> `blurmo-transitions-method.md` (add, never rewrite his notes).

## Variant B (older, Seq02): a fresh "Cuts" comp from Premiere V1
When there is no render-in-comp yet: `make_cut_comp.py` -> `ae/cuts.jsx` builds comp `<sequence> Cuts` with "Cut 1..N" layers; he labels them; `read-labels.jsx`
-> `labels.json`; `cut_frames.py --adobe-offset 1` -> `ae/cut-frames.json`; then `plan_zooms.py --labels labels.json` (same flags as above, Cut N numbering) and
`build_zooms.py` (new zoom layers named "Zoom N"). The smoothing / curve / flash rules apply identically.

## Gotchas
- **Do not smoke-test in his own hand-made project** (Seq01: a test comp was briefly built in `calude islamvsaa.aep` by mistake and removed again) - use the Sandbox
  project, a throwaway comp, and delete it afterwards (and its solids). `ae_project_info` first.
- **Edge cases:** a layer running past the comp end is clamped by the plan; label other than 9/10/11 = no zoom; weak (static jump) cuts have no measurable morph -> the
  standard p-3 / p+2 trim; merged cuts keep their blend inside the piece.
- The Stage 1 render may already carry a grade, baked zoom-blurs and baked B-roll bands (blurred background): keep them, stack Stage 2 on top, say so.
- `ae_render_frame`: <= 4 frames per call (40 full-res frames killed the AE connection once); a single-frame call returns a tiny image - ask for 2-4.
- `ae_run_jsx` can't return emoji / NaN: return ASCII numbers; read keys with `keyTime * fps` rounded.
- AE's frame for a time can be 1 later than ffmpeg's decode of the same file (`--adobe-offset` in Variant B); in Variant A the detect_cuts frame numbers already match the comp.
- A comp rendered via Dynamic Link carries the Sapphire + BCC effects - verify by measurement, not by eye on a 0.5 s sheet.
