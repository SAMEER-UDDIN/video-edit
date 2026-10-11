---
name: stage-3-1-creating-captions
description: "Stage 3.1 - Creating Captions: Sameer's captions for a Fight Club short he has already cut (after Stages 1-2). Transcribes the sequence's dialogue on the sequence timeline (WhisperX + a rescue pass for noisy audio), builds 3-4-word ALL-CAPS captions with no full stops or commas, loads them as a Premiere caption track, and hands over his part: upgrade to graphics, drag his 'newfinal' text style on, set position, colour one emphasis word per caption by hand (from a suggestion table). Triggers: stage 3, stage 3.1, captions, create captions, make captions, subtitle this short."
---

# Stage 3.1 - Creating Captions

His cut and audio are never touched. Captions are made **in Premiere**, styled with **his** text style.
First made on `Sequence 02 BACKUP` (Greg Hardy inhaler, 2026-10-07): job `projects/seq02-greg-hardy-inhaler/`.

## His rules (Seq02)
- **3–4 words per caption** (2 only where a sentence leaves no better split), **ALL CAPS**.
- **No full stops, no commas.** Question marks stay; apostrophes and hyphens stay. Swears censored (`F***`), say so.
- Caption = his text style **"newfinal"** (`assets/premiere-presets/newfinal.prtextstyle`, TimesNewRomanPSMT; it's already a
  Text Style item in his project). Mid-frame (style guide § 2: ~50–58 % height).
- **One emphasis word per caption coloured by meaning, done BY HIM** (Premiere can't colour words by script). Give him the table.
- Don't save one-off wording corrections he makes (e.g. "USADA approved") as rules unless he asks.

## Procedure

### 0. Read state
The sequence he names (read it fresh: he moves things around — Seq02 BACKUP had the short at 0–29.78 s and parked clips at 186 s+).
Find the short's range (V1 clip(s) + A1 dialogue under it).

### 1. Sequence audio
`python .claude/skills/stage-3-1-creating-captions/scripts/sequence_audio.py "<sequence>" projects/<job> --from 0 --to <end>`
→ `captions/seq-audio.wav` (A1 clips mixed at their sequence positions, 16 kHz mono).

### 2. Words (with the rescue pass)
`"%USERPROFILE%\.cache\video-editor\whisperx-venv\Scripts\python.exe" .claude/skills/stage-3-1-creating-captions/scripts/transcribe_words.py projects/<job>`
→ `captions/words.json`. Any stretch of speech-level audio with no words (Seq02's noisy fight-corner section) is re-heard
twice (beam 5 / beam 1, VAD off); only matching text is kept and force-aligned. **Rescued lines are marked `[ ]` — read
them back to him as "please check"** (Seq02's rescue heard "auto-approved"; it was "USADA approved").

### 3. Captions + emphasis table
`python .claude/skills/stage-3-1-creating-captions/scripts/make_captions.py projects/<job>`
→ `captions/captions.srt`, `captions.json`, `emphasis-words.md`. Read the caption list once for bad breaks or wrong words
(names!) and fix `words.json` if needed, then re-run. Review the emphasis table **by meaning** (the lexicon only proposes):
one word per caption at most; plain filler captions stay white.

### 4. Into Premiere
ES via the premiere-pro MCP: import the SRT into a bin (`stage3-captions`; use a NEW file name if re-importing — Premiere
caches by path), then `seq.createCaptionTrack(srtItem, <short start>, Sequence.CAPTION_FORMAT_SUBTITLE)` → `true`.
Scripting can't edit, restyle or delete caption tracks: a fix = a new SRT → a new track, and he deletes the old one.

### 5. Hand over — his part, exact clicks
1. Right-click the caption track ▸ **Upgrade Captions to Graphics** (he does this; the captions become graphic clips on V2).
2. Keep them all selected; in the **Project** panel search **newfinal** and **drag it onto one of the selected graphics** →
   all get the style (fallback: Essential Graphics ▸ Edit ▸ text layer ▸ Styles ▸ newfinal).
3. With all selected: **Properties ▸ Transform ▸ Position** to mid-frame if needed.
4. Colour the emphasis words from the table: double-click the caption in the Program monitor, select the word, change **Fill**.
Then verify from a short Premiere export (`exportAsMediaDirect` with in/out, backslash paths): font serif, position
mid-frame, nothing clipped, words match the sheet. (Graphic text can't be read by script — compare rendered frames.)

## Gotchas (Seq02)
- faster-whisper's own word timestamps were ~0.4 s off; WhisperX alignment is the timing source.
- `importFiles` of a `.prtextstyle` adds nothing if the style is already in the project (it was: item "newfinal", type 5).
- After "Upgrade Captions to Graphics", the caption tracks look empty and V2 holds one Graphic per caption — that's expected.
