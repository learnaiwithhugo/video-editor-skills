// Shared start-up for every page: loads the person's brand (colours + font) and anything already locked,
// then paints the page chrome in their colours. Every page waits on window.boot before drawing.
async function getJSON(url, fallback = null) {
  try { const r = await fetch(url, { cache: "no-store" }); return r.ok ? await r.json() : fallback; } catch { return fallback; }
}
window.boot = (async () => {
  const brand = await getJSON("/locked/brand.json");
  if (!brand) throw new Error("locked/brand.json is missing");
  const [shine, zoom, shadow, icons, site, repo] = await Promise.all([
    getJSON("/locked/shine.json"), getJSON("/locked/zoom.json"), getJSON("/locked/shadow.json"),
    getJSON("assets/icons/icons.json", []), getJSON("assets/site.json"), getJSON("assets/repo.json"),
  ]);
  const c = brand.colours, root = document.documentElement.style;
  root.setProperty("--paper", c.paper || "#FFFFFF");
  root.setProperty("--accent", c.accent);
  root.setProperty("--accent-soft", c.accent_soft);
  root.setProperty("--accent-deep", c.accent_deep);
  root.setProperty("--ink", c.ink);
  root.setProperty("--font", `"${brand.font.family}", "Helvetica Neue", Helvetica, Arial, sans-serif`);
  const css = brand.font.css || brand.font.remote_css;
  if (css) document.head.insertAdjacentHTML("beforeend", `<link rel="stylesheet" href="${css}">`);
  try {
    const f = `"${brand.font.family}"`, w = brand.font.weights || {};
    await Promise.race([
      Promise.all([w.title || 700, w.caption || 600, w.label || 500].map(n => document.fonts.load(`${n} 60px ${f}`))),
      new Promise(r => setTimeout(r, 2500)),
    ]);
  } catch {}
  document.title = `${brand.name ? brand.name + " · " : ""}${document.title}`;
  const extra = { shine, zoom, shadow, icons: icons || [], site, repo };
  if (typeof setBrand === "function") setBrand(brand, extra);
  return { brand, ...extra };
})();
function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toast.h); toast.h = setTimeout(() => { t.hidden = true; }, 3600);
}
