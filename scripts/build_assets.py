#!/usr/bin/env python3
"""Builds the animated SVGs in assets/ for the profile README.

    pip install fonttools brotli
    python3 scripts/build_assets.py

Every word on the cards lives in this file: change it here and re-run rather
than editing the SVGs by hand (the terminal's timings are worked out from the
text). The type matches kingsdevandai.com: Plus Jakarta Sans and IBM Plex Mono,
both SIL OFL. They are fetched once into scripts/.fonts, then subset and
embedded in each SVG, because an SVG shown as an <img> can't load anything
from the network.

Animation is CSS where it can be, so prefers-reduced-motion switches it off,
and SMIL for the one thing CSS can't do in every browser (sweeping a gradient).
"""
import base64
import html
import io
import random
import re
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'assets'
FONT_DIR = HERE / '.fonts'
FONT_URL = 'https://kingsdevandai.com/fonts/'

# key: (family, file, weight range)
FONTS = {
    'sans': ('KDJakarta', 'jakarta-var-latin.woff2', '200 800'),
    'mono': ('KDPlex', 'plexmono-400-latin.woff2', '400'),
    'mono-bold': ('KDPlex', 'plexmono-600-latin.woff2', '600'),
}

# kingsdevandai.com, dark theme
BG, FG = '#141218', '#F4F1EA'
FLAME, EMBER, AMBER, DEEP, COPPER = '#F26B3F', '#FF7A4D', '#F2B23F', '#B33A16', '#C4835F'


def fg(a):
    return f'rgba(244,241,234,{a})'


# ── CONTENT ───────────────────────────────────────────────────────────────

HERO = {
    'kicker': 'KING’S DEVELOPMENT AND AI',
    'name': 'George King',
    'lead': 'I build',
    'words': ['bespoke software.', 'web applications.', 'AI-powered systems.', 'apps for the Mac.'],
    'tagline': 'Designed with purpose. Built with precision.',
}

# Each row is a typed command, a line of output (coloured runs), or the
# final idle prompt.
KEY, PUNCT, VAL, NOTE = COPPER, fg(.42), fg(.9), fg(.38)
TERMINAL = [
    ('cmd', 'whoami'),
    ('out', [('George King', FG), (' — designing & building software at ', fg(.66)),
             ('King’s Development and AI', AMBER)]),
    ('cmd', 'cat about.yml'),
    ('out', [('studio:   ', KEY), ('King’s Development and AI', VAL), ('  # kingsdevandai.com', NOTE)]),
    ('out', [('craft:    ', KEY), ('bespoke software, web apps, AI & automation', VAL)]),
    ('out', [('clients:  ', KEY), ('businesses across the UK', VAL)]),
    ('out', [('stack:    ', KEY), ('[', PUNCT), ('react, next.js, typescript, c#/.net, python, swift', VAL),
             (']', PUNCT)]),
    ('out', [('repos:    ', KEY), ('most of my projects are private', VAL), ('  # so this page is the tip of it', NOTE)]),
    ('out', [('belief:   ', KEY), ('"Understand the business first, then build the right solution."', AMBER)]),
    ('cmd', './say-hello.sh'),
    ('out', [('» ', FLAME), ('hello@kingsdevandai.com', FG), ('  ·  ', NOTE), ('kingsdevandai.com/contact', FG)]),
    ('out', [('» ', FLAME), ('linkedin.com/in/georgenking09', FG)]),
    ('end',),
]
TERMINAL_TITLE = 'george@kingsdevandai: ~ — zsh'

FOOTER = {
    'line': 'Thanks for stopping by.',
    'sub': 'HAVE A PROJECT IN MIND?  HELLO@KINGSDEVANDAI.COM',
}

# The studio's K, from the kingsdevandai.com masthead (viewBox 0 -12 208 272).
K_PATHS = ['M28 0V244', 'M70 104L186 10', 'M70 140L186 234']


# ── FONTS ─────────────────────────────────────────────────────────────────

def font_file(name):
    path = FONT_DIR / name
    if not path.exists():
        FONT_DIR.mkdir(exist_ok=True)
        req = urllib.request.Request(FONT_URL + name, headers={'User-Agent': 'build_assets.py'})
        with urllib.request.urlopen(req, timeout=30) as r:
            path.write_bytes(r.read())
    return path


_metrics = {}


def text_width(s, size, weight=400, mono=False, spacing=0.0):
    """Advance width of s, ignoring kerning; good enough to lay out a line."""
    key = ('mono', 400) if mono else ('sans', weight)
    if key not in _metrics:
        font = TTFont(font_file(FONTS[key[0]][1]))
        if not mono:
            font = instancer.instantiateVariableFont(font, {'wght': weight})
        _metrics[key] = (font.getBestCmap(), font['hmtx'], font['head'].unitsPerEm)
    cmap, hmtx, upm = _metrics[key]
    units = sum(hmtx[cmap[ord(c)]][0] if ord(c) in cmap else upm * .55 for c in s)
    return units * size / upm + spacing * len(s)


def font_faces(keys, body):
    chars = set()
    for m in re.finditer(r'>([^<>]+)<', body):
        chars |= set(html.unescape(m.group(1)))
    text = ''.join(sorted(chars - set('\n\t')))
    css = []
    for key in keys:
        family, name, weight = FONTS[key]
        opts = subset.Options()
        opts.flavor = 'woff2'
        opts.layout_features = ['kern', 'liga', 'calt', 'tnum']
        font = subset.load_font(str(font_file(name)), opts)
        sub = subset.Subsetter(opts)
        sub.populate(text=text)
        sub.subset(font)
        buf = io.BytesIO()
        subset.save_font(font, buf, opts)
        data = base64.b64encode(buf.getvalue()).decode()
        css.append(f"@font-face{{font-family:{family};font-weight:{weight};"
                   f"src:url(data:font/woff2;base64,{data}) format('woff2')}}")
    return ''.join(css)


# ── SVG HELPERS ───────────────────────────────────────────────────────────

BASE_CSS = """
.j{font-family:KDJakarta,-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}
.m{font-family:KDPlex,ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


def esc(s):
    return html.escape(s, quote=False)


def write(name, w, h, title, body, css='', fonts=()):
    style = font_faces(fonts, body) + BASE_CSS + css
    style = '\n'.join(line.strip() for line in style.strip().splitlines() if line.strip())
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
           f'fill="none" role="img" aria-label="{html.escape(title)}">\n'
           f'<title>{esc(title)}</title>\n<style>\n{style}\n</style>\n{body.strip()}\n</svg>\n')
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(doc, encoding='utf-8')
    print(f'  assets/{name:<14} {len(doc.encode()) / 1024:6.1f} KB')


def text(x, y, s, size, fill, cls='j', weight=None, spacing=None, anchor=None, extra=''):
    attrs = f'class="{cls}" x="{x:g}" y="{y:g}" font-size="{size:g}" fill="{fill}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if spacing:
        attrs += f' letter-spacing="{spacing:g}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    return f'<text {attrs} {extra}>{esc(s)}</text>'


def rounded_rect_path(x, y, w, h, r):
    """Clockwise from the top-left corner, so a dash runs round it like a beam."""
    return (f'M{x + r} {y}H{x + w - r}A{r} {r} 0 0 1 {x + w} {y + r}V{y + h - r}'
            f'A{r} {r} 0 0 1 {x + w - r} {y + h}H{x + r}A{r} {r} 0 0 1 {x} {y + h - r}'
            f'V{y + r}A{r} {r} 0 0 1 {x + r} {y}Z')


def kmark(cls, stroke, extra=''):
    return ''.join(f'<path class="{cls} {cls}{i + 1}" d="{d}" pathLength="100" stroke="{stroke}" '
                   f'stroke-width="36" {extra}/>' for i, d in enumerate(K_PATHS))


def embers(rng, n, x_range, y0, rise, dim_left_of=None):
    out = []
    for _ in range(n):
        x = rng.uniform(*x_range)
        o = rng.uniform(.45, .9)
        if dim_left_of and x < dim_left_of:
            o *= .35
        dur = rng.uniform(6, 12)
        out.append(
            f'<circle class="e" cx="{x:.0f}" cy="{y0}" r="{rng.uniform(.8, 2.2):.1f}" '
            f'fill="{rng.choice([AMBER, FLAME, EMBER, FG])}" style="--dx:{rng.uniform(-40, 40):.0f}px;'
            f'--o:{o:.2f};--h:-{rise}px;animation-duration:{dur:.1f}s;animation-delay:-{rng.uniform(0, dur):.1f}s"/>')
    return ''.join(out)


EMBER_CSS = """
.e{opacity:0;animation:rise linear infinite}
@keyframes rise{0%{transform:translate(0,0);opacity:0}12%,75%{opacity:var(--o)}100%{transform:translate(var(--dx),var(--h));opacity:0}}
"""


# ── HERO ──────────────────────────────────────────────────────────────────

def hero():
    W, H = 1000, 320
    ex, ey = 812, 160                       # emblem centre
    ks = .6                                 # K scale; its visual centre is (104, 122)
    c = HERO
    lead_w = text_width(c['lead'] + ' ', 26, 500)
    wx = 56 + lead_w + 2
    tag_w = len(c['tagline']) * 13 * .6

    words = ''.join(
        text(wx, 214, w, 26, 'url(#wordg)', cls=f'j w w{i + 1}', weight=700, spacing=-.4)
        for i, w in enumerate(c['words']))
    word_css = ''.join(f'.w{i + 1}{{animation-delay:{1 + 3 * i}s}}' for i in range(len(c['words'])))

    body = f'''
<defs>
  <clipPath id="card"><rect width="{W}" height="{H}" rx="22"/></clipPath>
  <clipPath id="nameclip"><rect x="30" y="92" width="640" height="94"/></clipPath>
  <clipPath id="wordclip"><rect x="{wx - 4:.1f}" y="184" width="440" height="40"/></clipPath>
  <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="{fg(.11)}"/></pattern>
  <radialGradient id="gridfade" cx="{ex}" cy="{ey}" r="520" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
  <mask id="gridmask"><rect width="{W}" height="{H}" fill="url(#gridfade)"/></mask>
  <radialGradient id="g1"><stop offset="0" stop-color="{FLAME}" stop-opacity=".55"/><stop offset="1" stop-color="{FLAME}" stop-opacity="0"/></radialGradient>
  <radialGradient id="g2"><stop offset="0" stop-color="{EMBER}" stop-opacity=".3"/><stop offset="1" stop-color="{EMBER}" stop-opacity="0"/></radialGradient>
  <radialGradient id="g3"><stop offset="0" stop-color="{DEEP}" stop-opacity=".5"/><stop offset="1" stop-color="{DEEP}" stop-opacity="0"/></radialGradient>
  <radialGradient id="g4"><stop offset="0" stop-color="{COPPER}" stop-opacity=".18"/><stop offset="1" stop-color="{COPPER}" stop-opacity="0"/></radialGradient>
  <linearGradient id="nameg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="560" y2="0">
    <stop offset="0" stop-color="{FG}"/><stop offset=".4" stop-color="{FG}"/><stop offset=".48" stop-color="{AMBER}"/>
    <stop offset=".54" stop-color="{FLAME}"/><stop offset=".62" stop-color="{FG}"/><stop offset="1" stop-color="{FG}"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="-640 0;-640 0;640 0" keyTimes="0;.55;1"
      calcMode="spline" keySplines="0 0 1 1;.45 0 .25 1" dur="7s" repeatCount="indefinite"/>
  </linearGradient>
  <linearGradient id="wordg" gradientUnits="userSpaceOnUse" x1="{wx:.0f}" y1="0" x2="{wx + 280:.0f}" y2="0">
    <stop offset="0" stop-color="{EMBER}"/><stop offset="1" stop-color="{AMBER}"/></linearGradient>
  <linearGradient id="kgrad" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="200" y2="250">
    <stop offset="0" stop-color="{AMBER}"/><stop offset=".5" stop-color="{FLAME}"/><stop offset="1" stop-color="{DEEP}"/></linearGradient>
  <filter id="kblur" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="22"/></filter>
  <filter id="soft" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="3"/></filter>
</defs>

<g clip-path="url(#card)">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <ellipse class="au" cx="{ex + 10}" cy="{ey - 40}" rx="300" ry="210" fill="url(#g1)"/>
  <ellipse class="au au2" cx="{ex + 120}" cy="{ey + 120}" rx="240" ry="170" fill="url(#g2)"/>
  <ellipse class="au au3" cx="560" cy="{H + 40}" rx="360" ry="140" fill="url(#g3)"/>
  <ellipse class="au au2" cx="120" cy="-30" rx="380" ry="140" fill="url(#g4)"/>
  <rect width="{W}" height="{H}" fill="url(#dots)" mask="url(#gridmask)"/>
  <g>{embers(random.Random(9), 34, (20, 990), H + 10, H + 30, dim_left_of=600)}</g>

  <g class="fade" style="animation-delay:.2s">
    <circle cx="{ex}" cy="{ey}" r="112" stroke="{fg(.16)}" stroke-dasharray="2 7" class="spin"/>
    <circle cx="{ex}" cy="{ey}" r="140" stroke="{fg(.08)}"/>
    <circle cx="{ex}" cy="{ey}" r="140" stroke="{FLAME}" stroke-width="2" stroke-linecap="round" stroke-dasharray="70 1000" class="spin fast"/>
    <circle cx="{ex}" cy="{ey}" r="140" stroke="{AMBER}" stroke-width="2" stroke-linecap="round" stroke-dasharray="22 1000" class="spin fast rev"/>
    <g class="spin orbit"><circle cx="{ex + 112}" cy="{ey}" r="9" fill="{AMBER}" opacity=".22"/><circle cx="{ex + 112}" cy="{ey}" r="3.5" fill="{AMBER}"/></g>
    <g class="spin orbit2"><circle cx="{ex - 140}" cy="{ey}" r="3" fill="{FG}"/></g>
  </g>
  <g transform="translate({ex - 104 * ks:.1f} {ey - 122 * ks:.1f}) scale({ks})">
    <g class="kg" filter="url(#kblur)" opacity=".75">{kmark('kb', FLAME)}</g>
    {kmark('k', 'url(#kgrad)')}
  </g>

  <g class="fade">
    <circle cx="61" cy="78" r="4" fill="{FLAME}"/>
    <circle cx="61" cy="78" r="4" fill="{FLAME}" opacity="0" class="ping"/>
    {text(76, 82.5, c['kicker'], 12, fg(.66), cls='m', weight=600, spacing=3)}
  </g>
  <g clip-path="url(#nameclip)">
    {text(52, 162, c['name'], 80, 'url(#nameg)', cls='j nm', weight=800, spacing=-2.6)}
  </g>
  {text(56, 214, c['lead'], 26, fg(.72), cls='j fade', weight=500, spacing=-.2, extra='style="animation-delay:.6s"')}
  <g clip-path="url(#wordclip)">{words}</g>
  <g class="fade" style="animation-delay:1.1s">
    {text(57, 264, c['tagline'], 13, fg(.5), cls='m')}
    <rect class="cur" x="{57 + tag_w + 5:.1f}" y="253" width="8" height="14" fill="{FLAME}"/>
  </g>
</g>

<path d="{rounded_rect_path(.5, .5, W - 1, H - 1, 22)}" stroke="{fg(.1)}"/>
<path d="{rounded_rect_path(.5, .5, W - 1, H - 1, 22)}" pathLength="1000" stroke="{FLAME}" stroke-width="5" class="beam" filter="url(#soft)" opacity=".7"/>
<path d="{rounded_rect_path(.5, .5, W - 1, H - 1, 22)}" pathLength="1000" stroke="{AMBER}" stroke-width="1.5" stroke-linecap="round" class="beam"/>
'''
    css = EMBER_CSS + f'''
.fade{{animation:fade 1s ease both}}
@keyframes fade{{from{{opacity:0}}}}
.nm{{animation:up 1.1s cubic-bezier(.2,.8,.2,1) .15s both}}
@keyframes up{{from{{transform:translateY(100px)}}}}
.k{{stroke-dasharray:100;animation:draw 1s cubic-bezier(.65,0,.35,1) both}}
.k1{{animation-delay:.35s}}.k2{{animation-delay:.75s}}.k3{{animation-delay:.95s}}
@keyframes draw{{from{{stroke-dashoffset:100}}to{{stroke-dashoffset:0}}}}
.kg{{animation:fade 1.2s 1.5s both,glow 3.5s 2.7s ease-in-out infinite alternate}}
@keyframes glow{{to{{opacity:.3}}}}
.au{{transform-box:fill-box;transform-origin:center;animation:drift 16s ease-in-out infinite alternate}}
.au2{{animation-duration:21s;animation-delay:-7s}}.au3{{animation-duration:13s;animation-delay:-4s}}
@keyframes drift{{0%{{transform:translate(0,0) scale(1)}}50%{{transform:translate(-50px,24px) scale(1.18)}}100%{{transform:translate(30px,-16px) scale(.92)}}}}
.spin{{transform-box:view-box;transform-origin:{ex}px {ey}px;animation:spin 60s linear infinite}}
.fast{{animation-duration:9s}}.rev{{animation-direction:reverse;animation-duration:14s}}
.orbit{{animation-duration:12s}}.orbit2{{animation-duration:20s;animation-direction:reverse}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.ping{{transform-box:fill-box;transform-origin:center;animation:ping 2s cubic-bezier(0,0,.2,1) infinite}}
@keyframes ping{{from{{transform:scale(1);opacity:.7}}to{{transform:scale(3.4);opacity:0}}}}
.w{{animation:word 12s cubic-bezier(.3,.7,.2,1) infinite both}}
.w2,.w3,.w4{{opacity:0}}
{word_css}
@keyframes word{{0%{{transform:translateY(36px);opacity:0}}5%,22%{{transform:translateY(0);opacity:1}}28%,100%{{transform:translateY(-36px);opacity:0}}}}
.cur{{animation:blink 1.1s steps(1,end) infinite}}
@keyframes blink{{50%{{opacity:0}}}}
.beam{{stroke-dasharray:70 930;animation:beam 10s linear infinite}}
@keyframes beam{{to{{stroke-dashoffset:-1000}}}}
'''
    write('hero.svg', W, H,
          f"{c['name']} — {c['kicker'].title()}. {c['lead']} " + ', '.join(w.rstrip('.') for w in c['words']) + '.',
          body, css, fonts=('sans', 'mono-bold', 'mono'))


# ── TERMINAL ──────────────────────────────────────────────────────────────

def terminal():
    W, FS, LH, X0, BAR, T = 1000, 17, 30, 36, 46, 20.0
    CW = FS * .6                             # Plex Mono is 600 units to the em
    PROMPT = [('~', COPPER), (' › ', FLAME)]
    CMD_X = X0 + 4 * CW
    H = BAR + 40 + (len(TERMINAL) - 1) * LH + 30

    def pct(t):
        return f'{t / T * 100:.3f}%'

    def runs(x, y, segs):
        out = []
        for s, color in segs:
            if s.strip():
                out.append(f'<tspan x="{x:.1f}" fill="{color}" textLength="{len(s) * CW:.1f}" '
                           f'lengthAdjust="spacing">{esc(s)}</tspan>')
            x += len(s) * CW
        return f'<text class="m" y="{y}" font-size="{FS}" xml:space="preserve">{"".join(out)}</text>'

    rows, css, t = [], [], .6
    for i, row in enumerate(TERMINAL):
        y = BAR + 40 + i * LH
        appear = t
        css.append(f'.l{i}{{animation:l{i} {T}s linear infinite}}'
                   f'@keyframes l{i}{{0%,{pct(appear)}{{opacity:0;transform:translateY(4px)}}'
                   f'{pct(appear + .1)},100%{{opacity:1;transform:none}}}}')
        if row[0] == 'cmd':
            cmd = row[1]
            start = appear + .45
            end = start + len(cmd) * .065
            hide = end + .25
            shift = len(cmd) * CW
            rows.append(
                f'<g class="l{i}">{runs(X0, y, PROMPT)}{runs(CMD_X, y, [(cmd, FG)])}'
                f'<g class="t{i}"><rect x="{CMD_X:.1f}" y="{y - 18}" width="{W}" height="26" fill="{BG}"/>'
                f'<rect class="c{i}" x="{CMD_X:.1f}" y="{y - 14}" width="{CW:.1f}" height="19" fill="{FLAME}"/></g></g>')
            css.append(
                f'.t{i}{{transform:translateX({shift:.1f}px);animation:t{i} {T}s infinite}}'
                f'@keyframes t{i}{{0%,{pct(start)}{{transform:translateX(0);animation-timing-function:steps({len(cmd)},end)}}'
                f'{pct(end)},100%{{transform:translateX({shift:.1f}px)}}}}'
                f'.c{i}{{opacity:0;animation:c{i} {T}s infinite}}'
                f'@keyframes c{i}{{0%,{pct(appear)}{{opacity:0}}{pct(appear + .01)},{pct(hide)}{{opacity:1}}'
                f'{pct(hide + .01)},100%{{opacity:0}}}}')
            t = hide
        elif row[0] == 'out':
            rows.append(f'<g class="l{i}">{runs(X0, y, row[1])}</g>')
            t += .12
            if i + 1 < len(TERMINAL) and TERMINAL[i + 1][0] != 'out':
                t += .3
        else:
            rows.append(f'<g class="l{i}">{runs(X0, y, PROMPT)}'
                        f'<rect class="blink" x="{CMD_X:.1f}" y="{y - 14}" width="{CW:.1f}" height="19" fill="{FLAME}"/></g>')
    assert t < T - 4, f'terminal script runs {t:.1f}s; raise T'

    body = f'''
<defs>
  <clipPath id="win"><rect width="{W}" height="{H}" rx="16"/></clipPath>
  <clipPath id="screen"><rect x="1" y="{BAR + 1}" width="{W - 2}" height="{H - BAR - 2}"/></clipPath>
  <radialGradient id="glow" cx="{W - 120}" cy="0" r="520" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="{FLAME}" stop-opacity=".16"/><stop offset="1" stop-color="{FLAME}" stop-opacity="0"/></radialGradient>
  <linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{FG}" stop-opacity="0"/><stop offset=".5" stop-color="{FG}" stop-opacity=".035"/>
    <stop offset="1" stop-color="{FG}" stop-opacity="0"/></linearGradient>
</defs>
<g clip-path="url(#win)">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <rect width="{W}" height="{BAR}" fill="{fg(.035)}"/>
  <path d="M0 {BAR}.5H{W}" stroke="{fg(.08)}"/>
  <circle cx="26" cy="23" r="6.5" fill="#FF5F57"/><circle cx="48" cy="23" r="6.5" fill="#FEBC2E"/><circle cx="70" cy="23" r="6.5" fill="#28C840"/>
  {text(W / 2, 27.5, TERMINAL_TITLE, 12.5, fg(.45), cls='m', anchor='middle')}
  <g clip-path="url(#screen)"><g class="scr">{''.join(rows)}</g></g>
  <rect class="scan" x="0" y="-140" width="{W}" height="140" fill="url(#scan)"/>
  <rect width="{W}" height="{H}" fill="url(#glow)"/>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="15.5" stroke="{fg(.12)}"/>
'''
    css = ''.join(css) + f'''
.scr{{animation:scr {T}s infinite}}
@keyframes scr{{0%,{pct(T - 1.4)}{{opacity:1}}{pct(T - .6)},100%{{opacity:0}}}}
.blink{{animation:blink 1.1s steps(1,end) infinite}}
@keyframes blink{{50%{{opacity:0}}}}
.scan{{animation:scan 7s linear infinite}}
@keyframes scan{{to{{transform:translateY({H + 140}px)}}}}
'''
    write('terminal.svg', W, H, 'Terminal: whoami — George King, King’s Development and AI. '
          'Bespoke software, web apps, AI and automation for businesses across the UK. hello@kingsdevandai.com, linkedin.com/in/georgenking09',
          body, css, fonts=('mono',))


# ── DIVIDER ───────────────────────────────────────────────────────────────

def divider():
    W, H = 1000, 24
    body = f'''
<defs>
  <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{COPPER}" stop-opacity="0"/><stop offset=".5" stop-color="{COPPER}" stop-opacity=".55"/>
    <stop offset="1" stop-color="{COPPER}" stop-opacity="0"/></linearGradient>
  <linearGradient id="spark" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{FLAME}" stop-opacity="0"/><stop offset=".7" stop-color="{FLAME}"/>
    <stop offset=".95" stop-color="{AMBER}"/><stop offset="1" stop-color="{AMBER}" stop-opacity="0"/></linearGradient>
  <filter id="b" x="-20%" y="-300%" width="140%" height="700%"><feGaussianBlur stdDeviation="2.5"/></filter>
</defs>
<rect y="11.5" width="{W}" height="1" fill="url(#rule)"/>
<g class="spark"><rect x="-160" y="10" width="160" height="4" rx="2" fill="url(#spark)" filter="url(#b)"/>
  <rect x="-160" y="11.25" width="160" height="1.5" rx=".75" fill="url(#spark)"/></g>
<rect x="495" y="7" width="10" height="10" fill="{FLAME}" transform="rotate(45 500 12)" class="gem"/>
'''
    css = f'''
.spark{{animation:spark 5s cubic-bezier(.6,0,.4,1) infinite}}
@keyframes spark{{0%{{transform:translateX(0)}}70%,100%{{transform:translateX({W + 160}px)}}}}
.gem{{transform-box:fill-box;transform-origin:center;animation:gem 5s ease-in-out infinite}}
@keyframes gem{{0%,30%,48%,100%{{transform:rotate(45deg) scale(1)}}38%{{transform:rotate(135deg) scale(1.5)}}}}
'''
    write('divider.svg', W, H, 'Divider', body, css)


# ── FOOTER ────────────────────────────────────────────────────────────────

def footer():
    W, H = 1000, 210

    def wave(y, amp, length, cls, fill='none', stroke=None):
        d = f'M0 {y}Q{length / 4} {y - amp} {length / 2} {y}'
        x = length / 2
        while x < W + length:
            x += length / 2
            d += f'T{x:g} {y}'
        if stroke:
            return f'<path class="wave {cls}" d="{d}" stroke="{stroke}" stroke-width="1.5"/>'
        return f'<path class="wave {cls}" d="{d}V{H}H0z" fill="{fill}"/>'

    def fall(id_, color, a):
        return (f'<linearGradient id="{id_}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{color}" '
                f'stop-opacity="{a}"/><stop offset=".7" stop-color="{color}" stop-opacity="0"/></linearGradient>')

    ks = .17
    body = f'''
<defs>
  <clipPath id="card"><rect width="{W}" height="{H}" rx="22"/></clipPath>
  <linearGradient id="lineg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="520" y2="0">
    <stop offset="0" stop-color="{FG}"/><stop offset=".4" stop-color="{FG}"/><stop offset=".48" stop-color="{AMBER}"/>
    <stop offset=".54" stop-color="{FLAME}"/><stop offset=".62" stop-color="{FG}"/><stop offset="1" stop-color="{FG}"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="-300 0;-300 0;1000 0" keyTimes="0;.5;1"
      calcMode="spline" keySplines="0 0 1 1;.45 0 .25 1" dur="8s" repeatCount="indefinite"/>
  </linearGradient>
  <linearGradient id="kgrad" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="200" y2="250">
    <stop offset="0" stop-color="{AMBER}"/><stop offset=".5" stop-color="{FLAME}"/><stop offset="1" stop-color="{DEEP}"/></linearGradient>
  {fall('f1', DEEP, .55)}{fall('f2', FLAME, .3)}{fall('f3', AMBER, .22)}
  <filter id="soft" x="-5%" y="-100%" width="110%" height="300%"><feGaussianBlur stdDeviation="3"/></filter>
</defs>
<g clip-path="url(#card)">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  {wave(H - 44, 16, 300, 'w1', fill='url(#f1)')}
  {wave(H - 32, 12, 380, 'w2', fill='url(#f2)')}
  {wave(H - 20, 9, 220, 'w3', fill='url(#f3)')}
  <g filter="url(#soft)" opacity=".8">{wave(H - 20, 9, 220, 'w3', stroke=FLAME)}</g>
  {wave(H - 20, 9, 220, 'w3', stroke=AMBER + 'CC')}
  <g>{embers(random.Random(3), 22, (20, 980), H - 20, H, dim_left_of=None)}</g>
  <g transform="translate({W / 2 - 104 * ks:.1f} 34) scale({ks})">{kmark('k', 'url(#kgrad)')}</g>
  {text(W / 2, 112, FOOTER['line'], 32, 'url(#lineg)', weight=700, spacing=-.8, anchor='middle')}
  {text(W / 2, 144, FOOTER['sub'], 11.5, fg(.5), cls='m', weight=600, spacing=2.6, anchor='middle')}
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="21.5" stroke="{fg(.1)}"/>
'''
    css = EMBER_CSS + '''
.wave{animation:wave linear infinite}
.w1{--l:-300px;animation-duration:11s}.w2{--l:-380px;animation-duration:15s;animation-direction:reverse}.w3{--l:-220px;animation-duration:7s}
@keyframes wave{to{transform:translateX(var(--l))}}
.k{stroke-dasharray:100;animation:draw 6s cubic-bezier(.65,0,.35,1) infinite}
.k2{animation-delay:.25s}.k3{animation-delay:.4s}
@keyframes draw{0%{stroke-dashoffset:100}25%,85%{stroke-dashoffset:0}100%{stroke-dashoffset:-100}}
'''
    write('footer.svg', W, H, FOOTER['line'] + ' Have a project in mind? hello@kingsdevandai.com',
          body, css, fonts=('sans', 'mono-bold'))


if __name__ == '__main__':
    print('Building:')
    hero()
    terminal()
    divider()
    footer()
