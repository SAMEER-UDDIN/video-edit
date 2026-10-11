#!/usr/bin/env python3
# /// script
# dependencies = ["pillow"]
# ///
"""
Fight Club caption builder  (channel preset — see presets/youtube/fight-club/README.md)

The channel's signature caption: bold ALL-CAPS serif (Times New Roman Bold), 2-3 words per line,
white with a soft dark shadow, ONE keyword coloured by meaning, mid-frame (~50-58 % height), and
Sameer's "fightclubcaps / Revised Light pop" animation read straight off fightcaps.prfpset:

    t = 0.000 s   scale 100.0 %   position y 0.5000   (anchor = frame centre)
    t = 0.050 s   scale 107.6 %   position y 0.4656   (pop up and in)
    t = 0.367 s   scale 107.6 %   position y 0.4656   (hold)
    t = 0.383 s   scale 112.0 %   position y 0.4479   (second nudge, then holds)

Same engine as presets/tiktok/raw: PIL draws the type, ffmpeg encodes. Each frame is composed in
Python (the pop needs per-frame scale) and piped raw into ffmpeg.

Three ways in:
  uv run presets/youtube/fight-club/build.py projects/<job> --prep            # transcript → editable captions.fight-club.json
  uv run presets/youtube/fight-club/build.py projects/<job> --alpha           # captions.fight-club.json → V5 alpha overlay
  uv run presets/youtube/fight-club/build.py --lines <file.json> --out x.mov  # any hand-written line sheet (tests, one-offs)
Add --preview <video> (or --test-bg) to burn the layer over footage as an H.264 look-check instead.
"""
import argparse, json, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

for _s in (sys.stdout, sys.stderr):   # Windows cp1252 consoles choke on → (see tiktok/raw/build.py)
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

# ---------------------------------------------------------------- canvas (LOCKED)
W, H = 1080, 1920
FPS = "30000/1001"                      # 29.97, the channel's rate
FPS_F = 30000 / 1001
SAFE_TOP, SAFE_BOT = 200, 1620          # house short-form safe band

# ---------------------------------------------------------------- type
# Bold by Sameer's request. His shipped captions (newfinal.prtextstyle = TimesNewRomanPSMT) are the
# REGULAR weight; set FC_WEIGHT=regular to match them exactly.
_REG = os.environ.get("FC_WEIGHT", "bold").lower() == "regular"
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\times.ttf" if _REG else r"C:\Windows\Fonts\timesbd.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    "/Library/Fonts/Times New Roman Bold.ttf",
    os.path.join(REPO, "assets", "fonts", "Tinos-Bold.ttf"),          # metric-compatible free fallback, if added
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
]
CAP_SIZE      = 66                      # px at 1080 wide ("small to medium")
CAP_MIN_SIZE  = 48                      # a long line shrinks to fit before it wraps
CAP_MAX_W     = 900                     # one line, never wider than this
CAP_TRACKING  = 1                       # px between letters (TNR caps sit tight)
WORD_GAP      = 0.28                    # space width as a fraction of the font size

# authored centre of the text inside the graphic, BEFORE the pop transform. Calibrated 2026-10-05
# against "Ryan Garcia Is A FAKE MEXICAN" (held captions measured at ~51 % height): the held
# 107.6 % state sits at y≈990 (51.5 %), frame 0 at 54.7 %, the 112 % nudge at 50.0 %.
CAP_BASE_Y    = 1050

# colour (white + one meaningful keyword)
WHITE  = (255, 255, 255)
COLORS = {
    "green":  (46, 230, 92),            # money, weights, nationality, win/positive
    "red":    (255, 46, 46),            # violence, negative
    "yellow": (255, 214, 10),           # *CUES*, "CHAMP", names on yellow
    "cyan":   (36, 222, 242),           # names / emphasis
    "purple": (205, 72, 255),           # names / emphasis (the second name in a rivalry)
    "white":  WHITE,
}

# soft dark drop shadow + faint glow (no hard stroke: the channel's type has none)
SHADOW_OFFSET = (0, 4)
SHADOW_BLUR   = 5
SHADOW_ALPHA  = 0.85
GLOW_BLUR     = 14
GLOW_ALPHA    = 0.45

# ---------------------------------------------------------------- the pop (fightcaps.prfpset)
# (time s, scale %, position y as a fraction of frame height). Premiere's ticks: 254016000000 / s.
POP_KEYS = [(0.000, 100.0, 0.5000), (0.050, 107.6, 0.46557), (0.367, 107.6, 0.46557), (0.383, 112.0, 0.44792)]

def _ease(u):                           # the preset's bezier handles are a plain ease (≈ smoothstep)
    return u * u * (3 - 2 * u)

def pop_state(t):
    """scale (fraction) and y-offset (px) at t seconds after the caption appears."""
    if t <= POP_KEYS[0][0]:
        k = POP_KEYS[0]; return k[1] / 100, (k[2] - 0.5) * H
    for (t0, s0, y0), (t1, s1, y1) in zip(POP_KEYS, POP_KEYS[1:]):
        if t <= t1:
            u = _ease((t - t0) / (t1 - t0))
            return (s0 + (s1 - s0) * u) / 100, ((y0 + (y1 - y0) * u) - 0.5) * H
    k = POP_KEYS[-1]; return k[1] / 100, (k[2] - 0.5) * H

# ---------------------------------------------------------------- keyword colouring
GREEN_WORDS = {"WIN", "WINS", "WON", "WINNER", "WINNING", "RESPECT", "MONEY", "PAID", "MILLION", "MILLIONS",
               "BELT", "CHAMPION", "CHAMPIONS", "POUNDS", "LBS", "LB", "MEXICAN", "AMERICAN", "IRISH", "BRITISH",
               "RUSSIAN", "DAGESTANI", "GOAT", "PRIME", "LEGEND", "UNDEFEATED", "OFFICIAL", "PROVEN"}
RED_WORDS = {"BLOOD", "BLOODY", "DEAD", "DIE", "DIED", "KILL", "KILLED", "CHEAT", "CHEATED", "CHEATING", "CHEATER",
             "LOSE", "LOST", "LOSS", "LOSER", "RUINED", "RUIN", "SCARED", "AFRAID", "FAKE", "LIE", "LIES", "LIAR",
             "LYING", "BANNED", "BAN", "FINED", "SUSPENDED", "ASSAULTED", "ATTACKED", "HIT", "HURT", "BROKE",
             "BROKEN", "KO", "KO'D", "KNOCKOUT", "KNOCKED", "DESTROY", "DESTROYED", "TRASH", "NEVER", "QUIT",
             "DUCK", "DUCKING", "DUCKED", "DRAINED", "BREATHE", "CRIED", "TEARS", "INJURY", "INJURED", "PED",
             "PEDS", "STEROIDS", "SLAPPED", "SLAP", "EXPOSED", "THREAT", "THREATENED", "OVER", "SLEEP"}
YELLOW_WORDS = {"CHAMP", "SHAKY", "TUNE-UP"}
NAMES = {"RYAN", "GARCIA", "TANK", "DAVIS", "GERVONTA", "BENN", "CONOR", "MCGREGOR", "KHABIB", "NURMAGOMEDOV",
         "ISLAM", "MAKHACHEV", "JON", "JONES", "DC", "CORMIER", "BISPING", "PADDY", "PIMBLETT", "ILIA", "TOPURIA",
         "FURY", "TYSON", "AJ", "JOSHUA", "USMAN", "GSP", "ARMAN", "TSARUKYAN", "POIRIER", "DUSTIN", "IAN", "GARRY",
         "MAX", "HOLLOWAY", "VOLK", "VOLKANOVSKI", "CHARLES", "OLIVEIRA", "NGANNOU", "FRANCIS", "ASPINALL", "TOM",
         "DANA", "WHITE", "ROGAN", "HELWANI", "BRONER", "ABDULMANAP", "CAIN", "BROCK", "LESNAR", "GABLE", "SEAN",
         "O'MALLEY", "NATE", "DIAZ", "TONY", "FERGUSON", "ALEX", "PEREIRA", "CANELO", "HANEY", "DEVIN", "LOGAN",
         "JAKE", "PAUL"}
NUM = re.compile(r"^\$?\d[\d,.]*(K|M|LBS?|%)?$")

def _core(tok):
    return re.sub(r"^[^\w$*]+|[^\w*%']+$", "", tok.upper())

def auto_key(words, name_colors):
    """Pick ONE keyword (or a 2-word number+unit) for a caption, by meaning. Returns (start, n, colour) or None.
    Priority: *cue* > violence/negative > money/weight/win > names."""
    cores = [_core(w) for w in words]
    for i, c in enumerate(cores):
        if c.startswith("*") and c.endswith("*"):
            return i, 1, "yellow"
    for i, c in enumerate(cores):
        if c in RED_WORDS:
            return i, 1, "red"
    for i, c in enumerate(cores):
        if NUM.match(c):
            n = 2 if i + 1 < len(cores) and cores[i + 1] in {"POUNDS", "LBS", "LB", "MILLION", "GRAND", "K"} else 1
            return i, n, "green"
        if c in GREEN_WORDS:
            return i, 1, "green"
    for i, c in enumerate(cores):
        if c in YELLOW_WORDS:
            return i, 1, "yellow"
    for i, c in enumerate(cores):
        base = c.replace("'S", "")
        if base in NAMES:
            if base not in name_colors:   # first name seen → cyan, the rival → purple, then alternate
                name_colors[base] = ["cyan", "purple"][len(name_colors) % 2]
            n = 2 if i + 1 < len(cores) and cores[i + 1].replace("'S", "") in NAMES else 1
            return i, n, name_colors[base]
    return None

# ---------------------------------------------------------------- phrasing (2-3 words)
SENT_END = (".", "?", "!", "…", ",")
MAX_WORDS, MAX_CHARS = 3, 16

def chunk(words):
    lines, cur = [], []
    def flush():
        if cur:
            lines.append({"words": [w["text"] for w in cur], "start": cur[0]["start"], "end": cur[-1]["end"]})
            cur.clear()
    for w in words:
        cur.append(w)
        joined = " ".join(x["text"] for x in cur)
        if w["text"].rstrip().endswith(SENT_END) or len(cur) >= MAX_WORDS or len(joined) >= MAX_CHARS:
            flush()
    flush()
    # a lone word that isn't a keyword joins its neighbour (2-3 words is the look; 1 only for a punch word)
    out = []
    for ln in lines:
        if out and len(ln["words"]) == 1 and len(out[-1]["words"]) < MAX_WORDS and ln["start"] - out[-1]["end"] < 0.25 \
                and _core(ln["words"][0]) not in RED_WORDS | GREEN_WORDS:
            out[-1]["words"] += ln["words"]; out[-1]["end"] = ln["end"]
        else:
            out.append(ln)
    for i in range(len(out) - 1):       # hold until the next line: no flicker, no gaps mid-speech
        out[i]["end"] = out[i + 1]["start"]
    return out

def load_corrections():
    p = os.path.join(REPO, "transcript-corrections.json")
    return json.load(open(p, encoding="utf-8")).get("auto", {}) if os.path.exists(p) else {}

def prep(job_dir):
    """canonical transcript → captions.fight-club.json (edit keywords/colours/phrasing by hand, then --alpha)."""
    job = os.path.basename(os.path.abspath(job_dir))
    tj = os.path.join(job_dir, "outputs", f"{job}.transcript.json")
    assert os.path.exists(tj), f"missing transcript: {tj} (run the rough cut first)"
    table = load_corrections()
    words = []
    for w in json.load(open(tj, encoding="utf-8"))["words"]:
        m = re.match(r"^(\W*)(.*?)(\W*)$", w["text"], re.DOTALL)
        pre, core, suf = m.groups()
        fix = table.get(core.lower()) if core else None
        words.append({**w, "text": f"{pre}{fix}{suf}" if fix else w["text"]})
    names, sheet = {}, []
    for ln in chunk(words):
        k = auto_key(ln["words"], names)
        entry = {"start": round(ln["start"], 3), "end": round(ln["end"], 3), "text": " ".join(ln["words"]).upper()}
        if k:
            i, n, col = k
            entry["key"] = " ".join(ln["words"][i:i + n]).upper(); entry["color"] = col
        sheet.append(entry)
    out = os.path.join(job_dir, "captions.fight-club.json")
    json.dump({"lines": sheet}, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"[fight-club] {len(sheet)} caption lines → {out}")
    for e in sheet:
        print(f"  {e['start']:6.2f}-{e['end']:6.2f}  {e['text']:<24} {e.get('key', '')} {e.get('color', '')}")
    return out

# ---------------------------------------------------------------- rendering
def font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    sys.exit("no Times New Roman Bold (or fallback) font found; see FONT_CANDIDATES")

def _clean(text):
    return re.sub(r"\s+", " ", text.upper().replace("\u2019", "'")).strip()

def layout(text, key, size):
    """split into word runs with colours; returns (runs, font, total width)."""
    f = font(size)
    words = _clean(text).split(" ")
    kw = _clean(key).split(" ") if key else []
    colored = set()
    if kw:
        for i in range(len(words) - len(kw) + 1):
            if [_core(x) for x in words[i:i + len(kw)]] == [_core(x) for x in kw]:
                colored = set(range(i, i + len(kw))); break
    gap = size * WORD_GAP
    runs, x = [], 0.0
    for i, wd in enumerate(words):
        wdt = sum(f.getlength(ch) + CAP_TRACKING for ch in wd) - CAP_TRACKING
        runs.append((wd, x, i in colored))
        x += wdt + gap
    return runs, f, x - gap

def render_line(entry):
    """one caption → a tight RGBA image (text + shadow), centred at its own middle."""
    text, key = entry["text"], entry.get("key")
    col = COLORS.get(entry.get("color", "white"), WHITE)
    size = CAP_SIZE
    runs, f, tw = layout(text, key, size)
    while tw > CAP_MAX_W and size > CAP_MIN_SIZE:
        size -= 2; runs, f, tw = layout(text, key, size)
    asc, desc = f.getmetrics()
    pad = GLOW_BLUR * 3
    cw, ch = int(tw + 2 * pad), int(asc + desc + 2 * pad)
    ink = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(ink)
    for wd, x0, is_key in runs:
        x = pad + x0
        for c in wd:
            d.text((x, pad), c, font=f, fill=(col if is_key else WHITE) + (255,))
            x += f.getlength(c) + CAP_TRACKING
    alpha = ink.split()[3]
    shadow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sh = Image.new("L", (cw, ch), 0); sh.paste(alpha, SHADOW_OFFSET)
    sh = sh.filter(ImageFilter.GaussianBlur(SHADOW_BLUR)).point(lambda v: int(v * SHADOW_ALPHA))
    glow = alpha.filter(ImageFilter.GaussianBlur(GLOW_BLUR)).point(lambda v: min(255, int(v * GLOW_ALPHA * 1.6)))
    black = Image.new("RGBA", (cw, ch), (0, 0, 0, 255))
    shadow = Image.composite(black, shadow, glow)
    shadow.alpha_composite(Image.composite(black, Image.new("RGBA", (cw, ch), (0, 0, 0, 0)), sh))
    shadow.alpha_composite(ink)
    return shadow

def frames(sheet, duration):
    """yield RGBA frame bytes for the whole layer; animation frames are cached per caption."""
    n = int(round(duration * FPS_F))
    blank = Image.new("RGBA", (W, H), (0, 0, 0, 0)).tobytes()
    base = [render_line(e) for e in sheet]
    cache = {}
    j = 0
    for fi in range(n):
        t = fi / FPS_F
        while j < len(sheet) - 1 and t >= sheet[j + 1]["start"]:
            j += 1
        e = sheet[j] if sheet else None
        if not e or t < e["start"] or t >= e["end"]:
            yield blank; continue
        k = min(int(round((t - e["start"]) * FPS_F)), 13)     # past ~0.4 s the pose is constant
        if (j, k) not in cache:
            s, dy = pop_state(k / FPS_F)
            img = base[j]
            sw, shh = max(1, round(img.width * s)), max(1, round(img.height * s))
            im = img.resize((sw, shh), Image.LANCZOS)
            cy = H / 2 + (CAP_BASE_Y - H / 2) * s + dy          # scale about the frame centre, then move
            fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            fr.alpha_composite(im, (int(round(W / 2 - sw / 2)), int(round(cy - shh / 2))))
            assert SAFE_TOP <= cy <= SAFE_BOT, "caption left the short-form safe band"
            cache[(j, k)] = fr.tobytes()
        yield cache[(j, k)]

def encode(sheet, duration, out, under=None, test_bg=False):
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", FPS, "-i", "-"]
    if under or test_bg:
        if under:
            cmd += ["-i", under]
            bg = (f"[1:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
                  f"trim=duration={duration:.3f},setpts=PTS-STARTPTS[bg]")
        else:   # a dark, vignetted navy→teal plate in the channel's grade, so shadow + colours read true
            cmd += ["-f", "lavfi", "-i", f"gradients=s={W}x{H}:c0=0x0b1a2e:c1=0x1d3b4a:x0=540:y0=0:x1=540:y1=1920:d={duration:.3f}:r={FPS}"]
            bg = "[1:v]vignette=PI/4,format=yuv420p[bg]"
        cmd += ["-filter_complex", f"{bg};[bg][0:v]overlay=0:0:format=auto,format=yuv420p[v]", "-map", "[v]"]
        if under:
            cmd += ["-map", "1:a?", "-c:a", "aac", "-b:a", "256k"]
        cmd += ["-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-movflags", "+faststart", out]
    else:   # the step-5 layer: straight-alpha ProRes 4444, what Premiere's V5 placer expects
        cmd += ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-an", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fb in frames(sheet, duration):
        p.stdin.write(fb)
    p.stdin.close()
    if p.wait() != 0:
        sys.exit("ffmpeg failed")

def job_duration(job_dir, sheet):
    cj = os.path.join(job_dir, "transcript", "cuts.json")
    if os.path.exists(cj):
        segs = json.load(open(cj, encoding="utf-8")).get("segments", [])
        if segs:
            return sum(float(s["end"]) - float(s["start"]) for s in segs)
    return max(e["end"] for e in sheet) + 0.4

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job_dir", nargs="?")
    ap.add_argument("--prep", action="store_true", help="write projects/<job>/captions.fight-club.json from the transcript")
    ap.add_argument("--lines", help="a caption sheet JSON ({lines:[{start,end,text,key?,color?}]}) instead of the job's")
    ap.add_argument("--alpha", action="store_true", help="emit the transparent ProRes 4444 layer (default)")
    ap.add_argument("--preview", metavar="VIDEO", help="burn the captions over this video (H.264 look-check)")
    ap.add_argument("--test-bg", action="store_true", help="burn over a dark graded test plate")
    ap.add_argument("--duration", type=float)
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.prep:
        assert a.job_dir, "--prep needs a job dir"
        prep(a.job_dir); sys.exit(0)
    sheet_path = a.lines or (a.job_dir and os.path.join(a.job_dir, "captions.fight-club.json"))
    assert sheet_path and os.path.exists(sheet_path), f"no caption sheet ({sheet_path}); run --prep first or pass --lines"
    sheet = sorted(json.load(open(sheet_path, encoding="utf-8"))["lines"], key=lambda e: e["start"])
    names = {}
    for e in sheet:                         # lines without a hand-set key get the automatic one
        if "key" not in e:
            k = auto_key(e["text"].split(), names)
            if k:
                i, n, col = k; e["key"] = " ".join(e["text"].split()[i:i + n]); e["color"] = col
    dur = a.duration or (job_duration(a.job_dir, sheet) if a.job_dir else max(e["end"] for e in sheet) + 0.4)
    burn = a.preview or a.test_bg
    out = a.out or (os.path.join(a.job_dir, "hf-graphics", "captions", "renders",
                                 "captions-preview.mp4" if burn else "captions-alpha.mov") if a.job_dir else None)
    assert out, "--out is required with --lines and no job dir"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    print(f"[fight-club] {'burn' if burn else 'ALPHA overlay'} {W}x{H} @29.97  lines={len(sheet)}  dur={dur:.2f}s → {out}")
    encode(sheet, dur, out, under=a.preview, test_bg=bool(a.test_bg))
    for e in sheet:
        print(f"  {e['start']:6.2f}-{e['end']:6.2f}  {e['text']:<24} {e.get('key', '') or ''} {e.get('color', '') or ''}")
    print(f"[fight-club] done: {out}")
