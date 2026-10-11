# Sameer's Stage 2: BlurMo Curves zooms + Brightness transitions (learned Oct 6, 2026)

Source: Sameer's explanation and his AE project `D:\1.aep`, comp **fightcluB Linked Comp 09** (1080×1920, 60 fps, 30.13 s, footage
`1sameer.mp4`, Francis Ngannou short). Read with an import into a sandbox project; his file was never opened or changed.

## Structure
- **One adjustment layer per segment** on top of the footage, spanning the segment **exactly** (in = segment start, out = segment
  end = the next cut). A segment can cover more than one footage piece (e.g. 10.80–14.38 s spans two pieces).
- Comp 09 had **12 segments in 30 s** (0.87–5.92 s long, most 1.2–3.5 s), so a new zoom roughly every 2.5 s.
- Transitions sit on **separate adjustment layers** ("Adjustment Layer 2"), one per transition.

## Zoom: Sapphire `S_BlurMoCurves` on each segment's adjustment layer
- **All parameters at their defaults** (Effect = Transform and Blur, Shutter Duration 1, Exposure Bias 0.5, Blur Res Full,
  Subpixel on, Wrap X/Y = No, Mask Use Luma, Blur Mask 12). Only **Center XY** and **Z Dist** are keyframed: 2 keys, at the
  segment's first and last frame (one segment had a 3rd key one frame before the end).
- **Z Dist 1.0 = no zoom; lower = zoomed in.** Values used: 0.66–0.86.
- **Two moves, alternating through the video:**
  - **Push-in:** 1.0 → 0.70–0.85 (e.g. 1 → 0.809, 1 → 0.745, 1 → 0.702, last big one 1 → 0.660).
  - **Release:** starts zoomed in (0.685–0.86) → 1.0.
  Order in Comp 09: release, in, release, in, release, in, in, release, in, release, in, release.
- **Continuity across cuts:** a push-in usually ends zoomed in and the next segment starts zoomed in at a similar value
  (0.809 → 0.859, 0.845 → 0.746, 0.745 → 0.804, 0.702 → 0.746, 0.660 → 0.764), then releases. So the zoom **flows through
  the cut**. A release that ends at 1.0 is followed by a push-in starting at 1.0.
- **Strength builds:** the first zoom is strong (0.685, the hook), the deepest is the payoff near the end (1 → 0.660).
- **Curve (graph editor):** Bezier keys, Easy Ease applied and then hand-tuned. The ends keep velocity (key influence only 2–8 %,
  speeds ≈ 0.3–1.2 units/s at both ends, up to 3.5 on a fast one), so the zoom is **fast at the cut, slow in the middle,
  fast again into the next cut** (an S/whip shape). In the graph it rises steeply, flattens, then steepens again.
- **Center XY = the subject:** usually frame centre (540, 960); on the subject when it's off-centre (601.8, 828.2;
  1055, 679.8; 634.8, 708.7; 622.4, 593.3). Constant within a segment.

## Transitions: `BCC Brightness-Contrast` on its own adjustment layer at a cut
- Only **Brightness** is animated; everything else default. Keys are **linear**. **The peak lands exactly on the cut frame.**
- **Dark:** 0 → **−30** over 10 frames (0.167 s @ 60 fps) → 0 over 5 frames (0.083 s). (He says −23 to −30.)
- **Bright / camera flash:** 0 → **+25** over 10–13 frames → 0 over 5 frames. (He says +20; Comp 09 used 25.)
- The transition layer spans about 0.47 s before the peak to 0.42 s after.
- **Comp 09:** 8 transitions on 11 cuts, **strictly alternating** dark, bright, dark, bright… (1.93 dark, 4.22 bright,
  8.52 dark, 14.38 bright, 15.57 dark, 21.48 bright, 24.95 dark, 29.20 bright).

## Applied: Sequence 02 (Oct 6, 2026)
- Picked by Sameer: Comp 09 rhythm (extra zoom splits inside long segments, placed on his existing jump cuts), transitions **by mood**
  (dark = tension / negative / a deflating twist; flash = outburst, reveal, the camera turning to someone, the receipt),
  flash **+25**, dark **−30**.
- Transitions and zoom boundaries go on the **actual picture-change frame** in the footage as After Effects reads it, not on the
  razor mark (his 2_2.mp4 changed picture 2–3 frames after the razor).
- **Correction (same day): one zoom per cut Sameer made in Premiere — no extra "mini zooms".** He labels each cut layer in AE:
  **Green = zoom in, Purple = zoom out** (AE labels 9 and 10). Read the labels; never invent the direction.

## Sameer's own tuning of the Seq02 build (read back Oct 7, 2026)
After Claude's build he deepened the zooms by hand in "Seq02 V1 Cuts":
- Zoom-ins: 1 → **0.70** (cut 2), 1 → **0.60** (cut 4), payoff 1 → **0.56** (cut 6). Claude had 0.80 / 0.80 / 0.66.
- Zoom-outs: start **0.68** (cut 3), **0.71** (cut 5). Claude had 0.82 / 0.82. The hook (cut 1) stayed 0.70 → 1.
- Faster starts on the zoom-ins (out speed −0.99 and −1.11 vs −0.57 / −0.21).
- Some zoom adjustment layers snapped back to his razor positions (e.g. 5.017–7.483).
→ Seq02 says: **zooms ~0.56–0.71 deep, not 0.80**. Treat as the reference until he says otherwise.

## Learned 2026-10-11 from "fightclubtestingphase Linked Comp 01" (Islam / Burroughs / Magomedov short, 60 fps, 40 s) - SUPERSEDES the depths and transitions above
Read from his AE project (enabled layers only). Footage = his Stage-1 render `2.mp4` cut into 24 pieces; 21 zoom adjustment layers, 19 flashes.
- **Zoom layers:** one `S_BlurMoCurves` adjustment layer per cut piece, exactly cut-to-cut; Z Dist keys on the first frame (sometimes 1 frame
  before) and the LAST frame (out-1). Defaults otherwise. **Zoom-in ends 0.715-0.77 (mean 0.74); zoom-out starts 0.715-0.79 (mean 0.75)** - NOT
  0.56-0.71 like Seq02. The first cut is a **hook zoom-out starting 0.64** with a whip (out speed 14.4, influence 1 %) and a soft landing (in influence 56 %).
  Direction is the editor's call (no Green/Purple labels were set in this comp: label 5 everywhere), sequence from the start:
  out, in, in, out, in, in, out, out, in, in, in, out, in, in, in, out, in, out, out(+kick), in(+Film Damage), out.
- **Ease (20 zooms):** zoom-in out speed = 4.5x the average slope / influence 6-13 % (mean 9), in speed = 2.6x / 9-19 % (mean 15). Zoom-out out =
  3.8x / 9-13 %, in = 3.5x / 9-14 %. So: fast kick at the cut, softer landing. Short segments (< 1 s) use the larger multiples.
- **Center XY = the FACE** in that piece (537,590 / 502,590 / 509,524 / 350,614 ... y 427-614 in a frame whose nose sits ~y 530); 540,960 where there
  is no face (B-roll, a few cuts); one B-roll centre 554,1199. Constant per segment.
- **Transitions are ALL bright, never dark here:** `BCC Brightness-Contrast`, Brightness 3 LINEAR keys: **cut-14 frames = 0, cut = +19..+30 (mean ~24), cut+15 = 0**
  (60 fps; 0.23 s up, 0.25 s down), peak ON the cut frame, layer 145 frames = from cut-52 to cut+93. **19 of the 20 cuts have one** (every cut but the one
  that has the white-solid flash).
- **White-solid camera flash** (hard impact cut, replaces the brightness flash on that cut): a 1080x1920 white solid, layer from cut-1 to cut+75 frames,
  Opacity 100 on the cut frame -> 0 25 frames later (Bezier/easy ease). At 14.65 s, the cut just before a B-roll.
- **Wide-B-roll look** (3.77-5.77 s wrestling clip): 4 layers - the 2.mp4 piece masked to a band (rectangle y 346-1571, i.e. 18-82 % of the height,
  x past both sides), the same piece at **163.8 % with Gaussian Blur 25** behind it (also masked), and two white solids scaled to ~1.26 % tall (about 24 px)
  at y 349 and y 1564 as thin lines on the band edges. Used only on WIDE B-roll that doesn't fit vertical; he names which clips.
- Extras seen (not part of the stage unless he asks): a red circle PNG with Drop Shadow tracking a face at one cut (7.45-8.97 s), and Sapphire
  Film Damage on the last zoom layer.
- **Decisions he gave (Q&A, 2026-10-11):** bright only; solid flash only on a hard impact cut he names; band look only on the wide clips he names;
  zoom direction = he labels Green/Purple, Claude reads them.

### Other BlurMo curve types he uses (2026-10-11, measured on Linked Comp 01 layers 42 and 6)
- **Intense DROP curve (mostly the FIRST clip):** hook zoom-out 0.639 -> 1.0 over the whole 145-frame segment, but the first key's out speed is 14.36 with
  **0.6 % influence** and the last key's in influence is 55.6 %. Result: 0.639 -> 0.745 in 6 frames, 0.818 by frame 18, 0.90 by 42, then a long soft settle to 1.0
  (almost all the move happens in the first ~0.3 s, then it drifts). It is a whip/snap, not the usual S-curve.
- **3-key layer** (layer 6, a long 4.4 s segment): keys at frame 0 / 202 / 264 (relative): **0.741 -> 1.0 -> 0.755**. Leg 1 is a slow, almost linear zoom-out
  (out 0.33/11.7 %, in 0.31/12.7 %). At the middle key (77 % of the segment) the out speed is **-14.39 with 1 % influence** = a drop-curve zoom-IN: 1.0 -> 0.941 in 2 frames,
  0.80 by +26 frames, landing at 0.755 on the cut (last key in 0/50 %). Center XY also has 3 (equal) keys. The next segment then starts again at ~1.0.
  Use: a long segment where the release should be followed by a hit/emphasis zoom just before the cut.
- Both are the SAME ingredient: a key with out speed +/-14.4 and ~1 % influence (a snap) followed by a long low-speed settle. Stage 2: `plan_zooms.py --curve "<cut>:drop"` /
  `"<cut>:drop3@0.77"`; cut 1 Purple is `drop` by default.
- **Confirmed by Sameer (2026-10-11):** the 3-key curve means "the zoom releases, then snaps back in before the cut"; **he names which cuts get it** (Claude never picks them).

### Sameer's smoothing rules (2026-10-11, after reviewing the Seq01 Stage 2 build) - SUPERSEDE the fixed +25 / full-depth defaults
- **Short adjustment layers get SUBTLE zooms** ("the scene changes quickly; an intense zoom feels unpleasant"). Long layers (>= ~1.8 s) were perfect as built.
  Implemented as: depth scaled by k = clamp((len - 0.6) / 1.2, 0.35, 1) and a softer ease (influence + up to 14 / 10 %). e.g. 0.72 s: 1 -> 0.91; 1.35 s: 1 -> 0.84; 2+ s: 1 -> 0.74.
  The first-clip hook (intense drop curve) and the 3-key layer stay intense.
- **Brightness flashes get LOWER when they occur back to back** ("I want a smooth transition into different cuts, not to flash my viewer"). Peak = +25 x clamp((gap - 0.5) / 2, 0.35, 1),
  gap = seconds to the nearest neighbouring transition: isolated (>= 2.5 s) +25, ~1 s apart about +9. The starting value (+25) was right for isolated cuts.
- **ORANGE label (11) = the 3-key curve** (release, then snap back in before the cut); Green 9 = in, Purple 10 = out. He merged two layers into one orange layer (2058-2291) for it.
- **White-solid camera flash replaces the brightness flash on the cut into a B-roll he points at** (the PNG B-roll at 6.0 s): pure white on the cut frame, ~25 frames fade, layer cut-1..cut+75.

### Learned 2026-10-11 (Seq01): his white-solid camera flash at 6 s, and the white lines on a baked-blur B-roll
- **Camera flash he hand-tuned (white solid, cut-1 .. cut+75, Opacity 100 on the cut -> 0 at +25):** key 1 out speed **-5485.5 with 3.1 % influence**, key 2 in speed 0 with **73.8 %** influence.
  Result: pure white on the cut frame, 64 % on the next frame, 50 % at +2, 27 % at +5, 11 % at +10, 4 % at +15, gone by +24 = a pop that decays exponentially (my first easy-ease version faded linearly and read as a fade, not a flash).
  Use it for every white-solid flash (`--transitions "<seg>:solid"`); it replaces the brightness flash on that cut (6 s, the cut into the portrait B-roll).
- **Lines only (31 s fight B-roll):** Premiere had already baked the blurred-background band into 2.mp4 (sharp band y 257-1658 of 1920, blurred strips above/below). He wants just the two thin white lines
  on the band edges: 24 px (1080x1920 white solid, Scale Y 1.26 %), top centre = edge + 3 (y 260), bottom centre = edge - 7 (y 1651), spanning the B-roll's piece (1864-1993 f), **placed directly above that
  2.mp4 piece, below the zoom adjustment layers** so they zoom with the picture. Measure the edges with `band_edges.py <video> <t...>` (top edge is stable, the bottom can under-read on dark frames - check a crop).
  CLI: `plan_zooms.py ... --lines "<segment>:<top>-<bottom>"`. (The full band + blurred-copy + lines build, `--bands`, is only for B-roll whose blur is NOT already in the render.)

## Final form, 2026-10-11 (Seq01, Sameer: "perfect") - what Stage 2 does now
Flow: Stage 1 render (2.mp4) in the Stage 1 comp under one plain adjustment layer -> `detect_cuts.py` (picture frame = razor+1, Morph Cut blend p-3..p+2) -> `prep_stage2.py` scripts:
split the adjustment layer at the picture frames -> **he labels Green / Purple / Orange** (and merges weak cuts) -> `read-layers.jsx` -> split the render at his layers -> **Time Remap every piece to cut the
Morph Cut blend** (head = first clean frame, tail = last clean frame of the old clip, ~3 % stretch; his own remapped pieces are skipped) -> `plan_zooms.py --layers` -> `build_zooms.py`.
Rules baked in: zoom-in 1 -> 0.74 / zoom-out 0.75 -> 1; first clip = intense drop curve (0.64); **short layers subtle**; Orange = 3-key (release, snap back in); **brightness flash on every segment start,
+25 smoothed lower when back to back**; **white-solid camera flash with his decay curve on the cut(s) he names**; **white edge lines on a baked-blur B-roll he names**; Center XY = the Stage 1 nose (540,672), 540,960
on B-roll with no face. His Seq01 numbers: 22 labelled layers, 20 flashes (+8.8..+21.9), 1 solid flash (6 s), 1 line B-roll (31 s), 26 remapped pieces.
