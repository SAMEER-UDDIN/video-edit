#!/usr/bin/env python3
"""Step 3: captions/words.json -> captions/captions.srt (+ .json) + captions/emphasis-words.md.

  python .claude/skills/stage-3-1-creating-captions/scripts/make_captions.py projects/<job> [--censor fuck=F*** ...] [--fps 60]

Sameer's rules (Seq02, 2026-10-07): 3-4 words per caption (2 only where a sentence leaves no better split), ALL CAPS,
NO full stops or commas (question marks stay), phrase-aware breaks (sentence ends and commas first; 1-2-word phrases join a
neighbour when the result stays <= 4; long phrases split evenly, never ending on a small word), each caption holds until the
next (a gap > 0.6 s ends it 0.2 s after its last word), frame-snapped. emphasis-words.md suggests ONE word per caption to
colour by meaning (style guide: green money/weight/win/positive, red violence/negative, yellow cues/key repeated nouns,
cyan/purple names) for his manual colouring pass — Premiere can't colour words by script.
"""
import argparse, importlib.util, json, os, re

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
ap = argparse.ArgumentParser(); ap.add_argument("job"); ap.add_argument("--fps", type=float, default=60)
ap.add_argument("--censor", nargs="*", default=["fuck=F***", "fucking=F***ING", "shit=S***", "bitch=B****"])
a = ap.parse_args()
job = os.path.abspath(a.job); cap = os.path.join(job, "captions")
CENSOR = dict(x.split("=", 1) for x in a.censor)
words = [w for w in json.load(open(os.path.join(cap, "words.json"))) if w.get("w")]
for i, w in enumerate(words):
    if w["s"] is None: w["s"] = (words[i - 1]["e"] or words[i - 1]["s"]) if i else 0.0
    if w["e"] is None: w["e"] = w["s"] + 0.2
import wave
_wav = os.path.join(cap, "seq-audio.wav")
END = (lambda f: f.getnframes() / f.getframerate())(wave.open(_wav)) if os.path.exists(_wav) else max(w["e"] for w in words) + 0.5   # never past the short
core = lambda t: re.sub(r"[^\w']", "", t).lower()
def clean(t):
    c = core(t); out = CENSOR[c] if c in CENSOR else t
    return out.upper().replace(",", "").replace(".", "")
ends = lambda t: t.rstrip().endswith((".", "?", "!"))
FUNC = {"the", "a", "an", "to", "my", "and", "of", "at", "in", "for", "is", "are", "i", "he", "we", "you", "so", "what", "can",
        "was", "or", "it's", "i've", "she", "they", "his", "her", "on", "with", "but", "that", "if"}

phrases, cur = [], []
for w in words:
    cur.append(w)
    if ends(w["w"]) or w["w"].endswith(","): phrases.append(cur); cur = []
if cur: phrases.append(cur)
merged = []
for ph in phrases:
    if merged and (len(ph) <= 2 or len(merged[-1]) <= 2) and len(merged[-1]) + len(ph) <= 4: merged[-1] = merged[-1] + ph
    else: merged.append(ph)
def split(ph):
    n = len(ph)
    if n <= 4: return [ph]
    k, best, bestc = -(-n // 4), None, 1e9
    def rec(start, parts, acc):
        nonlocal best, bestc
        if parts == 1:
            if 2 <= n - start <= 4:
                cuts, cost, prev = acc + [n], 0, 0
                for c in cuts: cost += abs((c - prev) - 3.5) + (3 if c != n and core(ph[c - 1]["w"]) in FUNC else 0); prev = c
                if cost < bestc: best, bestc = cuts, cost
            return
        for sz in (2, 3, 4):
            if start + sz < n: rec(start + sz, parts - 1, acc + [start + sz])
    rec(0, k, [])
    out, prev = [], 0
    for c in best: out.append(ph[prev:c]); prev = c
    return out
groups = [g for ph in merged for g in split(ph)]
snap = lambda t: round(t * a.fps) / a.fps
caps = []
for k, g in enumerate(groups):
    s = snap(g[0]["s"]); nxt = snap(groups[k + 1][0]["s"]) if k + 1 < len(groups) else END
    e = nxt if nxt - g[-1]["e"] <= 0.6 else snap(g[-1]["e"] + 0.2)
    caps.append({"start": s, "end": min(e, END), "text": " ".join(clean(x["w"]) for x in g), "words": len(g),
                 "rescued": any(x.get("rescued") for x in g)})
if caps: caps[0]["start"] = min(caps[0]["start"], 0.0) if caps[0]["start"] < 0.3 else caps[0]["start"]

def ts(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
with open(os.path.join(cap, "captions.srt"), "w", encoding="utf-8") as f:
    for k, c in enumerate(caps, 1): f.write(f"{k}\n{ts(c['start'])} --> {ts(c['end'])}\n{c['text']}\n\n")
json.dump(caps, open(os.path.join(cap, "captions.json"), "w", encoding="utf-8"), indent=1)

# emphasis suggestions: the channel caption builder's meaning lexicon (presets/youtube/fight-club/build.py)
spec = importlib.util.spec_from_file_location("fc", os.path.join(REPO, "presets", "youtube", "fight-club", "build.py"))
fc = importlib.util.module_from_spec(spec); spec.loader.exec_module(fc)
names, rows = {}, []
for c in caps:             # EVERY caption gets a row: the lexicon only drafts a hint, Claude decides by meaning before handing over
    k = fc.auto_key(c["text"].split(), names)
    hint = f"{' '.join(c['text'].split()[k[0]:k[0] + k[1]])} ({k[2]})" if k else ""
    rows.append(f"| {c['start']:.2f} | {c['text']} | {hint} | |")
with open(os.path.join(cap, "emphasis-words.md"), "w", encoding="utf-8") as f:
    f.write("<!-- DRAFT: Claude fills the last column by MEANING (one word per caption at most; filler stays white), then gives\n"
            "     Sameer the finished table: Time | Caption | Colour this word -->\n"
            "| Time | Caption | Lexicon hint | Colour this word |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")
for c in caps: print(f"{c['start']:6.2f}-{c['end']:6.2f} [{c['words']}] {c['text']}{'   <- rescued, check' if c['rescued'] else ''}")
print(f"{len(caps)} captions (ending {caps[-1]['end']:.2f} s) -> captions/captions.srt; emphasis DRAFT for all {len(rows)} -> captions/emphasis-words.md (fill by meaning)")
