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
