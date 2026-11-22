// Gemeinsame Helfer für tts.mjs, images.mjs und build.mjs.
import fs from "node:fs";
import path from "node:path";

export function loadStory(dir) {
  const file = path.join(dir, "story.json");
  if (!fs.existsSync(file)) throw new Error(`Keine story.json in ${dir}`);
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

// Jede gesprochene Zeile bekommt eine stabile ID: <szene>-<beatindex>
export function voiceLines(story) {
  const lines = [];
  for (const scene of story.scenes) {
    scene.beats.forEach((beat, i) => {
      if (beat.say) lines.push({ id: `${scene.id}-${i}`, scene, beat });
    });
  }
  return lines;
}

// Wörter mit geschätzten Zeiten, falls (noch) keine Sprachaufnahme existiert.
export function estimateWords(text, rate = 1) {
  const words = text.split(/\s+/).filter(Boolean);
  let t = 0.05;
  const out = [];
  for (const w of words) {
    const len = 0.16 + w.replace(/[^\p{L}\p{N}]/gu, "").length * 0.055;
    out.push({ word: w, start: t, end: t + len });
    t += len;
    if (/[.!?…]$/.test(w)) t += 0.32;
    else if (/[,;:]$/.test(w)) t += 0.16;
    else t += 0.04;
  }
  return { words: out.map((w) => ({ ...w, start: w.start / rate, end: w.end / rate })), duration: t / rate };
}

// Aus der Zeichen-Ausrichtung von ElevenLabs Wörter mit Zeiten bauen.
export function wordsFromAlignment(text, alignment) {
  const chars = alignment.characters;
  const starts = alignment.character_start_times_seconds;
  const ends = alignment.character_end_times_seconds;
  const words = [];
  let cur = null;
  for (let i = 0; i < chars.length; i++) {
    const c = chars[i];
    if (/\s/.test(c)) {
      if (cur) words.push(cur);
      cur = null;
      continue;
    }
    if (!cur) cur = { word: "", start: starts[i], end: ends[i] };
    cur.word += c;
    cur.end = ends[i];
  }
  if (cur) words.push(cur);
  // Regie-Tags wie [whispers] nicht als Untertitel zeigen
  return words.filter((w) => !/^\[.*\]$/.test(w.word));
}

export function ensureDir(d) {
  fs.mkdirSync(d, { recursive: true });
  return d;
}
