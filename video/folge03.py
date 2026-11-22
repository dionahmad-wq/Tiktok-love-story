#!/usr/bin/env python3
"""„30 TAGE“ – Folge 3: „Die Wette“.  Aufruf: python3 video/folge03.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stil import *  # noqa: F401,F403

GREY = (190, 190, 200)


def build_scenes():
    return [
        dict(bg="lockerroom", dur=4.4, fx="dust_cool", items=[
            (0.0, render_block([("Ihr wisst es. Ich wusste es nicht.", F("Inter-ExtraBold.otf", 76), WHITE, 0)])),
            (1.7, narr("Und genau das macht's so schlimm.", 64, PINK, "Inter-ExtraBold.otf"))]),
        dict(bg="lockerroom", dur=4.4, fx="dust_cool", items=[
            (0.25, narr("Jungs-Umkleide. Nach Sport.", 52, GREY, "Inter-SemiBold.otf")),
            (1.2, narr("Was ich nicht gesehen hab…", 74, WHITE, "Inter-ExtraBold.otf"))]),
        dict(bg="lockerroom", dur=6.2, fx="dust_cool", items=[
            (0.3, speaker("Luca", "500 Euro, Noah. 30 Tage. Sie verliebt sich in dich – dann machst du Schluss. Vor allen.", LUCA_C))]),
        dict(bg="lockerroom_cool", dur=6.6, fx="dust_cool", items=[
            (0.3, speaker("Noah", "Sie ist nicht wie die anderen.", NOAH_C)),
            (2.8, speaker("Luca", "Hast du Angst, oder was?", LUCA_C))]),
        dict(bg="lockerroom_cool", dur=4.2, fx="dust_cool", items=[
            (0.3, narr("Ein Handschlag.", 64)),
            (1.3, narr("Deal.", 140, WHITE, "Inter-Black.otf"))]),
        dict(bg="lockerroom_phone", dur=5.0, fx=None, items=[
            (0.3, narr("Aber hinter dem letzten Spind…", 62)),
            (1.9, narr("…hat jemand gefilmt.", 74, PINK, "Inter-ExtraBold.otf"))]),
        dict(bg="black_red", dur=3.4, fx=None, items=[
            (0.5, narr("Jassi.", 130, JASSI_C, "Inter-Black.otf")),
            (1.4, narr("Noahs Ex.", 64, WHITE, "Inter-ExtraBold.otf"))], boom=0.5, heartbeat=(1.0, 3)),
        dict(bg="black", dur=2.6, fx=None, badge=False, items=[
            (0.2, narr("Am nächsten Morgen.", 52, GREY, "Inter-SemiBold.otf")),
            (0.9, narr("Auf meinem Tisch.", 72, WHITE, "Inter-ExtraBold.otf"))]),
        dict(bg="note", dur=4.4, fx="dust", items=[
            (1.2, narr("Von ihm.", 84, NOAH_C, "Inter-Black.otf"))]),
        dict(chat=True, dur=15.2, chat_opts=dict(
                title="Selin 💅", subtitle="online", avatar="💅", group=False, clock="07:58",
                react_t=8.8, react=[("Ich hab Ja gesagt.", 84, WHITE, 0),
                                    ("Zu einer Wette.", 76, PINK, 16)]),
             heartbeat=(8.8, 2),
             msgs=[
                 dict(**{"from": "Du"}, text="SELIN.", typing=None, t=0.7),
                 dict(**{"from": "Du"}, text="Noah hat mir 'nen Zettel hingelegt 😳", typing=None, t=1.6),
                 dict(**{"from": "Selin"}, text="WAS 😭😭 was steht drauf", typing=2.3, t=3.4),
                 dict(**{"from": "Du"}, text="Kino. Freitag.", typing=None, t=4.6),
                 dict(**{"from": "Selin"}, text="UND??? sag JA", typing=5.2, t=6.3),
                 dict(**{"from": "Du"}, text="hab schon ja gesagt 🙈", typing=None, t=7.5),
             ], end_t=11.0),
    ]


if __name__ == "__main__":
    render(build_scenes, teil=3, out=os.path.join(OUT_DIR, "folge03_30tage.mp4"))
