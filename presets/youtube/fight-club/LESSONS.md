# Fight Club: lessons (lesson → change made → file)

- **2026-10-05 · setup.** Caption height was first authored at 55 % (the middle of the guide's 50–58 % band). Overlaid
  on "Ryan Garcia Is A FAKE MEXICAN", the real captions sit at ~51 %. → `CAP_BASE_Y` 1110 → 1050 (held pose 51.5 %),
  verified exactly on top of the real captions. → `build.py`
- **2026-10-05 · setup.** Sameer's shipped caption font is TimesNewRomanPSMT *regular*, not bold. He asked for bold.
  → bold default, `FC_WEIGHT=regular` switch. Confirm with him on the first real job. → `build.py`, `README.md`
- **2026-10-06 · Sequence 02.** Sameer's own head-tracking method (from his AE project): Stabilize-type point track on the
  **nose**, Position-only → Anchor Point keys, constant Position; each new clip's nose Position = the previous clip's; **no
  zooms, no push-ins, no blur**; scale just enough (≈187 % for 1080p); Motion Tile Output 100/120 + Mirror Edges. → My first
  Seq02 pass (face-box centre, 7 %/s push-in, impact blur, Motion Tile 300 %) does NOT match it. → Full method:
  `docs/fight-club/headtracking-method.md` (overrides style guide § 4 for tracking).
- **2026-10-07 · Sequence 02 Stage 2.** Sameer hand-deepened Claude's zooms: zoom-ins 0.80→0.70/0.60, payoff 0.66→0.56,
  zoom-outs start 0.82→0.68/0.71, faster zoom-in starts. → Recorded in `blurmo-transitions-method.md`; skill defaults
  pending his OK. → `.claude/skills/stage-2-zooms-transitions/scripts/plan_zooms.py`
- **2026-10-07 · Sequence 02 Stage 3.** Sameer: captions without full stops or commas (question marks stay), 3-4 words per
  caption, his Track Style "newfinal". → `projects/seq02-greg-hardy-inhaler/make_captions.py` strips them; carry into the Stage 3 skill.

## Stage 1, 2026-10-11 (Seq01 Yan vs Merab)
- A Premiere track that is muted/hidden (V4 here) never renders a linked comp: check `track.isMuted()` before overwriteClip; use a visible free track.
- Split-screen shots (two people in one frame): the first-frame seed can latch the centre graphic. Seeding now honours `prefer_x` strictly (+ `prefer_x_clip` per clip).
- Skipped (B-roll) layers keep the Motion Tile effect; a still must not get Time Remap.
- Split-screen source + the editor's Premiere crop: read his Motion Position per V1 clip (x<0 / x>1 = right / left half) and set `prefer_x_clip` from it, or the tracker shows the wrong person.
- No Time Remap in Stage 1 (Sameer): per-cut layers are the source slid by `tin - src_in`.
- Mirror-Edge flipped head at the top: a face low in the frame + 1080p source at ~188 % leaves only ~107 px of vertical slack, so no nose height clears both edges. Raise scale to ~205 % and put the nose at the middle of the feasible band (here y 672) - compute it from the anchor keys (top: ny <= min_ay*k; bottom: ny >= 1920-(sh-max_ay)*k).

## Stage 2, 2026-10-11 (Seq01)
- Variant A is the real workflow: render Stage 1, put it in the same comp, split one plain adjustment layer at the PICTURE-change frames (razor + 1), he labels, split the render at his layers, then Time Remap away the Premiere Morph Cut blend (keep <= p-3 of the old clip, >= p+2 of the new).
- Smooth > flashy: short layers get shallow zooms, back-to-back flashes get low peaks (+9), the hook gets the intense drop curve, a late snap-in is the Orange 3-key. White-solid flash must DECAY (out -5485/3.1 %, in 0/73.8 %), not fade linearly.
- Never test scripts in his own hand-made .aep: use the Sandbox project and a throwaway comp (a test comp was briefly built in `calude islamvsaa.aep` by mistake and removed).
