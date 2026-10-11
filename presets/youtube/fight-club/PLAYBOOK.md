# Fight Club: per-short playbook

Run the normal eight-step line (`CLAUDE.md` § The Pipeline, owned by `edit-video`). The finish is **Premiere**
(`lane=premiere`). Only the points below differ for this channel.

## Step 0: before anything
1. Read `docs/fight-club/README.md`, then `editing-style-guide.md`, then the short's plan in
   `projects/sequences/` if one exists (for example `2026-10-05_garcia-tank-147.md`).
2. Check `performance-analysis.md`: is there a news peg within ~24 h? Is this angle already at ~3 shorts?
   If so, say so before building.
3. Source clips usually arrive through IDM in `your downloads folder`. Copy them (never move) into
   `projects/<job>/raw/`. Name the job after the story, e.g. `tank-wont-come-to-147`.

## Step 2: rough cut
- **This is a multi-source montage, not one talking head.** The sequence plan's beat table is the EDL
  intent: each beat is a clip with an in/out. Transcribe each source once, pick the lines the plan names,
  and assemble in beat order.
- Hook = the plan's beat 1, starting **mid-sentence**. First cut by **1.5 s**. Average shot ~2.2–2.6 s.
- Kill every silence ≥ 0.2 s. The channel's dialogue is wall-to-wall.

## Step 3: audio
- Run the house chain as usual (`audio-polish.py`), then lay the music bed (the `background-music` pass is
  **always on** for this channel: slowed instrumental, ducked under the voice).
- **Channel master target: −13 LUFS integrated** (house chain + music lands lower, so add a final gain into a
  −1 dBTP limiter on the master in Premiere). Verify on the export:
  `ffmpeg -hide_banner -nostats -i <final>.mp4 -af ebur128=peak=true -f null -` → expect I ≈ −13 (−12 to −14).
- `reverb.prfpset` on the voice only on 1–2 dramatic echo beats, never throughout.

## Step 4: grade
Not the long-form Autumn-Rec709 lock. Sameer's Boris Continuum HDR look (see README § Look) is applied by
hand in Premiere, or with a BCC preset he names. Ask once which preset he uses and record it in `LESSONS.md`.

## Step 5: graphics + captions
1. `uv run presets/youtube/fight-club/build.py projects/<job> --prep` writes `projects/<job>/captions.fight-club.json`.
2. **Edit the sheet:** 2–3 words per line, ONE `key` per line, `color` by meaning (README table). Use the sequence
   plan's caption column wherever it exists. Add `*CUES*` for non-English or reactions.
3. Look-check: `uv run presets/youtube/fight-club/build.py projects/<job> --preview projects/<job>/outputs/<job>.mp4`
4. Ship: `uv run presets/youtube/fight-club/build.py projects/<job> --alpha` → place on **V5**
   (`lanes/premiere/place-graphics.py`).
5. Other graphics for this channel: text cards (e.g. "10 lb REHYDRATION CLAUSE"), number swaps (140 → 144),
   red circles, and blurred-fill strips for landscape B-roll. Build these in **After Effects** through the
   `after-effects` MCP when they need motion, or in Premiere directly.

## Step 6: SFX
Usually none. The channel cuts on dialogue, not whooshes. Only white-flash beats may get an impact.

## Step 8: export
1080×1920 H.264, 29.97 fps, AAC 48 kHz, about −13 LUFS. Verify with ffprobe and ebur128 before handing it over.

## After the job
Append to `LESSONS.md` (*lesson → change made → file*), and add the new short to the catalog **as a new file**
in `docs/fight-club/` (never edit the existing memory files).
