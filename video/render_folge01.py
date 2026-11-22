#!/usr/bin/env python3
"""Rendert Folge 1 von „30 TAGE“ als TikTok-Video (1080x1920, 30 fps, mit Musik).

Aufruf:  python3 video/render_folge01.py
Ergebnis: video/folge01_30tage.mp4
Benötigt: ffmpeg, Pillow, numpy, Inter- und Noto-Color-Emoji-Schrift.
"""
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
BW, BH = 1188, 2112  # Hintergrund etwas größer für langsamen Zoom
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(OUT_DIR, "folge01_30tage.mp4")
FONT_DIR = "/usr/share/fonts/opentype/inter/"
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

_fonts = {}


def F(name, size):
    key = (name, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_DIR + name, size)
    return _fonts[key]


# ---------------------------------------------------------------- Text + Emoji
EMO_RE = re.compile("([\U0001F000-\U0001FAFF]️?)")
_emoji_cache = {}


def emoji_img(ch, size):
    key = (ch, size)
    if key not in _emoji_cache:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((20, 20), ch, font=f, embedded_color=True)
        im = im.crop(im.getbbox())
        s = size / im.height
        _emoji_cache[key] = im.resize((max(1, round(im.width * s)), size), Image.LANCZOS)
    return _emoji_cache[key]


def segments(text):
    return [s for s in EMO_RE.split(text) if s]


def is_emo(s):
    return bool(EMO_RE.fullmatch(s))


def text_w(text, font):
    w = 0
    for s in segments(text):
        w += (font.size * 1.05 + 4) if is_emo(s) else font.getlength(s)
    return w


def wrap(text, font, maxw):
    lines, cur = [], ""
    for wd in text.split(" "):
        t = (cur + " " + wd).strip()
        if not cur or text_w(t, font) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_rich(img, xy, text, font, fill, stroke=0, stroke_fill=None):
    d = ImageDraw.Draw(img)
    x, y = xy
    asc, _ = font.getmetrics()
    for s in segments(text):
        if is_emo(s):
            e = emoji_img(s, int(font.size * 0.95))
            img.alpha_composite(e, (int(x) + 2, int(y + asc - font.size * 0.88)))
            x += font.size * 1.05 + 4
        else:
            d.text((x, y), s, font=font, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
            x += font.getlength(s)


def render_block(parts, maxw=920, gap=1.2):
    """parts: Liste von (text, font, farbe, abstand_davor). Gibt RGBA-Bild (Breite W) zurück."""
    layout, y = [], 0
    for text, font, color, sp in parts:
        y += sp
        for ln in wrap(text, font, maxw):
            layout.append((ln, font, color, y))
            y += int(font.size * gap)
    pad = 30
    txt = Image.new("RGBA", (W, y + 2 * pad), (0, 0, 0, 0))
    for ln, font, color, yy in layout:
        x = (W - text_w(ln, font)) / 2
        draw_rich(txt, (x, yy + pad), ln, font, color, stroke=3, stroke_fill=(0, 0, 0, 210))
    shadow = Image.new("RGBA", txt.size, (0, 0, 0, 255))
    shadow.putalpha(txt.getchannel("A").filter(ImageFilter.GaussianBlur(16)).point(lambda v: min(255, int(v * 1.1))))
    out = Image.new("RGBA", txt.size, (0, 0, 0, 0))
    out.alpha_composite(shadow, (0, 8))
    out.alpha_composite(txt)
    return out


WHITE = (255, 255, 255)
NOAH_C = (140, 200, 255)
LINA_C = (255, 255, 255)
TEACH_C = (255, 214, 150)
PINK = (255, 92, 122)


def narr(text, size=66, color=WHITE, font="Inter-Bold.otf"):
    return render_block([(text, F(font, size), color, 0)])


def speaker(name, text, color, name_color=None):
    return render_block([
        (name.upper(), F("Inter-ExtraBold.otf", 36), name_color or color, 0),
        ("„" + text + "“", F("Inter-Bold.otf", 64), color, 10),
    ])


def badge():
    f = F("Inter-ExtraBold.otf", 32)
    label = "30 TAGE  ·  TEIL 1"
    tw = f.getlength(label)
    im = Image.new("RGBA", (W, 90), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0 = (W - tw) / 2 - 34
    d.rounded_rectangle((x0, 10, x0 + tw + 68, 80), radius=35, fill=(0, 0, 0, 140))
    d.ellipse((x0 + 18, 38, x0 + 30, 50), fill=PINK)
    d.text(((W - tw) / 2 + 8, 25), label, font=f, fill=WHITE)
    return im


# ---------------------------------------------------------------- Hintergründe
def lerp(a, b, s):
    return a + (b - a) * s


def gradient(c1, c2, size=(BW, BH)):
    w, h = size
    t = np.linspace(0, 1, h)[:, None]
    arr = (np.array(c1)[None, None, :] * (1 - t[..., None]) + np.array(c2)[None, None, :] * t[..., None])
    arr = np.broadcast_to(arr, (h, w, 3)).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def glow_layer(draw_fn, blur, size=(BW, BH)):
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(lay))
    return lay.filter(ImageFilter.GaussianBlur(blur))


def vignette(strength=230):
    yy, xx = np.mgrid[0:BH, 0:BW]
    r = np.sqrt(((xx - BW / 2) / (BW * 0.62)) ** 2 + ((yy - BH / 2) / (BH * 0.6)) ** 2)
    a = np.clip((r - 0.45) / 0.75, 0, 1) ** 1.6 * strength
    im = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    im.putalpha(Image.fromarray(a.astype(np.uint8), "L"))
    return im


def bg_rain():
    rnd = random.Random(1)
    img = gradient((8, 12, 28), (24, 22, 48))
    def bokeh(d):
        for _ in range(45):
            x, y, r = rnd.randint(0, BW), rnd.randint(300, BH - 300), rnd.randint(25, 95)
            c = rnd.choice([(255, 170, 90), (255, 120, 80), (110, 160, 255), (255, 210, 140), (255, 90, 130)])
            d.ellipse((x - r, y - r, x + r, y + r), fill=c + (rnd.randint(40, 110),))
    img.alpha_composite(glow_layer(bokeh, 14))
    drops = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(drops)
    for _ in range(420):
        x, y, r = rnd.randint(0, BW), rnd.randint(0, BH), rnd.uniform(2, 9)
        d.ellipse((x - r, y - r * 1.2, x + r, y + r * 1.2), fill=(200, 215, 255, 45))
        d.ellipse((x - r * 0.4, y - r * 0.8, x + r * 0.1, y - r * 0.2), fill=(255, 255, 255, 90))
    img.alpha_composite(drops.filter(ImageFilter.GaussianBlur(1)))
    return img


def bg_hallway(tint=(0, 0, 0)):
    vx, vy = BW / 2, 1000
    ew, et, eb = 200, vy - 280, vy + 190
    img = Image.new("RGBA", (BW, BH), (30, 38, 50, 255))
    d = ImageDraw.Draw(img)
    d.polygon([(0, 0), (BW, 0), (vx + ew, et), (vx - ew, et)], fill=(24, 28, 38))
    d.polygon([(0, 0), (vx - ew, et), (vx - ew, eb), (0, BH)], fill=(44, 54, 68))
    d.polygon([(BW, 0), (vx + ew, et), (vx + ew, eb), (BW, BH)], fill=(40, 50, 64))
    d.polygon([(0, BH), (BW, BH), (vx + ew, eb), (vx - ew, eb)], fill=(34, 36, 44))
    d.rectangle((vx - ew, et, vx + ew, eb), fill=(200, 215, 230))
    # Spinde links und rechts
    for side in (-1, 1):
        for i in range(26):
            s0, s1 = 1 - 1 / (1 + i * 0.32), 1 - 1 / (1 + (i + 0.92) * 0.32)
            def pt(s, f):
                x = lerp(0 if side < 0 else BW, vx + side * ew, s)
                yt, yb = lerp(0, et, s), lerp(BH, eb, s)
                return (x, lerp(yt, yb, f))
            col = (48, 82, 120) if i % 2 == 0 else (44, 76, 112)
            d.polygon([pt(s0, 0.32), pt(s1, 0.32), pt(s1, 0.86), pt(s0, 0.86)], fill=col)
            d.line([pt(s0, 0.32), pt(s0, 0.86)], fill=(20, 30, 44), width=3)
    def lights(dd):
        for i in range(14):
            s0, s1 = 1 - 1 / (1 + i * 0.45), 1 - 1 / (1 + (i + 0.4) * 0.45)
            for s_a, s_b in [(s0, s1)]:
                y0, y1 = lerp(0, et, s_a), lerp(0, et, s_b)
                w0, w1 = lerp(150, 30, s_a), lerp(150, 30, s_b)
                dd.polygon([(vx - w0, y0), (vx + w0, y0), (vx + w1, y1), (vx - w1, y1)], fill=(235, 245, 255, 255))
                fy0, fy1 = lerp(BH, eb, s_a), lerp(BH, eb, s_b)
                dd.polygon([(vx - w0, fy0), (vx + w0, fy0), (vx + w1, fy1), (vx - w1, fy1)], fill=(200, 220, 240, 70))
        dd.rectangle((vx - ew, et, vx + ew, eb), fill=(255, 255, 255, 160))
    img.alpha_composite(glow_layer(lights, 30))
    img.alpha_composite(glow_layer(lights, 4))
    img = img.filter(ImageFilter.GaussianBlur(5))
    over = Image.new("RGBA", (BW, BH), tint + (40,))
    img.alpha_composite(over)
    return img


def bg_door():
    img = gradient((14, 12, 18), (6, 6, 10))
    dx0, dx1, dy0, dy1 = 360, 828, 420, 1720
    def spill(d):
        d.polygon([(dx0, dy1), (dx1, dy1), (BW + 300, BH), (-300, BH)], fill=(255, 220, 170, 90))
        d.rectangle((dx0 - 40, dy0 - 40, dx1 + 40, dy1), fill=(255, 225, 180, 200))
    img.alpha_composite(glow_layer(spill, 60))
    d = ImageDraw.Draw(img)
    d.rectangle((dx0, dy0, dx1, dy1), fill=(255, 236, 205))
    cx = BW / 2
    sil = (8, 8, 12)
    d.ellipse((cx - 78, 800, cx + 78, 980), fill=sil)
    d.rectangle((cx - 40, 950, cx + 40, 1050), fill=sil)
    d.polygon([(cx - 150, 1050), (cx + 150, 1050), (cx + 205, 1180), (cx + 190, 1720), (cx - 190, 1720), (cx - 205, 1180)], fill=sil)
    d.ellipse((cx - 210, 1030, cx - 90, 1180), fill=sil)
    d.ellipse((cx + 90, 1030, cx + 210, 1180), fill=sil)
    img = img.filter(ImageFilter.GaussianBlur(3))
    rim = glow_layer(lambda dd: dd.rectangle((dx0, dy0, dx1, dy1), outline=(255, 210, 160, 255), width=30), 25)
    img.alpha_composite(rim)
    return img


def bg_classroom(cool=False):
    top, bot = ((62, 42, 38), (22, 18, 26)) if not cool else ((28, 36, 58), (12, 14, 24))
    img = gradient(top, bot)
    d = ImageDraw.Draw(img)
    d.rectangle((240, 380, 950, 760), fill=(30, 52, 44) if not cool else (22, 40, 40))
    d.rectangle((228, 368, 962, 772), outline=(70, 52, 40), width=12)
    wincol = (255, 196, 140) if not cool else (150, 180, 255)
    def win(dd):
        for r in range(2):
            for c in range(3):
                dd.rectangle((10 + c * 70, 300 + r * 330, 70 + c * 70, 610 + r * 330), fill=wincol + (255,))
    img.alpha_composite(glow_layer(win, 30))
    img.alpha_composite(glow_layer(win, 2))
    def rays(dd):
        for k in range(5):
            dd.polygon([(0, 300 + k * 120), (220, 260 + k * 120), (BW, 1500 + k * 140), (BW, 1700 + k * 140), (0, 700 + k * 120)],
                       fill=wincol + (28,))
    img.alpha_composite(glow_layer(rays, 40))
    d = ImageDraw.Draw(img)
    for row in range(5):
        y = 1180 + row ** 1.6 * 130
        hgt = 40 + row * 22
        w = 260 + row * 120
        for side in (-1, 1):
            cx = BW / 2 + side * (180 + row * 150)
            d.polygon([(cx - w / 2, y), (cx + w / 2, y), (cx + w / 2 + 30, y + hgt), (cx - w / 2 - 30, y + hgt)], fill=(70, 50, 40))
            d.rectangle((cx - w / 2 - 30, y + hgt, cx + w / 2 + 30, y + hgt + 18 + row * 6), fill=(40, 28, 24))
    return img.filter(ImageFilter.GaussianBlur(7))


def bg_yard():
    img = gradient((110, 124, 140), (176, 182, 190))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 640, BW, 1180), fill=(72, 76, 88))
    for r in range(4):
        for c in range(9):
            d.rectangle((40 + c * 128, 700 + r * 115, 120 + c * 128, 780 + r * 115), fill=(120, 132, 150))
    gr = gradient((96, 98, 102), (52, 54, 58), (BW, BH - 1180))
    img.alpha_composite(gr, (0, 1180))
    rnd = random.Random(3)
    def person(dd, x, base, s, col):
        dd.ellipse((x - 34 * s, base - 470 * s, x + 34 * s, base - 395 * s), fill=col)
        dd.rounded_rectangle((x - 62 * s, base - 390 * s, x + 62 * s, base - 170 * s), radius=40 * s, fill=col)
        dd.rectangle((x - 50 * s, base - 180 * s, x - 10 * s, base), fill=col)
        dd.rectangle((x + 10 * s, base - 180 * s, x + 50 * s, base), fill=col)
    for i, x in enumerate([720, 830, 935, 1040]):
        person(d, x + rnd.randint(-10, 10), 1560 + rnd.randint(-15, 15), 0.95 + rnd.random() * 0.15, (24, 24, 30))
    person(d, 160, 1900, 1.6, (40, 40, 48))
    img = img.filter(ImageFilter.GaussianBlur(6))
    img.alpha_composite(Image.new("RGBA", (BW, BH), (10, 16, 30, 95)))
    return img


def bg_black(red=False):
    img = gradient((6, 6, 9), (10, 8, 12))
    if red:
        img.alpha_composite(glow_layer(lambda d: d.ellipse((194, 650, 994, 1450), fill=(140, 20, 40, 120)), 120))
    return img


BACKGROUNDS = {
    "rain": bg_rain, "hallway": bg_hallway, "door": bg_door, "classroom": bg_classroom,
    "classroom_cool": lambda: bg_classroom(cool=True), "yard": bg_yard,
    "black": bg_black, "black_red": lambda: bg_black(red=True),
}


# ---------------------------------------------------------------- Partikel
class Rain:
    def __init__(self, seed, n=260):
        rnd = random.Random(seed)
        self.p = [(rnd.uniform(-200, W), rnd.uniform(0, H + 300), rnd.uniform(1400, 2400), rnd.uniform(40, 120),
                   rnd.randint(30, 90)) for _ in range(n)]

    def draw(self, lay, t):
        d = ImageDraw.Draw(lay)
        for x, y0, v, ln, a in self.p:
            y = (y0 + v * t) % (H + 300) - 150
            xx = x + (y + 150) * 0.12
            d.line((xx, y, xx + ln * 0.12, y + ln), fill=(190, 205, 255, a), width=2)


class Dust:
    def __init__(self, seed, n=70, color=(255, 230, 190)):
        rnd = random.Random(seed)
        self.c = color
        self.p = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(-12, 12), rnd.uniform(-30, -6),
                   rnd.uniform(1.5, 4.5), rnd.uniform(0, 6.28)) for _ in range(n)]

    def draw(self, lay, t):
        d = ImageDraw.Draw(lay)
        for x, y, vx, vy, r, ph in self.p:
            xx, yy = (x + vx * t) % W, (y + vy * t) % H
            a = int(70 + 60 * math.sin(ph + t * 2))
            d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=self.c + (a,))


# ---------------------------------------------------------------- Chat-Szene
class Chat:
    BG, HEAD = (11, 20, 26), (32, 44, 51)
    IN_C, OUT_C = (32, 44, 51), (0, 92, 75)
    NAME_C = {"Luca": (255, 120, 110), "Emre": (120, 220, 160)}

    def __init__(self, msgs, end_overlay_t, dur):
        self.msgs, self.end_t, self.dur = msgs, end_overlay_t, dur
        base = Image.new("RGBA", (W, H), self.BG + (255,))
        pat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dp = ImageDraw.Draw(pat)
        rnd = random.Random(7)
        for _ in range(110):
            x, y, r = rnd.randint(0, W), rnd.randint(330, H), rnd.randint(8, 22)
            dp.ellipse((x - r, y - r, x + r, y + r), outline=(255, 255, 255, 14), width=3)
        base.alpha_composite(pat)
        d = ImageDraw.Draw(base)
        d.rectangle((0, 0, W, 330), fill=self.HEAD)
        d.text((60, 62), "22:14", font=F("Inter-SemiBold.otf", 34), fill=(230, 235, 238))
        d.rounded_rectangle((930, 70, 1000, 100), radius=8, outline=(230, 235, 238), width=3)
        d.rectangle((936, 76, 980, 94), fill=(230, 235, 238))
        d.line((70, 245, 100, 215), fill=(230, 235, 238), width=6)
        d.line((70, 245, 100, 275), fill=(230, 235, 238), width=6)
        d.ellipse((125, 190, 235, 300), fill=(70, 84, 94))
        base.alpha_composite(emoji_img("🐐", 64), (148, 212))
        draw_rich(base, (262, 192), "Die Jungs 🐐", F("Inter-SemiBold.otf", 46), (233, 237, 239))
        for k in range(3):
            d.ellipse((1010, 215 + k * 22, 1020, 225 + k * 22), fill=(200, 210, 215))
        fchip = F("Inter-SemiBold.otf", 28)
        tw = fchip.getlength("HEUTE")
        d.rounded_rectangle(((W - tw) / 2 - 24, 370, (W + tw) / 2 + 24, 420), radius=14, fill=(24, 34, 40))
        d.text(((W - tw) / 2, 378), "HEUTE", font=fchip, fill=(140, 155, 165))
        d.rounded_rectangle((30, 1690, 900, 1800), radius=55, fill=(42, 57, 66))
        d.text((90, 1722), "Nachricht", font=F("Inter-Regular.otf", 40), fill=(140, 155, 165))
        d.ellipse((920, 1690, 1030, 1800), fill=(0, 168, 132))
        d.rounded_rectangle((962, 1712, 988, 1758), radius=13, fill=(255, 255, 255))
        d.arc((950, 1730, 1000, 1776), 0, 180, fill=(255, 255, 255), width=5)
        self.base = base
        self.bubbles, y = [], 520
        for m in msgs:
            b = self.bubble(m["from"], m["text"])
            self.bubbles.append((b, y))
            y += b.height + 30
        self.typing = self.bubble_typing()
        self.end_block = render_block([("Teil 2 folgt…", F("Inter-ExtraBold.otf", 84), WHITE, 0),
                                       ("#30tage 🖤", F("Inter-SemiBold.otf", 44), (220, 220, 230), 20)])

    def bubble(self, who, text):
        own = who == "Du"
        fn, ft, fm = F("Inter-SemiBold.otf", 36), F("Inter-Regular.otf", 52), F("Inter-Regular.otf", 26)
        lines = wrap(text, ft, 760)
        tw = max(text_w(l, ft) for l in lines)
        nh = 0 if own else 50
        bw = int(max(tw + 120, 0 if own else fn.getlength(who)) + 52)
        bh = int(nh + len(lines) * 64 + 62)
        im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=26, fill=(self.OUT_C if own else self.IN_C) + (255,))
        if not own:
            d.text((26, 16), who, font=fn, fill=self.NAME_C.get(who, (200, 200, 200)))
        for i, l in enumerate(lines):
            draw_rich(im, (26, 18 + nh + i * 64), l, ft, (233, 237, 239))
        d.text((bw - (130 if own else 96), bh - 42), "22:14", font=fm, fill=(170, 190, 185) if own else (140, 155, 165))
        if own:
            for dx in (0, 14):
                d.line((bw - 30 + dx - 14, bh - 26, bw - 30 + dx - 8, bh - 20), fill=(83, 189, 235), width=3)
                d.line((bw - 30 + dx - 8, bh - 20, bw - 30 + dx + 2, bh - 32), fill=(83, 189, 235), width=3)
        im._own = own
        return im

    def bubble_typing(self):
        im = Image.new("RGBA", (150, 86), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle((0, 0, 149, 85), radius=26, fill=self.IN_C + (255,))
        return im

    def frame(self, t):
        img = self.base.copy()
        d = ImageDraw.Draw(img)
        typing_who, typing_y = None, None
        for m, (b, y) in zip(self.msgs, self.bubbles):
            if m.get("typing") is not None and m["typing"] <= t < m["t"]:
                typing_who, typing_y = m["from"], y
            if t >= m["t"]:
                p = min(1, (t - m["t"]) / 0.22)
                e = 1 - (1 - p) ** 3
                x = W - b.width - 30 if b._own else 30
                bb = b if p >= 1 else _fade(b, e)
                img.alpha_composite(bb, (int(x), int(y + (1 - e) * 30)))
        sub = "Luca, Emre, Du"
        sub_c = (140, 155, 165)
        if typing_who:
            sub, sub_c = f"{typing_who} schreibt…", (0, 200, 150)
            img.alpha_composite(self.typing, (30, typing_y))
            for k in range(3):
                off = math.sin(t * 9 - k * 0.9) * 7
                cx = 45 + 30 + k * 30
                d.ellipse((cx - 9, 43 - 9 + typing_y + off, cx + 9, 43 + 9 + typing_y + off), fill=(150, 165, 175))
        d.text((264, 252), sub, font=F("Inter-Regular.otf", 30), fill=sub_c)
        if t >= self.end_t:
            p = min(1, (t - self.end_t) / 0.6)
            img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(185 * p))))
            img.alpha_composite(_fade(self.end_block, p), (0, int(860 - self.end_block.height / 2 + (1 - p) * 30)))
        return img


def _fade(im, k):
    if k >= 1:
        return im
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * k)))
    return out


# ---------------------------------------------------------------- Drehbuch Folge 1
def build_scenes():
    return [
        dict(bg="rain", dur=4.4, fx="rain", items=[
            (0.0, render_block([("Er hatte 30 Tage, um mich in sich verliebt zu machen.", F("Inter-ExtraBold.otf", 76), WHITE, 0)])),
            (1.7, narr("Ich wusste es nicht.", 70, PINK, "Inter-ExtraBold.otf"))]),
        dict(bg="hallway", dur=4.6, fx="dust_cool", items=[
            (0.25, narr("Montag. 7:52 Uhr.", 72, WHITE, "Inter-ExtraBold.otf")),
            (1.4, narr("Der Tag, an dem alles angefangen hat.", 60))]),
        dict(bg="door", dur=5.4, fx="dust", items=[
            (0.2, narr("Jeder kannte ihn.", 62)),
            (1.2, narr("Noah.", 120, NOAH_C, "Inter-Black.otf")),
            (2.4, narr("Sitzengeblieben. Schlägerei-Gerüchte. Lederjacke.", 54, (230, 230, 235), "Inter-SemiBold.otf"))]),
        dict(bg="classroom", dur=3.8, fx="dust", items=[
            (0.3, speaker("Lehrerin", "Noah, setz dich neben Lina.", TEACH_C))]),
        dict(bg="classroom", dur=7.0, fx="dust", items=[
            (0.3, speaker("Noah", "Lina also. Lächelst du auch mal?", NOAH_C)),
            (3.1, speaker("Lina", "Nur bei Leuten, die mich nicht nerven.", LINA_C, PINK))]),
        dict(bg="classroom_cool", dur=3.9, fx="dust_cool", items=[
            (0.3, speaker("Noah", "Dann hab ich ja 'ne Challenge.", NOAH_C))]),
        dict(bg="yard", dur=5.8, fx="dust_cool", items=[
            (0.3, narr("Ich hab nicht verstanden, warum seine Jungs die ganze Pause zu mir rübergeschaut haben.", 58))]),
        dict(bg="black_red", dur=3.0, fx=None, items=[
            (0.5, narr("Heute weiß ich's.", 92, WHITE, "Inter-Black.otf"))], boom=0.5),
        dict(bg="black", dur=2.4, fx=None, badge=False, items=[
            (0.2, narr("Am selben Abend.", 52, (190, 190, 200), "Inter-SemiBold.otf")),
            (0.9, narr("Noahs Handy.", 72, NOAH_C, "Inter-ExtraBold.otf"))]),
        dict(chat=True, dur=11.8, msgs=[
            dict(**{"from": "Luca"}, text="Tag 1 von 30. Die Uhr läuft, Bruder 😂💸", typing=0.5, t=1.5),
            dict(**{"from": "Du"}, text="Chill. Sie hat schon geredet.", typing=None, t=3.4),
            dict(**{"from": "Emre"}, text="Ich find das immer noch lost ey…", typing=4.3, t=5.6),
            dict(**{"from": "Luca"}, text="Noch 29 Tage. Dann will ich sehen, wie sie heult 😂", typing=6.6, t=7.8),
        ], end_t=9.8),
    ]


SCENES = None
BADGE = None
GRAIN = None


def init_worker():
    global SCENES, BADGE, GRAIN
    SCENES = build_scenes()
    BADGE = badge()
    rng = np.random.default_rng(5)
    GRAIN = []
    for _ in range(6):
        g = rng.integers(0, 255, (H, W), dtype=np.uint8)
        im = Image.new("RGBA", (W, H), (128, 128, 128, 0))
        im.putalpha(Image.fromarray((g // 14).astype(np.uint8), "L"))
        lum = Image.fromarray(np.where(g > 127, 255, 0).astype(np.uint8), "L")
        im = Image.merge("RGBA", (lum, lum, lum, im.getchannel("A")))
        GRAIN.append(im)


def render_scene(idx):
    sc = SCENES[idx]
    n = int(round(sc["dur"] * FPS))
    path = os.path.join(TMP, f"seg{idx:02d}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    if sc.get("chat"):
        chat = Chat(sc["msgs"], sc["end_t"], sc["dur"])
    else:
        bg = BACKGROUNDS[sc["bg"]]()
        bg.alpha_composite(vignette())
        bg = bg.convert("RGB")
        fx = {"rain": Rain(idx), "dust": Dust(idx), "dust_cool": Dust(idx, color=(200, 220, 255)), None: None}[sc["fx"]]
        total_h = sum(im.height for _, im in sc["items"]) + 10 * (len(sc["items"]) - 1)
        y = 930 - total_h / 2
        placed = []
        for t0, im in sc["items"]:
            placed.append((t0, im, y))
            y += im.height + 10
    for f in range(n):
        t = f / FPS
        if sc.get("chat"):
            frame = chat.frame(t).convert("RGB")
        else:
            p = t / sc["dur"]
            z = 1 + 0.07 * p
            cw, ch = BW / z, BH / z
            box = ((BW - cw) / 2, (BH - ch) / 2, (BW + cw) / 2, (BH + ch) / 2)
            frame = bg.resize((W, H), Image.BILINEAR, box=box).convert("RGBA")
            if fx:
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                fx.draw(lay, t + idx * 3)
                frame.alpha_composite(lay)
            frame.alpha_composite(GRAIN[f % len(GRAIN)])
            for t0, im, yy in placed:
                if t < t0:
                    continue
                k = min(1, (t - t0) / 0.4) if t0 > 0 else min(1, 0.6 + t / 0.25)
                e = 1 - (1 - k) ** 3
                frame.alpha_composite(_fade(im, e), (0, int(yy + (1 - e) * 36)))
            if sc.get("badge", True):
                frame.alpha_composite(BADGE, (0, 215))
            frame = frame.convert("RGB")
        # kurzer Übergang über Schwarz zwischen Szenen
        k = 1.0
        if idx > 0 and t < 0.16:
            k = t / 0.16
        if idx < len(SCENES) - 1 and sc["dur"] - t < 0.16:
            k = min(k, (sc["dur"] - t) / 0.16)
        if k < 1:
            frame = Image.eval(frame, lambda v, k=k: int(v * k))
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    return path


# ---------------------------------------------------------------- Musik (selbst komponiert, lizenzfrei)
def make_audio(path, scenes):
    sr = 44100
    starts, acc = [], 0.0
    for sc in scenes:
        starts.append(acc)
        acc += round(sc["dur"] * FPS) / FPS
    total = acc
    n = int((total + 0.2) * sr)
    music = np.zeros(n)
    midi = lambda m: 440 * 2 ** ((m - 69) / 12)

    def note(m, start, dur=2.6, vel=0.22):
        i0 = int(start * sr)
        if i0 >= n:
            return
        L = min(int(dur * sr), n - i0)
        tt = np.arange(L) / sr
        f = midi(m)
        sig = sum(a * np.sin(2 * np.pi * f * k * tt) * np.exp(-tt * k * 0.9) for k, a in ((1, 1), (2, .4), (3, .15), (4, .06)))
        music[i0:i0 + L] += vel * sig * np.exp(-tt * 1.8) * np.minimum(1, tt / 0.005)

    beat = 60 / 74
    prog = [(57, [69, 72, 76]), (53, [65, 69, 72]), (48, [64, 67, 72]), (55, [67, 71, 74])]
    pat = [0, 1, 2, 1, 0, 2, 1, 2]
    melody = [81, 79, 76, 79, 77, 76, 72, 74]
    bar = 0
    while bar * 4 * beat < total:
        root, ch = prog[bar % 4]
        t0 = bar * 4 * beat
        note(root - 12, t0, 4.5, 0.32)
        note(root, t0, 4.0, 0.14)
        for i, pi in enumerate(pat):
            note(ch[pi], t0 + i * beat / 2, 1.8, 0.11 + (0.03 if i == 0 else 0))
        if bar >= 2:
            note(melody[bar % 8], t0 + beat * 0.02, 3.0, 0.13)
            if bar % 2:
                note(melody[(bar + 3) % 8], t0 + beat * 2.5, 2.0, 0.09)
        bar += 1
    # Hall
    ir_len = int(2.2 * sr)
    rng = np.random.default_rng(2)
    ir = rng.standard_normal(ir_len) * np.exp(-np.arange(ir_len) / sr * 2.6)
    ir /= np.sqrt(np.sum(ir ** 2))
    N = 1 << int(np.ceil(np.log2(n + ir_len)))
    wet = np.fft.irfft(np.fft.rfft(music, N) * np.fft.rfft(ir, N), N)[:n]
    music = music * 0.75 + wet * 0.35
    # Lautstärke-Kurve: ducken bei „Heute weiß ich's“
    t = np.arange(n) / sr
    vol = np.ones(n)
    d0, d1 = starts[7], starts[9]
    vol = np.where((t > d0) & (t < d1), 0.18, vol)
    vol = np.convolve(vol, np.ones(int(0.35 * sr)) / int(0.35 * sr), mode="same")
    vol *= np.clip((total - t) / 1.4, 0, 1)
    music *= vol
    # Regen
    noise = rng.standard_normal(n)
    spec = np.fft.rfft(noise)
    fr = np.fft.rfftfreq(n, 1 / sr)
    rain = np.fft.irfft(spec / (1 + (fr / 1500) ** 2) * (fr > 120), n)
    rain /= np.max(np.abs(rain))
    rv = np.where(t < starts[1], 0.16, 0.045) * np.clip((total - t) / 1.4, 0, 1)
    rv = np.convolve(rv, np.ones(int(0.5 * sr)) / int(0.5 * sr), mode="same")
    out = music + rain * rv
    # Boom
    b0 = int((starts[7] + scenes[7]["boom"]) * sr)
    L = int(2.2 * sr)
    tt = np.arange(L) / sr
    boom = np.sin(2 * np.pi * np.cumsum(np.linspace(75, 32, L)) / sr) * np.exp(-tt * 2.2) * 0.9
    boom += np.fft.irfft(np.fft.rfft(rng.standard_normal(L)) / (1 + (np.fft.rfftfreq(L, 1 / sr) / 200) ** 2), L) * np.exp(-tt * 8) * 0.15
    out[b0:b0 + L] += boom[: max(0, min(L, n - b0))]
    # Nachrichten-Töne
    for m in scenes[9]["msgs"]:
        i0 = int((starts[9] + m["t"]) * sr)
        L = int(0.3 * sr)
        tt = np.arange(L) / sr
        tone = (np.sin(2 * np.pi * 1568 * tt) * (tt < 0.09) + np.sin(2 * np.pi * 2093 * tt) * (tt >= 0.07)) * np.exp(-tt * 14)
        out[i0:i0 + L] += 0.22 * tone[: max(0, min(L, n - i0))]
    out = out / np.max(np.abs(out)) * 0.89
    pcm = (np.repeat(out[:, None], 2, axis=1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


TMP = tempfile.mkdtemp(prefix="folge01_")

if __name__ == "__main__":
    init_worker()
    with Pool(os.cpu_count() or 2, initializer=init_worker) as pool:
        segs = pool.map(render_scene, range(len(SCENES)), chunksize=1)
    audio = os.path.join(TMP, "audio.wav")
    make_audio(audio, SCENES)
    lst = os.path.join(TMP, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{s}'\n" for s in segs)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", audio,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT], check=True)
    print("Fertig:", OUT)
