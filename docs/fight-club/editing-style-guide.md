# Fight Club — Editing Style Guide (learned from the shorts)

> Source: frame-by-frame analysis (ffmpeg + OpenCV, every frame at 29.97 fps) of 30 shorts (the top 15 and bottom 15 by views), plus Sameer's own Premiere presets (`fightcaps.prfpset`, `newfinal.prtextstyle`, `reverb.prfpset`). Analyzed Oct 5, 2026.
> Channel: "Fight Club" (UC5Jxh9Won8pDeGLZUK85BuQ). Sameer is an **editor** on the channel; owner contact is in the descriptions.

## 1. Format at a glance
| Spec | Value |
|---|---|
| Canvas | 1080×1920 vertical (Studio download comes out as 720×1280), 29.97 fps |
| Length | 20–42 s. Top-15 median **32.5 s**, bottom-15 median 26.6 s. Best performers: 24–41 s |
| Cut rhythm | Median shot length **~2.2–2.6 s**, 9–17 cuts per short. First cut lands within **0.7–1.8 s** on the best ones |
| Loudness | −11 to −16 LUFS integrated (median −13.6). LRA 1.4–4.4 (compressed, dense) |
| Structure | Cold open mid-sentence. No intro, no logo, no outro, no CTA |

## 2. Captions (the signature look)
- **Font:** bold, all-caps **serif** (Times New Roman–style). This serif look sets the channel apart from the usual Montserrat/Komika caption style.
- **Size/position:** small to medium, centered horizontally, **vertically at ~50–58% of frame height** (chest/mic level, *not* the bottom third). Measured white-pixel density peaks in the 50–60% band.
- **Words per caption:** 2–3 words (rarely 4), one line, replaced on every phrase, so the text changes about every 0.3–0.6 s.
- **Color:** white with a soft dark drop shadow/glow. **One keyword per caption is color-highlighted**, and the color carries meaning:
  - **Green**: money, nationality, positive/"win" words, weights (e.g. `$40,000`, `MEXICAN`, `146 POUNDS`, `WIN`, `RESPECT`)
  - **Yellow/gold**: non-English or sound cues in asterisks (`*SPANISH*`, `*TEARS UP*`), names, "CHAMP"
  - **Red**: violence/negative (`BLOOD`, `DEAD`, `CHEAT`, `LOSE`, `RUINED`)
  - **Cyan/teal and purple/magenta**: names and emphasis (`KHABIB'S FATHER`, `NURMAGOMEDOV`)
- **Bracketed cues:** `*SPANISH*`, `*TEARS UP*`, `*LAUGHS*` in yellow when the speaker isn't speaking English or is reacting.
- **Animation:** the preset "fightclubcaps / Revised Light pop" on the graphic group:
  - frame 0: scale 100%, y = 0.500
  - +0.05 s (≈1.5 frames): **scale 107.6%, y = 0.466** (pops up and in)
  - hold until +0.367 s
  - +0.383 s: scale 112%, y = 0.448 (second nudge before the next caption)
  - Result: each caption **pops ~8% bigger and slides up slightly** the instant it appears.
- Some early July shorts ("Conor Is About To DESTROY Max", "Conor is in his PRIME now", "Conor SLAPPED Max") had **no captions**, only a faint "Fight Club" script watermark, and all three flopped. Every short checked from mid-July on has captions, including all 15 hits.

## 3. Color grade / look
- Heavy, "HDR edit" look: **crushed blacks, strong vignette, very high clarity/sharpening** (skin texture and beard hairs look etched), warm/orange skin against teal/navy backgrounds.
- Saturation is pushed. Faces glow (bright skin highlights), and the backgrounds fall off into the dark vignette.
- Boris Continuum (BCC 2026) is installed on Sameer's machine, so it's the likely source of the glow/sharpen/film looks.

## 4. Reframing, zoom and head tracking
- **Every talking head is reframed tight**: face fills ~40–60% of the frame width, eyes in the upper third. Wide press-conference shots get cropped to a single speaker.
- **Constant slow push-in** on talking heads (face-tracked): about 0.2–0.3% scale per frame (≈6–8%/s). On long climactic holds it keeps going: the final 12 s of "Ryan Garcia Is A FAKE MEXICAN" pushes **~2.5×** into Ryan's face while keeping it centered (keyframed head tracking).
- The clip **opens already zoomed/blurred** and settles in 2–3 frames (impact zoom-out), e.g. #1 "Conor Benn SHUTS UP Ryan Garcia" frame 0.
- **Landscape footage** (fight footage, wide shots) goes in as a 16:9 strip in the middle, with a **blurred, zoomed copy filling the top and bottom** separated by **thin white horizontal lines**. Sometimes the bars are black instead.
- **Red circle** annotation to point at a detail (Khabib on the phone, the fighter on the canvas).

## 5. Transitions
- **About 85–90% are hard cuts on the word**: a cut lands on the speaker change or on the noun the B-roll illustrates.
- Accents, used sparingly (top shorts average ~1 blur event per 10 s; flops ~2.7 per 10 s, so *less is more*):
  - **1–2-frame directional/zoom (radial) blur** entering the new shot (e.g. Paddy short at 6.5 s, Garcia short at 4.0 s).
  - **White flash/exposure flash** of 2–4 frames on a big beat (Garcia short at 9.2 s; top shorts have ~3 flashes each, flops ~1).
  - Short cross-blur/dissolve (1 frame) between related shots.
- No SFX whooshes on cuts (audio hits line up with cuts <10% of the time). Cuts follow the dialogue, not sound effects.

## 6. Sequencing / story structure (most important)
Winning template = **Claim → Counter → Receipts/Payoff**:
1. **Hook (0–2 s):** start mid-sentence on the most provocative line, often from the antagonist ("You're son ain't gonna knock me out", "$40,000 for me", "That is probably the most ridiculous rule").
2. **Back-and-forth:** alternate the two sides of the rivalry every 1.5–3 s (Garcia ↔ Benn, DC ↔ Bisping). Press-conference audio is the spine.
3. **Literal B-roll on keywords:** when a speaker names a thing, cut to it for 1–2 s (says "jumped on the cage" → shot of him on the cage; "blood" → bloody fight still; "Mexican" → Ryan in front of the Mexican flag).
4. **Payoff/receipts at the end:** the weigh-in number, the KO, the belt, the emotional reaction. The last 5–12 s is one long tracked push-in on the winner's face or the proof moment, then the video ends abruptly (good for loops).
- Talking-head commentators (DC, Bisping, Rogan clips, podcasters) work as a "narrator" between event clips.

## 7. Audio
- Background music: an instrumental, often **slowed/slowed+reverb phonk or rap instrumental**, ducked under dialogue. Repeat winners: *Lose Yourself (Instrumental)*, *BONES & Eddy Baker – LooseScrew*, *Egzod – Royalty*, *DISCIPLINE (Extremely Slowed + Reverb)*, *EsDeeKid – Mist*.
- Music is credited in every description ("Music Name: …").
- Reverb preset "Reverb Best" (Studio Reverb): room size 0.85, decay 0.20, wet 0.25, dry 0.20, damping/diffusion 0.59, width 0.70, HF cut 0.70, LF cut 0.20. Used on the voice for dramatic echo moments.
- Dialogue is kept dense with almost no silence gaps (0 silences ≥0.2 s in most shorts).

## 8. Packaging
- **Title:** `[Name] [CAPS VERB/ADJ] [Name/Object] [?!] [2 emojis]`, e.g. "Conor Benn SHUTS UP Ryan Garcia 😳🥶". One or two words in CAPS, frequent 😳.
- **Description:** disclaimer → music credit → business email → line separator → 2–3 sentence story recap with emojis → separator.

## 9. Checklist for a new short
- [ ] Hook line in the first frame, first cut by 1.5 s
- [ ] Rivalry back-and-forth, with a cut every 2–2.5 s
- [ ] Serif all-caps captions at mid-frame, 2–3 words, 1 colored keyword, pop preset
- [ ] Tight face reframe with a slow push-in; landscape B-roll in a blurred-fill strip with white lines
- [ ] Hard cuts on words, max ~3 blur/flash accents
- [ ] Payoff/receipt at the end with a long push-in
- [ ] 25–40 s, about −13 LUFS, slowed instrumental bed
