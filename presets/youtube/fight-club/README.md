# Fight Club: YouTube Shorts (UFC / MMA / boxing rivalry + news)

Channel preset for **Fight Club** (YouTube channel ID `UC5Jxh9Won8pDeGLZUK85BuQ`). Sameer edits for the
channel in **Premiere Pro 2025** (Boris Continuum installed). This README is the look, `PLAYBOOK.md` is the
per-short procedure, and `LESSONS.md` records what each job taught.

> **The source of truth is the notes in `docs/fight-club/`.** It holds
> `editing-style-guide.md` (the full measured style), `performance-analysis.md` (what goes viral),
> `shorts-catalog.md` (all 85 shorts) and `sequences/` (planned shorts). This folder turns that guide into
> the pipeline's numbers. If the two disagree, the memory folder wins; update this file to match.
> Never edit the memory files. Add new ones next to them instead.

## Format
| Spec | Value |
|---|---|
| Canvas | 1080×1920, **29.97 fps** (`30000/1001`) |
| Length | 25–40 s (best 30–40). Under 20 s flops |
| Cuts | Hard cuts on the word, a cut every ~2–2.5 s, **first cut by 1.5 s** |
| Accents | At most ~3 per short: a 1–2-frame zoom/directional blur in, or a 2–4-frame white flash on a big beat. No whoosh SFX |
| Loudness | **About −13 LUFS integrated** (channel range −11 to −16), dense, no silences ≥ 0.2 s |
| Structure | Cold open mid-sentence on the most inflammatory line. **Claim → counter → receipts.** Long face-tracked push-in on the payoff, then a hard end that loops |

## 🔒 Captions (the signature): `build.py`
- **Font:** Times New Roman **Bold**, ALL CAPS (`C:\Windows\Fonts\timesbd.ttf`). Sameer's shipped style
  (`newfinal.prtextstyle`) is TimesNewRomanPSMT **regular**; `FC_WEIGHT=regular` matches it exactly.
- **Size:** 66 px at 1080 wide (shrinks to fit 900 px, never wraps). Calibrated: 3.72 % of frame width per
  character at the held pose, vs 3.75 % measured on "Ryan Garcia Is A FAKE MEXICAN".
- **Position:** centred; held pose at **y≈990 (51.5 %)**, moving within 50–55 % during the pop. This lands exactly
  on the real captions in the reference short. Inside the y200–1620 safe band.
- **Phrasing:** 2–3 words (`MAX_WORDS=3`, `MAX_CHARS=16`), one line, each line holds until the next.
  A lone word only when it is the punch word.
- **Colour:** white `#FFFFFF`, soft black drop shadow (offset 0/4, blur 5, 85 %) plus a faint black glow
  (blur 14). **Exactly ONE keyword coloured, by meaning:**

  | Colour | Hex | Meaning | Examples |
  |---|---|---|---|
  | green | `#2EE65C` | money, weights, nationality, win/positive | `$40,000`, `146 POUNDS`, `MEXICAN`, `WIN`, `RESPECT`, `CHAMPION` |
  | red | `#FF2E2E` | violence, negative | `BLOOD`, `DEAD`, `CHEAT`, `LOSE`, `RUINED`, `SCARED` |
  | yellow | `#FFD60A` | `*CUES*`, non-English, CHAMP, some names | `*SPANISH*`, `*TEARS UP*`, `*LAUGHS*` |
  | cyan | `#24DEF2` | names / emphasis (first name in the rivalry) | `KHABIB'S FATHER`, `FACE OF BOXING` |
  | purple | `#CD48FF` | names / emphasis (the rival) | `NURMAGOMEDOV`, `HALF BLACK` |

  `--prep` picks the keyword automatically (priority: cue > red > green > names). **Always read the sheet and
  fix keywords by hand.** Meaning beats the lexicon. For example, the Garcia–Tank sequence makes `136` yellow
  and `147` green on purpose.
- **Pop**, read off `fightcaps.prfpset` ("fightclubcaps / Revised Light pop"), anchored at the frame centre:

  | t | Scale | Position y |
  |---|---|---|
  | 0.000 s | 100 % | 0.5000 |
  | 0.050 s | **107.6 %** | 0.4656 |
  | 0.367 s | 107.6 % | 0.4656 |
  | 0.383 s | **112 %** | 0.4479 (then holds) |

- **Ships as** a straight-alpha ProRes 4444 (`hf-graphics/captions/renders/captions-alpha.mov`) on Premiere
  **V5**, like every short-form caption layer in this repo. Nothing is burned in after the render.
- **Editable alternative:** Sameer's own Premiere presets still work if he wants live text. Apply
  `newfinal.prtextstyle` and then the `fightclubcaps` effect preset to each caption graphic (both in
  `assets/premiere-presets/`).

## Look (what Claude can't fully script; do it in Premiere)
- **Grade:** heavy "HDR edit": crushed blacks, strong vignette, very high clarity/sharpening, warm skin against
  teal/navy, pushed saturation, glowing faces (Boris Continuum). **Not** the repo's Autumn-Rec709 long-form look.
- **Reframe:** every talking head tight (face 40–60 % of width, eyes in the upper third). Constant
  face-tracked push-in of ~6–8 %/s, up to ~2.5× on the final payoff hold. The clip opens zoomed/blurred and
  settles in 2–3 frames.
- **Landscape B-roll:** a 16:9 strip in the middle, with a blurred zoomed copy filling top and bottom and thin
  white horizontal lines between them (sometimes black bars).
- **Red circle** callouts on the detail that proves the point.

## Audio
Slowed / slowed+reverb phonk or rap instrumental, ducked under the dialogue. Repeat winners: *Lose Yourself
(Instrumental)*, *BONES & Eddy Baker – LooseScrew*, *Egzod – Royalty*, *DISCIPLINE (Extremely Slowed +
Reverb)*, *EsDeeKid – Mist*. Credit the music in the description. Voice echo on dramatic beats uses
Sameer's `reverb.prfpset` ("Reverb Best": room 0.85, decay 0.20, wet 0.25, dry 0.20, width 0.70).

## Files
- [`build.py`](build.py): the caption builder (`--prep` / `--alpha` / `--preview` / `--test-bg`)
- [`PLAYBOOK.md`](PLAYBOOK.md): the per-short procedure
- [`LESSONS.md`](LESSONS.md): what each job taught
- [`test/garcia-tank-test.json`](test/garcia-tank-test.json): the look-test caption sheet
