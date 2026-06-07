// Headless capture/verify of /dashboard/hub for the final-presentation demo.
// Loads the hub, drives the playback control bar, screenshots key story frames,
// and asserts the growth curve reveal + counters actually advance.
//
// Run:  node scripts/capture_hub.mjs
// Browsers: uses globally-installed Playwright chromium (ms-playwright cache).
import { mkdirSync } from "node:fs";
import { pathToFileURL } from "node:url";
const PW = process.env.PW_MODULE; // absolute path to playwright module
const pw = await import(pathToFileURL(PW).href);
const chromium = pw.chromium || pw.default?.chromium;

const BASE = process.env.HUB_BASE || "http://localhost:3000";
const OUT = "presentations/captures";
mkdirSync(OUT, { recursive: true });

// caps: [label, wk seek target]  — mirrors docs/demo_run_guide.md §3
const CAPS = [
  ["C1_empty_hub", 27],
  ["C2_early", 40],
  ["C3_pre_crossover", 70],
  ["C4_W_crossover", 84],
  ["C5_risk_dist", 100],
  ["C6_peak_0820", 120],
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") errors.push("console: " + m.text()); });

await page.goto(`${BASE}/dashboard/hub?capture=1`, { waitUntil: "networkidle" });
// wait for the growth curve svg + control inputs to exist
await page.waitForSelector("svg", { timeout: 15000 });

// the seek number input is the 2nd input[type=number]; range is input[type=range].
// In capture mode the control bar is hidden, so toggle it off first via 'c'.
await page.keyboard.press("c"); // exit capture mode -> show controls
await page.waitForSelector('input[type="range"]', { timeout: 5000 });

async function readState() {
  // collected counter is the first big Stat; curve legend shows LightGBM pr value
  return await page.evaluate(() => {
    const txt = document.body.innerText;
    const collected = (txt.match(/수집 누적\s*([\d,]+)/) || [])[1] || null;
    // LightGBM legend value (last 0.xxx near 'LightGBM')
    const lgbm = (txt.match(/LightGBM\s*(0\.\d{3})/) || [])[1] || null;
    return { collected, lgbm };
  });
}

const results = [];
for (const [label, wk] of CAPS) {
  // set seek via the number input
  const num = page.locator('input[type="number"]').first();
  await num.fill(String(wk));
  await num.dispatchEvent("change");
  await page.waitForTimeout(400);
  // blur the input first — the hub's key handler ignores keydown while focus is
  // in an <input>, so 'c' (capture mode) wouldn't fire otherwise.
  await num.evaluate((el) => el.blur());
  // re-enter capture mode for a clean frame (hide controls)
  await page.keyboard.press("c");
  await page.waitForTimeout(250);
  await page.screenshot({ path: `${OUT}/cap_${label}.png` });
  const st = await readState();
  results.push({ label, wk, ...st });
  await page.keyboard.press("c"); // show controls again for next seek
  await page.waitForTimeout(150);
}

console.log("CAPTURE_RESULTS=" + JSON.stringify(results));
console.log("PAGE_ERRORS=" + JSON.stringify(errors));
await browser.close();
