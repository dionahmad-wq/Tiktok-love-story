#!/usr/bin/env python3
"""„30 TAGE“-Stil: Render-Engine für alle Folgen (1080x1920, 30 fps).

Jede Folge ist eine eigene Datei (z. B. folge01.py), die nur ihr Drehbuch
definiert und `render(build_scenes, teil, out)` aufruft. Siehe serie/04_stil.md.

TON-REGEL: KEINE Musikinstrumente. Nur Atmo (Regen, Raumton, Wind, Stille)
und Soundeffekte (Übergangs-Whoosh, Bass-Schlag, Herzschlag, Nachrichtenton).
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
LUCA_C = (255, 120, 110)
EMRE_C = (120, 220, 160)
JASSI_C = (255, 150, 210)
SELIN_C = (255, 200, 90)


def narr(text, size=66, color=WHITE, font="Inter-Bold.otf"):
    return render_block([(text, F(font, size), color, 0)])


def speaker(name, text, color, name_color=None):
    return render_block([
        (name.upper(), F("Inter-ExtraBold.otf", 36), name_color or color, 0),
        ("„" + text + "“", F("Inter-Bold.otf", 64), color, 10),
    ])


def badge(teil):
    f = F("Inter-ExtraBold.otf", 32)
    label = f"30 TAGE  ·  TEIL {teil}"
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


def bg_spaeti(cool=False):
    """Späti bei Nacht: Regale mit bunten Produkten, Neon-Schild, Kühlschrank-Licht, Kassentresen."""
    rnd = random.Random(11)
    img = gradient((26, 16, 38), (10, 8, 18)) if not cool else gradient((12, 22, 40), (6, 10, 20))
    d = ImageDraw.Draw(img)
    vx, vy = BW / 2, 1050
    d.polygon([(0, BH), (BW, BH), (vx + 260, vy + 200), (vx - 260, vy + 200)], fill=(30, 26, 36))
    d.rectangle((vx - 260, vy - 330, vx + 260, vy + 200), fill=(22, 18, 30))
    for side in (-1, 1):
        for shelf in range(6):
            f0 = 0.22 + shelf * 0.12
            for i in range(14):
                s0, s1 = 1 - 1 / (1 + i * 0.3), 1 - 1 / (1 + (i + 0.85) * 0.3)
                def pt(s, f):
                    x = lerp(0 if side < 0 else BW, vx + side * 260, s)
                    yt, yb = lerp(0, vy - 330, s), lerp(BH, vy + 200, s)
                    return (x, lerp(yt, yb, f))
                col = rnd.choice([(230, 60, 70), (250, 200, 60), (60, 160, 240), (90, 210, 120), (240, 120, 40),
                                  (200, 80, 200), (240, 240, 240), (40, 40, 60)])
                col = tuple(int(c * 0.55) for c in col)
                d.polygon([pt(s0, f0), pt(s1, f0), pt(s1, f0 + 0.09), pt(s0, f0 + 0.09)], fill=col)
                d.line([pt(s0, f0 + 0.095), pt(s1, f0 + 0.095)], fill=(70, 70, 80), width=4)
    fridge = (150, 210, 255) if not cool else (120, 180, 255)
    def lights(dd):
        dd.rectangle((vx - 230, vy - 300, vx + 230, vy + 170), fill=fridge + (150,))
        dd.rounded_rectangle((250, 330, 940, 470), radius=40, outline=(255, 60, 150, 255), width=18)
    img.alpha_composite(glow_layer(lights, 45))
    d = ImageDraw.Draw(img)
    for k in range(4):
        x = vx - 230 + k * 115
        d.rectangle((x + 6, vy - 300, x + 109, vy + 170), fill=tuple(int(c * 0.7) for c in fridge))
        d.line((x + 95, vy - 120, x + 95, vy - 40), fill=(220, 230, 240), width=6)
    neon = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    nd = ImageDraw.Draw(neon)
    nd.rounded_rectangle((250, 330, 940, 470), radius=40, outline=(255, 120, 190, 255), width=8)
    f = F("Inter-Black.otf", 96)
    nd.text((BW / 2 - f.getlength("SPÄTI 24/7") / 2, 345), "SPÄTI 24/7", font=f, fill=(255, 150, 210, 255))
    img.alpha_composite(neon.filter(ImageFilter.GaussianBlur(16)))
    img.alpha_composite(neon.filter(ImageFilter.GaussianBlur(3)))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 1560, BW, BH), fill=(34, 26, 30))
    d.rectangle((0, 1540, BW, 1575), fill=(70, 56, 60))
    d.rectangle((760, 1380, 1060, 1545), fill=(24, 22, 28))
    d.rectangle((780, 1400, 1040, 1480), fill=(40, 120, 110))
    img = img.filter(ImageFilter.GaussianBlur(5))
    img.alpha_composite(Image.new("RGBA", (BW, BH), (8, 4, 20, 60)))
    return img


def bg_counter():
    """Nahaufnahme Kassentresen: Milch, Kinderkekse, Fiebersaft im Neonlicht."""
    img = gradient((30, 18, 40), (14, 10, 20))
    d = ImageDraw.Draw(img)
    def back(dd):
        for k in range(16):
            x = k * 80
            dd.rectangle((x, 300, x + 60, 1100), fill=random.Random(k).choice(
                [(140, 40, 60), (40, 90, 150), (150, 120, 40), (60, 130, 80)]) + (160,))
        dd.ellipse((-200, 200, 500, 900), fill=(255, 60, 150, 120))
        dd.ellipse((700, 300, 1400, 1000), fill=(80, 160, 255, 110))
    img.alpha_composite(glow_layer(back, 50))
    d.rectangle((0, 1240, BW, BH), fill=(40, 32, 38))
    refl = glow_layer(lambda dd: (dd.ellipse((-100, 1300, 500, 1700), fill=(255, 60, 150, 70)),
                                  dd.ellipse((700, 1250, 1300, 1650), fill=(80, 160, 255, 60))), 60)
    img.alpha_composite(refl)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 1225, BW, 1250), fill=(90, 72, 80))
    # Milch
    mx = 230
    d.rectangle((mx - 110, 1270, mx + 110, 1640), fill=(235, 238, 242))
    d.polygon([(mx - 110, 1270), (mx + 110, 1270), (mx + 60, 1200), (mx - 60, 1200)], fill=(215, 220, 228))
    d.rectangle((mx - 110, 1440, mx + 110, 1520), fill=(60, 120, 210))
    # Kinderkekse
    kx = 590
    d.rectangle((kx - 170, 1380, kx + 170, 1640), fill=(230, 120, 40))
    for i in range(3):
        cx = kx - 100 + i * 100
        d.ellipse((cx - 38, 1460, cx + 38, 1536), fill=(170, 100, 40), outline=(250, 210, 120), width=6)
    d.rectangle((kx - 170, 1390, kx + 170, 1430), fill=(250, 220, 70))
    # Fiebersaft
    fx = 930
    d.rounded_rectangle((fx - 70, 1410, fx + 70, 1640), radius=22, fill=(150, 80, 30))
    d.rectangle((fx - 30, 1350, fx + 30, 1412), fill=(245, 245, 245))
    d.rectangle((fx - 70, 1480, fx + 70, 1570), fill=(240, 240, 235))
    d.line((fx - 45, 1510, fx + 45, 1510), fill=(220, 60, 60), width=8)
    d.line((fx - 45, 1540, fx + 25, 1540), fill=(120, 120, 120), width=6)
    img = img.filter(ImageFilter.GaussianBlur(2.5))
    return img


def bg_lockerroom(cool=False, phone=False):
    """Jungs-Umkleide: Metallspinde frontal, Bank, kaltes Neonröhrenlicht."""
    img = gradient((40, 50, 48), (16, 20, 22)) if not cool else gradient((24, 34, 52), (8, 12, 22))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 1500, BW, BH), fill=(44, 46, 50) if not cool else (26, 30, 40))
    lc = (70, 96, 90) if not cool else (52, 70, 100)
    for i in range(8):
        x0 = 20 + i * 145
        d.rectangle((x0, 420, x0 + 135, 1500), fill=lc)
        d.rectangle((x0 + 8, 430, x0 + 127, 1490), outline=tuple(int(c * 0.7) for c in lc), width=5)
        for k in range(5):
            d.line((x0 + 30, 480 + k * 22, x0 + 105, 480 + k * 22), fill=tuple(int(c * 0.55) for c in lc), width=6)
        d.rectangle((x0 + 100, 900, x0 + 112, 990), fill=(170, 175, 180))
    d.rectangle((0, 400, BW, 425), fill=(30, 34, 36))
    d.rectangle((60, 1600, BW - 60, 1660), fill=(110, 80, 55))
    d.rectangle((120, 1660, 150, 1800), fill=(50, 50, 55))
    d.rectangle((BW - 150, 1660, BW - 120, 1800), fill=(50, 50, 55))
    d.rounded_rectangle((300, 1560, 560, 1610), radius=20, fill=(180, 40, 50))  # Sporttasche
    tube = (200, 255, 230) if not cool else (190, 215, 255)
    def lights(dd):
        dd.rectangle((200, 140, 980, 175), fill=tube + (255,))
        dd.polygon([(200, 175), (980, 175), (BW + 200, 1500), (-200, 1500)], fill=tube + (26,))
    img.alpha_composite(glow_layer(lights, 40))
    img.alpha_composite(glow_layer(lambda dd: dd.rectangle((200, 140, 980, 175), fill=tube + (255,)), 3))
    if phone:
        # Handy-Licht in der Ecke hinter dem letzten Spind, mit rotem Aufnahmepunkt
        img.alpha_composite(Image.new("RGBA", (BW, BH), (0, 0, 0, 120)))
        img.alpha_composite(glow_layer(lambda dd: dd.ellipse((900, 900, 1250, 1300), fill=(200, 220, 255, 170)), 60))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((1060, 1000, 1150, 1170), radius=16, fill=(225, 235, 255))
        d.ellipse((1085, 1020, 1105, 1040), fill=(255, 40, 50))
    return img.filter(ImageFilter.GaussianBlur(5))


def bg_note():
    """Linas Tisch von oben, darauf ein gefalteter Zettel von Noah."""
    img = gradient((92, 62, 42), (60, 40, 28))
    d = ImageDraw.Draw(img)
    rnd = random.Random(8)
    for _ in range(60):
        y = rnd.randint(0, BH)
        d.line((0, y, BW, y + rnd.randint(-30, 30)), fill=(70, 46, 30, 255), width=rnd.randint(2, 6))
    img = img.filter(ImageFilter.GaussianBlur(2))
    img.alpha_composite(glow_layer(lambda dd: dd.ellipse((-300, -200, 900, 900), fill=(255, 230, 190, 70)), 120))
    note = Image.new("RGBA", (760, 520), (0, 0, 0, 0))
    nd = ImageDraw.Draw(note)
    nd.rectangle((0, 0, 759, 519), fill=(250, 248, 238))
    for k in range(7):
        nd.line((0, 90 + k * 62, 760, 90 + k * 62), fill=(170, 200, 235), width=3)
    nd.line((90, 0, 90, 520), fill=(240, 150, 150), width=3)
    nd.text((130, 150), "Lust auf Kino", font=F("InterDisplay-BoldItalic.otf", 74), fill=(30, 40, 110))
    nd.text((130, 260), "Freitag?", font=F("InterDisplay-BoldItalic.otf", 74), fill=(30, 40, 110))
    nd.text((470, 380), "– N.", font=F("InterDisplay-BoldItalic.otf", 70), fill=(30, 40, 110))
    note = note.rotate(-6, expand=True, resample=Image.BICUBIC)
    sh = Image.new("RGBA", note.size, (0, 0, 0, 0))
    sh.putalpha(note.getchannel("A").point(lambda v: int(v * 0.6)))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    x, y = (BW - note.width) // 2, 1180
    img.alpha_composite(sh, (x + 14, y + 24))
    img.alpha_composite(note, (x, y))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((80, 1850, 900, 1890), radius=18, fill=(40, 90, 200))  # Stift
    return img


BACKGROUNDS = {
    "rain": bg_rain, "hallway": bg_hallway, "door": bg_door, "classroom": bg_classroom,
    "classroom_cool": lambda: bg_classroom(cool=True), "yard": bg_yard,
    "black": bg_black, "black_red": lambda: bg_black(red=True),
    "spaeti": bg_spaeti, "spaeti_cool": lambda: bg_spaeti(cool=True), "counter": bg_counter,
    "lockerroom": bg_lockerroom, "lockerroom_cool": lambda: bg_lockerroom(cool=True),
    "lockerroom_phone": lambda: bg_lockerroom(cool=True, phone=True), "note": bg_note,
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

    def __init__(self, msgs, end_overlay_t, dur, title="Die Jungs 🐐", subtitle="Luca, Emre, Du", avatar="🐐",
                 group=True, clock="22:14", react=None, react_t=None):
        self.msgs, self.end_t, self.dur = msgs, end_overlay_t, dur
        self.subtitle, self.group, self.clock, self.react_t = subtitle, group, clock, react_t
        self.react = render_block([(t, F("Inter-ExtraBold.otf", s_), c, sp) for t, s_, c, sp in react]) if react else None
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
        d.text((60, 62), clock, font=F("Inter-SemiBold.otf", 34), fill=(230, 235, 238))
        d.rounded_rectangle((930, 70, 1000, 100), radius=8, outline=(230, 235, 238), width=3)
        d.rectangle((936, 76, 980, 94), fill=(230, 235, 238))
        d.line((70, 245, 100, 215), fill=(230, 235, 238), width=6)
        d.line((70, 245, 100, 275), fill=(230, 235, 238), width=6)
        d.ellipse((125, 190, 235, 300), fill=(70, 84, 94))
        base.alpha_composite(emoji_img(avatar, 64), (148, 212))
        draw_rich(base, (262, 192), title, F("Inter-SemiBold.otf", 46), (233, 237, 239))
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
        self.endcard = EndCard(end_overlay_t)

    def bubble(self, who, text):
        own = who == "Du"
        fn, ft, fm = F("Inter-SemiBold.otf", 36), F("Inter-Regular.otf", 52), F("Inter-Regular.otf", 26)
        lines = wrap(text, ft, 760)
        tw = max(text_w(l, ft) for l in lines)
        nh = 0 if own or not self.group else 50
        bw = int(max(tw + 120, 0 if own else fn.getlength(who)) + 52)
        bh = int(nh + len(lines) * 64 + 62)
        im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=26, fill=(self.OUT_C if own else self.IN_C) + (255,))
        if not own and self.group:
            d.text((26, 16), who, font=fn, fill=self.NAME_C.get(who, (200, 200, 200)))
        for i, l in enumerate(lines):
            draw_rich(im, (26, 18 + nh + i * 64), l, ft, (233, 237, 239))
        d.text((bw - (130 if own else 96), bh - 42), self.clock, font=fm, fill=(170, 190, 185) if own else (140, 155, 165))
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
        sub = self.subtitle
        sub_c = (140, 155, 165)
        if typing_who:
            sub, sub_c = (f"{typing_who} schreibt…" if self.group else "schreibt…"), (0, 200, 150)
            img.alpha_composite(self.typing, (30, typing_y))
            for k in range(3):
                off = math.sin(t * 9 - k * 0.9) * 7
                cx = 45 + 30 + k * 30
                d.ellipse((cx - 9, 43 - 9 + typing_y + off, cx + 9, 43 + 9 + typing_y + off), fill=(150, 165, 175))
        d.text((264, 252), sub, font=F("Inter-Regular.otf", 30), fill=sub_c)
        if self.react is not None and t >= self.react_t:
            img = react_overlay(img, t - self.react_t, self.react)
        return self.endcard.apply(img, t)


def react_overlay(img, dt, block, y=1000):
    """Reaktion auf dem Handy-Screen: Hintergrund unscharf + dunkel, großer Text."""
    e = 1 - (1 - min(1, dt / 0.45)) ** 3
    img = img.filter(ImageFilter.GaussianBlur(10 * e))
    img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(170 * e))))
    img.alpha_composite(_fade(block, e), (0, int(y - block.height / 2 + (1 - e) * 36)))
    return img


# ---------------------------------------------------------------- Insta-Szene (geheimer Account)
class Insta:
    """Dark-Mode-Post eines Accounts. Ein Like trifft als Push-Banner ein, dann kommt die Reaktion als Text."""

    def __init__(self, sc):
        self.sc = sc
        self.endcard = EndCard(sc["end_t"])
        user, clock = sc["user"], sc.get("clock", "01:12")
        base = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        d = ImageDraw.Draw(base)
        d.text((60, 62), clock, font=F("Inter-SemiBold.otf", 34), fill=(235, 235, 235))
        d.rounded_rectangle((930, 70, 1000, 100), radius=8, outline=(235, 235, 235), width=3)
        d.rectangle((936, 76, 960, 94), fill=(235, 235, 235))
        d.line((60, 235, 90, 205), fill=WHITE, width=6)
        d.line((60, 235, 90, 265), fill=WHITE, width=6)
        hf = F("Inter-Bold.otf", 44)
        d.text(((W - hf.getlength("Beiträge")) / 2, 205), "Beiträge", font=hf, fill=WHITE)
        ring = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ring)
        for r in range(60, 0, -1):
            k = r / 60
            rd.ellipse((60 - r, 60 - r, 60 + r, 60 + r), fill=(int(255 * k + 120 * (1 - k)), int(60 + 40 * k), int(200 - 60 * k)))
        rd.ellipse((8, 8, 112, 112), fill=(0, 0, 0))
        rd.ellipse((14, 14, 106, 106), fill=(28, 24, 48))
        ring.alpha_composite(emoji_img("🌙", 54), (33, 33))
        base.alpha_composite(ring, (40, 320))
        d.text((182, 352), user, font=F("Inter-Bold.otf", 38), fill=WHITE)
        for k in range(3):
            d.ellipse((1000 + k * 0, 350 + k * 18, 1010, 360 + k * 18), fill=WHITE)
        # Beitragsbild: Gedicht auf Nachthimmel
        post = gradient((14, 14, 40), (52, 22, 70), (W, W)).convert("RGBA")
        pd = ImageDraw.Draw(post)
        rnd = random.Random(4)
        for _ in range(120):
            x, y, r = rnd.randint(0, W), rnd.randint(0, W), rnd.uniform(1, 3.2)
            pd.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, rnd.randint(60, 200)))
        post.alpha_composite(glow_layer(lambda dd: dd.ellipse((700, 90, 960, 350), fill=(255, 230, 200, 120)), 50, (W, W)))
        pd.ellipse((760, 150, 900, 290), fill=(250, 240, 225))
        pd.ellipse((800, 130, 940, 270), fill=(40, 22, 58))
        self.post_top = 450
        base.alpha_composite(post, (0, self.post_top))
        self.poem = [render_block([(ln, F("Inter-LightItalic.otf", 66), (245, 240, 255), 0)], gap=1.0)
                     for ln in sc["poem"]]
        sig = F("Inter-Italic.otf", 34)
        self.sig = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
        ImageDraw.Draw(self.sig).text((W - 140, 10), "— m.", font=sig, fill=(200, 190, 230))
        ay = self.post_top + W + 30
        hx = 40
        for i, e in enumerate(("🤍", "💬", "📩")):
            base.alpha_composite(emoji_img(e, 64), (hx + i * 100, ay))
        base.alpha_composite(emoji_img("🔖", 60), (W - 100, ay))
        self.likes_y = ay + 100
        cf = F("Inter-Regular.otf", 36)
        d.text((40, self.likes_y + 60), user, font=F("Inter-Bold.otf", 36), fill=WHITE)
        d.text((60 + F("Inter-Bold.otf", 36).getlength(user), self.likes_y + 60), sc.get("caption", ""), font=cf, fill=(235, 235, 235))
        d.text((40, self.likes_y + 115), "vor 3 Minuten", font=F("Inter-Regular.otf", 30), fill=(140, 140, 140))
        self.base = base
        self.banner = self._banner(sc["like_from"])
        self.react = render_block([(t, F("Inter-ExtraBold.otf", s_), c, sp) for t, s_, c, sp in sc["react"]])

    def _banner(self, who):
        bw, bh = W - 60, 170
        im = Image.new("RGBA", (bw + 40, bh + 40), (0, 0, 0, 0))
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((20, 26, 20 + bw, 26 + bh), radius=40, fill=(0, 0, 0, 200))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((20, 20, 20 + bw, 20 + bh), radius=40, fill=(48, 48, 54, 250))
        icon = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        idr = ImageDraw.Draw(icon)
        for y in range(96):
            k = y / 95
            idr.line((0, y, 95, y), fill=(int(130 + 120 * k), int(50 + 20 * (1 - k)), int(220 - 120 * k)))
        mask = Image.new("L", (96, 96), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 95, 95), radius=24, fill=255)
        icon.putalpha(mask)
        idr = ImageDraw.Draw(icon)
        idr.rounded_rectangle((20, 20, 76, 76), radius=16, outline=WHITE, width=6)
        idr.ellipse((35, 35, 61, 61), outline=WHITE, width=6)
        im.alpha_composite(icon, (52, 57))
        d.text((175, 52), "INSTA", font=F("Inter-SemiBold.otf", 28), fill=(170, 170, 178))
        d.text((bw - 70, 52), "jetzt", font=F("Inter-Regular.otf", 28), fill=(170, 170, 178))
        draw_rich(im, (175, 94), f"{who} gefällt dein Beitrag. 🤍", F("Inter-SemiBold.otf", 40), WHITE)
        return im

    def frame(self, t):
        sc = self.sc
        img = self.base.copy()
        n = len(self.poem)
        total = sum(b.height for b in self.poem)
        y = self.post_top + W / 2 - total / 2 - 20
        for i, b in enumerate(self.poem):
            t0 = 0.3 + i * 0.7
            if t >= t0:
                e = 1 - (1 - min(1, (t - t0) / 0.6)) ** 3
                img.alpha_composite(_fade(b, e), (0, int(y + (1 - e) * 20)))
            y += b.height
        if t >= 0.3 + n * 0.7:
            img.alpha_composite(_fade(self.sig, min(1, (t - 0.3 - n * 0.7) / 0.5)), (0, self.post_top + W - 90))
        liked = t >= sc["like_t"]
        lf = F("Inter-Bold.otf", 36)
        label = f"Gefällt {1 if liked else 0} Mal"
        if liked and t - sc["like_t"] < 0.4:
            k = 1 + 0.35 * math.sin((t - sc["like_t"]) / 0.4 * math.pi)
            lf = F("Inter-Bold.otf", int(36 * k))
        ImageDraw.Draw(img).text((40, self.likes_y), label, font=lf, fill=(255, 92, 122) if liked else WHITE)
        if liked:
            p = min(1, (t - sc["like_t"]) / 0.35)
            e = 1 - (1 - p) ** 3
            img.alpha_composite(self.banner, (10, int(-200 + e * 500)))
        if t >= sc["react_t"]:
            p = min(1, (t - sc["react_t"]) / 0.45)
            e = 1 - (1 - p) ** 3
            img = img.filter(ImageFilter.GaussianBlur(10 * e))
            img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(170 * e))))
            img.alpha_composite(self.banner, (10, 300))
            img.alpha_composite(_fade(self.react, e), (0, int(1000 - self.react.height / 2 + (1 - e) * 36)))
        return self.endcard.apply(img, t)


# ---------------------------------------------------------------- Ende + CTA (für jede Folge gleich)
class EndCard:
    def __init__(self, end_t):
        self.end_t = end_t
        self.end_block = render_block([(f"Teil {TEIL + 1} folgt…", F("Inter-ExtraBold.otf", 88), WHITE, 0)])
        self.cta_text = render_block([("Folge dem Kanal,", F("Inter-ExtraBold.otf", 58), WHITE, 0),
                                      (f"damit du Teil {TEIL + 1} nicht verpasst 💗", F("Inter-Bold.otf", 46),
                                       (225, 225, 235), 6)])
        self.cta_button = cta_button()
        self.pointer = emoji_img("👆", 96)

    def apply(self, img, t):
        if t >= self.end_t:
            p = min(1, (t - self.end_t) / 0.6)
            img = img.filter(ImageFilter.GaussianBlur(14 * p))
            img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(205 * p))))
            img.alpha_composite(_fade(self.end_block, p), (0, int(600 - self.end_block.height / 2 + (1 - p) * 30)))
        tc = t - self.end_t - CTA_DELAY
        if tc >= 0:
            # Call-to-Action: „Folge dem Kanal“ + pulsierender Folgen-Button + tippender Finger
            p = min(1, tc / 0.45)
            e = 1 - (1 - p) ** 3
            img.alpha_composite(_fade(self.cta_text, e), (0, int(780 + (1 - e) * 30)))
            pop = 1 + 0.25 * math.sin(min(1, tc / 0.35) * math.pi) * (1 - min(1, tc / 0.35))
            pulse = pop * (1 + 0.045 * math.sin(max(0, tc - 0.35) * 2 * math.pi * 1.4))
            b = self.cta_button
            bw, bh = int(b.width * pulse * e + 1), int(b.height * pulse * e + 1)
            if bw > 4:
                bb = _fade(b.resize((bw, bh), Image.LANCZOS), e)
                img.alpha_composite(bb, (int(W / 2 - bw / 2), int(1110 - bh / 2)))
            if tc > 0.5:
                k = min(1, (tc - 0.5) / 0.3)
                bounce = abs(math.sin((tc - 0.5) * math.pi * 1.4)) * 28
                img.alpha_composite(_fade(self.pointer, k), (int(W / 2 + 120), int(1185 + bounce)))
        return img


CTA_DELAY = 0.8
CTA_PINK = (254, 44, 85)


def cta_button():
    """TikTok-artiger „+ Folgen“-Button (Pink, abgerundet, mit Glow)."""
    f = F("Inter-ExtraBold.otf", 60)
    label = "Folgen"
    tw = f.getlength(label)
    bw, bh = int(tw + 230), 130
    pad = 40
    im = Image.new("RGBA", (bw + 2 * pad, bh + 2 * pad), (0, 0, 0, 0))
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((pad, pad, pad + bw, pad + bh), radius=bh // 2, fill=CTA_PINK + (170,))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(22)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((pad, pad, pad + bw, pad + bh), radius=bh // 2, fill=CTA_PINK + (255,))
    cx, cy = pad + 82, pad + bh // 2
    d.rectangle((cx - 24, cy - 6, cx + 24, cy + 6), fill=WHITE)
    d.rectangle((cx - 6, cy - 24, cx + 6, cy + 24), fill=WHITE)
    d.text((pad + 135, cy - 38), label, font=f, fill=WHITE)
    return im


def _fade(im, k):
    if k >= 1:
        return im
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * k)))
    return out




SCENES = None
BADGE = None
GRAIN = None
BUILD = None
TEIL = 1


def init_worker():
    global SCENES, BADGE, GRAIN
    SCENES = BUILD()
    BADGE = badge(TEIL)
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
        chat = Chat(sc["msgs"], sc["end_t"], sc["dur"], **sc.get("chat_opts", {}))
    elif sc.get("insta"):
        chat = Insta(sc)
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
        if sc.get("chat") or sc.get("insta"):
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


# ---------------------------------------------------------------- Ton (KEINE Musikinstrumente!)
# Nur Atmo + Soundeffekte. Pro Szene steuerbar über:
#   amb="rain" | "room" | "outdoor" | "night" | "phone" | "silence"
#   boom=<sek>              dumpfer Bass-Schlag (Dramamoment)
#   heartbeat=(<sek>, <n>)  Herzschlag, n Schläge
# Automatisch: leiser Whoosh bei jedem Szenenwechsel, Nachrichtenton bei Chat-Nachrichten.
SR = 44100
AMB_DEFAULT = {"lockerroom": "room", "lockerroom_cool": "room", "lockerroom_phone": "night", "note": "room", "spaeti": "room", "spaeti_cool": "room", "counter": "room", "rain": "rain", "hallway": "room", "door": "room", "classroom": "room",
               "classroom_cool": "room", "yard": "outdoor", "black": "silence", "black_red": "silence"}


def _shaped_noise(rng, n, lo, hi):
    spec = np.fft.rfft(rng.standard_normal(n))
    fr = np.fft.rfftfreq(n, 1 / SR)
    spec *= (fr > lo) / (1 + (fr / hi) ** 2)
    x = np.fft.irfft(spec, n)
    return x / (np.max(np.abs(x)) + 1e-9)


def _ambience(kind, n, rng):
    t = np.arange(n) / SR
    if kind == "rain":
        base = _shaped_noise(rng, n, 150, 2200) * 0.20
        drops = np.zeros(n)
        for i in rng.integers(0, n, int(n / SR * 35)):
            L = min(400, n - i)
            drops[i:i + L] += rng.uniform(0.1, 0.35) * np.exp(-np.arange(L) / 60) * rng.standard_normal(L)
        return base + drops * 0.25
    if kind == "room":
        return _shaped_noise(rng, n, 40, 350) * 0.10
    if kind == "outdoor":
        wind = _shaped_noise(rng, n, 60, 600) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.23 * t + 1))
        return wind * 0.13
    if kind == "night":
        return _shaped_noise(rng, n, 30, 250) * 0.07
    if kind == "phone":
        return _shaped_noise(rng, n, 40, 300) * 0.06
    return _shaped_noise(rng, n, 30, 200) * 0.025  # silence = fast nichts


def _whoosh(rng):
    L = int(0.45 * SR)
    x = _shaped_noise(rng, L, 300, 3000)
    env = np.sin(np.linspace(0, np.pi, L)) ** 2
    return x * env * 0.09


def _boom(rng):
    L = int(2.2 * SR)
    tt = np.arange(L) / SR
    b = np.sin(2 * np.pi * np.cumsum(np.linspace(75, 32, L)) / SR) * np.exp(-tt * 2.2) * 0.38
    return b + _shaped_noise(rng, L, 20, 200) * np.exp(-tt * 8) * 0.2


def _heartbeat():
    L = int(0.9 * SR)
    tt = np.arange(L) / SR
    def thump(t0, amp):
        x = np.clip(tt - t0, 0, None)
        return amp * np.sin(2 * np.pi * 52 * x) * np.exp(-x * 22) * (tt >= t0)
    return thump(0, 0.42) + thump(0.24, 0.3)


def _pop(rng):
    """Kurzer, weicher „Plopp“ wenn der Folgen-Button erscheint (kein Instrument)."""
    L = int(0.12 * SR)
    tt = np.arange(L) / SR
    return (np.sin(2 * np.pi * np.cumsum(np.linspace(420, 160, L)) / SR) * np.exp(-tt * 40) * 0.35
            + _shaped_noise(rng, L, 500, 4000) * np.exp(-tt * 90) * 0.08)


def _pling():
    L = int(0.3 * SR)
    tt = np.arange(L) / SR
    return (np.sin(2 * np.pi * 1568 * tt) * (tt < 0.09) + np.sin(2 * np.pi * 2093 * tt) * (tt >= 0.07)) * np.exp(-tt * 14) * 0.22


def make_audio(path, scenes):
    rng = np.random.default_rng(2)
    starts, acc = [], 0.0
    for sc in scenes:
        starts.append(acc)
        acc += round(sc["dur"] * FPS) / FPS
    total = acc
    n = int((total + 0.2) * SR)
    out = np.zeros(n)
    xf = int(0.3 * SR)  # Überblendung der Atmo zwischen Szenen

    def add(sig, t0, gain=1.0):
        i0 = int(t0 * SR)
        if 0 <= i0 < n:
            L = min(len(sig), n - i0)
            out[i0:i0 + L] += sig[:L] * gain

    for i, sc in enumerate(scenes):
        kind = sc.get("amb") or ("phone" if sc.get("chat") or sc.get("insta") else AMB_DEFAULT.get(sc.get("bg"), "room"))
        i0 = max(0, int(starts[i] * SR) - xf // 2)
        i1 = min(n, int((starts[i] + sc["dur"]) * SR) + xf // 2)
        L = i1 - i0
        a = _ambience(kind, L, rng)
        env = np.ones(L)
        r = min(xf, L // 2)
        env[:r] = np.linspace(0, 1, r) if i > 0 else 1
        env[-r:] = np.linspace(1, 0, r)
        out[i0:i1] += a * env
        if i > 0:
            add(_whoosh(rng), starts[i] - 0.25)
        if sc.get("boom") is not None:
            add(_boom(rng), starts[i] + sc["boom"])
        if sc.get("heartbeat"):
            t0, k = sc["heartbeat"]
            for j in range(k):
                add(_heartbeat(), starts[i] + t0 + j * 0.85)
        for m in sc.get("msgs", []):
            add(_pling(), starts[i] + m["t"])
        for pt in sc.get("plings", []):
            add(_pling(), starts[i] + pt)
        if sc.get("end_t") is not None:
            add(_pop(rng), starts[i] + sc["end_t"] + CTA_DELAY)
    t = np.arange(n) / SR
    out *= np.clip((total - t) / 1.2, 0, 1)
    out = out / np.max(np.abs(out)) * 0.89
    pcm = (np.repeat(out[:, None], 2, axis=1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- Rendern
TMP = tempfile.mkdtemp(prefix="30tage_")


def render(build_scenes, teil, out):
    """Rendert eine Folge im 30-TAGE-Stil nach `out` (MP4, TikTok-fertig)."""
    global BUILD, TEIL
    BUILD, TEIL = build_scenes, teil
    init_worker()
    with Pool(os.cpu_count() or 2, initializer=init_worker) as pool:
        segs = pool.map(render_scene, range(len(SCENES)), chunksize=1)
    audio = os.path.join(TMP, "audio.wav")
    make_audio(audio, SCENES)
    lst = os.path.join(TMP, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{s}'\n" for s in segs)
    raw = os.path.join(TMP, "raw.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", audio,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", raw], check=True)
    # finale Kompression: TikTok-taugliche Bitrate, Datei < 60 MB
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-c:v", "libx264", "-preset", "slow",
                    "-crf", "21", "-maxrate", "9M", "-bufsize", "18M", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", out], check=True)
    print("Fertig:", out)
