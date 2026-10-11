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

## Update 2026-10-06: one layer per scene
Sameer: "you dont need to make cut a clip unless scene is changing ... so the video looks in continuity instead of small cuts."
- In AE, **consecutive clips of the same camera shot are ONE layer**, not one layer per edit. Track the nose **continuously**
  through the scene's source footage; reproduce his Premiere cut with **Time Remap** (hold into each cut) so the picture
  stays in sync with his audio. Start a new layer only when the camera / scene / framing changes.
- His cut, order and audio are never changed for this. The jump cuts themselves stay (he chose to keep them over restoring
  the removed gaps).
