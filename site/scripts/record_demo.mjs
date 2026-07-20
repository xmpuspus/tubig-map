// Records the tubig-map flythrough as webm for the README hero GIF.
// Real recording of the real site (workflow rule: no mockups).
// Run: node site/scripts/record_demo.mjs  (server must be up on :8737)

import { chromium } from "/Users/xavier/Desktop/leaves-ph/site/node_modules/playwright/index.mjs";

const OUT_DIR = "tmp/demo";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const SHOTS = [
  { center: [121.05, 14.55], zoom: 10.5, duration: 2800, hold: 1400 },  // Metro Manila cluster
  { center: [121.05, 14.5928], zoom: 13.8, duration: 2400, hold: 1800 }, // Wack Wack close-up
  { center: [121.07, 14.3], zoom: 11.6, duration: 2600, hold: 1800 },   // Laguna DC corridor
  { center: [121.1, 14.42], zoom: 9.2, duration: 2200, hold: 1600 },    // pull back out
];

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  recordVideo: { dir: OUT_DIR, size: { width: 1280, height: 800 } },
  deviceScaleFactor: 1,
});
const page = await ctx.newPage();
await page.goto("http://localhost:8737/", { waitUntil: "networkidle" });
await page.waitForFunction(() => window._map && window._map.loaded());
await page.evaluate(() => {
  document.querySelector("#map").scrollIntoView({ block: "center" });
  window._map.jumpTo({ center: [122.0, 12.5], zoom: 5.6 });
});
await sleep(1600);

for (const s of SHOTS) {
  await page.evaluate(
    ({ center, zoom, duration }) => window._map.flyTo({ center, zoom, duration, essential: true }),
    s
  );
  await sleep(s.duration + s.hold);
}

await ctx.close();
const video = await page.video().path();
console.log("video:", video);
await browser.close();
