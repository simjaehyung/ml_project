// Verify presentations/dss_story_demo.html runs as a standalone, server-less fallback.
// Loads it via file:// (no dev server), checks it renders + can play, screenshots.
import { mkdirSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
const pw = await import(pathToFileURL(process.env.PW_MODULE).href);
const chromium = pw.chromium || pw.default?.chromium;

const HTML = resolve("presentations/dss_story_demo.html");
const OUT = "presentations/captures";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") errors.push("console: " + m.text()); });

await page.goto(pathToFileURL(HTML).href, { waitUntil: "load" });
await page.waitForTimeout(800);
const bodyLen = (await page.evaluate(() => document.body.innerText.length)) || 0;
const hasSvg = await page.$("svg") != null;
await page.screenshot({ path: `${OUT}/fallback_dss_story_demo.png` });
// let any autoplay/animation run a couple seconds, capture a mid frame
await page.waitForTimeout(2500);
await page.screenshot({ path: `${OUT}/fallback_dss_story_demo_mid.png` });

console.log("FALLBACK_OK=" + JSON.stringify({ bodyLen, hasSvg, errors }));
await browser.close();
