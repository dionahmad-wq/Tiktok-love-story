// Baut aus videos/<id>/story.json ein HyperFrames-Projekt (index.html) im selben Ordner.
// Aufruf: node tools/build.mjs videos/<id>
// Danach: (cd videos/<id> && npx hyperframes render -o out/<id>.mp4)
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { loadStory, estimateWords, ensureDir } from "./lib.mjs";

const TOOLS = path.dirname(fileURLToPath(import.meta.url));
const dir = process.argv[2];
if (!dir) {
  console.error("Aufruf: node tools/build.mjs videos/<id>");
  process.exit(1);
}
const story = loadStory(dir);
const W = 1080, H = 1920;
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const r3 = (n) => Math.round(n * 1000) / 1000;

ensureDir(path.join(dir, "assets"));
fs.copyFileSync(path.join(TOOLS, "node_modules/gsap/dist/gsap.min.js"), path.join(dir, "assets/gsap.min.js"));

// ---------- Soundeffekte (einmal erzeugen) ----------
const sfxDir = path.join(dir, "assets", "sfx");
if (!fs.existsSync(path.join(sfxDir, "receive.wav"))) {
  execFileSync("python3", [path.join(TOOLS, "audio_gen.py"), "sfx", sfxDir], { stdio: "inherit" });
}

// ---------- Bilder: echte Bilder oder Platzhalter ----------
const GRADES = {
  flashback: "saturate(0.45) sepia(0.28) contrast(1.06) brightness(0.93)",
  night: "contrast(1.08) brightness(0.92) saturate(0.9)",
  warm: "saturate(1.08) sepia(0.12) brightness(1.03)",
  none: "contrast(1.03) saturate(1.02)",
};
function sceneImage(scene) {
  for (const ext of ["png", "jpg", "jpeg", "webp"]) {
    const rel = `assets/img/${scene.id}.${ext}`;
    if (fs.existsSync(path.join(dir, rel))) return { src: rel, placeholder: false };
  }
  // Platzhalter, bis die Bild-KI das echte Bild geliefert hat
  const rel = `assets/img/${scene.id}.placeholder.svg`;
  ensureDir(path.join(dir, "assets/img"));
  const words = scene.image.prompt.split(" ");
  const lines = [];
  let cur = "";
  for (const w of words) {
    if ((cur + " " + w).length > 34) { lines.push(cur); cur = w; } else cur = cur ? cur + " " + w : w;
  }
  if (cur) lines.push(cur);
  const hue = { flashback: 35, night: 225, warm: 25 }[scene.grade] ?? 200;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1536" viewBox="0 0 1024 1536">
<defs><linearGradient id="g" x1="0" y1="0" x2="0.4" y2="1"><stop offset="0" stop-color="hsl(${hue},25%,32%)"/><stop offset="1" stop-color="hsl(${hue + 20},30%,12%)"/></linearGradient></defs>
<rect width="1024" height="1536" fill="url(#g)"/>
<text x="512" y="300" text-anchor="middle" font-family="Inter" font-weight="800" font-size="54" fill="#fff" opacity="0.9">BILD ${esc(scene.id.toUpperCase())}</text>
<text x="512" y="360" text-anchor="middle" font-family="Inter" font-size="30" fill="#fff" opacity="0.6">kommt von der Bild-KI</text>
${lines.slice(0, 14).map((l, i) => `<text x="512" y="${980 + i * 40}" text-anchor="middle" font-family="Inter" font-size="30" fill="#fff" opacity="0.55">${esc(l)}</text>`).join("\n")}
</svg>`;
  fs.writeFileSync(path.join(dir, rel), svg);
  return { src: rel, placeholder: true };
}

// ---------- Zeitplan berechnen ----------
const FADE = 0.5;
let t = 0;
const scenes = [];
const audio = []; // {src, start, dur, vol}
const words = []; // {word, start, end}
const texts = []; // {text, start, dur, style}
const notifs = []; // {start, app, title, text}
const flashes = []; // times
let missingVoice = 0, placeholders = 0;

// Chat-Zustand über alle Handy-Szenen hinweg
const chat = { items: story.chat ? story.chat.history.map((m) => ({ ...m })) : [], draft: story.chat?.draft || "", status: null };

for (let si = 0; si < story.scenes.length; si++) {
  const scene = story.scenes[si];
  const tr = scene.transition || "cut";
  const start = si > 0 && tr === "fade" ? t - FADE : t;
  if (tr === "flash") {
    flashes.push(start);
    audio.push({ src: "assets/sfx/impact.wav", start: Math.max(0, start - 0.05), dur: 1.6, vol: 0.55 });
  }
  let c = start + (tr === "fade" ? FADE * 0.6 : 0.1);
  const phoneEvents = [];
  const phoneStart = { items: chat.items.map((m) => ({ ...m })), draft: chat.draft, status: chat.status };

  for (let bi = 0; bi < scene.beats.length; bi++) {
    const b = scene.beats[bi];
    if (b.say) {
      const id = `${scene.id}-${bi}`;
      const metaFile = path.join(dir, "assets/voice", `${id}.json`);
      let meta;
      if (fs.existsSync(metaFile) && JSON.parse(fs.readFileSync(metaFile, "utf8")).text === b.text) {
        meta = JSON.parse(fs.readFileSync(metaFile, "utf8"));
        audio.push({ src: `assets/voice/${id}.mp3`, start: c, dur: meta.duration + 0.3, vol: 1 });
      } else {
        meta = estimateWords(b.text);
        missingVoice++;
      }
      if (b.captions !== false) {
        for (const w of meta.words) words.push({ word: w.word, start: c + w.start, end: c + w.end });
      }
      c += meta.duration + (b.gap ?? 0.25);
    } else if (b.text && !b.phone) {
      texts.push({ text: b.text, start: c, dur: b.dur, style: b.style || "caption" });
      if (b.style === "end") audio.push({ src: "assets/sfx/impact.wav", start: c, dur: 1.6, vol: 0.4 });
      c += b.dur;
    } else if (b.wait) {
      c += b.wait;
    } else if (b.notify) {
      notifs.push({ start: c, ...b.notify });
      audio.push({ src: "assets/sfx/receive.wav", start: c, dur: 0.6, vol: 0.6 });
      c += b.dur ?? 0.4;
    } else if (b.phone) {
      const at = c;
      if (b.phone === "send") {
        chat.items.push({ from: "me", text: chat.draft, key: `m${chat.items.length}`, appear: at });
        chat.draft = "";
        chat.status = "Zugestellt";
        phoneEvents.push({ type: "send", at });
        audio.push({ src: "assets/sfx/send.wav", start: at, dur: 0.5, vol: 0.6 });
      } else if (b.phone === "read") {
        chat.status = "Gelesen 14:32";
        phoneEvents.push({ type: "read", at });
      } else if (b.phone === "typing") {
        phoneEvents.push({ type: "typing", at, dur: b.dur });
      } else if (b.phone === "receive") {
        chat.items.push({ from: "them", text: b.text, key: `m${chat.items.length}`, appear: at });
        phoneEvents.push({ type: "receive", at });
        audio.push({ src: "assets/sfx/receive.wav", start: at, dur: 0.6, vol: 0.65 });
      }
      c += b.dur ?? 1;
    }
  }
  const end = c + 0.15;
  const s = { scene, start, end, tr, phoneEvents, phoneStart, phoneEnd: { items: chat.items.map((m) => ({ ...m })), status: chat.status } };
  if (scene.image) {
    s.img = sceneImage(scene);
    if (s.img.placeholder) placeholders++;
  }
  scenes.push(s);
  t = end;
}
const TOTAL = r3(t + 0.2);

// Musik in passender Länge
const mood = story.music?.mood || "sad";
const musicRel = `assets/music-${mood}.wav`;
const musicFile = path.join(dir, musicRel);
const needLen = Math.ceil(TOTAL) + 1;
let haveLen = 0;
if (fs.existsSync(musicFile)) haveLen = (fs.statSync(musicFile).size - 44) / (44100 * 4);
if (haveLen < needLen || haveLen > needLen + 1) {
  execFileSync("python3", [path.join(TOOLS, "audio_gen.py"), "music", musicFile, String(needLen), mood], { stdio: "inherit" });
}
audio.push({ src: musicRel, start: 0, dur: TOTAL, vol: story.music?.volume ?? 0.32, fadeOut: 1.5 });

// ---------- HTML ----------
const html = [];
const js = [];
let uid = 0;
const nid = (p) => `${p}${++uid}`;

// Szenen
scenes.forEach((s, i) => {
  const dur = r3(s.end - s.start);
  const sid = `scene-${s.scene.id}`;
  if (s.scene.image) {
    const grade = GRADES[s.scene.grade || "none"];
    html.push(`<div id="${sid}" class="clip scene" data-start="${r3(s.start)}" data-duration="${dur}" style="z-index:${10 + i}">
  <img id="${sid}-img" class="still" src="${s.img.src}" style="filter:${grade}" alt="">
  ${s.scene.grade === "flashback" ? '<div class="flashback-tint"></div>' : ""}
</div>`);
    const cam = s.scene.camera || "push-in";
    const im = `#${sid}-img`;
    const from = { "push-in": { scale: 1.0, x: 0 }, "pull-out": { scale: 1.14, x: 0 }, "pan-left": { scale: 1.14, x: 50 }, "pan-right": { scale: 1.14, x: -50 }, static: { scale: 1.04, x: 0 } }[cam];
    const to = { "push-in": { scale: 1.13, x: 0 }, "pull-out": { scale: 1.0, x: 0 }, "pan-left": { scale: 1.14, x: -50 }, "pan-right": { scale: 1.14, x: 50 }, static: { scale: 1.06, x: 0 } }[cam];
    js.push(`tl.fromTo("${im}", ${JSON.stringify(from)}, { ...${JSON.stringify(to)}, duration: ${dur}, ease: "none" }, ${r3(s.start)});`);
    // leichtes Handkamera-Wackeln
    js.push(`tl.fromTo("#${sid}", { y: -4, rotation: -0.15 }, { y: 4, rotation: 0.15, duration: ${r3(dur / 2)}, ease: "sine.inOut", yoyo: true, repeat: 1 }, ${r3(s.start)});`);
  } else if (s.scene.phone) {
    const bg = scenes.find((x) => x.scene.id === s.scene.phone.background);
    html.push(`<div id="${sid}" class="clip scene phone-scene" data-start="${r3(s.start)}" data-duration="${dur}" style="z-index:${10 + i}">
  <img class="still blurred" src="${bg?.img?.src || ""}" alt="">
  <div class="phone-dim"></div>
  ${phoneHTML(s, sid)}
</div>`);
    js.push(`tl.fromTo("#${sid} .phone", { y: 260, rotation: -1, scale: 0.96 }, { y: 0, rotation: -2.5, scale: 1, duration: 0.55, ease: "power3.out" }, ${r3(s.start)});`);
    js.push(`tl.to("#${sid} .phone", { y: -10, rotation: -2, duration: ${r3(Math.max(0.6, dur - 0.55))}, ease: "sine.inOut" }, ${r3(s.start + 0.55)});`);
    for (const ev of s.phoneEvents) phoneEventJS(ev, sid);
  }
  if (s.tr === "fade" && i > 0) js.push(`tl.fromTo("#${sid}", { opacity: 0 }, { opacity: 1, duration: ${FADE}, ease: "sine.inOut" }, ${r3(s.start)});`);
});

function bubble(m, sid, hiddenKeys) {
  const hidden = hiddenKeys.has(m.key);
  const cls = m.from === "me" ? "me" : "them";
  return `${m.time ? `<div class="chat-time">${esc(m.time)}</div>` : ""}<div class="slot${hidden ? " later" : ""}" ${hidden ? `id="${sid}-${m.key}"` : ""}><div class="bubble ${cls}">${esc(m.text)}</div></div>`;
}

function phoneHTML(s, sid) {
  const start = s.phoneStart;
  const endItems = s.phoneEnd.items;
  const newKeys = new Set(endItems.filter((m) => m.appear !== undefined && m.appear >= s.start).map((m) => m.key));
  const hasTyping = s.phoneEvents.some((e) => e.type === "typing");
  const hasSend = s.phoneEvents.some((e) => e.type === "send");
  const hasRead = s.phoneEvents.some((e) => e.type === "read");
  const lastMe = [...endItems].reverse().find((m) => m.from === "me");
  // Bubbles inkl. Status unter der letzten eigenen Nachricht
  const parts = [];
  for (const m of endItems) {
    parts.push(bubble(m, sid, newKeys));
    if (lastMe && m.key === lastMe.key) {
      const initial = start.status && !hasSend ? start.status : "";
      parts.push(`<div class="slot${hasSend ? " later" : ""}" id="${sid}-status"><div class="status"><span class="st-a">${esc(hasSend ? "Zugestellt" : initial)}</span><span class="st-b">${esc("Gelesen 14:32")}</span></div></div>`);
    }
  }
  if (hasTyping) parts.push(`<div class="slot later" id="${sid}-typing"><div class="bubble them typing"><i></i><i></i><i></i></div></div>`);
  const draft = start.draft;
  const keys = "QWERTZUIOPÜ|ASDFGHJKLÖÄ|YXCVBNM".split("|");
  return `<div class="phone">
  <div class="screen">
    <div class="statusbar" data-layout-ignore><span>14:31</span><span class="island"></span><span class="sb-right">▮▮▮ 5G ▭</span></div>
    <div class="chat-head"><span class="back">‹</span><div class="avatar">${esc(story.chat.contact[0])}</div><div class="contact">${esc(story.chat.contact)} ›</div></div>
    <div class="chat-body">${parts.join("\n")}</div>
    <div class="inputbar"><span class="plus">+</span><div class="input"><span class="draft">${esc(draft)}</span><span class="placeholder"${draft ? "" : ' style="opacity:1"'}>iMessage</span></div><span class="sendbtn">↑</span></div>
    <div class="keyboard" data-layout-ignore>${keys.map((r) => `<div class="krow">${[...r].map((k) => `<b>${k}</b>`).join("")}</div>`).join("")}<div class="krow"><b class="wide">123</b><b class="space">Leerzeichen</b><b class="wide">⏎</b></div></div>
  </div>
</div>`;
}

function phoneEventJS(ev, sid) {
  const at = r3(ev.at);
  if (ev.type === "send") {
    js.push(`growNext("#${sid}", ${at});`);
    js.push(`tl.to("#${sid} .draft", { opacity: 0, duration: 0.12 }, ${at}); tl.to("#${sid} .placeholder", { opacity: 1, duration: 0.12 }, ${at});`);
    js.push(`tl.to("#${sid} .sendbtn", { scale: 0.8, duration: 0.08, yoyo: true, repeat: 1 }, ${r3(ev.at - 0.1)});`);
    js.push(`grow("#${sid}-status", ${r3(ev.at + 0.35)});`);
  } else if (ev.type === "read") {
    js.push(`tl.to("#${sid}-status .st-a", { opacity: 0, duration: 0.15 }, ${at}); tl.to("#${sid}-status .st-b", { opacity: 1, duration: 0.15 }, ${at});`);
  } else if (ev.type === "typing") {
    js.push(`grow("#${sid}-typing", ${at});`);
    js.push(`tl.fromTo("#${sid}-typing i", { opacity: 0.3 }, { opacity: 1, duration: 0.3, stagger: 0.12, yoyo: true, repeat: ${Math.max(1, Math.floor(ev.dur / 0.3))} }, ${at});`);
  } else if (ev.type === "receive") {
    js.push(`shrink("#${sid}-typing", ${r3(ev.at - 0.05)});`);
    js.push(`growNext("#${sid}", ${at});`);
  }
}

// Untertitel: ein Wort nach dem anderen
words.forEach((w, i) => {
  const id = nid("w");
  const next = words[i + 1];
  const end = next && next.start - w.end < 0.6 ? next.start : w.end + 0.25;
  html.push(`<div id="${id}" class="clip word" data-start="${r3(w.start)}" data-duration="${r3(end - w.start)}">${esc(w.word.toUpperCase())}</div>`);
  js.push(`tl.fromTo("#${id}", { scale: 0.82 }, { scale: 1, duration: 0.09, ease: "back.out(3)" }, ${r3(w.start)});`);
});

// Texttafeln (Datum, Ende)
for (const x of texts) {
  const id = nid("t");
  html.push(`<div id="${id}" class="clip title title-${x.style}" data-start="${r3(x.start)}" data-duration="${r3(x.dur)}"><span>${esc(x.text)}</span></div>`);
  js.push(`tl.fromTo("#${id} span", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, ${r3(x.start)});`);
}

// Benachrichtigungen
for (const n of notifs) {
  const id = nid("n");
  html.push(`<div id="${id}" class="clip notif" data-start="${r3(n.start)}" data-duration="3.4">
  <div class="n-icon">${n.app === "WhatsApp" ? "✆" : "✉"}</div>
  <div class="n-body"><div class="n-top"><b>${esc(n.title)}</b><span>jetzt</span></div><div class="n-text">${esc(n.text)}</div></div>
</div>`);
  js.push(`tl.fromTo("#${id}", { y: -260 }, { y: 0, duration: 0.45, ease: "power3.out" }, ${r3(n.start)});`);
  js.push(`tl.to("#${id}", { y: -260, duration: 0.35, ease: "power2.in" }, ${r3(n.start + 3.0)});`);
}

// Weiße Blitze bei harten Wendungen
for (const f of flashes) {
  const id = nid("f");
  html.push(`<div id="${id}" class="clip flash" data-start="${r3(f)}" data-duration="0.5"></div>`);
  js.push(`tl.fromTo("#${id}", { opacity: 0.95 }, { opacity: 0, duration: 0.45, ease: "power2.out" }, ${r3(f)});`);
}

// Audio
audio.forEach((a) => {
  html.push(`<audio id="${nid("a")}" src="${a.src}" data-start="${r3(a.start)}" data-duration="${r3(a.dur)}" data-volume="${a.vol}"${a.fadeOut ? ` data-fade-out="${a.fadeOut}"` : ""}></audio>`);
});

const page = `<!doctype html>
<html lang="de" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=${W}, height=${H}" />
<title>${esc(story.title)}</title>
<script src="assets/gsap.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: ${W}px; height: ${H}px; overflow: hidden; background: #000; }
#root { position: relative; width: ${W}px; height: ${H}px; overflow: hidden; font-family: "Inter", sans-serif; }
.clip { position: absolute; }
.scene { inset: 0; overflow: hidden; background: #000; }
.still { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; transform-origin: 50% 45%; }
.blurred { filter: blur(26px) brightness(0.55); transform: scale(1.15); }
.flashback-tint { position: absolute; inset: 0; background: radial-gradient(ellipse at center, rgba(255,235,200,0.06) 40%, rgba(40,25,10,0.55) 100%); }
.vignette { position: absolute; inset: 0; z-index: 900; pointer-events: none; background: radial-gradient(ellipse at 50% 45%, transparent 55%, rgba(0,0,0,0.45) 100%); }
.grain { position: absolute; inset: 0; z-index: 901; opacity: 0.07; mix-blend-mode: overlay; pointer-events: none; }
.word { left: 60px; right: 60px; top: 1235px; z-index: 950; text-align: center; color: #fff; font-weight: 900; font-size: 74px; letter-spacing: 0.01em;
  -webkit-text-stroke: 3px #000; paint-order: stroke fill; text-shadow: 0 4px 14px rgba(0,0,0,0.65), 0 0 2px #000; }
.title { left: 0; right: 0; z-index: 950; text-align: center; color: #fff; }
.title-date { top: 300px; font-weight: 800; font-size: 46px; letter-spacing: 0.32em; text-shadow: 0 3px 16px rgba(0,0,0,0.8); }
.title-caption { top: 1235px; font-weight: 900; font-size: 70px; -webkit-text-stroke: 3px #000; paint-order: stroke fill; }
.title-end { top: 820px; font-weight: 900; font-size: 120px; -webkit-text-stroke: 4px #000; paint-order: stroke fill; text-shadow: 0 6px 24px rgba(0,0,0,0.7); }
.flash { inset: 0; z-index: 990; background: #fff; }
.notif { left: 34px; right: 34px; top: 70px; z-index: 980; display: flex; gap: 22px; align-items: center; padding: 26px 30px;
  background: rgba(235,235,240,0.88); border-radius: 44px; box-shadow: 0 10px 40px rgba(0,0,0,0.35); backdrop-filter: blur(20px); }
.n-icon { width: 84px; height: 84px; border-radius: 20px; background: #25d366; color: #fff; font-size: 50px; display: flex; align-items: center; justify-content: center; flex: none; }
.n-body { flex: 1; color: #111; }
.n-top { display: flex; justify-content: space-between; font-size: 34px; }
.n-top span { color: #666; font-size: 28px; }
.n-text { font-size: 33px; margin-top: 6px; line-height: 1.25; }
/* Handy */
.phone-dim { position: absolute; inset: 0; background: rgba(0,0,0,0.25); }
.phone { position: absolute; left: 115px; top: 150px; width: 850px; height: 1740px; border-radius: 120px; background: #1c1c1e; padding: 22px;
  box-shadow: 0 40px 120px rgba(0,0,0,0.6), inset 0 0 0 4px #3a3a3c; transform-origin: 50% 80%; }
.screen { position: relative; width: 100%; height: 100%; border-radius: 100px; overflow: hidden; background: #fff; display: flex; flex-direction: column; }
.statusbar { height: 110px; display: flex; align-items: center; justify-content: space-between; padding: 26px 70px 0; font-weight: 700; font-size: 34px; color: #000; }
.island { width: 230px; height: 66px; background: #000; border-radius: 40px; }
.sb-right { font-size: 24px; letter-spacing: 2px; }
.chat-head { height: 190px; display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative; border-bottom: 1px solid #e5e5ea; background: #f9f9f9; }
.back { position: absolute; left: 34px; top: 40px; font-size: 80px; color: #0a84ff; font-weight: 300; }
.avatar { width: 96px; height: 96px; border-radius: 50%; background: linear-gradient(#a8adb7, #858a94); color: #fff; font-size: 46px; font-weight: 600; display: flex; align-items: center; justify-content: center; }
.contact { margin-top: 10px; font-size: 28px; color: #000; }
.chat-body { flex: 1; display: flex; flex-direction: column; justify-content: flex-end; padding: 0 30px 20px; gap: 0; overflow: hidden; }
.chat-time { text-align: center; color: #8e8e93; font-size: 24px; margin: 16px 0 10px; }
.slot { overflow: hidden; display: flex; flex-direction: column; }
.slot.later { max-height: 0; opacity: 0; }
.bubble { max-width: 76%; padding: 20px 30px; border-radius: 44px; font-size: 38px; line-height: 1.28; margin-top: 10px; }
.bubble.them { align-self: flex-start; background: #e9e9eb; color: #000; }
.bubble.me { align-self: flex-end; background: #0a84ff; color: #fff; }
.typing { display: flex; gap: 10px; padding: 28px 32px; }
.typing i { width: 18px; height: 18px; border-radius: 50%; background: #8e8e93; display: block; }
.status { align-self: flex-end; position: relative; height: 34px; width: 260px; margin-top: 4px; color: #8e8e93; font-size: 24px; text-align: right; }
.status span { position: absolute; right: 8px; top: 2px; }
.st-b { opacity: 0; }
.inputbar { display: flex; align-items: center; gap: 18px; padding: 14px 26px 18px; }
.plus { width: 66px; height: 66px; border-radius: 50%; background: #e9e9eb; color: #8e8e93; font-size: 46px; display: flex; align-items: center; justify-content: center; }
.input { flex: 1; position: relative; min-height: 72px; border: 2px solid #d1d1d6; border-radius: 40px; padding: 14px 28px; font-size: 34px; color: #000; }
.input .placeholder { position: absolute; left: 28px; top: 16px; color: #b0b0b5; opacity: 0; }
.sendbtn { width: 66px; height: 66px; border-radius: 50%; background: #0a84ff; color: #fff; font-size: 40px; font-weight: 700; display: flex; align-items: center; justify-content: center; }
.keyboard { background: #d1d3d9; padding: 16px 8px 60px; }
.krow { display: flex; justify-content: center; gap: 9px; margin: 11px 0; }
.krow b { width: 66px; height: 88px; background: #fff; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-weight: 400; font-size: 36px; color: #000; box-shadow: 0 2px 0 #898a8d; }
.krow b.wide { width: 130px; background: #abafb9; font-size: 28px; }
.krow b.space { width: 420px; font-size: 28px; }
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="${TOTAL}" data-width="${W}" data-height="${H}">
${html.join("\n")}
<div class="vignette"></div>
<svg class="grain" width="${W}" height="${H}"><filter id="nf"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4"/></filter><rect width="100%" height="100%" filter="url(#nf)"/></svg>
</div>
<script>
const tl = gsap.timeline({ paused: true });
// Chat-Elemente: über max-height aufklappen (ohne Messen, funktioniert auch in versteckten Szenen)
const OPEN = { maxHeight: 320, opacity: 1, duration: 0.32, ease: "power1.out" };
function grow(sel, at) {
  const el = document.querySelector(sel);
  if (!el) return;
  el.classList.add("grown");
  tl.fromTo(el, { maxHeight: 0, opacity: 0 }, { ...OPEN }, at);
}
function shrink(sel, at) {
  const el = document.querySelector(sel);
  if (el) tl.to(el, { maxHeight: 0, opacity: 0, duration: 0.12 }, at);
}
function growNext(sceneSel, at) {
  const el = [...document.querySelectorAll(sceneSel + " .slot.later")].find((e) => !e.classList.contains("grown") && !/(status|typing)$/.test(e.id));
  if (!el) return;
  el.classList.add("grown");
  tl.fromTo(el, { maxHeight: 0, opacity: 0 }, { ...OPEN }, at);
  tl.fromTo(el.firstElementChild, { scale: 0.6, transformOrigin: "0% 100%" }, { scale: 1, duration: 0.3, ease: "back.out(2)" }, at);
}
${js.join("\n")}
window.__timelines = window.__timelines || {};
window.__timelines["main"] = tl;
tl.seek(0);
</script>
</body>
</html>
`;
fs.writeFileSync(path.join(dir, "index.html"), page);
fs.writeFileSync(path.join(dir, "hyperframes.json"), JSON.stringify({ $schema: "https://hyperframes.heygen.com/schema/hyperframes.json", paths: { assets: "assets" } }, null, 2) + "\n");
fs.writeFileSync(path.join(dir, "meta.json"), JSON.stringify({ id: story.id, name: story.title }, null, 2) + "\n");

console.log(`✓ ${dir}/index.html  (${TOTAL.toFixed(1)} s, ${scenes.length} Szenen, ${words.length} Untertitel-Wörter)`);
if (missingVoice) console.log(`  ⚠ ${missingVoice} Zeilen ohne Stimme (Zeiten geschätzt) → node tools/tts.mjs ${dir}`);
if (placeholders) console.log(`  ⚠ ${placeholders} Szenen mit Platzhalter-Bild → node tools/images.mjs ${dir}`);
