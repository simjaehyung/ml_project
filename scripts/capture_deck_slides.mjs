// v24 발표덱 슬라이드별 PNG 캡처 (Notion 첨부용)
// 실행(코드방): PW_MODULE="$(cat /tmp/pwdir.txt)/playwright/index.js" node scripts/capture_deck_slides.mjs
//   또는 playwright 설치돼 있으면:  node scripts/capture_deck_slides.mjs
// 산출: presentations/captures/slide_00.png ~ slide_13.png (deck 요소 2x, 1280x720)
import { mkdirSync } from "node:fs";
import { pathToFileURL } from "node:url";

const pwPath = process.env.PW_MODULE;
const pw = pwPath ? await import(pathToFileURL(pwPath).href) : await import("playwright");
const chromium = pw.chromium || pw.default?.chromium;

const deckRel = "presentations/Hotel No-Show DSS v24_final.html";
const url = pathToFileURL(process.cwd().replace(/\\/g, "/") + "/" + deckRel).href;
const OUT = "presentations/captures";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1360, height: 800 }, deviceScaleFactor: 2 });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));

await page.goto(url, { waitUntil: "networkidle" });
const N = await page.evaluate(() => document.querySelectorAll(".slide").length);

for (let i = 0; i < N; i++) {
  await page.evaluate((n) => { location.hash = "#s" + (n + 1); }, i);
  await page.waitForTimeout(280); // fade + chart settle
  const deck = await page.$(".deck");
  await deck.screenshot({ path: `${OUT}/slide_${String(i).padStart(2, "0")}.png` });
}

console.log("DECK_CAPTURE=" + JSON.stringify({ slides: N, out: OUT, errors }));
await browser.close();
