#!/usr/bin/env node
// Real screenshots with headless Chrome, after the page has FULLY loaded (no grey placeholder bars),
// using only Node 22+ (built-in WebSocket talks to Chrome directly; nothing to install).
//
//   node shot.mjs --url <url> --out <file.png> [--width 1080] [--height 1920] [--scale 1] [--mobile]
//                 [--full] [--max 6000] [--wait 1500] [--find "70.1k"] [--wait-for "window.pageReady"]
//                 [--eval "js"] [--after 0] [--json meta.json]
//
// --find   returns the box of the smallest element containing that text, in image pixels (for rings
//          and push-ins). --wait-for polls a JS expression until true. --eval runs JS after load (it may
//          return a promise) and prints the result; --after waits that many ms after --eval before the shot.
// Prints JSON: { out, width, height, target, errors, eval }. errors = console errors, uncaught
// exceptions and failed loads, so the same script checks a page renders cleanly.
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, rmSync, writeFileSync, readdirSync } from "node:fs";
import { tmpdir, homedir } from "node:os";
import { join } from "node:path";

const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf(k); return i < 0 ? d : argv[i + 1]; };
const flag = (k) => argv.includes(k);
const url = opt("--url"), out = opt("--out");
if (!url || !out) { console.error("usage: node shot.mjs --url <url> --out <file.png> [options]"); process.exit(2); }
const W = +opt("--width", 1080), H = +opt("--height", 1920), SCALE = +opt("--scale", 1), MAX = +opt("--max", 6000);

function findChrome() {
  const c = [process.env.CHROME, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"].filter(Boolean);
  for (const p of c) if (existsSync(p)) return p;
  const cache = join(homedir(), ".cache", "puppeteer", "chrome-headless-shell");
  if (existsSync(cache)) for (const v of readdirSync(cache).sort().reverse()) for (const plat of readdirSync(join(cache, v))) {
    const exe = join(cache, v, plat, "chrome-headless-shell"); if (existsSync(exe)) return exe;
  }
  return null;
}
const chrome = findChrome();
if (!chrome) { console.error("No Chrome found. Install Google Chrome, or HyperFrames (it brings its own)."); process.exit(3); }
const profile = mkdtempSync(join(tmpdir(), "style-shot-"));
const proc = spawn(chrome, ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "--no-first-run", "--no-default-browser-check",
  "--hide-scrollbars", "--mute-audio", "--autoplay-policy=no-user-gesture-required", "--disable-background-timer-throttling", "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
const cleanup = () => { try { proc.kill("SIGKILL"); } catch {} try { rmSync(profile, { recursive: true, force: true }); } catch {} };
const fail = (m) => { console.error(m); cleanup(); process.exit(1); };
setTimeout(() => fail("Timed out after 90 s"), 90000).unref();

const wsUrl = await new Promise((res, rej) => {
  let buf = "";
  proc.stderr.on("data", d => { buf += d; const m = buf.match(/DevTools listening on (ws:\/\/\S+)/); if (m) res(m[1]); });
  proc.on("exit", () => rej(new Error("Chrome exited: " + buf.slice(-400))));
}).catch(e => fail(e.message));

const ws = new WebSocket(wsUrl);
await new Promise(r => ws.addEventListener("open", r, { once: true }));
let id = 0; const pending = new Map(), listeners = [];
ws.addEventListener("message", ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
  else listeners.forEach(f => f(m));
});
const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
const sleep = ms => new Promise(r => setTimeout(r, ms));

const { targetId } = await send("Target.createTarget", { url: "about:blank" });
const { sessionId: S } = await send("Target.attachToTarget", { targetId, flatten: true });
const errors = []; let inflight = 0, lastNet = Date.now(), loaded = false;
listeners.push(m => {
  if (m.sessionId !== S) return;
  if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") errors.push("console: " + m.params.args.map(a => a.value ?? a.description ?? "").join(" "));
  if (m.method === "Runtime.exceptionThrown") errors.push("exception: " + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
  if (m.method === "Log.entryAdded" && m.params.entry.level === "error") errors.push("log: " + m.params.entry.text + (m.params.entry.url ? " " + m.params.entry.url : ""));
  if (m.method === "Network.requestWillBeSent") { inflight++; lastNet = Date.now(); }
  if (m.method === "Network.loadingFinished" || m.method === "Network.loadingFailed") { inflight = Math.max(0, inflight - 1); lastNet = Date.now(); }
  if (m.method === "Page.loadEventFired") loaded = true;
});
for (const d of ["Page.enable", "Runtime.enable", "Log.enable", "Network.enable"]) await send(d, {}, S);
await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: SCALE, mobile: flag("--mobile") }, S);
if (flag("--mobile")) await send("Emulation.setUserAgentOverride", { userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1" }, S);
await send("Page.navigate", { url }, S);
const t0 = Date.now();
while (!loaded && Date.now() - t0 < 30000) await sleep(100);
while ((inflight > 0 || Date.now() - lastNet < 800) && Date.now() - t0 < 30000) await sleep(100);   // network quiet
const evalJS = async (expr) => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }, S)).result?.value;
if (opt("--wait-for")) { const e = opt("--wait-for"); const t1 = Date.now(); while (!(await evalJS(`!!(${e})`)) && Date.now() - t1 < 20000) await sleep(150); }
// scroll through once so lazy images load, then back to the top
if (flag("--full")) { await evalJS(`(async()=>{const h=Math.min(document.documentElement.scrollHeight, ${MAX});for(let y=0;y<h;y+=${H}/2){scrollTo(0,y);await new Promise(r=>setTimeout(r,120));}scrollTo(0,0);})()`); }
await sleep(+opt("--wait", 1500));
let evalResult;
if (opt("--eval")) { evalResult = await evalJS(opt("--eval")); await sleep(+opt("--after", 0)); }

let target = null;
if (opt("--find")) {
  target = await evalJS(`(() => { const q = ${JSON.stringify(opt("--find").toLowerCase())}; let best = null;
    const maxY = ${flag("--full") ? MAX : H};
    for (const el of document.querySelectorAll("body *")) { const t = (el.innerText || "").toLowerCase(); if (!t.includes(q)) continue;
      if (el.checkVisibility && !el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
      const r = el.getBoundingClientRect(); if (r.width < 4 || r.height < 4 || r.top + scrollY < 0 || r.top + scrollY > maxY) continue;
      if (!best || r.width * r.height < best.a) best = { a: r.width * r.height, r }; }
    if (!best) return null; const r = best.r; return [r.left + scrollX, r.top + scrollY, r.width, r.height].map(n => Math.round(n * ${SCALE})); })()`);
}
const metrics = await send("Page.getLayoutMetrics", {}, S);
let fullH = Math.min(Math.ceil((metrics.cssContentSize || metrics.contentSize).height), MAX);
if (flag("--full") && fullH <= H + 2) {
  // Some sites scroll inside a full-height box instead of the page. Make the window as tall as that box's content.
  const inner = await evalJS(`Math.max(0, ...[...document.querySelectorAll("body *")].filter(e => /(auto|scroll)/.test(getComputedStyle(e).overflowY) && e.scrollHeight > e.clientHeight + 50).map(e => e.scrollHeight))`);
  if (inner > H) {
    fullH = Math.min(inner, MAX);
    await send("Emulation.setDeviceMetricsOverride", { width: W, height: fullH, deviceScaleFactor: SCALE, mobile: flag("--mobile") }, S);
    await sleep(1500);
  }
}
const clip = flag("--full") ? { x: 0, y: 0, width: W, height: fullH, scale: 1 } : { x: 0, y: 0, width: W, height: H, scale: 1 };
const shot = await send("Page.captureScreenshot", { format: out.endsWith(".jpg") ? "jpeg" : "png", quality: out.endsWith(".jpg") ? 85 : undefined, ...(flag("--full") ? { clip, captureBeyondViewport: true } : {}) }, S);
writeFileSync(out, Buffer.from(shot.data, "base64"));
const meta = { out, width: Math.round(clip.width * SCALE), height: Math.round(clip.height * SCALE), target, errors, eval: evalResult };
if (opt("--json")) writeFileSync(opt("--json"), JSON.stringify({ w: meta.width, h: meta.height, target, url }, null, 1));
console.log(JSON.stringify(meta));
ws.close(); cleanup(); process.exit(0);
