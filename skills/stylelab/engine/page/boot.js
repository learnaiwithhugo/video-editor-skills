// Shared start-up helpers for the style page. Everything is fetched with RELATIVE paths (never a leading
// slash), so the page works the same as a published artifact and from a plain local server.
// app.js decides what to load; this file only knows how to ask politely and how to paint a brand.

// assets/has.json says which optional files exist ({"assets/face-cutout.webm": true, ...}). null = not read
// yet, or there isn't one. An optional file that has.json lists as false is never requested, so the console
// stays clean; anything it doesn't list is simply tried.
let HAS = null;

async function getJSON(url, fallback = null) {
  try { const r = await fetch(url, { cache: "no-store" }); return r.ok ? await r.json() : fallback; } catch { return fallback; }
}
async function loadHas() {
  const h = await getJSON("assets/has.json", null);
  HAS = h && typeof h === "object" && !Array.isArray(h) ? h : null;
  return HAS;
}
function optJSON(path, fallback = null) {
  if (HAS && HAS[path] === false) return Promise.resolve(fallback);
  return getJSON(path, fallback);
}

// A path that came out of a data file must stay inside the page's own folder: no scheme, no climbing out.
function relPath(p) {
  p = String(p == null ? "" : p);
  return p && !p.startsWith("/") && !p.includes("..") && !/^[a-z][a-z0-9+.-]*:/i.test(p) && !/[\\<>"']/.test(p) ? p : "";
}
function safeUrl(u) {
  try { const x = new URL(String(u), location.href); return x.protocol === "https:" || x.protocol === "http:" ? x.href : ""; } catch { return ""; }
}
const safeHex = (h, fallback) => (/^#[0-9a-f]{3,8}$/i.test(String(h || "")) ? h : fallback);

// Puts the person's font on the page's stage text, waits (briefly) for it, hands colours and locked settings
// to the animation library. `locked` is { shine, zoom, shadow, icons, site, repo }.
async function applyBrand(brand, locked = {}) {
  const fam = String((brand.font && brand.font.family) || "Helvetica Neue").replace(/["'\\;{}<>]/g, "");
  document.documentElement.style.setProperty("--font", `"${fam}", "Helvetica Neue", Helvetica, Arial, sans-serif`);
  const css = brand.font && (brand.font.css || brand.font.remote_css);
  if (css && (relPath(css) || /^https:\/\//i.test(css))) {
    const l = document.createElement("link");
    l.rel = "stylesheet"; l.href = css;
    document.head.appendChild(l);
  }
  try {
    const w = (brand.font && brand.font.weights) || {};
    await Promise.race([
      Promise.all([w.title || 700, w.caption || 600, w.label || 500].map(n => document.fonts.load(`${n} 60px "${fam}"`))),
      new Promise(r => setTimeout(r, 2500)),
    ]);
  } catch {}
  if (typeof setBrand === "function") setBrand(brand, { ...locked, icons: locked.icons || [] });
}
