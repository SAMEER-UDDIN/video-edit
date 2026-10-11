#!/usr/bin/env python3
"""parse_fcpxml.py <timeline.xml> [--json out.json] — everything a Premiere FCP XML export knows about
one sequence, per clip, on every video and audio track.

This is the reader the post-mortem and every future "what did the creator change" diff run on. The
four traps it encodes, each found the hard way on Hot Coffee:

  1. A <video>/<audio>/<media> is ALSO nested inside every <file>, so the sequence's own sections
     cannot be found with find(): depth-match from the sequence's <media>.
  2. Only the FIRST clipitem to use a source carries <pathurl>; every repeat writes <file id="…"/>
     with no path. Build id → path first, then resolve, or every repeat use vanishes (51 vs 59).
  3. A clip that carries no Basic Motion filter is at the DEFAULT (scale 100, centred) — that is a
     value, not a blank. Report it as 100, never None.
  3b. A KEYFRAMED parameter is a RANGE, not its first <value>: the creator's face nests read as a
     static 100 until param() learned to collect the <keyframe>s (they are 100 -> 110, the gradual
     zoom on every face block). Such a value comes back as {min, max, keyframes}.
  4. Colour labels live in <labels><label2>; nothing in the ExtendScript DOM returns them.
"""
import io, json, re, sys, pathlib
from collections import Counter, defaultdict
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding='utf-8')
    except Exception: pass


def load(path):
    s = io.open(path, encoding='utf-8', errors='replace').read()
    tb = re.search(r'<sequence[^>]*>.*?<rate>\s*<timebase>(\d+)</timebase>\s*<ntsc>(\w+)</ntsc>', s, re.S)
    timebase = int(tb.group(1)) if tb else 60
    ntsc = (tb.group(2).upper() == 'TRUE') if tb else True
    fps = timebase * 1000 / 1001 if ntsc else float(timebase)
    return s, fps


def span(s, o, c, start):
    lo = s.find(o, start)
    if lo < 0: return None
    depth, i, pat = 0, lo, re.compile(re.escape(o) + '|' + re.escape(c))
    while True:
        m = pat.search(s, i)
        if not m: return None
        depth += 1 if m.group(0) == o else -1
        if depth == 0: return (lo, m.start())
        i = m.end()


def tracks_in(s, lo, hi):
    out, depth, cur = [], 0, None
    for m in re.finditer(r'<track[ >]|</track>', s[lo:hi]):
        if m.group(0).startswith('</'):
            depth -= 1
            if depth == 0 and cur is not None: out.append((cur, lo + m.start())); cur = None
        else:
            if depth == 0: cur = lo + m.start()
            depth += 1
    return out


def num(blk, tag):
    m = re.search(r'<%s>(-?[\d.]+)</%s>' % (tag, tag), blk)
    return float(m.group(1)) if m else None


def param(blk, effectid, pid):
    """the first <value> of <parameterid>pid</parameterid> inside the filter whose effectid matches"""
    for f in re.finditer(r'<filter>(.*?)</filter>', blk, re.S):
        fb = f.group(1)
        if ('<effectid>%s</effectid>' % effectid) not in fb: continue
        # a KEYFRAMED parameter carries several <keyframe><when/><value/></keyframe> after its static
        # <value>; reading only the first <value> reports a 100 -> 110 ramp as a static 100 (the
        # creator's gradual zoom on every face nest went unseen this way, 2026-09-19). Report the range.
        pm = re.search(r'<parameterid>%s</parameterid>(.*?)</parameter>' % pid, fb, re.S)
        if pm:
            kfs = re.findall(r'<keyframe>\s*<when>-?\d+</when>\s*<value>(-?[\d.]+)</value>', pm.group(1))
            if len(kfs) >= 2:
                vals = [float(k) for k in kfs]
                return {'min': min(vals), 'max': max(vals), 'keyframes': len(vals)}
        m = re.search(r'<parameterid>%s</parameterid>.*?<value>(.*?)</value>' % pid, fb, re.S)
        if m:
            v = m.group(1).strip()
            if '<horiz>' in v:
                h = re.search(r'<horiz>(-?[\d.]+)</horiz>', v); ve = re.search(r'<vert>(-?[\d.]+)</vert>', v)
                return (float(h.group(1)), float(ve.group(1)))
            try: return float(v)
            except ValueError: return v
    return None


def blank_nested(tblk):
    """A nested-sequence clipitem embeds the WHOLE child <sequence>, with its own <track>s and
    clipitems whose <start> is nest-relative. A flat clipitem scan over the track block therefore
    reports the child's sub-clips as top-level clips at the wrong times (21 phantom "punch-ins" at
    2-15 s, all overlapping - impossible on one track). Blank every child <sequence> span first."""
    out, i = [], 0
    while True:
        sp = span(tblk, '<sequence', '</sequence>', i)
        if not sp: out.append(tblk[i:]); break
        lo, hi = sp
        out.append(tblk[i:lo]); out.append(' ' * (hi + len('</sequence>') - lo))
        i = hi + len('</sequence>')
    return ''.join(out)


def nested_contents(s):
    """name -> the child sequence's own top-level clips (nest-relative seconds), for the anatomy."""
    out = {}
    for m in re.finditer(r'<sequence[^>]*>', s):
        i = m.start(); j = s.find('</sequence>', i)
        blk = s[i:j]
        nm = re.search(r'<name>(.*?)</name>', blk)
        if not nm or not nm.group(1).startswith('Nested'): continue
        med = blk.find('<media>'); v0 = blk.find('<video>', med); v1 = blk.find('</video>', v0)
        clips = []
        for c in re.finditer(r'<clipitem[^>]*>(.*?)</clipitem>', blk[v0:v1], re.S):
            cb = c.group(1)
            st, en = num(cb, 'start'), num(cb, 'end')
            if st is None or en is None: continue
            sc = param(cb, 'basic', 'scale')
            clips.append(dict(a=st, b=en, scale=sc if sc is not None else 100.0,
                              name=(re.search(r'<name>(.*?)</name>', cb) or [None, ''])[1] if re.search(r'<name>(.*?)</name>', cb) else ''))
        out[nm.group(1)] = clips
    return out


def parse(path):
    s, fps = load(path)
    seq = s.find('<sequence ')
    name = re.search(r'<name>(.*?)</name>', s[seq:]).group(1)
    nests = nested_contents(s)
    filepath = {}
    for m in re.finditer(r'<file id="([^"]+)"[^/>]*>(.*?)</file>', s, re.S):
        p = re.search(r'<pathurl>(.*?)</pathurl>', m.group(2))
        if p: filepath[m.group(1)] = p.group(1)
    med = span(s, '<media>', '</media>', seq)
    V = span(s, '<video>', '</video>', med[0])
    A = span(s, '<audio>', '</audio>', V[1])
    clips = []
    for kind, (lo, hi) in (('V', V), ('A', A)):
        for n, (tlo, thi) in enumerate(tracks_in(s, lo, hi), 1):
            tblk = blank_nested(s[tlo:thi])          # same length as the original: offsets still hold
            locked = '<locked>TRUE</locked>' in tblk[:400]
            enabled = '<enabled>FALSE</enabled>' not in tblk[:400]
            for m in re.finditer(r'<clipitem[ >]', tblk):
                i = tlo + m.start(); j = tblk.find('</clipitem>', m.start())
                blk = tblk[m.start():j if j > 0 else m.start() + 12000]
                st, en = num(blk, 'start'), num(blk, 'end')
                if st is None or en is None or st < 0: continue
                nm = re.search(r'<name>(.*?)</name>', blk)
                fid = re.search(r'<file id="([^"]+)"', blk)
                pa = re.search(r'<pathurl>(.*?)</pathurl>', blk)
                path_ = pa.group(1) if pa else (filepath.get(fid.group(1), '') if fid else '')
                lab = re.search(r'<labels>.*?<label2>(.*?)</label2>', blk, re.S)
                sin, sout = num(blk, 'in'), num(blk, 'out')
                fils = re.findall(r'<effectid>(.*?)</effectid>', blk)
                nested = ('<sequence' in blk[:3000]) or (not path_ and bool(re.search(r'Nested Sequence', nm.group(1) if nm else '')))
                sc = param(blk, 'basic', 'scale'); pos = param(blk, 'basic', 'center')
                op = param(blk, 'opacity', 'opacity')
                lvl = param(blk, 'audiolevels', 'level')
                speed = None
                if sin is not None and sout is not None and en > st:
                    speed = round((sout - sin) / (en - st), 3)
                clips.append(dict(
                    kind=kind, track=n, a=round(st / fps, 4), b=round(en / fps, 4),
                    dur=round((en - st) / fps, 4), name=nm.group(1) if nm else '',
                    path=path_, label=lab.group(1) if lab else '', nested=nested,
                    scale=(sc if sc is not None else 100.0), center=pos,
                    opacity=(op if op is not None else 100.0),
                    level=lvl, speed=speed, filters=[f for f in fils if f not in ('basic', 'opacity', 'audiolevels')],
                    track_locked=locked, track_enabled=enabled))
    return dict(sequence=name, fps=fps, clips=clips, nests=nests)


if __name__ == '__main__':
    src = sys.argv[1]
    d = parse(src)
    vc = [c for c in d['clips'] if c['kind'] == 'V']; ac = [c for c in d['clips'] if c['kind'] == 'A']
    print(f"{d['sequence']} @ {d['fps']:.3f} fps · {len(vc)} video clips on {max((c['track'] for c in vc), default=0)} tracks · "
          f"{len(ac)} audio clips on {max((c['track'] for c in ac), default=0)} tracks")
    print('  labels:', dict(Counter(c['label'] or '-' for c in vc)))
    print('  end   :', round(max(c['b'] for c in d['clips']), 3), 's')
    if '--json' in sys.argv:
        out = sys.argv[sys.argv.index('--json') + 1]
        json.dump(d, open(out, 'w'), indent=1); print('  wrote', out)
