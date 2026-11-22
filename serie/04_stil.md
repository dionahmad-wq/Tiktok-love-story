# 🎨 Der „30 TAGE“-Stil (verbindlich für alle Folgen)

Folge 1 ist die Referenz. **Jede neue Folge sieht und klingt genau so.**

## 1. Format
- Hochformat **1080×1920**, **30 fps**, H.264 + AAC, Länge **45–60 Sekunden**
- 9–11 Szenen pro Folge, jede **3–7 Sekunden** lang
- Zwischen den Szenen eine **kurze Abblende über Schwarz** (0,16 s). Ausnahme: Die allererste Szene startet sofort ohne Abblende.

## 2. Aufbau jeder Folge
1. **Hook (0–4 s):** Text ist **ab Frame 1 lesbar**, groß (Inter ExtraBold 76). Die zweite Zeile ist die Pointe in **Pink**.
2. **Story-Szenen:** Erzähltext und Dialoge
3. **Dramamoment:** kurzer Satz auf Schwarz mit rotem Glühen, dazu Bass-Schlag und Herzschlag
4. **Überleitung:** „Am selben Abend.“ / „<Name>s Handy.“ auf Schwarz
5. **Cliffhanger als Chat** (WhatsApp-Dark-Mode) mit „schreibt…“-Anzeige und Nachrichtenton
6. **Ende mit CTA (immer!):** Der Chat wird unscharf und dunkel, dann erscheint „Teil X+1 folgt…“. 0,8 s später kommt **„Folge dem Kanal, damit du Teil X+1 nicht verpasst 💗“** mit einem pinken, pulsierenden **„+ Folgen“-Button** (Plopp-Geräusch) und einem tippenden 👆. Die CTA steht mindestens 3 Sekunden. Das macht die Engine automatisch, die Chat-Szene muss nur `dur ≈ end_t + 4.2` haben.

## 3. Optik
| Element | Regel |
|---|---|
| Hintergründe | gezeichnet und stimmungsvoll: `rain`, `hallway`, `door`, `classroom`, `classroom_cool`, `yard`, `black`, `black_red` |
| Bewegung | langsamer Zoom (7 % pro Szene), Partikel (`rain`, `dust`, `dust_cool`) und Filmkorn |
| Look | Vignette, dunkle Farbtöne, leichte Unschärfe im Hintergrund |
| Badge | oben mittig „● 30 TAGE · TEIL X“, außer auf Überleitungen und im Chat |
| Textposition | vertikal um **y = 930** zentriert (TikTok-sichere Zone), max. 920 px breit |
| Schrift | **Inter** (Bold / ExtraBold / Black), schwarze Kontur und weicher Schatten |
| Animation | Text blendet in 0,4 s ein und gleitet dabei 36 px nach oben |

### Figurenfarben (immer gleich!)
| Figur | Farbe |
|---|---|
| Erzähltext | Weiß |
| **Noah** | Hellblau `(140, 200, 255)` |
| **Lina** | Weiß, Namensschild in Pink `(255, 92, 122)` |
| Lehrer/Erwachsene | Warmgelb `(255, 214, 150)` |
| Pointe/Schock | Pink `(255, 92, 122)` |
| Chat: Luca | Rot `(255, 120, 110)` |
| Chat: Emre | Grün `(120, 220, 160)` |

Dialoge stehen immer so: **NAME** (klein, Großbuchstaben), darunter das Zitat in deutschen Anführungszeichen „…“.

## 4. Ton: ⚠️ KEINE MUSIKINSTRUMENTE
Kein Klavier, keine Gitarre, keine Beats, keine Melodien. Erlaubt sind nur:
- **Atmo** pro Szene: Regen (`rain`), Raumton (`room`), Wind draußen (`outdoor`), Nacht (`night`), Handy-Stille (`phone`), fast Stille (`silence`)
- **Soundeffekte:** leiser Whoosh beim Szenenwechsel, dumpfer Bass-Schlag (`boom`), Herzschlag (`heartbeat`), Nachrichtenton im Chat, Plopp beim Folgen-Button

Einen Trend-Sound legt der Account-Inhaber selbst in der TikTok-App drüber, falls gewünscht.

## 5. Neue Folge erstellen
1. `video/folge01.py` nach `video/folgeXX.py` kopieren
2. In `build_scenes()` das Drehbuch aus `serie/02_staffel1_folgen.md` eintragen
3. Unten `teil=XX` und den Dateinamen `folgeXX_30tage.mp4` anpassen
4. `python3 video/folgeXX.py` dauert ca. 4 Minuten
5. Vor dem Abschluss Standbilder prüfen: Text lesbar, nichts abgeschnitten, Datei unter 60 MB
