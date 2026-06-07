import { mkdirSync } from "node:fs";
import { pathToFileURL } from "node:url";
const pw = await import(pathToFileURL(process.env.PW_MODULE).href);
const chromium = pw.chromium || pw.default?.chromium;
const OUT = "presentations/captures";
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") errors.push("console: " + m.text()); });

await page.goto("http://localhost:3000/dashboard/reservations/new", { waitUntil: "networkidle" });
await page.getByRole("button", { name: /자동 유입 데모/ }).click();
await page.waitForTimeout(800); // let hub_stream.json load
function readCollected() {
  return page.evaluate(() => {
    const m = document.body.innerText.match(/수집 누적\s*([\d,]+)/);
    return m ? m[1] : null;
  });
}
await page.getByRole("button", { name: /자동 유입 시작|다시재생/ }).click();
await page.waitForTimeout(2500);
const mid = await readCollected();
await page.screenshot({ path: `${OUT}/autofeed_mid.png` });
await page.waitForTimeout(3500);
const later = await readCollected();
await page.screenshot({ path: `${OUT}/autofeed_later.png` });
const domCounts = await page.evaluate(() => {
  const txt = document.body.innerText;
  return ["오버부킹", "업셀", "동적 가격", "수요"].filter((k) => txt.includes(k));
});
console.log("AUTOFEED=" + JSON.stringify({ mid, later, advanced: mid !== later, domains: domCounts, errors }));
await browser.close();
