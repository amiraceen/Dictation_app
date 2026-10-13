// Renders promo/scenes.html frame by frame with Playwright.
//   node render.mjs frames <outDir> [fps]      → every frame as JPEG
//   node render.mjs stills <outDir> t1 t2 …    → PNG stills at given seconds (previews, poster)
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
let playwright;
try { playwright = require("playwright"); } catch { playwright = require("/opt/node22/lib/node_modules/playwright"); }

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TYPES = { ".html": "text/html", ".png": "image/png", ".webp": "image/webp", ".svg": "image/svg+xml", ".woff2": "font/woff2" };

const server = http.createServer((req, res) => {
  const p = path.join(HERE, decodeURIComponent(new URL(req.url, "http://x").pathname));
  if (!p.startsWith(HERE) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "Content-Type": TYPES[path.extname(p)] || "application/octet-stream" });
  fs.createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, r));
const port = server.address().port;

const [mode, outDir, ...rest] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });

const browser = await playwright.chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
await page.goto(`http://127.0.0.1:${port}/scenes.html`);
await page.waitForFunction(() => window.__ready === true);
await page.evaluate(() => document.fonts.ready);
// Make sure every image has decoded before the first frame.
await page.evaluate(() => Promise.all([...document.images].map((i) => i.decode().catch(() => {}))));

async function frame(t, file, type) {
  await page.evaluate((t) => window.renderAt(t), t);
  await page.screenshot({ path: file, type, ...(type === "jpeg" ? { quality: 95 } : {}) });
}

if (mode === "frames") {
  const fps = Number(rest[0] || 30);
  const duration = await page.evaluate(() => window.DURATION);
  const n = Math.round(duration * fps);
  for (let i = 0; i < n; i++) {
    await frame(i / fps, path.join(outDir, `f${String(i).padStart(5, "0")}.jpg`), "jpeg");
    if (i % 60 === 0) console.log(`frame ${i}/${n}`);
  }
} else {
  for (const s of rest) await frame(Number(s), path.join(outDir, `t${s}.png`), "png");
}
await browser.close();
server.close();
