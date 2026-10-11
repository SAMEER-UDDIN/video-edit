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
