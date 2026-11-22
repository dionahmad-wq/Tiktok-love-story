#!/usr/bin/env python3
"""„30 TAGE“ – Folge 1: „Der neue Typ“.  Aufruf: python3 video/folge01.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stil import *  # noqa: F401,F403


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
            (0.5, narr("Heute weiß ich's.", 92, WHITE, "Inter-Black.otf"))], boom=0.5, heartbeat=(0.9, 3)),
        dict(bg="black", dur=2.4, fx=None, badge=False, items=[
            (0.2, narr("Am selben Abend.", 52, (190, 190, 200), "Inter-SemiBold.otf")),
            (0.9, narr("Noahs Handy.", 72, NOAH_C, "Inter-ExtraBold.otf"))]),
        dict(chat=True, dur=14.0, msgs=[
            dict(**{"from": "Luca"}, text="Tag 1 von 30. Die Uhr läuft, Bruder 😂💸", typing=0.5, t=1.5),
            dict(**{"from": "Du"}, text="Chill. Sie hat schon geredet.", typing=None, t=3.4),
            dict(**{"from": "Emre"}, text="Ich find das immer noch lost ey…", typing=4.3, t=5.6),
            dict(**{"from": "Luca"}, text="Noch 29 Tage. Dann will ich sehen, wie sie heult 😂", typing=6.6, t=7.8),
        ], end_t=9.8),
    ]


if __name__ == "__main__":
    render(build_scenes, teil=1, out=os.path.join(OUT_DIR, "folge01_30tage.mp4"))
