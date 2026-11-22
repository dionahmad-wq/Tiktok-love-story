// Erzeugt die Stimmen aller Dialogzeilen über ElevenLabs (mit Wort-Zeitstempeln).
// Aufruf: node tools/tts.mjs videos/<id> [--force]
// Der API-Schlüssel wird vom Proxy der Umgebung eingesetzt; lokal geht auch ELEVENLABS_API_KEY.
import fs from "node:fs";
import path from "node:path";
import { loadStory, voiceLines, wordsFromAlignment, ensureDir } from "./lib.mjs";

const dir = process.argv[2];
const force = process.argv.includes("--force");
if (!dir) {
  console.error("Aufruf: node tools/tts.mjs videos/<id> [--force]");
  process.exit(1);
}
const story = loadStory(dir);
const outDir = ensureDir(path.join(dir, "assets", "voice"));
const model = process.env.ELEVEN_MODEL || story.voiceModel || "eleven_v3";
const key = process.env.ELEVENLABS_API_KEY || "proxy-injected";

let ok = 0, failed = 0;
for (const { id, beat } of voiceLines(story)) {
  const mp3 = path.join(outDir, `${id}.mp3`);
  const meta = path.join(outDir, `${id}.json`);
  if (!force && fs.existsSync(mp3) && fs.existsSync(meta)) {
    const m = JSON.parse(fs.readFileSync(meta, "utf8"));
    if (m.text === beat.text && m.speaker === beat.say) { ok++; continue; }
  }
  const ch = story.characters[beat.say];
  if (!ch?.voice?.id) throw new Error(`Keine Stimme für ${beat.say}`);
  const v = ch.voice;
  // eleven_v3 versteht Regie-Tags wie [whispers]
  let text = beat.text;
  if (model === "eleven_v3" && beat.tone) text = `[${beat.tone === "whisper" ? "whispers" : beat.tone}] ${text}`;
  const body = {
    text,
    model_id: model,
    voice_settings: { stability: v.stability ?? 0.5, similarity_boost: v.similarity_boost ?? 0.8, style: v.style ?? 0.3, use_speaker_boost: true },
  };
  if (model !== "eleven_multilingual_v2") body.language_code = "de";
  const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${v.id}/with-timestamps?output_format=mp3_44100_128`, {
    method: "POST",
    headers: { "xi-api-key": key, "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    console.error(`✗ ${id} (${beat.say}): HTTP ${res.status} ${(await res.text()).slice(0, 200)}`);
    failed++;
    if (res.status === 401) break;
    continue;
  }
  const data = await res.json();
  fs.writeFileSync(mp3, Buffer.from(data.audio_base64, "base64"));
  const align = data.normalized_alignment || data.alignment;
  const words = wordsFromAlignment(text, align);
  const duration = align.character_end_times_seconds.at(-1);
  fs.writeFileSync(meta, JSON.stringify({ speaker: beat.say, text: beat.text, model, duration, words }, null, 2));
  console.log(`✓ ${id} ${beat.say}: "${beat.text}" (${duration.toFixed(2)}s)`);
  ok++;
}
console.log(`Stimmen fertig: ${ok} ok, ${failed} fehlgeschlagen`);
if (failed) process.exit(2);
