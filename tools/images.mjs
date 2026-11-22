// Erzeugt die fotorealistischen Szenenbilder mit der OpenAI-Bild-API.
// 1. Pro Figur ein Referenzbild (assets/refs/<figur>.png), damit Gesicht und Outfit gleich bleiben.
// 2. Pro Szene ein Bild (assets/img/<szene>.png), mit den Referenzbildern als Vorlage.
// Aufruf: node tools/images.mjs videos/<id> [--force] [--only s03,s04] [--refs-only]
// Der Schlüssel kommt vom Proxy der Umgebung; lokal geht auch OPENAI_API_KEY.
import fs from "node:fs";
import path from "node:path";
import { loadStory, ensureDir } from "./lib.mjs";

const args = process.argv.slice(2);
const dir = args[0];
if (!dir) {
  console.error("Aufruf: node tools/images.mjs videos/<id> [--force] [--only s03,s04] [--refs-only]");
  process.exit(1);
}
const force = args.includes("--force");
const refsOnly = args.includes("--refs-only");
const onlyIdx = args.indexOf("--only");
const only = onlyIdx >= 0 ? new Set(args[onlyIdx + 1].split(",")) : null;

const story = loadStory(dir);
const model = process.env.OPENAI_IMAGE_MODEL || "gpt-image-1";
const quality = process.env.OPENAI_IMAGE_QUALITY || "high";
const key = process.env.OPENAI_API_KEY || "proxy-injected";
const refDir = ensureDir(path.join(dir, "assets", "refs"));
const imgDir = ensureDir(path.join(dir, "assets", "img"));

async function call(endpoint, init) {
  for (let attempt = 1; attempt <= 3; attempt++) {
    const res = await fetch(`https://api.openai.com/v1/images/${endpoint}`, {
      ...init,
      headers: { authorization: `Bearer ${key}`, ...(init.headers || {}) },
    });
    if (res.ok) {
      const data = await res.json();
      return Buffer.from(data.data[0].b64_json, "base64");
    }
    const msg = (await res.text()).slice(0, 300);
    if (res.status === 401 || res.status === 400 || attempt === 3) throw new Error(`HTTP ${res.status}: ${msg}`);
    await new Promise((r) => setTimeout(r, 4000 * attempt));
  }
}

// 1. Referenzbilder der Figuren
for (const [id, ch] of Object.entries(story.characters)) {
  const out = path.join(refDir, `${id}.png`);
  if (fs.existsSync(out) && !force) continue;
  const prompt = `${story.style}. Character reference photo: ${ch.look}. Standing on a German city sidewalk, three-quarter body shot, face clearly visible, looking slightly past the camera, neutral expression.`;
  console.log(`→ Referenz ${ch.name} …`);
  const buf = await call("generations", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ model, prompt, size: "1024x1536", quality, n: 1 }),
  });
  fs.writeFileSync(out, buf);
  console.log(`✓ ${out}`);
}
if (refsOnly) process.exit(0);

// 2. Szenenbilder
for (const scene of story.scenes) {
  if (!scene.image) continue;
  if (only && !only.has(scene.id)) continue;
  const out = path.join(imgDir, `${scene.id}.png`);
  if (fs.existsSync(out) && !force) continue;
  const chars = scene.image.chars || [];
  const who = chars
    .map((c, i) => `${story.characters[c].name} is the person in reference image ${i + 1} (${story.characters[c].look})`)
    .join(". ");
  const prompt = `${story.style}. ${who}. Keep faces, hair and outfits exactly as in the reference images. Scene: ${scene.image.prompt}. Use the names only to identify people, never show them as text.`;
  const form = new FormData();
  form.append("model", model);
  form.append("prompt", prompt);
  form.append("size", "1024x1536");
  form.append("quality", quality);
  for (const c of chars) {
    const ref = path.join(refDir, `${c}.png`);
    form.append("image[]", new Blob([fs.readFileSync(ref)], { type: "image/png" }), `${c}.png`);
  }
  console.log(`→ Szene ${scene.id} …`);
  const buf = chars.length
    ? await call("edits", { method: "POST", body: form })
    : await call("generations", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ model, prompt, size: "1024x1536", quality, n: 1 }),
      });
  fs.writeFileSync(out, buf);
  console.log(`✓ ${out}`);
}
console.log("Bilder fertig.");
