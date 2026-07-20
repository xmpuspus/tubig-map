// Records the tubig-map flythrough as webm for the README hero GIF.
// Real recording of the real deployed site (workflow rule: no mockups).
// Run: node site/scripts/record_demo.mjs [url]
// Defaults to the live site; pass http://localhost:8737/ for a local build.

import { chromium } from "/Users/xavier/Desktop/leaves-ph/site/node_modules/playwright/index.mjs";

const URL = process.argv[2] || "https://tubig-map.vercel.app/";
const OUT_DIR = "tmp/demo";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  recordVideo: { dir: OUT_DIR, size: { width: 1280, height: 720 } },
  deviceScaleFactor: 1,
});
const page = await ctx.newPage();
await page.goto(URL, { waitUntil: "networkidle" });
await page.waitForFunction(() => window._map && window._map.loaded(), { timeout: 60000 });

// Full-bleed map so the recording is the product, not the page chrome.
await page.evaluate(() => {
  document.querySelectorAll("header, section, footer").forEach((el) => el.remove());
  Object.assign(document.body.style, { margin: "0", overflow: "hidden" });
  const wrap = document.getElementById("map-wrap");
  Object.assign(wrap.style, { position: "fixed", inset: "0", maxWidth: "none", padding: "0", margin: "0" });
  const map = document.getElementById("map");
  Object.assign(map.style, { height: "100vh", minHeight: "0", border: "0", borderRadius: "0" });
  window._map.resize();
});
await sleep(1800);

// Walk the story: the restricted ground, the Metro Manila cluster, one course
// popup with its 2024 and 2026 numbers, the Laguna corridor, then pull back.
const beats = [
  { fly: { center: [121.05, 14.62], zoom: 10.4, duration: 2600 }, hold: 1400 },
  { fly: { center: [121.0478, 14.5928], zoom: 13.7, duration: 2400 }, hold: 800, click: true },
  { hold: 2200 },
  { fly: { center: [121.07, 14.28], zoom: 11.4, duration: 2600 }, hold: 1800 },
  { fly: { center: [121.02, 14.55], zoom: 9.4, duration: 2400 }, hold: 1500 },
];

for (const b of beats) {
  if (b.fly) {
    await page.evaluate((f) => window._map.flyTo({ ...f, essential: true }), b.fly);
    await sleep(b.fly.duration);
  }
  if (b.click) await page.mouse.click(640, 360);
  await sleep(b.hold);
}

await ctx.close();
const video = await page.video().path();
console.log("video:", video);
await browser.close();
