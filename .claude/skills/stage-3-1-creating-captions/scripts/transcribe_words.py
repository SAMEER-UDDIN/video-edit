"""Step 2: word timings for the captions, on the sequence timeline -> <job>/captions/words.json.

Run with the WhisperX venv's python (built by the repo's rough-cut transcriber):
  "%USERPROFILE%\.cache\video-editor\whisperx-venv\Scripts\python.exe" .claude/skills/stage-3-1-creating-captions/scripts/transcribe_words.py projects/<job>

1. WhisperX large-v3 transcribe + wav2vec2 alignment of captions/seq-audio.wav (GPU if it works, else CPU int8).
2. RESCUE PASS (Seq02 lesson: noisy fight-corner audio got NO words): every stretch >= 1.5 s with speech-level audio and no
   words is re-transcribed with faster-whisper, VAD off, beam 5 and beam 1; only text both passes agree on is kept, and it is
   force-aligned with wav2vec2 (faster-whisper's own word times ran ~0.4 s off). Rescued text is flagged in the output so it
   gets a human check.
Writes [{"w","s","e","rescued"}] and prints the transcript with rescued parts marked.
"""
import json, os, sys
import numpy as np, whisperx

job = os.path.abspath(sys.argv[1]); cap = os.path.join(job, "captions")
wav = os.path.join(cap, "seq-audio.wav")
audio = whisperx.load_audio(wav); SR = 16000
dev, ct = "cuda", "float16"
try:
    model = whisperx.load_model("large-v3", dev, compute_type=ct, language="en")
    res = model.transcribe(audio, batch_size=8, language="en")
except Exception:
    dev, ct = "cpu", "int8"
    model = whisperx.load_model("large-v3", dev, compute_type=ct, language="en")
    res = model.transcribe(audio, batch_size=8, language="en")
am, md = whisperx.load_align_model(language_code="en", device=dev)
al = whisperx.align(res["segments"], am, md, audio, dev)
words = [{"w": x["word"], "s": x.get("start"), "e": x.get("end"), "rescued": False} for s in al["segments"] for x in s.get("words", [])]

# speech-level audio without words -> rescue windows
hop = int(0.05 * SR); rms = np.array([np.sqrt(np.mean(audio[i:i + hop] ** 2)) + 1e-9 for i in range(0, len(audio), hop)])
db = 20 * np.log10(rms); loud = db > (np.median(db) - 6)
covered = np.zeros(len(db), bool)
for w in words:
    if w["s"] is not None: covered[int(w["s"] / 0.05):int((w["e"] or w["s"] + 0.2) / 0.05) + 1] = True
gaps, start = [], None
for i, (l, c) in enumerate(zip(loud, covered)):
    if l and not c: start = i if start is None else start
    else:
        if start is not None and i - start >= 30: gaps.append((start * 0.05, i * 0.05))
        start = None
if start is not None and len(db) - start >= 30: gaps.append((start * 0.05, len(db) * 0.05))
if gaps:
    from faster_whisper import WhisperModel
    fw = WhisperModel("large-v3", device="cpu", compute_type="int8")
    for g0, g1 in gaps:
        seg = audio[int(g0 * SR):int(g1 * SR)]
        texts = []
        for beam in (5, 1):
            s, _ = fw.transcribe(seg, language="en", vad_filter=False, beam_size=beam, condition_on_previous_text=False, temperature=0)
            texts.append(" ".join(x.text.strip() for x in s).strip())
        a, b = texts[0].split(), texts[1].split()
        norm = lambda t: "".join(ch for ch in t.lower() if ch.isalnum())
        if not a or [norm(x) for x in a] != [norm(x) for x in b]:
            print(f"RESCUE {g0:.2f}-{g1:.2f}: passes disagree -> NOT captioned, check by ear: {texts}"); continue
        r = whisperx.align([{"text": texts[0], "start": 0.0, "end": g1 - g0}], am, md, seg, dev)
        for s2 in r["segments"]:
            for x in s2.get("words", []):
                words.append({"w": x["word"], "s": None if x.get("start") is None else x["start"] + g0,
                              "e": None if x.get("end") is None else x["end"] + g0, "rescued": True})
        print(f"RESCUE {g0:.2f}-{g1:.2f}: '{texts[0]}' (both passes agree; force-aligned)")
words.sort(key=lambda w: w["s"] if w["s"] is not None else 1e9)
json.dump(words, open(os.path.join(cap, "words.json"), "w"), indent=0)
print(" ".join(("[" + w["w"] + "]") if w["rescued"] else w["w"] for w in words))
print(f"{len(words)} words ({sum(w['rescued'] for w in words)} rescued) -> captions/words.json")
