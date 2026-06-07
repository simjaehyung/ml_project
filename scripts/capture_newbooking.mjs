// Verify New Booking tab: form view + domain inbox view.
import { mkdirSync } from "node:fs";
import { pathToFileURL } from "node:url";
const pw = await import(pathToFileURL(process.env.PW_MODULE).href);
const chromium = pw.chromium || pw.default?.chromium;
const BASE = process.env.HUB_BASE || "http://localhost:3000";
const OUT = "presentations/captures";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") errors.push("console: " + m.text()); });

await page.goto(`${BASE}/dashboard/reservations/new`, { waitUntil: "networkidle" });
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/newbooking_form.png` });

// switch to 도메인 인박스
await page.getByRole("button", { name: /도메인 인박스/ }).click();
await page.waitForTimeout(1200); // allow listBookings fetch
await page.screenshot({ path: `${OUT}/newbooking_inbox.png`, fullPage: true });

// read routed counts from the board headers
const counts = await page.evaluate(() => {
  const txt = document.body.innerText;
  const m = txt.match(/D[1-4][\s\S]{0,40}?\d+/g) || [];
  return { len: txt.length, sampleHasInbox: txt.includes("도메인 인박스"), domainsSeen: ["오버부킹","업셀","동적 가격","수요"].filter(k=>txt.includes(k)) };
});
console.log("NB_RESULT=" + JSON.stringify({ counts, errors }));
await browser.close();
