---
name: tiktok-love-story
description: Erstellt komplette deutsche TikTok-KI-Lovestory-Videos (#kistory #emojistories) im Stil der Referenz-Creator, vollständig im Code mit HyperFrames: Story, fotorealistische Szenenbilder, Stimmen, Untertitel Wort für Wort, Handy-Chats, Benachrichtigungen, Musik und Render als MP4. Benutzen, wenn der Nutzer ein neues Video, eine neue Folge, einen Teil 2 oder eine Story-Idee für seinen TikTok-Kanal will.
---

# TikTok-KI-Lovestory-Videos

Ziel: ein fertiges, hochkantes MP4 (1080×1920), das aussieht wie die Videos der Referenz-Creator
(@storyial, @selobitesxo). **Alles auf Deutsch.** Der Nutzer will nichts selbst machen; Claude macht alles im Code.

Lies zuerst:
- `serie/bibel.md`: die Serienbibel (Figuren mit festem Look, Orte, Endlos-Regeln, Staffelpläne). **Jede neue Folge setzt diese Serie fort**, außer der Nutzer will ausdrücklich etwas anderes.
- `serie/kanon.md`: Stand der Serie (letzter Cliffhanger, feste Fakten, Stimmen, offene Fäden). Nach jeder Folge aktualisieren.
- `references/stil.md`: wie die Referenzvideos aussehen (Bild, Kamera, Untertitel, Handy-UI). Danach richten sich alle Entscheidungen.
- `references/story-formel.md`: Aufbau der Geschichte, Hook, Cliffhanger, Themen-Ideen.

## Ablauf für ein neues Video

1. **Nächste Folge aus der Serienbibel nehmen** (Checkliste in Abschnitt 9). Für Einzelvideos außerhalb der Serie: **Thema wählen und Story schreiben.** Spannend, emotional und allgemein nachvollziehbar (erste Liebe, zweite Chance, Eifersucht, Geheimnis, Familie gegen die Liebe …). Wenn der Nutzer kein Thema nennt, selbst eins aussuchen. Dauer 45–75 s.
2. **`videos/<nnn>-<slug>/story.json` anlegen.** Vorlage: `videos/001-dreh-dich-um/story.json`. Gleiche Figuren über Folgen hinweg wiederverwenden (Look und Stimme aus der letzten Folge kopieren), damit der Kanal wiedererkennbar bleibt.
3. **Stimmen:** `NODE_USE_ENV_PROXY=1 node tools/tts.mjs videos/<id>` (ElevenLabs, Modell `eleven_v3`, Sprache Deutsch, mit Wort-Zeitstempeln).
4. **Bilder:** `NODE_USE_ENV_PROXY=1 node tools/images.mjs videos/<id>` (OpenAI `gpt-image-1`). Erst Referenzbilder der Figuren, dann jede Szene mit diesen Referenzen, damit die Gesichter gleich bleiben. Einzelne Szenen neu: `--only s03,s07 --force`.
5. **Bauen:** `node tools/build.mjs videos/<id>` erzeugt `index.html` (HyperFrames-Komposition), Musik und Soundeffekte.
6. **Prüfen:** im Videoordner `../../tools/node_modules/.bin/hyperframes check` (0 Fehler; Warnungen `line_unread` bei Einzelwort-Untertiteln sind gewollt), dann `… snapshot --at <sekunden>` und die Bilder **ansehen**, bevor gerendert wird.
7. **Rendern:** `../../tools/node_modules/.bin/hyperframes render -q delivery -o out/<id>.mp4` (für schnelle Vorschau `-q draft`).
8. **Kanon aktualisieren:** `serie/kanon.md` (Stand, neue Fakten, Outfits, offene Fäden).
9. **Liefern:** MP4 an den Nutzer schicken, dazu Caption und Hashtags aus der story.json zum Kopieren.

Erstes Setup in einer neuen Sitzung: `cd tools && npm install`. Node-Skripte brauchen `NODE_USE_ENV_PROXY=1`, sonst erreicht `fetch` das Netz nicht.
Die Umgebung „Tiktok-channel“ hat TikTok, ElevenLabs (Schlüssel als Netzwerk-Secret) und muss für Bilder `api.openai.com` mit Schlüssel haben.

Fehlen Stimmen oder Bilder, baut `build.mjs` trotzdem: Zeiten werden geschätzt, Bilder als Platzhalter-Tafeln gezeigt. So kann man Story und Schnitt schon prüfen. Platzhalter **nie** als fertiges Video ausgeben, sondern klar sagen, was fehlt.

## story.json – Bausteine

```jsonc
{
  "id": "002-…", "title": "…", "caption": "…", "hashtags": ["#kistory", "#fürdich", "#ki", "#lovestory", "#emojistories"],
  "style": "ultra-realistic candid smartphone photo, …",           // gilt für alle Bilder (Englisch, besser für die Bild-KI)
  "music": { "mood": "sad" | "hopeful", "volume": 0.32 },          // optional
  "characters": { "lina": { "name": "Lina", "look": "…", "voice": { "id": "<elevenlabs voice id>", "stability": 0.4 } } },
  "chat": { "contact": "Emre", "history": [{ "from": "them", "text": "…", "time": "12. Juni 2024, 22:41" }], "draft": "…" },
  "scenes": [
    { "id": "s01",
      "image": { "chars": ["lina"], "prompt": "close-up of Lina …" },  // Bildszene
      "camera": "push-in" | "pull-out" | "pan-left" | "pan-right" | "static",
      "grade": "none" | "night" | "flashback" | "warm",
      "transition": "cut" | "fade" | "flash",                         // Übergang INTO diese Szene
      "beats": [
        { "say": "lina", "text": "Zwei Jahre.", "tone": "whisper" },   // Dialog: Stimme + Untertitel Wort für Wort
        { "say": "lina", "text": "…", "captions": false },              // Stimme ohne Untertitel (z. B. über Handy)
        { "text": "12. JUNI 2024", "dur": 1.4, "style": "date" },     // Texttafel: date | caption | end
        { "notify": { "app": "WhatsApp", "title": "…", "text": "…" } }, // iOS-Banner oben
        { "wait": 0.8 }
      ] },
    { "id": "s02", "phone": { "background": "s01" },                  // Handy-Szene (iMessage), Hintergrund = unscharfes Bild einer Szene
      "beats": [ { "phone": "open", "dur": 2 }, { "phone": "send" }, { "phone": "read" },
                 { "phone": "typing", "dur": 1.5 }, { "phone": "receive", "text": "Dreh dich um." } ] }
  ]
}
```

Der Chat-Zustand läuft über alle Handy-Szenen weiter (gesendete und empfangene Nachrichten bleiben sichtbar).

## Regeln

- Sprache im Video: Deutsch, Jugendsprache, kurze Sätze. Bild-Prompts: Englisch.
- Hook in den ersten 2 Sekunden (Gesicht mit starker Emotion + erster Satz). Ende immer mit Cliffhanger + „TEIL 2? 🤍“.
- Jede Szene 2–4 s, ein Bild pro Einstellung, viel Nahaufnahme. Etwa 12–18 Szenen pro Video.
- Figuren tragen in jeder Szene derselben Folge dasselbe Outfit (außer es ist begründet, z. B. nachts im Bett).
- Keine echten Personen, Marken oder Logos nachbilden; eigene Figuren und eigene Musik (wird in `tools/audio_gen.py` erzeugt).
- Renders (`out/`) und `.hyperframes/` werden nicht committet; story.json, Bilder und Stimmen schon.
