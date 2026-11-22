#!/usr/bin/env python3
"""„30 TAGE“ – Folge 2: „Späti, 23:47 Uhr“.  Aufruf: python3 video/folge02.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stil import *  # noqa: F401,F403

MURAT_C = TEACH_C


def build_scenes():
    return [
        dict(bg="spaeti", dur=4.4, fx="dust", items=[
            (0.0, render_block([("Er kam jede Nacht in den Späti, in dem ich arbeite.", F("Inter-ExtraBold.otf", 76), WHITE, 0)])),
            (1.7, narr("Immer um 23:47 Uhr.", 70, PINK, "Inter-ExtraBold.otf"))]),
        dict(bg="spaeti", dur=4.6, fx="dust", items=[
            (0.25, narr("Ich hab den Laden immer gemocht.", 64)),
            (1.6, narr("Bis er reingelaufen ist.", 72, WHITE, "Inter-ExtraBold.otf"))]),
        dict(bg="spaeti", dur=7.0, fx="dust", items=[
            (0.3, speaker("Noah", "Ach ne. Du arbeitest hier?", NOAH_C)),
            (2.9, speaker("Lina", "Nein, ich steh nur aus Spaß an der Kasse.", LINA_C, PINK))]),
        dict(bg="counter", dur=5.2, fx="dust", items=[
            (0.3, narr("Milch. Kinderkekse. Fiebersaft.", 70, WHITE, "Inter-ExtraBold.otf")),
            (1.9, narr("Komischer Einkauf für einen Badboy.", 58))]),
        dict(bg="spaeti_cool", dur=6.4, fx="dust_cool", items=[
            (0.3, speaker("Lina", "Partynacht, oder was?", LINA_C, PINK)),
            (2.6, speaker("Noah", "Frag nicht.", NOAH_C))]),
        dict(bg="spaeti", dur=6.0, fx="dust", items=[
            (0.3, narr("Dann kam Onkel Murat aus dem Lager.", 54, (220, 220, 230), "Inter-SemiBold.otf")),
            (1.5, speaker("Onkel Murat", "Der Junge war gestern auch schon da. Um 2 Uhr nachts.", MURAT_C))]),
        dict(bg="rain", dur=5.0, fx="rain", items=[
            (0.3, narr("Ich wollte nicht über ihn nachdenken.", 62)),
            (2.0, narr("Hab ich trotzdem.", 78, PINK, "Inter-ExtraBold.otf"))]),
        dict(bg="black_red", dur=3.2, fx=None, items=[
            (0.5, narr("Ich hab ein Geheimnis.", 88, WHITE, "Inter-Black.otf"))], boom=0.5, heartbeat=(0.9, 3)),
        dict(bg="black", dur=2.6, fx=None, badge=False, items=[
            (0.2, narr("01:12 Uhr.", 52, (190, 190, 200), "Inter-SemiBold.otf")),
            (0.9, narr("Mein geheimer Account.", 70, PINK, "Inter-ExtraBold.otf"))]),
        dict(insta=True, dur=12.6, user="mitternachtsgedanken", clock="01:12",
             caption="nachts ist alles lauter.",
             poem=["manche menschen", "tragen ihre traurigkeit", "in lederjacken."],
             like_from="noah.k", like_t=3.8, plings=[3.8],
             react_t=5.4, heartbeat=(5.4, 2),
             react=[("noah.k.", 96, NOAH_C, 0),
                    ("Woher kennt ER meinen Account?!", 60, PINK, 14)],
             end_t=8.4),
    ]


if __name__ == "__main__":
    render(build_scenes, teil=2, out=os.path.join(OUT_DIR, "folge02_30tage.mp4"))
