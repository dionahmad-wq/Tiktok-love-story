# Bildstil der Referenzvideos

Analysiert aus zwei Referenzen (Nov. 2026):
- @storyial „Wieder zurück…“: 1:25, 1,1 Mio. Aufrufe, Originalton mit Stimmen, Untertitel Wort für Wort
- @selobitesxo „Das Kennenlernen..🤪“: 2:30, Musik „Theodora – Habiba“ plus Dialog
Hashtags bei beiden: #kistory #fürdich #ki #lovestory #emojistories

## Figuren
- Fotorealistische KI-Menschen, 17–20 Jahre, oft mit Migrationshintergrund, sehr attraktiv.
- Sie: lange dunkle Wellen, halber Pferdeschwanz, goldene Creolen und Kette, natürliches Make-up.
- Er: dunkle Locken (Taper Fade) oder blondiert, leichter Bart, Hoodie.
- **Festes Outfit pro Figur** durch das ganze Video, z. B. beige Strickjacke + helle Jeans, navy Zip-Hoodie + weißes Shirt + graue Jeans, roter Hoodie + graue Jogginghose, schwarze Pufferweste.

## Orte und Licht
- Echter deutscher Alltag: Bushaltestelle vor der Schule, Schultoilette mit Spiegel, ICE-Innenraum, Hauptbahnhof mit Glasdach, Hamburger Speicherstadt, Dönerladen mit Spieß, Hafen im Sonnenuntergang, Kinderzimmer nachts.
- Meist bewölkt, weich und natürlich. Warm nur im Dönerladen und bei Sonnenuntergang. Nachts: Gesicht nur vom Handy beleuchtet.

## Kamera und Schnitt
- 9:16, Einstellungen 2–4 s, harte Schnitte; @selobitesxo nutzt weiche Überblendungen.
- Wechsel Totale → Halbnah (zwei Personen) → Nahaufnahme der Person, die spricht oder reagiert. Viel Schuss-Gegenschuss über die Schulter.
- Starke Mimik: Tränen, große Augen, verlegenes Lächeln, verschmitztes Grinsen.

## Handy als Erzählmittel
- iPhone-Nahaufnahme mit iMessage und deutscher Tastatur (QWERTZ).
- iOS-Banner oben, z. B. „Klasse 11B – Screenshot von Deryas privater Nachricht“, „Kaan: Bist du gut nach Hause gekommen? :)“.
- Damit werden Wendungen und Cliffhanger erzählt.

## Untertitel (Stil @storyial)
- Ein Wort auf einmal, weiß, sehr fett, Großbuchstaben, schwarze Kontur und Schatten.
- Mittig, etwas unter der Bildmitte (bei uns top 1235 px, damit die TikTok-Leiste unten frei bleibt).
- Satzzeichen bleiben stehen („HAMBURG.“, „DAS?“, „IDIOT,“).

## Umsetzung im Code (tools/build.mjs)
- Standbilder mit Ken-Burns-Bewegung (push-in, pull-out, pan) und leichtem Handkamera-Wackeln.
- Farblooks: night, flashback (entsättigt, sepia, Vignette), warm.
- Leichtes Filmkorn und Vignette über allem.
- Weißer Blitz + tiefer Impact-Sound bei harten Wendungen.
