# Projekt: TikTok-Serie „30 TAGE“ (Deutsch, Teen-Romance)

## Feste Vorgaben des Nutzers (immer einhalten)
- **Folge 1 (`video/folge01_30tage.mp4`) ist die perfekte Referenz.** Alle weiteren Videos werden exakt in diesem Stil gemacht. Die Regeln stehen in `serie/04_stil.md`.
- **KEINE Musikinstrumente im Ton.** Kein Klavier, keine Melodie, keine Beats. Nur Atmo (Regen, Raumton, Wind, Stille) und Soundeffekte (Whoosh, Bass-Schlag, Herzschlag, Nachrichtenton).
- **Jedes Video endet mit einer CTA „Folge dem Kanal“** und einem „+ Folgen“-Button (ist in `video/stil.py` eingebaut).
- Alles auf **Deutsch**, im Stil deutscher Jugendlicher, spannend, mit Cliffhanger in jeder Folge.
- Mit dem Nutzer auf Deutsch kommunizieren.

## Technik
- Engine: `video/stil.py` (Hintergründe, Text, Chat, Ton, `render()`)
- Pro Folge eine Datei `video/folgeXX.py`, die nur `build_scenes()` definiert
- Drehbücher: `serie/02_staffel1_folgen.md`; Figuren: `serie/01_charaktere.md`
- Videos größer als 60 MB vermeiden (GitHub-Limit 100 MB); `render()` komprimiert schon passend
