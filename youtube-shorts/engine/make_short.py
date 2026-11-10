#!/usr/bin/env python3
"""Turn one storyboard JSON into a voiced 1080x1920 YouTube Short.

Usage: python3 make_short.py storyboard.json out.mp4 --model DIR

Storyboard keys: id, pillar ("marketing tip" | "business fact" | "interesting fact"),
beats: list of {say, show, emoji?, big?}. In `show`, wrap words in [brackets] to colour them lime.
"""
import argparse, json, math, os, random, re, subprocess, sys, tempfile, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
W, H, FPS = 1080, 1920, 30
BG = (19, 19, 19); LIME = (198, 242, 78); WHITE = (255, 255, 255); GREY = (170, 170, 170)
F800 = os.path.join(ROOT, 'assets', 'Inter-ExtraBold.otf'); F700 = os.path.join(ROOT, 'assets', 'Inter-Bold.otf')
EMOJI = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'
SR = 24000
PILL = {'marketing tip': 'MARKETING TIP', 'business fact': 'BUSINESS FACT', 'interesting fact': 'DID YOU KNOW?'}

_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]

def ease_out(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def back(t):
    t = min(max(t, 0), 1); c = 1.70158; t -= 1
    return 1 + (c + 1) * t ** 3 + c * t ** 2

# ---------------- text helpers
def parse_marked(s):
    """'Why [prices] end?' -> words, each a list of (text, is_lime) parts.
    Punctuation right after ']' stays attached to the word (no stray space)."""
    words = []; lime = False; last = 0; gap = True
    for m in re.finditer(r'\[|\]|[^\s\[\]]+', s):
        if s[last:m.start()].strip() == '' and s[last:m.start()] != '': gap = True
        last = m.end(); tok = m.group()
        if tok == '[': lime = True
        elif tok == ']': lime = False
        else:
            if words and not gap: words[-1].append((tok, lime))
            else: words.append([(tok, lime)])
            gap = False
    return words

def wlen(word, f, d): return sum(d.textlength(t, font=f) for t, _ in word)

def wrap_words(words, f, maxw, d):
    lines, cur = [], []
    space = d.textlength(' ', font=f)
    for w in words:
        width = sum(wlen(x, f, d) for x in cur + [w]) + space * len(cur)
        if cur and width > maxw:
            lines.append(cur); cur = [w]
        else: cur.append(w)
    if cur: lines.append(cur)
    return lines

def text_block(s, size, maxw=920, color=WHITE, align='center', lh=1.12, fpath=F800, max_lines=4):
    """Render marked text into an RGBA image, auto-shrinking to fit max_lines."""
    words = parse_marked(s)
    d = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    while True:
        f = font(fpath, size)
        lines = wrap_words(words, f, maxw, d)
        if len(lines) <= max_lines or size < 40: break
        size -= 6
    line_h = int(size * lh)
    img = Image.new('RGBA', (maxw, line_h * len(lines) + int(size * 0.3)), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    space = d.textlength(' ', font=f)
    for i, ln in enumerate(lines):
        total = sum(wlen(w, f, d) for w in ln) + space * (len(ln) - 1)
        x = (maxw - total) / 2 if align == 'center' else 0
        for w in ln:
            for t, lime in w:
                dr.text((x, i * line_h), t, font=f, fill=LIME if lime else color)
                x += d.textlength(t, font=f)
            x += space
    return img

_ec = {}
def emoji_img(ch, size):
    k = (ch, size)
    if k in _ec: return _ec[k]
    img = None
    if ch and os.path.exists(EMOJI):
        try:
            f = ImageFont.truetype(EMOJI, 109)
            im = Image.new('RGBA', (160, 160), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
            bb = im.getbbox()
            if bb:
                im = im.crop(bb)
                r = size / max(im.size)
                img = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
        except Exception:
            img = None
    _ec[k] = img
    return img

def paste_center(base, img, cx, cy, scale=1.0, alpha=1.0):
    if img is None or alpha <= 0.01 or scale <= 0.01: return
    if abs(scale - 1) > 0.01:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
    if alpha < 0.99:
        a = img.getchannel('A').point(lambda v: int(v * alpha)); img = img.copy(); img.putalpha(a)
    base.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))

# ---------------- audio
def synth(beats, model_dir, voice, speed):
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(model_dir, 'kokoro-v1.0.int8.onnx'), os.path.join(model_dir, 'voices-v1.0.bin'))
    out = []
    for b in beats:
        a, sr = k.create(b['say'], voice=voice, speed=speed, lang='en-us')
        a = np.asarray(a, dtype=np.float32)
        if sr != SR: a = np.interp(np.arange(0, len(a) * SR // sr) / SR * sr, np.arange(len(a)) / 1.0, a).astype(np.float32)
        nz = np.where(np.abs(a) > 0.02)[0]
        s0, s1 = (nz[0], nz[-1]) if len(nz) else (0, len(a))
        out.append((a, s0 / SR, s1 / SR))
    return out

def word_times(text, t0, t1):
    words = text.split()
    wts = [len(re.sub(r'\W', '', w)) + 2 + (3 if w.endswith(',') else 0) + (5 if w[-1] in '.!?:' else 0) for w in words]
    tot = sum(wts) or 1; t = t0; res = []
    for w, x in zip(words, wts):
        d = (t1 - t0) * x / tot; res.append((w, t, t + d)); t += d
    return res

def music(n, seed):
    rng = np.random.default_rng(seed); rr = random.Random(seed)
    bpm = rr.choice([100, 108, 116]); beat = 60 / bpm; root = rr.choice([57, 60, 62])
    prog = rr.choice([[0, 5, 7, 5], [0, 7, 9, 5], [0, 9, 5, 7]])
    out = np.zeros(n, np.float32); cache = {}
    def pl(m, d):
        if (m, d) in cache: return cache[(m, d)]
        f = 440 * 2 ** ((m - 69) / 12); L = int(d * SR); p = max(2, int(SR / f)); b = rng.uniform(-1, 1, p); o = np.zeros(L, np.float32)
        for i in range(L):
            o[i] = b[i % p]; b[i % p] = .5 * (b[i % p] + b[(i + 1) % p]) * .996
        cache[(m, d)] = o; return o
    def add(a, t, v):
        s = int(t * SR)
        if s < n: out[s:s + len(a)] += a[:n - s] * v
    t = 0; i = 0
    while t * SR < n:
        c = root + prog[int(t / (beat * 4)) % 4]
        if i % 4 == 0: add(pl(c - 12, 1.2), t, .55)
        if i % 2 == 1:
            for j, o in enumerate((0, 4, 7)): add(pl(c + o, .45), t + j * .01, .18)
        i += 1; t += beat / 2
    return out

def whoosh(L):
    n = int(L * SR); x = np.random.default_rng(1).normal(0, 1, n).astype(np.float32)
    k = np.ones(40) / 40; x = np.convolve(x, k, 'same')
    env = np.sin(np.linspace(0, math.pi, n)) ** 2
    return x * env * 0.25

# ---------------- background
def make_blob(r, color, a):
    s = int(r * 2.6); im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), fill=color + (a,))
    return im.filter(ImageFilter.GaussianBlur(r * 0.45))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('story'); ap.add_argument('out')
    ap.add_argument('--model', default='/tmp/kokoro'); ap.add_argument('--voice', default='af_heart'); ap.add_argument('--speed', type=float, default=1.05)
    ap.add_argument('--frames', default='', help='comma list of seconds: save PNGs instead of video')
    a = ap.parse_args()
    sb = json.load(open(a.story)); beats = sb['beats']; pillar = sb.get('pillar', 'interesting fact')
    aud = synth(beats, a.model, sb.get('voice', a.voice), a.speed)
    # timeline
    LEAD, GAP = 0.25, 0.28
    T = []; t = LEAD
    for (au, s0, s1), b in zip(aud, beats):
        dur = len(au) / SR
        T.append(dict(start=t, end=t + dur + GAP, audio=au, words=word_times(b['say'], t + s0, t + s1)))
        t += dur + GAP
    total = t + 0.5; N = int(total * SR)
    T[-1]['end'] = total
    # audio mix
    vo = np.zeros(N, np.float32); duck = np.ones(N, np.float32); fx = np.zeros(N, np.float32)
    for seg in T:
        s = int(seg['start'] * SR); au = seg['audio'] / (np.abs(seg['audio']).max() + 1e-6) * 0.9
        vo[s:s + len(au)] += au[:N - s]; duck[max(0, s - 2400):s + len(au) + 2400] = 0.3
        w = whoosh(0.35); ws = max(0, s - int(0.12 * SR)); fx[ws:ws + len(w)] += w[:N - ws]
    duck = np.convolve(duck, np.ones(4800) / 4800, 'same').astype(np.float32)
    mix = vo + music(N, sum(map(ord, sb.get('id', 'x')))) * duck * 0.16 + fx * 0.5
    fade = int(0.4 * SR); mix[-fade:] *= np.linspace(1, 0, fade)
    mix = mix / (np.abs(mix).max() + 1e-6) * 0.93
    tmp = tempfile.mkdtemp(); wav = os.path.join(tmp, 'mix.wav')
    with wave.open(wav, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes((mix * 32767).astype(np.int16).tobytes())

    # static layers
    base = Image.new('RGBA', (W, H), BG + (255,))
    logo = Image.open(os.path.join(REPO, 'brand', 'marketops-logo-transparent.png')).convert('RGBA')
    logo = logo.resize((300, int(300 * logo.height / logo.width)), Image.LANCZOS)
    base.alpha_composite(logo, ((W - logo.width) // 2, 120))
    label = PILL.get(pillar, 'DID YOU KNOW?'); pf = font(F800, 40)
    d0 = ImageDraw.Draw(base); tw = d0.textlength(label, font=pf)
    px0, py0 = (W - tw) / 2 - 36, 230
    d0.rounded_rectangle((px0, py0, px0 + tw + 72, py0 + 76), radius=38, fill=LIME)
    d0.text((px0 + 36, py0 + 14), label, font=pf, fill=(11, 11, 11))
    blobA = make_blob(360, LIME, 34); blobB = make_blob(300, (90, 120, 255), 30)

    # per-beat visuals
    vis = []
    for b in beats:
        big = b.get('big'); show = b.get('show', '')
        vis.append(dict(
            big=text_block(big, 230, maxw=980, color=LIME, max_lines=1) if big else None,
            head=text_block(show, 92 if big else 100, maxw=940) if show else None,
            emo=emoji_img(b.get('emoji'), 170 if big else 300)))
    # caption chunks
    chunks = []
    for seg in T:
        ws = seg['words']; cur = []
        for w in ws:
            cur.append(w)
            if len(cur) == 3 or len(' '.join(x[0] for x in cur)) > 15 or w[0][-1] in '.,!?:':
                chunks.append(cur); cur = []
        if cur: chunks.append(cur)
    cf = font(F800, 74)

    def frame(t):
        im = base.copy()
        # moving blobs
        bx = 540 + 260 * math.sin(t * 0.35); by = 760 + 180 * math.cos(t * 0.27)
        im.alpha_composite(blobA, (int(bx - blobA.width / 2), int(by - blobA.height / 2)))
        cx2 = 540 + 300 * math.cos(t * 0.22 + 1); cy2 = 1150 + 160 * math.sin(t * 0.31)
        im.alpha_composite(blobB, (int(cx2 - blobB.width / 2), int(cy2 - blobB.height / 2)))
        # progress bar
        dr = ImageDraw.Draw(im)
        dr.rectangle((0, 0, int(W * min(t / total, 1)), 10), fill=LIME)
        # current beat
        i = max(0, max(k for k, s in enumerate(T) if s['start'] <= t) if t >= T[0]['start'] else 0)
        seg = T[i]; v = vis[i]; lt = t - seg['start']
        p = ease_out(lt / 0.35); bs = back(lt / 0.45)
        zoom = 1 + 0.03 * min(lt / max(seg['end'] - seg['start'], 0.1), 1)
        float_y = 10 * math.sin(t * 2.2)
        y = 520
        if v['emo'] is not None:
            paste_center(im, v['emo'], W / 2, y + (100 if v['big'] else 160) + float_y, scale=max(bs, 0.01) * zoom, alpha=p)
            y += 230 if v['big'] else 360
        if v['big'] is not None:
            paste_center(im, v['big'], W / 2, y + v['big'].height / 2 + 60 * (1 - p), scale=zoom, alpha=p)
            y += v['big'].height + 20
        if v['head'] is not None:
            hp = ease_out((lt - 0.12) / 0.35)
            paste_center(im, v['head'], W / 2, y + v['head'].height / 2 + 60 * (1 - hp), scale=zoom, alpha=hp)
        # captions
        cur = None
        for ch in chunks:
            if ch[0][1] - 0.05 <= t <= ch[-1][2] + 0.25: cur = ch
        if cur:
            words = [w for w, _, _ in cur]; txt = ' '.join(words)
            tw = dr.textlength(txt, font=cf); x = (W - tw) / 2; yy = 1330
            pop = back((t - cur[0][1] + 0.05) / 0.2)
            cap = Image.new('RGBA', (W, 140), (0, 0, 0, 0)); cd = ImageDraw.Draw(cap)
            for w, s, e in cur:
                col = LIME if s - 0.03 <= t <= e + 0.05 else WHITE
                cd.text((x, 20), w, font=cf, fill=col, stroke_width=6, stroke_fill=(0, 0, 0))
                x += cd.textlength(w + ' ', font=cf)
            paste_center(im, cap, W / 2, yy + 70, scale=0.85 + 0.15 * pop)
        return im.convert('RGB')

    if a.frames:
        for s in a.frames.split(','):
            frame(float(s)).save(f'{a.out}_{float(s):05.1f}.png')
        return
    nf = int(total * FPS)
    tmpv = a.out + '.tmp.mp4'
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-pix_fmt', 'yuv420p',
                          '-af', 'loudnorm=I=-15:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '160k', '-ar', '44100', '-ac', '2', '-movflags', '+faststart', '-shortest', tmpv], stdin=subprocess.PIPE)
    for k in range(nf):
        p.stdin.write(frame(k / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0: sys.exit('ffmpeg failed')
    os.replace(tmpv, a.out)
    print(json.dumps({'out': a.out, 'seconds': round(total, 1)}))

if __name__ == '__main__':
    main()
