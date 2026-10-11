---
name: stage-2-zooms-transitions
description: "Stage 2 - Zooms and Transitions: Sameer's BlurMo Curves zooms + BCC Brightness-Contrast transitions on a Premiere sequence he has already cut (usually after Stage 1). His V1 cuts go into an After Effects comp as one layer per cut; HE labels each cut Green (zoom in) or Purple (zoom out); then exactly ONE zoom per cut (Sapphire S_BlurMoCurves on an adjustment layer, his Comp 09 curve) and dark/flash transitions picked by mood, peaking on the real picture-change frame; linked back onto V2 and QA'd from a real export. Triggers: stage 2, zooms and transitions, blurmo curves, add zooms, add transitions, do the zooms."
---

# Stage 2 - Zooms and Transitions

Sameer's cut, order and audio are never touched. This stage adds **one zoom per cut he made** and **mood transitions**,
in **After Effects**, exactly the way he builds them himself.

**The method is his** — read [`docs/fight-club/blurmo-transitions-method.md`](docs/fight-club/blurmo-transitions-method.md)
first (learned from his `D:\1.aep`, comp "fightcluB Linked Comp 09", incl. the same-day corrections).
First built on `Sequence 02 BACKUP` (Greg Hardy inhaler, 2026-10-06): job `projects/seq02-greg-hardy-inhaler/`, comp "Seq02 V1 Cuts".

## Hard rules
- **One zoom per cut he made in Premiere. No extra "mini zooms"** (he rejected a 13-zoom version on Seq02).
- **The direction is HIS:** he labels each cut layer in AE — **Green (label 9) = zoom in, Purple (label 10) = zoom out**.
  Read the labels; never invent a direction. Confirm the label names in his AE prefs
  (`%APPDATA%\Adobe\After Effects\<ver>\Adobe After Effects <ver> Prefs-indep-general.txt`, `"Label Text ID 2 # 9"`).
  An unlabelled cut gets no zoom — tell him.
- **Transitions by mood**, chosen by Claude and explained in one line each: **dark** (−30) for tension / negative / a
  deflating twist / the act → the fallout; **flash** (+25) for an outburst, a reveal, the camera turning to someone, the
  receipt. Not every cut needs one. (He confirmed "on mood" on Seq02.)
- Everything goes on **adjustment layers above his "Cut N" layers**; his layers and labels are never changed.
- The AE bridge only edits the project set as **Sandbox**; never work around that guard.

## Procedure

### 0. Read state
`blurmo-transitions-method.md`, `editing-style-guide.md`, `setup-log.md`, the job's `ANALYSIS.md`. Which sequence? (Seq02: he
named "Sequence 02 BACKUP", whose V1 was his Stage 1 render `2_2.mp4` razor-cut into 6 clips.) Read V1 fresh — he re-cuts.

### 1. His cuts → AE, then STOP for his labels
1. `python .claude/skills/stage-1-headtracking/scripts/premiere_clips.py "<sequence>" projects/<job>` → `clips.json`.
2. `python .claude/skills/stage-2-zooms-transitions/scripts/make_cut_comp.py projects/<job>` → `ae/cuts.jsx`, `ae/read-labels.jsx`.
3. `ae_run_jsx {"file": ".../ae/cuts.jsx"}` → comp `<sequence> Cuts` with layers "Cut 1…N", no effects, no labels, audio off.
4. Tell him: right-click each layer ▸ **Label ▸ Green** (zoom in) or **Purple** (zoom out), then say "labelled". Ask in the
   same message only what you can't decide (he decides transitions are "on mood" unless he says otherwise).

### 2. Read the labels + find the real cut frames
1. `ae_run_jsx {"file": ".../ae/read-labels.jsx"}` → save the returned JSON as `projects/<job>/ae/labels.json`.
2. `uv run .claude/skills/stage-2-zooms-transitions/scripts/cut_frames.py projects/<job> --adobe-offset 1` → `ae/cut-frames.json`.
   **Verify the Adobe offset** on the strongest cut: `ae_render_frame` on the two frames around the reported picture time
   (max ~4 frames per call). Seq02's `2_2.mp4`: the picture changed 1–2 frames after the razor in ffmpeg, +1 more in Adobe.
   Zooms and transitions go on the frame where the picture changes, not on the razor mark.
3. If the picture is ≥2 frames off the razor (= his audio cut), **flag the lip-sync offset to him**; don't move his timeline.

### 3. Plan (mood) → build
1. Read the transcript lines at each cut (the job's WhisperX words, or transcribe the sequence audio) and pick moods.
2. `python .claude/skills/stage-2-zooms-transitions/scripts/plan_zooms.py projects/<job> --labels projects/<job>/ae/labels.json --transitions "2:dark:<why>" "3:flash:<why>" ...`
   → `stage2-plan.json` (depths: hook zoom-out 0.70→1, zoom-in 1→0.80, zoom-out starts ~0.02 wider than the zoom-in before
   it ended, payoff = last zoom-in 1→0.66; `--depth "<cut>:<z>"` overrides).
3. `python .claude/skills/stage-2-zooms-transitions/scripts/build_zooms.py projects/<job>` → `ae/stage2.jsx`;
   `ae_run_jsx {"file": ".../ae/stage2.jsx"}`. Re-running replaces only the Zoom/Dark/Flash layers.
4. Read back (ES): every Zoom layer's label = its cut's label, Z Dist keys on the first/last frame; every transition's
   peak key on its cut frame.

### 4. Link + QA from a real export, then STOP
1. Premiere: on the sequence's **V2**, remove any older Stage-2 comp clip, `app.project.importAEComps("<aep, BACKSLASHES>", ["<comp>"], <bin>)`,
   `videoTracks[1].overwriteClip(item, 0.0001)`; read back V2 = 0 → end, V1 / A1 counts unchanged; save.
2. Export through Premiere (`exportAsMediaDirect`, backslash paths, the "Match Source - Adaptive High Bitrate" .epr — see
   stage-1-headtracking § 5; the bridge times out while it renders, poll the file).
3. Measure vs the raw V1 footage at each zoom's first/last frame (YuNet face width: zoom-in grows it, zoom-out shrinks it)
   and at each transition peak (mean brightness: dark lower, flash higher). Seq02: face 60→37 % on the hook, 49→59 % and
   43→59 % on zoom-ins; dark 43–48 vs raw 81–89; flash 163/89/55 vs raw 87/44/34.
4. Make the 540p preview into `previews/` and report: a table of cut → label → zoom, each transition
   with its mood reason, the measurements, any flag (lip-sync offset, unlabelled cuts). Then STOP.
5. Append to the job's `ANALYSIS.md`; new rules → `blurmo-transitions-method.md` (add, never rewrite his existing notes).

## Gotchas (Seq02)
- His V1 render may already carry a grade and some baked zoom-blurs; he chose to keep it as is and stack Stage 2 on top. Say
  so if you see it (compare a few frames against the Stage 1 export), then follow his call.
- A comp rendered via Dynamic Link does carry Sapphire + BCC effects — verify by measurement, not by eye on a 0.5 s sheet.
- `ae_render_frame`: keep to ~4 frames per call (40 full-res frames killed the AE MCP connection once).
- AE's frame for a given time can be 1 later than ffmpeg's decoded frame on the same file — that's what `--adobe-offset` is for.
