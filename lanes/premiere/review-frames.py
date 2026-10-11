#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""review-frames.py: the step-5c evidence set, grabbed off the Premiere program monitor.

  uv run lanes/premiere/review-frames.py projects/<job> --round 1                      # every placed graphic
  uv run lanes/premiere/review-frames.py projects/<job> --round 2 --ids g10,g16 --rest-sheet
  uv run lanes/premiere/review-frames.py projects/<job> --round 3 --ids g16            # a targeted re-check
  uv run lanes/premiere/review-frames.py projects/<job> --round 1 --dry-run            # the plan, nothing written
  ... --out <dir>      # somewhere other than hf-graphics/review/round<N>/
  ... --fps 30000/1001 # only when no placed render is on disk to probe
  (uv resolves Pillow from the header: the contact sheets are the only dependency)

Writes <out>/<id>-f<frame>.png, <out>/sheets/<id>.png (one contact sheet per graphic, plus
sheets/_rest.png for the untouched graphics under --rest-sheet) and <out>/INDEX.md, the list
the reviewers are handed: every frame on disk with its timeline second and what to look at.

Why (2026-09-07): the loop's evidence was hand-rolled inside the job folder every run, so it
carried that job's absolute path and a hardcoded 29.97, guessed one comp directory, handed the
bridge a relative out path (which the CEP panel resolves against Premiere's own cwd, writing
nowhere while reporting success) and exited 0 with frames missing. One tool, job as an argument.

Sample set per placed graphic (clamped to the row, frame in .. frame out-1):
  every row      in+2 (the entrance has started), mid (the readable hold), out-2 (the exit)
  HAND comps     in+6 (a pop has settled by frame 4, a rise is still mid-travel at 6), +4 after
                 every registry call and every tween parsed off the comp, plus the call time +2 on
                 a `pop` or `slam` (the overshoot peaks at +3, so the +4 alone never shows it), and
                 a 1.0 s sweep
A hand comp is a row whose kind is not `text`: the text-animation comps are generated, their
motion is the builder's, and scanning them for tl.to times floods the plan with dead frames.

Reads hf-graphics/placement.json (a bare list or {"rows": [...]}), the comps under
hf-graphics/*/compositions/<id>.html (the glob workflows/graphics-qa.py uses), and takes the fps
from the job, never a constant. Grabs run through lanes/premiere/premiere-bridge.mjs `frame`,
never fronting the app. A frame that does not land is a non-zero exit: a partial evidence set
must never feed a review round. An existing png is skipped, so a run is restartable.
"""
import json, os, re, subprocess, sys, glob
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BRIDGE = Path(__file__).resolve().parent / 'premiere-bridge.mjs'
NUDGE = 1e-4
CALL = re.compile(r"\b(riseIn|riseOut|pop|slam|drawOn|slideIn|slideOut|flash|exit|reveal|countUp)\(\s*'[^']*'\s*,\s*([0-9.]+)")
TL = re.compile(r"tl\.(?:to|set)\([^;]*?,\s*([0-9.]+)\s*\)\s*;")
TILE = 480        # contact sheet tile width, px
PAD = 6           # gutter around each tile, px
BAR = 22          # label bar above each tile, px
LABEL_FONT = Path(__file__).resolve().parents[2] / 'assets' / 'fonts' / 'Inter-Bold.otf'


def rows_of(job):
    d = json.load(open(job / 'hf-graphics' / 'placement.json'))
    return d['rows'] if isinstance(d, dict) and 'rows' in d else d


def parse_fps(s):
    num, _, den = str(s).partition('/')
    return float(num) / float(den or 1)


def job_fps(job, rows, override):
    """The timeline rate, from the job: the placed renders carry it, so nothing here is a constant.
    The grabber this replaces held 1001/30000, which samples every frame of a 24p job at the wrong
    second and reads as a motion defect."""
    if override:
        return parse_fps(override)
    f = next((r['file'] for r in rows if r.get('file') and os.path.exists(r['file'])), None)
    if f:
        r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                            'stream=r_frame_rate', '-of', 'json', f], capture_output=True, text=True)
        if not r.returncode:
            return parse_fps(json.loads(r.stdout)['streams'][0]['r_frame_rate'])
    cuts = job / 'transcript' / 'cuts.json'
    if cuts.exists():
        c = json.load(open(cuts))
        if isinstance(c, dict) and c.get('fps'):
            return parse_fps(c['fps'])
    sys.exit('no placed render to probe and no fps in transcript/cuts.json: pass --fps 30000/1001')


def comp_for(job, gid):
    """The comp, through the same wide glob graphics-qa.py uses: a job may split its comps across
    hf-graphics/gfx/ and hf-graphics/text-animation/."""
    hits = sorted(glob.glob(str(job / 'hf-graphics' / '*' / 'compositions' / f'{gid}.html')))
    return Path(hits[0]) if hits else None


def plan_rows(job, rows, fps, ids, rest_sheet):
    """[(id, frame, why)], in row order. `ids` limits full sampling; the rest get their mid frame
    only when --rest-sheet asked for it."""
    def fr(t): return int(round(t * fps))
    out = []
    for r in rows:
        gid, s, e = r['id'], float(r['start']), float(r['end'])
        full = not ids or gid in ids
        if not full and not rest_sheet:
            continue
        why = {fr((s + e) / 2): 'mid: the readable hold'}
        if full:
            why[fr(s) + 2] = 'in+2: the entrance has started'
            why[fr(e) - 2] = 'out-2: the exit, and the last frame is a hard kill'
            comp = comp_for(job, gid) if r.get('kind') != 'text' else None
            if comp:
                src = comp.read_text(encoding='utf-8', errors='replace')
                why.setdefault(fr(s) + 6, 'in+6: a pop has settled by frame 4, a rise is mid-travel at 6')
                for m in CALL.finditer(src):
                    name, t = m.group(1), float(m.group(2))
                    # the +2 twin is the pop/slam overshoot only: it peaks at +3 and is settled by +4
                    for off in ((2, 4) if name in ('pop', 'slam') else (4,)):
                        why.setdefault(fr(s + t) + off, f'{off} frames into {name}() at t={t:.2f}s')
                for m in TL.finditer(src):
                    t = float(m.group(1))
                    why.setdefault(fr(s + t) + 4, f'4 frames into a tween at t={t:.2f}s')
                t = s + 1.0
                while t < e - 0.1:
                    why.setdefault(fr(t), 'sweep'); t += 1.0
        for f in sorted(x for x in why if fr(s) <= x <= fr(e) - 1):
            out.append((gid, f, why[f]))
    return out


def grab(gid, f, fps, outp):
    """One program-monitor frame. The out path is ABSOLUTE because the ExtendScript runs inside
    Premiere, whose cwd is its own app folder: a relative path writes nowhere, silently."""
    subprocess.run(['node', str(BRIDGE), 'frame',
                    json.dumps({'time': round(f / fps + NUDGE, 5), 'out': str(outp)})],
                   capture_output=True, text=True)


def on_disk(out_dir):
    """{id: [frames]} from the round dir, not from this invocation: a targeted second run extends
    the index instead of replacing it."""
    have = {}
    for p in sorted(glob.glob(os.path.join(out_dir, '*.png'))):
        m = re.match(r'^(.+)-f(\d+)\.png$', os.path.basename(p))
        if m:
            have.setdefault(m.group(1), []).append(int(m.group(2)))
    for v in have.values():
        v.sort()
    return have


def sheet(tiles, out_png):
    """A labelled contact sheet: tiles = [(label, png path)], 3 per row, each TILE px wide under a
    BAR px caption. Pillow, not ImageMagick `montage`: montage is absent on a stock Windows Git Bash
    box, so a client would get frames and no sheets while the pack sends reviewers to sheets/<id>.png."""
    ims = []
    for label, p in tiles:
        try:
            im = Image.open(p).convert('RGB')
        except Exception:
            continue
        ims.append((label, im.resize((TILE, max(1, round(im.height * TILE / im.width))))))
    if not ims:
        return False
    try:
        font = ImageFont.truetype(str(LABEL_FONT), 15)
    except Exception:
        font = ImageFont.load_default()
    cell = max(im.height for _, im in ims) + BAR
    cols, rows_n = min(3, len(ims)), (len(ims) + 2) // 3
    canvas = Image.new('RGB', (cols * (TILE + PAD) + PAD, rows_n * (cell + PAD) + PAD), (21, 21, 21))
    d = ImageDraw.Draw(canvas)
    for i, (label, im) in enumerate(ims):
        x, y = PAD + (i % 3) * (TILE + PAD), PAD + (i // 3) * (cell + PAD)
        d.text((x + 2, y + 3), label, font=font, fill=(255, 255, 255))
        canvas.paste(im, (x, y + BAR))
    canvas.save(out_png)
    return True


def write_index(out_dir, rows, fps, why_all):
    """The reviewers' list, rebuilt from what is ON DISK in the round dir (frames and sheets alike),
    so a targeted second run extends the index instead of shrinking it to its own ids."""
    have = on_disk(out_dir)
    # ids as strings on both sides: the frame files carry the id as text, while a plan may write a
    # numeric id (cell 1 on your-job read as "? · 0.000s to 0.000s", 2026-09-08)
    row_ids = {str(r['id']) for r in rows}
    order = [str(r['id']) for r in rows if str(r['id']) in have] + [g for g in have if g not in row_ids]
    span = {str(r['id']): (float(r['start']), float(r['end']), r.get('kind', '?')) for r in rows}
    L = [f'# Evidence frames: {os.path.basename(out_dir)}', '',
         f'fps {fps:.5f} · frame N is at N/{fps:.5f} = {1.0 / fps:.6f} x N seconds on the timeline.',
         'Each png is the program monitor at that frame, every video track composited.', '']
    for gid in order:
        s, e, kind = span.get(gid, (0.0, 0.0, '?'))
        head = f'## {gid} · {kind} · {s:.3f}s to {e:.3f}s'
        for rel in (f'sheets/{gid}.png', 'sheets/_rest.png'):
            if os.path.exists(os.path.join(out_dir, rel)):
                head += f' · sheet {rel}'; break
        L += [head]
        for f in have[gid]:
            L.append(f'- `{gid}-f{f}.png` t={f / fps:.3f}s · {why_all.get((gid, f), "extra grab")}')
        L.append('')
    open(os.path.join(out_dir, 'INDEX.md'), 'w', encoding='utf-8').write('\n'.join(L))


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith('-'):
        sys.exit(__doc__)

    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default

    job = Path(a[0]).resolve()
    rnd = opt('--round', '1')
    ids = {x for x in (opt('--ids') or '').split(',') if x}
    rest_sheet = '--rest-sheet' in a
    dry = '--dry-run' in a
    rows = rows_of(job)
    fps = job_fps(job, rows, opt('--fps'))
    out_dir = os.path.abspath(opt('--out') or str(job / 'hf-graphics' / 'review' / f'round{rnd}'))

    plan = plan_rows(job, rows, fps, ids, rest_sheet)
    if dry:
        print(f'{len(plan)} frames planned at {fps:.5f} fps -> {out_dir}', file=sys.stderr)
        for gid, f, _ in plan:
            print(gid, f, os.path.join(out_dir, f'{gid}-f{f}.png'))
        return 0

    os.makedirs(os.path.join(out_dir, 'sheets'), exist_ok=True)
    print(f'{len(plan)} frames at {fps:.5f} fps -> {out_dir}', flush=True)
    missing, got = [], 0
    for gid, f, _ in plan:
        png = os.path.join(out_dir, f'{gid}-f{f}.png')
        if os.path.exists(png):
            continue
        grab(gid, f, fps, os.path.join(out_dir, f'{gid}-f{f}'))
        if os.path.exists(png):
            got += 1
        else:
            print(f'MISSING {gid} {f}', flush=True); missing.append((gid, f))
    print(f'{got} grabbed · {len(plan) - got - len(missing)} already on disk · {len(missing)} missing', flush=True)

    why_all = {(g, f): w for g, f, w in plan_rows(job, rows, fps, set(), True)}
    for g, f, w in plan:
        why_all[(g, f)] = w
    have, built = on_disk(out_dir), 0
    full = [r['id'] for r in rows if (not ids or r['id'] in ids) and r['id'] in have]
    for gid in full:
        tiles = [(f'{gid}-f{f}  t={f / fps:.2f}s', os.path.join(out_dir, f'{gid}-f{f}.png')) for f in have[gid]]
        built += sheet(tiles, os.path.join(out_dir, 'sheets', f'{gid}.png'))
    rest = [r['id'] for r in rows if r['id'] not in full and r['id'] in have]
    if rest_sheet and rest:
        mid = {g: have[g][len(have[g]) // 2] for g in rest}
        tiles = [(f'{g}-f{mid[g]}  t={mid[g] / fps:.2f}s', os.path.join(out_dir, f'{g}-f{mid[g]}.png')) for g in rest]
        built += sheet(tiles, os.path.join(out_dir, 'sheets', '_rest.png'))
    print(f'{built} contact sheet(s) -> {os.path.join(out_dir, "sheets")}')
    write_index(out_dir, rows, fps, why_all)
    print(f'INDEX.md -> {os.path.join(out_dir, "INDEX.md")}')
    if missing:
        sys.exit(f'{len(missing)} frame(s) did not land: a partial evidence set cannot feed a review round')
    return 0


if __name__ == '__main__':
    sys.exit(main())
