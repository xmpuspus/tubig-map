// Renders site/og-card.png (1200x630) from the real running map.
// No mockups: this screenshots the actual MapLibre render with the real layers,
// then overlays numbers read from summary.json at runtime.
// Run: node site/scripts/make_og_card.mjs   (server must be up on :8737)

import { chromium } from "/Users/xavier/Desktop/leaves-ph/site/node_modules/playwright/index.mjs";

const OUT = "site/og-card.png";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1200, height: 630 },
  deviceScaleFactor: 2,
});
await page.goto("http://localhost:8737/", { waitUntil: "networkidle" });
await page.waitForFunction(() => window._map && window._map.loaded());

// Strip the page down to a full-bleed map, then frame the Metro Manila cluster
// where golf and the data centre buildout overlap.
await page.evaluate(() => {
  document.querySelectorAll("header, section, footer, #controls, #legend, .maplibregl-ctrl-top-right")
    .forEach((el) => el.remove());
  Object.assign(document.body.style, { margin: "0", overflow: "hidden" });
  const wrap = document.getElementById("map-wrap");
  Object.assign(wrap.style, { position: "fixed", inset: "0", maxWidth: "none", padding: "0", margin: "0" });
  const map = document.getElementById("map");
  Object.assign(map.style, { height: "100vh", minHeight: "0", border: "0", borderRadius: "0" });
  window._map.resize();
  window._map.jumpTo({ center: [121.02, 14.56], zoom: 10.35 });
});
await sleep(2500);

await page.evaluate(async () => {
  const s = await fetch("data/summary.json").then((r) => r.json());
  const el = document.createElement("div");
  el.innerHTML = `
    <div style="position:fixed;inset:0;pointer-events:none;
      background:linear-gradient(90deg,rgba(249,249,247,.97) 0%,rgba(249,249,247,.93) 46%,rgba(249,249,247,0) 72%)"></div>
    <div style="position:fixed;top:0;left:0;width:660px;height:630px;padding:52px 44px;
      box-sizing:border-box;display:flex;flex-direction:column;justify-content:center;
      font:16px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif;color:#0b0b0b">
      <div style="font-size:13px;letter-spacing:.15em;text-transform:uppercase;color:#6b6a64;
        margin-bottom:14px">tubig-map &middot; measurement, not accusation</div>
      <div style="font-size:40px;line-height:1.1;font-weight:700;margin-bottom:18px">
        Who competes for Metro Manila's groundwater</div>
      <div style="display:flex;align-items:baseline;gap:14px;margin-bottom:10px">
        <span style="font-size:76px;font-weight:700;line-height:1;color:#a8451f">
          ${s.denr_named_golf} vs ${s.denr_named_dc}</span>
      </div>
      <div style="font-size:19px;line-height:1.4;color:#4c4b48;margin-bottom:20px;max-width:52ch">
        golf courses versus data centers ever named in a Philippine regulator's
        water directive, though both sit on the same restricted groundwater</div>
      <div style="font-size:15px;color:#4c4b48;line-height:1.55">
        ${s.golf_inside_named} of ${s.golf_standalone} mapped courses and
        ${s.dc_in_named} of ${s.dc_sites} data center sites sit inside an area NWRB named.<br>
        The per-course satellite signal fires on ${s.null_hit_rate}% of courses with no drought
        and ${s.drought_hit_rate}% with one, so it is reported as a failed instrument.</div>
      <div style="margin-top:26px;font-size:15px;color:#6b6a64">tubig-map.vercel.app</div>
    </div>`;
  document.body.appendChild(el);
});
await sleep(400);

await page.screenshot({ path: OUT, clip: { x: 0, y: 0, width: 1200, height: 630 } });
console.log("wrote", OUT);
await browser.close();
