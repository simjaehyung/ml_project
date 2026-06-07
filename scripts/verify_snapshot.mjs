import { mkdirSync } from "node:fs";
import { pathToFileURL } from "node:url";
const pw = await import(pathToFileURL(process.env.PW_MODULE).href);
const chromium = pw.chromium || pw.default?.chromium;
const OUT = "presentations/captures"; mkdirSync(OUT, { recursive: true });
const B = "http://localhost:3000";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
const errors = []; page.on("pageerror", e => errors.push(String(e)));
page.on("console", m => { if (m.type()==="error") errors.push("c:"+m.text()); });
const text = () => page.evaluate(() => document.body.innerText);

// 1) Overview 현황 (default)
await page.goto(`${B}/dashboard`, { waitUntil: "networkidle" });
await page.waitForTimeout(1200);
await page.screenshot({ path: `${OUT}/snap_overview.png` });
let t = await text();
const kpi = (t.match(/전체 예약\s*([\d—]+)/)||[])[1];
const donut = (t.match(/위험 분포 현황[\s\S]{0,400}/)||[""])[0].replace(/\n+/g,' ').slice(0,180);

// 2) Priority scatter
await page.getByRole("button", { name: /우선순위/ }).click();
await page.waitForTimeout(900);
await page.screenshot({ path: `${OUT}/snap_priority_scatter.png` });

// 3) Reservations time tabs
await page.goto(`${B}/dashboard/reservations`, { waitUntil: "networkidle" });
await page.waitForTimeout(900);
await page.screenshot({ path: `${OUT}/snap_reservations.png` });
const resv = await text();
const tabCounts = ["오늘·내일","이번 주","이번 달"].map(k=>{ const m=resv.match(new RegExp(k+"\s*(\d+)")); return k+":"+(m?m[1]:"·"); });

// 4) Domain inbox (criteria cards) — D3 lead>=90 should now have hits
await page.goto(`${B}/dashboard/reservations/new`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: /도메인 인박스/ }).click();
await page.waitForTimeout(1400);
await page.screenshot({ path: `${OUT}/snap_domain_inbox.png` });

// 5) Flexi
await page.goto(`${B}/dashboard/flexi`, { waitUntil: "networkidle" });
await page.waitForTimeout(900);
await page.screenshot({ path: `${OUT}/snap_flexi.png` });

console.log("VERIFY="+JSON.stringify({ kpi_total: kpi, donut, resvTabs: tabCounts, errors }));
await browser.close();
