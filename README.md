# Tiktok-love-story

Deutsche KI-Lovestory-Videos für TikTok, komplett im Code mit [HyperFrames](https://hyperframes.heygen.com).

- Skill: `.claude/skills/tiktok-love-story/SKILL.md` (Ablauf, Stil, Story-Formel)
- Werkzeuge: `tools/` (Stimmen, Bilder, Musik, Builder)
- Videos: `videos/<nnn>-<slug>/story.json`

```bash
cd tools && npm install && cd ..
NODE_USE_ENV_PROXY=1 node tools/tts.mjs videos/001-dreh-dich-um
NODE_USE_ENV_PROXY=1 node tools/images.mjs videos/001-dreh-dich-um
node tools/build.mjs videos/001-dreh-dich-um
cd videos/001-dreh-dich-um && ../../tools/node_modules/.bin/hyperframes render -o out/001.mp4
```
