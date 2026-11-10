#!/usr/bin/env python3
"""MarketOps brand intro video, 1920x1080, in the brand book's style.
python3 promo.py audio            -> builds timeline.json, mix.wav, captions.srt
python3 promo.py frames t1,t2,..  -> preview PNGs
python3 promo.py render a b out   -> frames [a, b) to out.mp4 (video only)
"""
import glob, json, math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = '/home/claude/marketops-images'
W, H, FPS = 1920, 1080, 30   # design units
K = 4 / 3; PW, PH = 2560, 1440  # pixels (1440p)
INK = (11, 11, 11); PAGE = (19, 19, 19); CARD = (23, 23, 23); BORDER = (46, 46, 46)
OLIVE = (53, 57, 28); LIME = (198, 242, 78); WHITE = (255, 255, 255); MUTED = (135, 135, 135); FAINT = (63, 63, 63)
F800 = REPO + '/youtube-shorts/assets/Inter-ExtraBold.otf'; F700 = REPO + '/youtube-shorts/assets/Inter-Bold.otf'
F400 = '/usr/share/fonts/opentype/inter/Inter-Regular.otf'
TARGET = 69.0

def ease(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def ease_io(t): t = min(max(t, 0), 1); return t * t * (3 - 2 * t)
def back(t):
    t = min(max(t, 0), 1); c = 1.6; t -= 1
    return 1 + (c + 1) * t ** 3 + c * t ** 2

_f = {}
def font(p, s):
    if (p, s) not in _f: _f[(p, s)] = ImageFont.truetype(p, max(1, round(s * K)))
    return _f[(p, s)]

class SD:
    """ImageDraw that takes design (1920x1080) units and draws at 1440p."""
    def __init__(s, im): s.d = ImageDraw.Draw(im)
    def _xy(s, xy):
        if isinstance(xy[0], (tuple, list)): return [tuple(v * K for v in p) for p in xy]
        return tuple(v * K for v in xy)
    def _kw(s, kw):
        if 'width' in kw: kw['width'] = max(1, round(kw['width'] * K))
        return kw
    def rectangle(s, xy, **kw): s.d.rectangle(s._xy(xy), **s._kw(kw))
    def rounded_rectangle(s, xy, radius=0, **kw): s.d.rounded_rectangle(s._xy(xy), radius=radius * K, **s._kw(kw))
    def ellipse(s, xy, **kw): s.d.ellipse(s._xy(xy), **s._kw(kw))
    def line(s, xy, **kw): s.d.line(s._xy(xy), **s._kw(kw))
    def text(s, xy, t, **kw): s.d.text(s._xy(xy), t, **kw)
    def textlength(s, t, font): return s.d.textlength(t, font=font) / K

def new(w, h, c=(0, 0, 0, 0)): return Image.new('RGBA', (round(w * K), round(h * K)), c)
def logo_w(A, lw):
    lw = round(lw * K); return A['logo'].resize((lw, int(lw * A['logo'].height / A['logo'].width)), Image.LANCZOS)

# ------------------------------------------------------------------ audio
SR = 44100
def load_wav(p):
    import soundfile as sf
    a, sr = sf.read(p, dtype='float32')
    if a.ndim > 1: a = a.mean(1)
    return np.interp(np.arange(0, len(a) * SR // sr) / SR * sr, np.arange(len(a)), a).astype(np.float32)

GROUPS = [[0], [1], [2], [3], [4], [5], [6, 7], [8, 9, 10, 11, 12, 13], [14, 15], [16], [17], [18], [19], [20], [21, 22], [23], [24], [25]]

def build_audio():
    lines = json.load(open(HERE + '/lines.json'))
    vos = [load_wav(HERE + f'/vo_{i:02d}.wav') for i in range(len(lines))]
    durs = [len(v) / SR for v in vos]
    intro, outro = 1.1, 2.4
    in_gap, sec_gap = 0.12, 0.42
    n_in = sum(len(g) - 1 for g in GROUPS); n_sec = len(GROUPS) - 1
    free = TARGET - intro - outro - sum(durs)
    scale = free / (n_in * in_gap + n_sec * sec_gap)
    in_gap *= scale; sec_gap *= scale
    t = intro; starts = [0] * len(lines); scenes = []
    for gi, g in enumerate(GROUPS):
        s0 = t
        for k, i in enumerate(g):
            starts[i] = t; t += durs[i] + (in_gap if k < len(g) - 1 else 0)
        scenes.append([s0 if gi else 0.0, None])
        t += sec_gap if gi < len(GROUPS) - 1 else 0
    for gi in range(len(scenes) - 1): scenes[gi][1] = scenes[gi + 1][0] - sec_gap * 0.5
    for gi in range(1, len(scenes)): scenes[gi][0] = scenes[gi - 1][1]
    scenes[-1][1] = TARGET
    N = int(TARGET * SR)
    vo = np.zeros(N, np.float32); duck = np.ones(N, np.float32)
    for i, v in enumerate(vos):
        s = int(starts[i] * SR); v = v / (np.abs(v).max() + 1e-6) * 0.9
        vo[s:s + len(v)] += v[:N - s]; duck[max(0, s - 3000):s + len(v) + 3000] = 0.32
    duck = np.convolve(duck, np.ones(6000) / 6000, 'same').astype(np.float32)
    mus = music(N, [sc[0] for sc in scenes])
    mix = vo * 1.0 + mus * duck * 0.42
    fade = int(1.2 * SR); mix[-fade:] *= np.linspace(1, 0, fade) ** 1.5
    mix = mix / (np.abs(mix).max() + 1e-6) * 0.95
    with wave.open(HERE + '/mix.wav', 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes((mix * 32767).astype(np.int16).tobytes())
    json.dump({'starts': starts, 'durs': durs, 'scenes': scenes, 'lines': lines}, open(HERE + '/timeline.json', 'w'), indent=1)
    # captions
    def ts(x): return f'{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(x * 1000 % 1000):03d}'
    srt = []
    for i, l in enumerate(lines):
        txt = l.replace('marketops dot in', 'marketops.in').replace('UI UX', 'UI/UX')
        srt.append(f'{i + 1}\n{ts(starts[i])} --> {ts(starts[i] + durs[i])}\n{txt}\n')
    open(HERE + '/captions.srt', 'w').write('\n'.join(srt))
    print('scenes', [(round(a, 2), round(b, 2)) for a, b in scenes])

def lowpass(x, a):
    from scipy.signal import lfilter
    return lfilter([1 - a], [1, -a], x).astype(np.float32)

def music(N, hits):
    rng = np.random.default_rng(7); bpm = 118; beat = 60 / bpm
    out = np.zeros(N, np.float32)
    def add(sig, t, v=1.0):
        s = int(t * SR)
        if 0 <= s < N: out[s:s + len(sig)] += sig[:N - s] * v
    L = int(0.35 * SR); tt = np.arange(L) / SR
    kick = (np.sin(2 * np.pi * np.cumsum(np.linspace(110, 42, L)) / SR) * np.exp(-tt * 9)).astype(np.float32)
    Ls = int(0.2 * SR); clap = (rng.normal(0, 1, Ls) * np.exp(-np.arange(Ls) / SR * 22)).astype(np.float32)
    clap = clap - lowpass(clap, 0.85)
    Lh = int(0.05 * SR); hat = rng.normal(0, 1, Lh).astype(np.float32); hat = (hat - lowpass(hat, 0.6)) * np.exp(-np.arange(Lh) / SR * 80)
    roots = [45, 41, 48, 43]  # A F C G
    chords = [[57, 60, 64], [53, 57, 60], [55, 60, 64], [55, 59, 62]]
    def saw(f, d):
        n = int(d * SR); ph = (np.arange(n) * f / SR) % 1.0
        return (2 * ph - 1).astype(np.float32)
    nbeats = int(TARGET / beat) + 2
    for b in range(nbeats):
        t = b * beat; bar = (b // 4) % 4
        if t < 1.0: continue
        add(kick, t, 0.9)
        if b % 4 in (1, 3): add(clap, t, 0.35)
        for h in (0.5,): add(hat, t + h * beat, 0.25)
        add(hat, t, 0.12)
        # bass: 8th notes
        f = 440 * 2 ** ((roots[bar] - 69) / 12)
        for e in (0, 0.5):
            d = beat * 0.45; bs = lowpass(saw(f, d), 0.92) * np.exp(-np.arange(int(d * SR)) / SR * 6)
            add(bs, t + e * beat, 0.5)
        if b % 4 == 0:  # pad per bar
            d = beat * 4; pad = np.zeros(int(d * SR), np.float32)
            for m in chords[bar]:
                fr = 440 * 2 ** ((m - 69) / 12)
                pad += saw(fr, d) + saw(fr * 1.006, d)
            env = np.minimum(1, np.arange(len(pad)) / (0.3 * SR)) * np.minimum(1, (len(pad) - np.arange(len(pad))) / (0.3 * SR))
            add(lowpass(pad, 0.97) * env * 0.08, t, 1.0)
    # whoosh + impact on scene changes
    for h in hits[1:]:
        n = int(0.4 * SR); w = rng.normal(0, 1, n).astype(np.float32); w = lowpass(w, 0.9) * np.sin(np.linspace(0, np.pi, n)) ** 2
        add(w * 0.6, h - 0.3)
    add(kick * 1.2, hits[0] + 1.0)
    return out / (np.abs(out).max() + 1e-6)

# ------------------------------------------------------------------ assets
def load_assets():
    A = {}
    lg = Image.open(REPO + '/brand/marketops-logo-transparent.png').convert('RGBA')
    A['logo'] = lg
    posts = sorted(glob.glob(REPO + '/daily/*/1[0-9]00.png'))
    imgs = []
    for p in posts:
        cw0, ch0 = 576, 720
        im = Image.open(p).convert('RGB').resize((cw0, ch0), Image.LANCZOS)
        card = Image.new('RGBA', (cw0, ch0), (0, 0, 0, 0)); m = Image.new('L', (cw0, ch0), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, cw0 - 1, ch0 - 1), radius=29, fill=255)
        card.paste(im, (0, 0), m); imgs.append(card)
    A['cards'] = imgs
    # tilted wall mosaic
    cw, ch, gap = 400, 500, 40; cols, rows = 9, 5
    mos = Image.new('RGBA', (cols * (cw + gap), rows * (ch + gap)), (0, 0, 0, 0))
    k = 0
    for r in range(rows):
        for c in range(cols):
            im = imgs[(k * 7) % len(imgs)].resize((cw, ch), Image.LANCZOS); k += 1
            mos.alpha_composite(im, (c * (cw + gap) + (r % 2) * 80, r * (ch + gap)))
    A['wall'] = mos.rotate(16, resample=Image.BICUBIC, expand=True)
    return A

# ------------------------------------------------------------------ text
def parse(s):
    out = []; lime = False; cur = []
    import re
    for tok in re.findall(r'\[|\]|\s+|[^\s\[\]]+', s):
        if tok == '[': lime = True
        elif tok == ']': lime = False
        elif tok.isspace():
            if cur: out.append(cur); cur = []
        else: cur.append((tok, lime))
    if cur: out.append(cur)
    return out

_wc = {}
def word_img(word, size, fp, color):
    k = (tuple(word), size, fp, color)
    if k in _wc: return _wc[k]
    f = font(fp, size); d = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    w = int(sum(d.textlength(t, font=f) for t, _ in word)) + 6
    asc, desc = f.getmetrics()
    im = Image.new('RGBA', (w, asc + desc + 6), (0, 0, 0, 0)); dr = ImageDraw.Draw(im); x = 2
    for t, lime in word:
        dr.text((x, 2), t, font=f, fill=LIME if lime else color); x += d.textlength(t, font=f)
    _wc[k] = im; return im

def kinetic(im, text, t, cx, cy, size, fp=F800, color=WHITE, maxw=1600, stagger=0.07, dur=0.45, align='center', lh=1.08, out_t=None):
    """Words rise into place one after another. t = seconds since the text starts."""
    cx, cy, maxw = cx * K, cy * K, maxw * K; px = size * K
    words = parse(text); f = font(fp, size); d = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    space = d.textlength(' ', font=f)
    imgs = [word_img(w, size, fp, color) for w in words]
    lines = [[]]; lw = 0
    for wi in imgs:
        if lines[-1] and lw + space + wi.width > maxw: lines.append([]); lw = 0
        lines[-1].append(wi); lw += wi.width + (space if len(lines[-1]) > 1 else 0)
    LH = int(px * lh); y0 = cy - LH * len(lines) / 2; k = 0
    for li, ln in enumerate(lines):
        tw = sum(w.width for w in ln) + space * (len(ln) - 1)
        x = cx - tw / 2 if align == 'center' else cx
        for w in ln:
            p = ease((t - k * stagger) / dur)
            if out_t is not None: p *= 1 - ease((t - out_t) / 0.25)
            if p > 0.01:
                dy = (1 - p) * px * 0.6
                ww = w
                if p < 0.99:
                    ww = w.copy(); ww.putalpha(w.getchannel('A').point(lambda v, p=p: int(v * p)))
                im.alpha_composite(ww, (int(x), int(y0 + li * LH + dy)))
            x += w.width + space; k += 1

def label(im, text, cx, cy, size=30, color=MUTED, fp=F400, alpha=1.0, anchor='mm'):
    if alpha <= 0.01: return
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.text((cx * K, cy * K), text, font=font(fp, size), fill=color + (int(255 * alpha),), anchor=anchor)
    im.alpha_composite(lay)

def paste(im, src, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if alpha <= 0.01 or scale <= 0.01: return
    s = src
    if abs(scale - 1) > 0.005: s = s.resize((max(1, int(s.width * scale)), max(1, int(s.height * scale))), Image.BILINEAR)
    if abs(rot) > 0.05: s = s.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 0.99: s = s.copy(); s.putalpha(s.getchannel('A').point(lambda v: int(v * alpha)))
    x, y = int(cx * K - s.width / 2), int(cy * K - s.height / 2)
    im.alpha_composite(s, (x, y)) if x >= 0 and y >= 0 and x + s.width <= PW and y + s.height <= PH else _safe(im, s, x, y)

def _safe(im, s, x, y):
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); lay.paste(s, (x, y), s); im.alpha_composite(lay)

def square(im, x, y, s, a=1.0):
    SD(im).rectangle((x, y, x + s, y + s), fill=LIME + (int(255 * a),))

# ------------------------------------------------------------------ scenes
def sc_logo(im, t, d, A, L):
    p = back(t / 0.7); lw = 900
    lg = logo_w(A, lw)
    paste(im, lg, W / 2, H / 2 - 20, scale=0.85 + 0.15 * p, alpha=ease(t / 0.5))
    wln = int(700 * ease((t - 0.4) / 0.6))
    SD(im).rectangle((W / 2 - wln / 2, H / 2 + 110, W / 2 + wln / 2, H / 2 + 114), fill=LIME)

def sc_agency(im, t, d, A, L):
    kinetic(im, 'Ecommerce. Advertising. [Creative.]', t, W / 2, H / 2 - 50, 120, maxw=1800)
    label(im, 'Proudly based in India', W / 2, H / 2 + 110, 40, MUTED, F700, alpha=ease((t - 1.6) / 0.5))

def sc_three(im, t, d, A, L):
    items = ['Look better.', 'Speak louder.', 'Grow [smarter.]']
    for i, s in enumerate(items):
        st = i * d / 3.4
        kinetic(im, s, t - st, W / 2, 330 + i * 210, 150)

def sc_fan(im, t, d, A, L):
    cards = A['cards']; n = 5; p = ease_io(t / 1.0)
    for i in range(n):
        k = i - 2; ang = -k * 11 * p; x = W / 2 + k * 300 * p; y = 520 + abs(k) * 40 * p - 10 * math.sin(t * 1.5 + i)
        paste(im, cards[(i * 3 + 1) % len(cards)], x, y + (1 - ease(t / 0.6)) * 400, scale=0.92, rot=ang, alpha=ease(t / 0.4))
    words = ['Branding', 'Design', 'Marketing', 'Storytelling']
    for i, w in enumerate(words):
        a = ease((t - 0.6 - i * d / 5.5) / 0.35)
        label(im, w, W / 2 + (i - 1.5) * 330, 975, 46, LIME if i == 3 else WHITE, F800, alpha=a)

def sc_belief(im, t, d, A, L):
    kinetic(im, 'Creativity is more than just [visuals.]', t, W / 2, H / 2, 128, maxw=1500)

def sc_spe(im, t, d, A, L):
    for i, s in enumerate(['Strategy.', 'Purpose.', '[Emotion.]']):
        kinetic(im, s, t - i * d / 3.6, W / 2, 300 + i * 240, 190)

def sc_partners(im, t, d, A, L):
    st = L['starts']; d6 = L['durs'][6]
    t2 = t - (st[7] - st[6])
    if t2 < 0:
        words = ['Founders.', 'Dreamers.', 'Innovators.', 'Businesses.']
        i = min(3, int(t / (d6 / 4))); lt = t - i * d6 / 4
        label(im, 'We partner with', W / 2, H / 2 - 150, 44, MUTED, F700, alpha=ease(t / 0.4))
        kinetic(im, f'[{words[i]}]' if i == 3 else words[i], lt, W / 2, H / 2 + 20, 170, stagger=0)
    else:
        wall = A['wall']; ox = -200 - t2 * 60; oy = -350 + t2 * 25
        paste(im, wall, ox + wall.width / K / 2 + 200, oy + wall.height / K / 2, alpha=ease(t2 / 0.5))
        ov = Image.new('RGBA', (PW, PH), PAGE + (int(255 * 0.62),)); im.alpha_composite(ov)
        kinetic(im, 'Ideas into meaningful [brand experiences.]', t2, W / 2, H / 2, 110, maxw=1500)

SERV = [('01', 'Branding & creative design'), ('02', 'Social media marketing'), ('03', 'Performance marketing'),
        ('04', 'UI/UX & website development'), ('05', 'Ecommerce marketplace management'), ('06', 'Marketplace performance marketing')]

def sc_services(im, t, d, A, L):
    st = L['starts']; base = st[8]; T = t + 0  # scene starts at base (approx)
    tt = t - (st[8] - L['scene_start'])
    if tt < L['durs'][8] + 0.1:
        kinetic(im, 'What we [do]', tt, W / 2, H / 2, 170)
        return
    # which service
    marks = [st[9], st[10], st[11], st[12], st[13], st[13] + L['durs'][13] * 0.48]
    now = L['scene_start'] + t; i = 0
    for k, m in enumerate(marks):
        if now >= m - 0.05: i = k
    lt = now - marks[i]
    num, name = SERV[i]
    label(im, num, 300, H / 2 - 10, 300, FAINT, F800, alpha=ease(lt / 0.3), anchor='mm')
    kinetic(im, name, lt, 520, H / 2 - 60, 84, maxw=780, align='left', stagger=0.05)

    label(im, 'What we do', 520, H / 2 - 190, 34, MUTED, F700, anchor='lm')
    c = A['cards'][(i * 5 + 2) % len(A['cards'])]
    paste(im, c, 1500 + (1 - ease(lt / 0.5)) * 400, H / 2, scale=1.25, rot=-6, alpha=ease(lt / 0.4))
    for k in range(6):
        SD(im).rectangle((520 + k * 46, H / 2 + 200, 520 + k * 46 + 34, H / 2 + 206), fill=LIME if k == i else BORDER)

def browser(im, t, A, alpha):
    bw, bh = 1360, 780; x0, y0 = (W - bw) / 2, 170 + (1 - ease(t / 0.6)) * 300
    lay = new(bw, bh); d = SD(lay)
    d.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=24, fill=CARD, outline=BORDER, width=2)
    for k, c in enumerate(((70, 70, 70), (70, 70, 70), (70, 70, 70))): d.ellipse((28 + k * 30, 26, 44 + k * 30, 42), fill=c)
    d.rounded_rectangle((bw / 2 - 180, 18, bw / 2 + 180, 52), radius=17, fill=PAGE); d.text((bw / 2, 35), 'marketops.in', font=font(F700, 22), fill=MUTED, anchor='mm')
    d.line((0, 70, bw, 70), fill=BORDER, width=2)
    scroll = min(1, max(0, (t - 1.6) / 1.6)) * 330
    content = new(bw - 4, 1200, PAGE + (255,)); cd = SD(content)
    lg = logo_w(A, 220); content.alpha_composite(lg, (round(50 * K), round(30 * K)))
    for k, m in enumerate(['Services', 'Work', 'Contact']): cd.text((bw - 420 + k * 130, 42), m, font=font(F400, 22), fill=MUTED)
    cd.text((60, 170), "Built for the brands", font=font(F800, 72), fill=WHITE)
    cd.text((60, 255), "that don't settle", font=font(F800, 72), fill=WHITE)
    tw = cd.textlength("that don't settle", font=font(F800, 72)); cd.rectangle((60 + tw + 8, 307, 60 + tw + 24, 323), fill=LIME)
    cd.text((60, 360), 'Ecommerce growth: ads, marketplaces, creative, web and SEO.', font=font(F400, 28), fill=MUTED)
    cd.rounded_rectangle((60, 430, 330, 492), radius=31, fill=LIME); cd.text((195, 461), 'Explore services', font=font(F700, 24), fill=INK, anchor='mm')
    names = ['Ecommerce Solutions', 'Performance Ads', 'Creative Studio', 'Web Development', 'SEO', 'Overseas Growth']
    for k, n in enumerate(names):
        cx0 = 60 + (k % 3) * 420; cy0 = 600 + (k // 3) * 270
        cd.rounded_rectangle((cx0, cy0, cx0 + 390, cy0 + 240), radius=24, fill=CARD, outline=BORDER, width=2)
        cd.ellipse((cx0 + 28, cy0 + 28, cx0 + 84, cy0 + 84), fill=OLIVE); cd.rectangle((cx0 + 50, cy0 + 50, cx0 + 62, cy0 + 62), fill=LIME)
        cd.text((cx0 + 360, cy0 + 30), f'0{k + 1}', font=font(F800, 40), fill=FAINT, anchor='ra')
        cd.text((cx0 + 28, cy0 + 120), n, font=font(F700, 30), fill=WHITE)
        cd.text((cx0 + 28, cy0 + 175), 'Explore service ↗', font=font(F400, 22), fill=MUTED)
    lay.alpha_composite(content.crop((0, round(scroll * K), round((bw - 4) * K), round((scroll + bh - 74) * K))), (round(2 * K), round(72 * K)))
    if alpha < 0.99: lay.putalpha(lay.getchannel('A').point(lambda v: int(v * alpha)))
    im.alpha_composite(lay, (round(x0 * K), round(y0 * K)))

def sc_build(im, t, d, A, L):
    st = L['starts']; split = st[15] - L['scene_start']
    if t < split:
        cards = A['cards']
        for i in range(7):
            k = i - 3; p = ease_io((t - 0.05 * abs(k)) / 0.9)
            paste(im, cards[(i * 2 + 5) % len(cards)], W / 2 + k * 250 * p, 470 + abs(k) * 30 * p, scale=0.75, rot=-k * 8 * p, alpha=ease(t / 0.4))
        label(im, 'Bold brand identities. Eye-catching visuals.', W / 2, 960, 46, WHITE, F800, alpha=ease((t - 0.4) / 0.4))
    else:
        browser(im, t - split, A, ease((t - split) / 0.4))
        label(im, 'Websites and campaigns that move people', W / 2, 1010, 40, WHITE, F800, alpha=ease((t - split - 0.5) / 0.4))

def sc_impact(im, t, d, A, L):
    kinetic(im, 'Imagination', t, W / 2, H / 2 - 120, 150, color=MUTED)
    a = ease((t - 0.55) / 0.3); SD(im).line((W / 2, H / 2 - 40, W / 2, H / 2 + 20), fill=LIME + (int(255 * a),), width=4)
    kinetic(im, 'into [impact.]', t - 0.7, W / 2, H / 2 + 110, 170)

def sc_name(im, t, d, A, L):
    lw = 1100; lg = logo_w(A, lw)
    paste(im, lg, W / 2, H / 2 - 60, scale=0.95 + 0.05 * ease(t / 1.2), alpha=ease(t / 0.4))
    label(im, 'Where brands sell', W / 2 - 250, H / 2 + 110, 34, MUTED, F700, alpha=ease((t - 0.5) / 0.4))
    label(im, 'The work that makes it happen', W / 2 + 330, H / 2 + 110, 34, LIME, F700, alpha=ease((t - 0.9) / 0.4))

def sc_mission(im, t, d, A, L):
    items = ['Own your space.', 'Command attention.', 'Lead with [clarity.]']
    for i, s in enumerate(items):
        kinetic(im, s, t - i * d / 3.3, W / 2, 300 + i * 220, 140)

def sc_notjust(im, t, d, A, L):
    kinetic(im, "We don't just create designs", t, W / 2, H / 2 - 90, 100, color=MUTED)
    kinetic(im, 'and spend money.', t - 0.6, W / 2, H / 2 + 50, 100, color=MUTED)
    a = ease((t - 1.5) / 0.4); f = font(F800, 100); tw = SD(im).textlength('and spend money.', font=f)
    SD(im).rectangle((W / 2 - tw / 2, H / 2 + 108, W / 2 - tw / 2 + tw * a, H / 2 + 116), fill=LIME)

def sc_define(im, t, d, A, L):
    for i, s in enumerate(['Define [brands.]', 'Tell stories.', 'Build connections.']):
        kinetic(im, s, t - i * d / 3.4, W / 2, 300 + i * 220, 140)

def icon(d, kind, cx, cy, r=22):
    w = 4
    if kind == 0:  # spark
        for a in range(0, 360, 45):
            rr = r if a % 90 == 0 else r * 0.6
            d.line((cx, cy, cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a))), fill=LIME, width=w)
    elif kind == 1:  # target
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=LIME, width=w); d.ellipse((cx - r / 2, cy - r / 2, cx + r / 2, cy + r / 2), outline=LIME, width=w)
    elif kind == 2:  # trend arrow
        d.line((cx - r, cy + r * .6, cx - r * .2, cy - r * .1, cx + r * .2, cy + r * .3, cx + r, cy - r * .6), fill=LIME, width=w, joint='curve')
        d.line((cx + r * .45, cy - r * .6, cx + r, cy - r * .6, cx + r, cy - r * .05), fill=LIME, width=w)
    else:  # bulb
        d.ellipse((cx - r * .7, cy - r, cx + r * .7, cy + r * .3), outline=LIME, width=w)
        d.line((cx - r * .35, cy + r * .55, cx + r * .35, cy + r * .55), fill=LIME, width=w); d.line((cx - r * .25, cy + r * .85, cx + r * .25, cy + r * .85), fill=LIME, width=w)

def sc_values(im, t, d, A, L):
    st = L['starts']; split = st[22] - L['scene_start']
    if t < split:
        kinetic(im, 'Every project is driven by', t, W / 2, H / 2, 110); return
    lt = t - split; names = ['Creativity', 'Strategy', 'Measurable growth', 'Big ideas']
    for i, n in enumerate(names):
        p = back((lt - i * L['durs'][22] / 4.5) / 0.5); a = ease((lt - i * L['durs'][22] / 4.5) / 0.3)
        if a <= 0.01: continue
        cw, chh = 380, 430; lay = new(cw, chh); dd = SD(lay)
        dd.rounded_rectangle((0, 0, cw - 1, chh - 1), radius=24, fill=CARD, outline=BORDER, width=2)
        dd.ellipse((32, 32, 120, 120), fill=OLIVE); icon(dd, i, 76, 76)
        dd.text((cw - 32, 36), f'0{i + 1}', font=font(F800, 64), fill=FAINT, anchor='ra')
        f = font(F800, 44 if len(n) < 12 else 38); words = n.split(); yy = 290
        if len(n) > 12: dd.text((32, 250), words[0], font=f, fill=WHITE); dd.text((32, 300), ' '.join(words[1:]), font=f, fill=WHITE)
        else: dd.text((32, 290), n, font=f, fill=WHITE)
        paste(im, lay, 300 + i * 440, H / 2 + (1 - p) * 120, alpha=a)

def sc_together(im, t, d, A, L):
    kinetic(im, "Let's build it [together.]", t, W / 2, H / 2, 160)

def sc_future(im, t, d, A, L):
    kinetic(im, 'The future belongs to those who dare to [create.]', t, W / 2, H / 2, 112, maxw=1500, stagger=0.06)

def sc_outro(im, t, d, A, L):
    lw = 760; lg = logo_w(A, lw)
    paste(im, lg, W / 2, H / 2 - 150, scale=0.9 + 0.1 * back(t / 0.6), alpha=ease(t / 0.4))
    label(im, 'For enquiries', W / 2, H / 2 + 10, 34, MUTED, F700, alpha=ease((t - 0.3) / 0.4))
    label(im, 'hello@marketops.in', W / 2, H / 2 + 75, 54, WHITE, F800, alpha=ease((t - 0.5) / 0.4))
    a = ease((t - 0.8) / 0.4)
    if a > 0.01:
        lay = Image.new('RGBA', (PW, PH), (0, 0, 0, 0)); dd = SD(lay)
        dd.rounded_rectangle((W / 2 - 190, H / 2 + 140, W / 2 + 190, H / 2 + 222), radius=41, fill=LIME + (int(255 * a),))
        dd.text((W / 2, H / 2 + 181), 'marketops.in', font=font(F800, 40), fill=INK + (int(255 * a),), anchor='mm')
        im.alpha_composite(lay)
    fa = ease((t - d + 1.0) / 0.9)
    if fa > 0: im.alpha_composite(Image.new('RGBA', (PW, PH), INK + (int(255 * fa),)))

SCENES = [sc_logo, sc_agency, sc_three, sc_fan, sc_belief, sc_spe, sc_partners, sc_services, sc_build, sc_impact,
          sc_name, sc_mission, sc_notjust, sc_define, sc_values, sc_together, sc_future, sc_outro]

# ------------------------------------------------------------------ frame
_base = None
def base():
    global _base
    if _base is None:
        y, x = np.mgrid[0:PH, 0:PW]; r = np.sqrt(((x - PW / 2) / PW) ** 2 + ((y - PH / 2) / PH) ** 2)
        v = np.clip(1 - r * 1.2, 0, 1)[..., None]
        arr = (np.array(PAGE) * (1 - v * 0.0) + (np.array(CARD) - np.array(PAGE)) * v * 1.4).clip(0, 255).astype(np.uint8)
        _base = Image.fromarray(np.dstack([arr, np.full((PH, PW), 255, np.uint8)]), 'RGBA')
    return _base

def frame(t, A, L):
    sc = L['scenes']; i = 0
    for k, (a, b) in enumerate(sc):
        if a <= t: i = k
    a, b = sc[i]; im = base().copy()
    L['scene_start'] = a
    SCENES[i](im, t - a, b - a, A, L)
    # progress line + corner mark
    SD(im).rectangle((0, H - 6, int(W * t / TARGET), H), fill=LIME)
    return im.convert('RGB')

def main():
    cmd = sys.argv[1]
    if cmd == 'audio': build_audio(); return
    L = json.load(open(HERE + '/timeline.json')); A = load_assets()
    if cmd == 'frames':
        for s in sys.argv[2].split(','):
            frame(float(s), A, L).save(HERE + f'/pv_{float(s):05.2f}.png')
        return
    a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{PW}x{PH}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', out + '.tmp.mp4'], stdin=subprocess.PIPE)
    for k in range(a, b): p.stdin.write(frame(k / FPS, A, L).tobytes())
    p.stdin.close()
    if p.wait() == 0: os.replace(out + '.tmp.mp4', out)

if __name__ == '__main__':
    main()
