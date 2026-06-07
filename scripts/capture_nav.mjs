import { pathToFileURL } from "node:url";
const pw = await import(pathToFileURL(process.env.PW_MODULE).href);
const chromium = pw.chromium || pw.default?.chromium;
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1400, height: 900 } });
const errs=[]; p.on("pageerror",e=>errs.push(String(e)));
await p.goto("http://localhost:3000/dashboard", { waitUntil: "networkidle" });
await p.waitForTimeout(800);
await p.screenshot({ path: "presentations/captures/nav_korean.png" });
const navText = await p.evaluate(()=>{
  const aside=document.querySelector("aside"); return aside?aside.innerText.replace(/\n+/g,' | '):null;
});
console.log("NAV="+JSON.stringify({navText, errs}));
await b.close();
