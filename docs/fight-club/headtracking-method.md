# Sameer's head-tracking + Motion Tile method (from his own AE project, Oct 6, 2026)

Source: Sameer's explanation plus screenshots of his AE comp "fightcluB Linked Comp 02" (60 fps, vertical, Gervonta "Tank" Davis interview short). **This overrides style guide § 4's push-in, impact-zoom and blur notes for head tracking.** Sameer: "dont do zooms just head track and motion tile no need to blur".

## How he does it
1. **One layer per camera shot.** He only cuts when the camera or scene actually switches, so each tracked layer is one continuous shot.
2. **Tracker ▸ Track Motion / Stabilize Motion, Track Type = Stabilize, Position only** (Rotation and Scale unticked). One tracker per clip (`Motion Trackers ▸ Tracker 1`), **track point on the subject's nose**.
3. Stabilize writes **Anchor Point keyframes** (e.g. 914.5, 559.5 changing per frame). **Position stays constant**: it's where the nose sits in the frame (e.g. 477, 901 or 353, 908).
4. **Nose matched across cuts:** when a clip changes, the new clip's Position is set to the **previous clip's nose position**, so the nose doesn't jump between shots.
5. **Scale only as much as needed** (≈187 % on 1080p footage in a 1080×1920 comp; 177.8 % is the minimum fill). **No zoom keyframes, no push-ins, no blur.**
6. **Motion Tile on each clip:** Tile W/H 100, **Output Width 100, Output Height 120, Mirror Edges ON**. Just enough to cover any gap the stabilization opens up.
7. Stills (ChatGPT PNGs) and B-roll (e.g. "The ROA…Garcia.mp4") sit untracked between the tracked clips.

## How Claude should replicate it
- AE scripting can't press the tracker's "Analyze" button reliably. Use the **same math** instead: track the nose per frame (YuNet face landmarks include the nose tip; or AE's tracker if Sameer runs Analyze), then write **Anchor Point keys = nose position in the source** and a **constant Position = the target nose point**. That is exactly what Stabilize produces.
- Nose target for the first clip ≈ frame centre; every later clip **inherits the previous clip's nose Position**.
- Scale: smallest value that keeps the face tight (≈187 % for 1080p); Motion Tile Output ≈100/120, Mirror Edges on.

## Update 2026-10-06: one layer per scene  (SUPERSEDED 2026-10-11: per-cut layers, NO Time Remap)
Sameer: "you dont need to make cut a clip unless scene is changing ... so the video looks in continuity instead of small cuts."
- In AE, **consecutive clips of the same camera shot are ONE layer**, not one layer per edit. Track the nose **continuously**
  through the scene's source footage; reproduce his Premiere cut with **Time Remap** (hold into each cut) so the picture
  stays in sync with his audio. Start a new layer only when the camera / scene / framing changes.
- His cut, order and audio are never changed for this. The jump cuts themselves stay (he chose to keep them over restoring
  the removed gaps).

## Update 2026-10-11: learned from "fightclubtestingphase Linked Comp 01" (Islam / Burroughs / Magomedov short) — SUPERSEDES the 10-06 scene note
Measured on his enabled layers 68-103 (60 fps, 1080x1920), then confirmed with Sameer:
- **One layer per CUT again** ("per-cut layers like here"). Layer = source clip trimmed to the cut, no Time Remap.
- **What he tracks:** every clip with a visible face (interviews, post-fight, coaching, podium) — **never fight/action clips**.
  Those (and B-roll) get fill only: no tracking, no Motion Tile (his layers 69-71, 74, 76-84 style).
- **Same person = same nose point** in every clip so cuts look like no cut. Two different people: matters less.
  Measured Position is NOT one global point though (nose lands ~22-54 % down the frame), so drifting nose across a cut
  is the thing he complains about — Stage 1 must hold ONE nose point per person across all their clips.
- **Anchor keys** start at the source centre (960,540) on a clip's first frame and move relative to it (AE Stabilize);
  Position is where that first-frame nose sits. Our absolute-nose + constant-Position build is equivalent.
- **Scale is constant per source/shot, 154-228 %** (Magomedov 184.9, Dc Check-In 167.1, Burroughs interview 176.2,
  tiny-face wide shot 227.8, wide fight 118.5). Not a pure face-size formula: ~188 % (fill x 1.0558) by default, raised so
  a tiny face reaches ~17 % of width (cap ~230), and a WIDE shot may sit BELOW fill: **Mirror Edges** covers the rest
  so the shot shows better in vertical. He leaves a UFC bar visible rather than zooming past it (banners opt-in only).
- **Motion Tile: Tile 100/100, Output Width 100, Output Height 150 (was 120), Mirror Edges ON.** On every tracked layer.
- Gaussian Blur appears only on a hand-made background copy of a clip (layer 70), not on tracked layers.

## Final form, 2026-10-11 (Seq01 Yan vs Merab, Sameer: "perfect") - this is what Stage 1 does now
- **No Time Remap anywhere** (he never uses it in Stage 1). Per-cut layers, source slid onto the cut.
- **Which person in a split screen = the one he framed in Premiere** (Position x<0 right half, x>1 left half; frac = 0.5 + (0.5W - posx*W) / (sw*scale/100)).
  Our first build ignored his Position and showed the wrong person on 15 clips; he caught it from the contact sheet.
- **No flipped-head line**: at ~188 % a 1080p source leaves only ~107 px of vertical slack, so nose height alone can't fix it.
  Scale goes up to ~205 % and the nose to the middle of the feasible band (Seq01: y 672 of 1920). Face = ~45 % of width.
- **Only the clips he names are tracked as B-roll** (4th B-roll, Merab standing); other B-roll / fights / stills are fill only.
- The comp goes on a **visible, empty track** (his V4 was muted -> comp never rendered).
