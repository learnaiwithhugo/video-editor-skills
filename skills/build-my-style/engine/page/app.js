// The style page: shows every option still in play (page/round.json), each as a looping clip with
// play/pause, a scrub bar, Keep / Maybe / Drop and a note. Submit sends the marks to the local server,
// which saves them in reviews/ for Claude to read.
let ROUND = null, review = {}, STORE_KEY = "";
const players = [];

// Instagram Reels screen on the 1080x1920 frame (organic Reels): top bar, the like/comment/share column
// and the username + caption are shaded; the dashed line is where text is safe.
const SAFE = { top: 220, bottom: 1500, side: 35, btnX: 940, btnTop: 1000 };
const SAFE_SVG = `<svg class="safe-zone" viewBox="0 0 1080 1920" preserveAspectRatio="none" aria-hidden="true">
  <g fill="rgba(10,14,22,.42)"><rect x="0" y="0" width="1080" height="${SAFE.top}"/><rect x="0" y="${SAFE.bottom}" width="1080" height="${1920 - SAFE.bottom}"/>
  <rect x="${SAFE.btnX}" y="${SAFE.btnTop}" width="${1080 - SAFE.btnX}" height="${SAFE.bottom - SAFE.btnTop}"/></g>
  <g fill="rgba(255,255,255,.9)"><rect x="40" y="120" width="190" height="34" rx="17"/>${[1080, 1210, 1340, 1450].map(y => `<circle cx="1010" cy="${y}" r="34"/>`).join("")}
  <circle cx="80" cy="1600" r="40"/><rect x="140" y="1580" width="260" height="40" rx="20"/><rect x="40" y="1670" width="760" height="30" rx="15"/><rect x="40" y="1720" width="520" height="30" rx="15"/></g>
  <path d="M${SAFE.side} ${SAFE.top} H${1080 - SAFE.side} V${SAFE.btnTop} H${SAFE.btnX} V${SAFE.bottom} H${SAFE.side} Z" fill="none" stroke="var(--accent)" stroke-width="6" stroke-dasharray="22 14"/>
</svg>`;

function load() { try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; } catch { return {}; } }
function save() { try { localStorage.setItem(STORE_KEY, JSON.stringify(review)); } catch {} updateCount(); }

// A player scales the 1080x1920 stage into its box and loops one option. Pausing or scrubbing rebuilds
// the option and parks every animation at the chosen time.
function makePlayer(stageEl, opt) {
  let timers = [], cues = [], start = 0;
  const spec = LIB[opt.use];
  const P = { ...(spec ? spec.params : {}), ...(opt.params || {}) };
  const p = { paused: false, t: 0, loop: opt.loop || (spec && spec.loop) || 4000 };
  const s = {
    el(tag, css = {}, parent, text) {
      const e = document.createElement(tag);
      Object.assign(e.style, css);
      if (text !== undefined) e.textContent = text;
      (parent || stageEl).appendChild(e);
      return e;
    },
    img(src, css, parent) { const i = s.el("img", css, parent); if (src) i.src = src; return i; },
    video(src, css, parent) {
      const v = s.el("video", css, parent);
      Object.assign(v, { muted: true, loop: true, autoplay: true, playsInline: true, src });
      v.muted = true; v.play().catch(() => {});
      return v;
    },
    at(ms, fn) { cues.push([ms, fn]); },
  };
  const anims = () => stageEl.getAnimations({ subtree: true });
  const clear = () => { timers.forEach(clearTimeout); timers = []; };
  function build() {
    clear(); cues = []; stageEl.replaceChildren();
    if (!spec) { s.el("div", { position: "absolute", inset: "0", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: "60px", padding: "80px", textAlign: "center" }, null, `Missing option "${opt.use}"`); return; }
    spec.build(s, P);
    cues.sort((a, b) => a[0] - b[0]);
  }
  const schedule = (from) => { for (const [ms, fn] of cues) if (ms > from) timers.push(setTimeout(fn, ms - from)); };
  p.fit = () => { stageEl.style.transform = `scale(${stageEl.parentElement.clientWidth / 1080})`; };
  p.restart = () => { build(); schedule(0); start = performance.now(); p.paused = false; p.t = 0; };
  p.seek = (t) => { build(); anims().forEach(a => { a.pause(); a.currentTime = t; }); cues.forEach(([ms, fn]) => { if (ms <= t) fn(); }); p.t = t; p.paused = true; };
  p.pause = () => { if (p.paused) return; p.t = performance.now() - start; anims().forEach(a => a.pause()); clear(); p.paused = true; };
  p.resume = () => { if (!p.paused) return; anims().forEach(a => a.play()); schedule(p.t); start = performance.now() - p.t; p.paused = false; };
  p.tick = (now) => { if (p.paused) return; p.t = now - start; if (p.t >= p.loop) p.restart(); };
  p.stop = () => { clear(); stageEl.replaceChildren(); };
  return p;
}

function controls(wrap, player) {
  wrap.innerHTML = `<button class="pp" aria-label="Play or pause"></button><input class="scrub" type="range" min="0" max="${player.loop}" step="1" value="0"><span class="time"></span>`;
  const btn = wrap.querySelector(".pp"), bar = wrap.querySelector(".scrub"), time = wrap.querySelector(".time");
  btn.addEventListener("click", () => (player.paused ? player.resume() : player.pause()));
  bar.addEventListener("input", () => player.seek(+bar.value));
  return () => {
    btn.textContent = player.paused ? "▶" : "❚❚";
    if (document.activeElement !== bar) bar.value = player.t;
    time.textContent = `${(player.t / 1000).toFixed(2)}s`;
  };
}

const safeBtn = document.getElementById("safeBtn");
function setSafe(on) { document.body.classList.toggle("safe", on); safeBtn.classList.toggle("on", on); try { localStorage.setItem("style-safe", on ? "1" : ""); } catch {} }
safeBtn.addEventListener("click", () => setSafe(!document.body.classList.contains("safe")));

function render(brand) {
  document.getElementById("roundTag").textContent = ROUND.title || `Round ${ROUND.round}`;
  const main = document.getElementById("main");
  const c = brand.colours, sw = [["Paper", c.paper], ["Accent", c.accent], ["Accent soft", c.accent_soft], ["Accent deep", c.accent_deep], ["Ink", c.ink]];
  const locked = document.createElement("section");
  locked.innerHTML = `<h2>Locked</h2><div class="locked">${sw.map(([n, hex]) => `<div class="swatch"><div class="chip" style="background:${hex}"></div><div class="meta"><b>${n}</b><span>${hex}</span></div></div>`).join("")}
    <div class="typecard"><div class="big">${brand.font.family}</div></div></div>`;
  main.appendChild(locked);
  for (const sec of ROUND.sections) {
    if (!sec.options.length) continue;
    const el = document.createElement("section");
    el.innerHTML = `<h2></h2><div class="grid"></div>`;
    el.querySelector("h2").textContent = sec.name;
    for (const opt of sec.options) el.querySelector(".grid").appendChild(card(opt));
    main.appendChild(el);
  }
  updateCount();
}

function card(opt) {
  const r = review[opt.id] || {};
  const c = document.createElement("div");
  c.className = "card";
  c.dataset.id = opt.id;
  if (r.verdict) c.dataset.verdict = r.verdict;
  c.innerHTML = `<div class="phone"><div class="stage-wrap"><div class="stage"></div></div>${SAFE_SVG}</div><div class="controls"></div>
    <div class="card-head"><span class="id"></span><span class="label"></span></div>
    <div class="verdicts"><button data-v="keep">Keep</button><button data-v="maybe">Maybe</button><button data-v="drop">Drop</button></div>
    <textarea placeholder="Note"></textarea>`;
  c.querySelector(".id").textContent = opt.id;
  c.querySelector(".label").textContent = opt.label || (LIB[opt.use] || {}).label || opt.use;
  const p = makePlayer(c.querySelector(".stage"), opt);
  p.ui = controls(c.querySelector(".controls"), p);
  players.push(p);
  c.querySelector(".phone").addEventListener("click", () => openBig(opt));
  const btns = c.querySelectorAll(".verdicts button");
  const paint = () => btns.forEach(b => b.classList.toggle("on", b.dataset.v === (review[opt.id] || {}).verdict));
  paint();
  btns.forEach(b => b.addEventListener("click", () => {
    const cur = review[opt.id] || {};
    cur.verdict = cur.verdict === b.dataset.v ? undefined : b.dataset.v;
    review[opt.id] = cur;
    if (cur.verdict) c.dataset.verdict = cur.verdict; else delete c.dataset.verdict;
    paint(); save();
  }));
  const ta = c.querySelector("textarea");
  ta.value = r.note || "";
  ta.addEventListener("input", () => { review[opt.id] = { ...(review[opt.id] || {}), note: ta.value }; save(); });
  return c;
}

const allOptions = () => ROUND.sections.flatMap(s => s.options.map(o => ({ ...o, section: s.name })));
function updateCount() {
  const all = allOptions(), rated = all.filter(o => (review[o.id] || {}).verdict).length;
  document.getElementById("count").textContent = `${rated} of ${all.length} rated`;
}

let big = null;
const modal = document.getElementById("modal");
function openBig(opt) { modal.hidden = false; big = makePlayer(modal.querySelector(".stage"), opt); big.ui = controls(modal.querySelector(".controls"), big); big.fit(); big.restart(); }
function closeBig() { modal.hidden = true; if (big) big.stop(); big = null; }
document.getElementById("modalClose").addEventListener("click", closeBig);
modal.addEventListener("click", e => { if (e.target === modal) closeBig(); });
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeBig();
  if (e.key === " " && big && document.activeElement.tagName !== "TEXTAREA") { e.preventDefault(); big.paused ? big.resume() : big.pause(); }
});

document.getElementById("submit").addEventListener("click", async () => {
  const btn = document.getElementById("submit");
  const payload = {
    kind: "round", round: ROUND.round, submitted_at: new Date().toISOString(),
    options: allOptions().map(o => ({ id: o.id, section: o.section, use: o.use, params: o.params || {}, label: o.label || (LIB[o.use] || {}).label || o.use,
      verdict: (review[o.id] || {}).verdict || null, note: (review[o.id] || {}).note || "" })),
  };
  btn.disabled = true;
  try {
    const res = await fetch("/api/review", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!res.ok) throw new Error(res.status);
    toast("Sent. Tell Claude \"done\".");
  } catch { toast("Couldn't send. Ask Claude to restart the page."); }
  finally { btn.disabled = false; }
});

(async () => {
  const { brand } = await window.boot;
  ROUND = await getJSON("round.json");
  if (!ROUND) { document.getElementById("main").textContent = "No round yet."; return; }
  STORE_KEY = `style-round-${ROUND.round}`;
  review = load();
  for (const o of ROUND.sections.flatMap(s => s.options)) if (o.kept && !review[o.id]) review[o.id] = { verdict: "keep" };   // already kept last round
  try { if (localStorage.getItem("style-safe")) setSafe(true); } catch {}
  document.querySelector(".modal-phone").insertAdjacentHTML("beforeend", SAFE_SVG);
  render(brand);
  const fitAll = () => { players.forEach(p => p.fit()); if (big) big.fit(); };
  window.addEventListener("resize", fitAll);
  fitAll();
  players.forEach(p => p.restart());
  (function frame(now) { for (const p of big ? [...players, big] : players) { p.tick(now); p.ui(); } requestAnimationFrame(frame); })(performance.now());
  window.pageReady = true;
})();
