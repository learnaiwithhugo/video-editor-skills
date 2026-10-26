// The StyleLab review page, one page with four tabs (Round, Images, Sounds, Creators).
// It runs as a private Claude artifact: Claude renders everything on the Mac, the page only shows it and
// collects Keep / Maybe / Drop. Marks are saved to the artifact's database as they click and type
// (marks/<tab>:<id>) and Submit files a submission (submissions/<time>); see references/artifact.md.
// With no database (a plain local server, or signed out) everything still renders and plays, marks stay in
// this browser, and Submit says it can't reach Claude. Data is only ever shown with textContent.
(() => {
"use strict";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
function h(tag, props = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else if (k === "dataset") Object.assign(e.dataset, v);
    else if (k === "style") Object.assign(e.style, v);
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k in e) e[k] = v;
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) e.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  return e;
}
const LS = {
  get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
};
const say = (el, text, kind) => { el.textContent = text; el.classList.toggle("ok", kind === "ok"); };
const syncNote = (text) => { const s = $("#sync"); s.hidden = !text; s.textContent = text || ""; };
const encPath = (p) => String(p).split("/").map(encodeURIComponent).join("/");

let EXAMPLE = false, ROUND = null, BRAND = null, PROFILE = null;
let SFX = [], CANDS = [], IMGINDEX = { liked: [], disliked: [], recreate: [] }, CREATORS = [];
let ACTIVE = "round";

// =====================================================================================================
// THE EXAMPLE ROUND (shown when there is no round or brand yet): a neutral grey brand, a few text-only
// options and three little sounds made in code, so the page is never empty.
// =====================================================================================================
const EXAMPLE_BRAND = {
  name: "", caption_colour: "#FFFFFF",
  colours: { paper: "#EDEDED", accent: "#7A7A7A", accent_soft: "#BDBDBD", accent_deep: "#3A3A3A", ink: "#1E1E1E" },
  font: { family: "IBM Plex Sans", weights: { title: 600, caption: 500, label: 500 } },
};
const EXAMPLE_ROUND = {
  round: 0, example: true,
  intro: "Play each one, tap it for full size, then mark Keep, Maybe or Drop.",
  sections: [
    { name: "Accent text", use: "How your key words come in.", options: [
      { id: "EX-A1", use: "accent-clean-rise", label: "Clean rise" },
      { id: "EX-A2", use: "accent-blur-rise", label: "Blur rise" },
      { id: "EX-A3", use: "headline-stack", label: "Two lines, accent line bigger" },
    ] },
    { name: "Intro text", use: "The line that opens the video.", options: [
      { id: "EX-I1", use: "intro-shine", label: "Hero word shine" },
      { id: "EX-I2", use: "intro-focus", label: "Hero word focus-in" },
    ] },
  ],
};
const EXAMPLE_SOUNDS = [
  { file: "example-click", name: "Click", need: "ex-click", mix_db: -14, duration_s: 0.12, hit_s: 0.003, synth: "click" },
  { file: "example-whoosh", name: "Soft whoosh", need: "ex-whoosh", mix_db: -18, duration_s: 0.9, hit_s: 0.45, synth: "whoosh" },
  { file: "example-impact", name: "Low impact", need: "ex-impact", mix_db: -12, duration_s: 0.7, hit_s: 0.01, synth: "impact" },
];
// With no footage in the example, a flat grey figure stands in so captions have something to sit under.
function installExampleFootage() {
  window.footage = function (s, css = {}, parent) {
    const box = s.el("div", { position: "absolute", left: "0", top: "0", width: "1080px", height: "1920px", overflow: "hidden", background: "#3f4246", ...css }, parent);
    s.el("div", { position: "absolute", left: "350px", top: "420px", width: "380px", height: "440px", borderRadius: "50%", background: "#50545a" }, box);
    s.el("div", { position: "absolute", left: "120px", top: "930px", width: "840px", height: "1100px", borderRadius: "420px 420px 0 0", background: "#50545a" }, box);
    return box;
  };
}

// =====================================================================================================
// MARKS: every Keep / Maybe / Drop (and note) lives in one map, is kept in this browser, and is saved to
// the artifact's database as marks/<tab>:<id>. The newer `at` wins when the two disagree.
// =====================================================================================================
const VERDICTS = { round: ["keep", "maybe", "drop"], images: ["like", "dislike"], sounds: ["keep", "drop"] };
const MARKS = {};          // doc key -> { tab, id, round, verdict, note, at, by }
const PAINT = {};          // doc key -> function(mark) that repaints that card
let DB = null, ME = null, LS_MARKS = "stylelab:marks";
const roundNo = () => (ROUND && ROUND.round != null ? ROUND.round : 0);
// document ids may only use letters, digits and _ - . ~ : @ +
function docKey(tab, id) {
  const safe = String(id).replace(/[^A-Za-z0-9_\-.~:@+]/g, (c) => "~" + c.charCodeAt(0).toString(16));
  return (tab + ":" + safe).slice(0, 190);
}
const markOf = (tab, id) => MARKS[docKey(tab, id)];
function verdictOf(tab, id, implicitKeep) {
  const m = markOf(tab, id);
  if (m && typeof m.verdict === "string") return m.verdict;
  return implicitKeep ? "keep" : "";
}
const noteOf = (tab, id) => (markOf(tab, id) || {}).note || "";
function persistLocal() {
  const out = {};
  for (const [k, m] of Object.entries(MARKS)) if (m.at > 0) out[k] = m;
  LS.set(LS_MARKS, out);
}
function loadLocal() {
  const stored = LS.get(LS_MARKS) || {};
  for (const [k, m] of Object.entries(stored)) {
    if (!m || !VERDICTS[m.tab] || k !== docKey(m.tab, m.id)) continue;
    if (m.tab === "round" && m.round !== roundNo()) continue;   // an old round's marks don't carry over
    MARKS[k] = m;
  }
}
function setMark(tab, id, patch, base = {}, extra = {}) {
  const k = docKey(tab, id), prev = MARKS[k] || { tab, id: String(id), round: roundNo(), verdict: "", note: "", ...base, ...extra };
  const m = { ...prev, ...patch, tab, id: String(id), round: roundNo(), at: Date.now(), by: ME };
  MARKS[k] = m;
  persistLocal();
  if (PAINT[k]) PAINT[k](m);
  updateBar();
  queueWrite(k, patch.verdict === undefined && patch.note !== undefined ? 800 : 0);
}

// ---- database
const pend = new Map(), chain = new Map();
function markError(e) {
  const c = e && e.code;
  if (c === "quota_exceeded") return "Claude's storage for this page is full, so that didn't save. Your marks are kept on this device.";
  if (c === "revoked" || c === "not_granted") return "This view can't save to Claude right now. Your marks are kept on this device.";
  return "Couldn't save to Claude just now. Your marks are kept on this device.";
}
function queueWrite(k, delay) {
  if (!DB || EXAMPLE) return;
  clearTimeout(pend.get(k));
  pend.set(k, setTimeout(() => { pend.delete(k); writeNow(k); }, delay));
}
function writeNow(k) {
  const next = (chain.get(k) || Promise.resolve())
    .then(() => (MARKS[k] ? DB.doc("marks/" + k).set({ ...MARKS[k] }) : null))
    .then(() => syncNote(""), (e) => syncNote(markError(e)));
  chain.set(k, next);
  return next;
}
async function flushAll() {
  for (const [k, t] of pend) { clearTimeout(t); pend.delete(k); writeNow(k); }
  await Promise.all([...chain.values()]);
}
function readRemote(d) {
  const m = d.data();
  if (!m || typeof m !== "object" || !VERDICTS[m.tab]) return null;
  const id = String(m.id == null ? "" : m.id);
  if (!id || d.id !== docKey(m.tab, id)) return null;
  const verdict = VERDICTS[m.tab].includes(m.verdict) ? m.verdict : "";
  const out = { tab: m.tab, id, round: m.round, verdict, note: typeof m.note === "string" ? m.note.slice(0, 2000) : "", at: Number(m.at) || 0, by: m.by == null ? null : String(m.by) };
  if (m.slug != null) out.slug = String(m.slug);
  if (m.pic != null) out.pic = String(m.pic);
  return out;
}
let firstSnap = true;
function onMarks(snap) {
  let changed = false;
  for (const d of snap.docs) {
    const m = readRemote(d);
    if (!m) continue;
    if (m.tab === "round" && m.round !== roundNo()) continue;
    const cur = MARKS[d.id];
    if (!cur || m.at > cur.at) { MARKS[d.id] = m; changed = true; if (PAINT[d.id]) PAINT[d.id](m); }
  }
  if (firstSnap) {   // anything saved here while offline and newer than what Claude has goes up once
    firstSnap = false;
    const remote = new Map(snap.docs.map((d) => [d.id, Number(d.data().at) || 0]));
    for (const [k, m] of Object.entries(MARKS)) if (m.at > 0 && m.at > (remote.get(k) || 0)) queueWrite(k, 0);
  }
  if (changed) { persistLocal(); updateBar(); }
}
async function connectDb() {
  try { DB = (await window.claude?.use?.("db")) || null; } catch { DB = null; }
  try { const u = await window.claude?.use?.("user"); ME = u ? await u.id() : null; } catch { ME = null; }
  if (!DB || EXAMPLE) return;
  try {
    DB.collection("marks").onSnapshot(onMarks, (e) => syncNote(markError(e)));   // subscribed once, here
  } catch (e) { syncNote(markError(e)); }
}

// ---- submit (every tab's button ends up here)
function submitError(e) {
  const c = e && e.code;
  if (c === "quota_exceeded") return "Claude's storage for this page is full, so that didn't send. Tell Claude in the chat instead.";
  if (c === "resource_exhausted") return "That was too many saves at once. Wait a few seconds and press Submit again.";
  if (c === "revoked" || c === "not_granted") return "This view can't send to Claude right now. Open the link on claude.ai and press Submit again.";
  return "That didn't send. Your marks are kept on this device; press Submit again in a moment.";
}
async function submit(kind, payload, btn, statusEl, rated, notes) {
  if (EXAMPLE) return say(statusEl, "Nothing was sent: this is the example round.");
  if (!DB) return say(statusEl, "This view can't reach Claude. Open the link on claude.ai and press Submit again.");
  btn.disabled = true;
  say(statusEl, "Sending");
  try {
    await flushAll();
    const at = Date.now();
    await DB.doc("submissions/" + at).set({ at, by: ME, kind, payload });
    say(statusEl, `Sent: ${rated} rated, ${notes} with notes. Go back to Claude and say "done".`, "ok");
  } catch (e) {
    say(statusEl, submitError(e));
  } finally { btn.disabled = false; }
}

// =====================================================================================================
// PLAYERS: a player scales the 1080x1920 stage into its box and loops one option. Pausing or scrubbing
// rebuilds the option and parks every animation at the chosen time.
// =====================================================================================================
function makePlayer(stageEl, opt) {
  let timers = [], cues = [], start = 0;
  const spec = LIB[opt.use];
  const P = { ...(spec ? spec.params : {}), ...(opt.params || {}) };
  const p = { paused: false, t: 0, loop: opt.loop || (spec && spec.loop) || 4000, built: false };
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
  const vids = () => [...stageEl.querySelectorAll("video")];
  const clear = () => { timers.forEach(clearTimeout); timers = []; };
  function build() {
    clear(); cues = []; stageEl.replaceChildren();
    p.built = true;
    if (!spec) { s.el("div", { position: "absolute", inset: "0", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: "60px", padding: "80px", textAlign: "center" }, null, `Missing option "${opt.use}"`); return; }
    spec.build(s, P);
    cues.sort((a, b) => a[0] - b[0]);
  }
  const schedule = (from) => { for (const [ms, fn] of cues) if (ms > from) timers.push(setTimeout(fn, ms - from)); };
  p.fit = () => { stageEl.style.transform = `scale(${stageEl.parentElement.clientWidth / 1080})`; };
  p.restart = () => { build(); schedule(0); start = performance.now(); p.paused = false; p.t = 0; };
  p.seek = (t) => { build(); anims().forEach((a) => { a.pause(); a.currentTime = t; }); cues.forEach(([ms, fn]) => { if (ms <= t) fn(); }); p.t = t; p.paused = true; };
  p.pause = () => { if (p.paused) return; p.t = performance.now() - start; anims().forEach((a) => a.pause()); vids().forEach((v) => v.pause()); clear(); p.paused = true; };
  p.resume = () => { if (!p.paused) return; anims().forEach((a) => a.play()); vids().forEach((v) => v.play().catch(() => {})); schedule(p.t); start = performance.now() - p.t; p.paused = false; };
  p.tick = (now) => { if (p.paused) return; p.t = now - start; if (p.t >= p.loop) p.restart(); };
  p.stop = () => { clear(); stageEl.replaceChildren(); p.built = false; };
  return p;
}
const ICON_PLAY = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.2v11.6L13.2 8z" fill="currentColor"/></svg>';
const ICON_PAUSE = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3.2" y="2.4" width="3.2" height="11.2" rx=".8" fill="currentColor"/><rect x="9.6" y="2.4" width="3.2" height="11.2" rx=".8" fill="currentColor"/></svg>';
function controls(wrap, player) {
  wrap.innerHTML = `<button type="button" class="pp" aria-label="Play or pause"></button><input class="scrub" type="range" min="0" max="${player.loop}" step="1" value="0" aria-label="Scrub"><span class="time"></span>`;
  const btn = $(".pp", wrap), bar = $(".scrub", wrap), time = $(".time", wrap);
  btn.addEventListener("click", (e) => { e.stopPropagation(); player.paused ? player.resume() : player.pause(); });
  bar.addEventListener("input", () => player.seek(+bar.value));
  let lastPaused = null, lastTime = "";
  return () => {
    if (lastPaused !== player.paused) { lastPaused = player.paused; btn.innerHTML = player.paused ? ICON_PLAY : ICON_PAUSE; }
    if (document.activeElement !== bar) bar.value = player.t;
    const t = `${(player.t / 1000).toFixed(2)}s`;
    if (t !== lastTime) { lastTime = t; time.textContent = t; }
  };
}

// Cards only run while they are on screen; leaving the screen pauses them, and the far ones are let go.
const tracked = new Map();    // phone element -> { player, visible, stamp }
const live = new Set();
const MAX_BUILT = 24;
function evict() {
  const built = [...tracked.values()].filter((c) => c.player.built);
  if (built.length < MAX_BUILT) return;
  built.filter((c) => !c.visible).sort((a, b) => a.stamp - b.stamp).slice(0, built.length - MAX_BUILT + 1).forEach((c) => { c.player.stop(); c.player.auto = false; });
}
const IO = "IntersectionObserver" in window ? new IntersectionObserver((entries) => {
  for (const en of entries) {
    const c = tracked.get(en.target);
    if (!c) continue;
    const p = c.player;
    c.visible = en.isIntersecting;
    if (c.visible) {
      c.stamp = Date.now(); live.add(c);
      p.fit();
      if (!p.built) { evict(); p.restart(); } else if (p.auto) { p.auto = false; p.resume(); }
    } else {
      live.delete(c);
      if (p.built && !p.paused) { p.auto = true; p.pause(); }
    }
  }
}, { rootMargin: "300px 0px" }) : null;
const RO = "ResizeObserver" in window ? new ResizeObserver((entries) => { for (const en of entries) { const c = tracked.get(en.target); if (c) c.player.fit(); } }) : null;
function track(phone, player) {
  const c = { player, visible: false, stamp: 0 };
  tracked.set(phone, c);
  if (IO) { IO.observe(phone); } else { c.visible = true; live.add(c); player.fit(); player.restart(); }
  if (RO) RO.observe(phone);
}
function frame(now) {
  for (const c of live) if (c.player.built) { c.player.tick(now); c.player.ui(); }
  if (big) { big.tick(now); big.ui(); }
  requestAnimationFrame(frame);
}

// =====================================================================================================
// SAFE ZONES: Instagram Reels on the 1080x1920 frame. The top bar, the like / comment / share column and
// the username + caption are shaded; the dashed line is where text is safe. Their handle and picture show
// in the name row when profile.json exists.
// =====================================================================================================
const SAFE = { top: 220, bottom: 1500, side: 35, btnX: 940, btnTop: 1000 };
let SAFE_NODE = null;
function buildSafe() {
  const tpl = document.createElement("template");
  tpl.innerHTML = `<svg class="safe-zone" viewBox="0 0 1080 1920" preserveAspectRatio="none" aria-hidden="true">
  <g fill="rgba(10,14,22,.42)"><rect x="0" y="0" width="1080" height="${SAFE.top}"/><rect x="0" y="${SAFE.bottom}" width="1080" height="${1920 - SAFE.bottom}"/>
  <rect x="${SAFE.btnX}" y="${SAFE.btnTop}" width="${1080 - SAFE.btnX}" height="${SAFE.bottom - SAFE.btnTop}"/></g>
  <g fill="rgba(255,255,255,.9)"><rect x="40" y="120" width="190" height="34" rx="17"/>${[1080, 1210, 1340, 1450].map((y) => `<circle cx="1010" cy="${y}" r="34"/>`).join("")}
  <rect x="40" y="1670" width="760" height="30" rx="15"/><rect x="40" y="1720" width="520" height="30" rx="15"/></g>
  <circle cx="80" cy="1600" r="40" fill="rgba(255,255,255,.9)"/>
  <text class="handle" x="140" y="1613" fill="#fff" font-size="40" font-weight="600" font-family="'IBM Plex Sans', system-ui, sans-serif" stroke="rgba(0,0,0,.4)" stroke-width="6" paint-order="stroke"></text>
  <path d="M${SAFE.side} ${SAFE.top} H${1080 - SAFE.side} V${SAFE.btnTop} H${SAFE.btnX} V${SAFE.bottom} H${SAFE.side} Z" fill="none" stroke="rgba(255,255,255,.92)" stroke-width="6" stroke-dasharray="22 14"/>
</svg>`;
  const svg = tpl.content.firstElementChild;
  const handle = PROFILE && typeof PROFILE.handle === "string" ? PROFILE.handle.replace(/^@/, "").trim().slice(0, 40) : "";
  $(".handle", svg).textContent = handle || "yourhandle";
  const pfp = PROFILE ? relPath(PROFILE.pfp) : "";
  if (pfp) {
    const img = document.createElementNS("http://www.w3.org/2000/svg", "image");
    img.setAttribute("x", "40"); img.setAttribute("y", "1560"); img.setAttribute("width", "80"); img.setAttribute("height", "80");
    img.setAttribute("preserveAspectRatio", "xMidYMid slice");
    img.setAttribute("href", pfp);
    img.style.clipPath = "circle(50%)";
    $("circle[cx='80']", svg).after(img);
  }
  return svg;
}
const safeNode = () => SAFE_NODE.cloneNode(true);

// =====================================================================================================
// TOP OF THE PAGE: title, intro, what changed, and the locked brand
// =====================================================================================================
function renderHead() {
  const n = roundNo(), title = ROUND.title ? String(ROUND.title) : "";
  const label = EXAMPLE ? "example round" : n > 0 ? `Round ${n}` : title || `Round ${n}`;
  $("#pageTitle").textContent = `StyleLab · ${label}`;
  if (title && n > 0) { $("#roundTitle").textContent = title; $("#roundTitle").hidden = false; }
  if (ROUND.intro) { $("#intro").textContent = String(ROUND.intro); $("#intro").hidden = false; }
  const notes = Array.isArray(ROUND.notes) ? ROUND.notes.filter((x) => typeof x === "string" && x.trim()) : [];
  if (notes.length) { $("#notesList").replaceChildren(...notes.map((t) => h("li", { text: t }))); $("#notes").hidden = false; }
  if (EXAMPLE) {
    const b = $("#exampleBanner");
    b.textContent = "This is an example round. Nothing's loaded yet: go back to Claude and it builds your first real one.";
    b.hidden = false;
  }
  const c = BRAND.colours || {};
  const sw = [["Paper", c.paper], ["Accent", c.accent], ["Accent soft", c.accent_soft], ["Accent deep", c.accent_deep], ["Ink", c.ink]];
  $("#swatches").replaceChildren(...sw.map(([name, hex]) => {
    const ok = safeHex(hex, "");
    return h("div", { class: "sw" }, h("span", { class: "chip", style: ok ? { background: ok } : {} }), h("span", { class: "nm", text: name }), h("span", { class: "hx", text: ok ? ok.toUpperCase() : "none" }));
  }));
  $("#fontName").textContent = (BRAND.font && BRAND.font.family) || "";
}

// =====================================================================================================
// ROUND TAB
// =====================================================================================================
const allOptions = () => (ROUND.sections || []).flatMap((s) => (s.options || []).map((o) => ({ ...o, section: s.name })));
const ITEMS = { round: [], images: [], sounds: [] };   // { el, rated() } for the "Unrated only" filter

function verdictRow(buttons, onPick) {
  const row = h("div", { class: buttons.cls });
  buttons.list.forEach(([v, text]) => row.append(h("button", { type: "button", text, dataset: { v }, "aria-pressed": "false", onclick: () => onPick(v) })));
  return row;
}
function paintVerdict(card, row, v) {
  $$("button", row).forEach((b) => { const on = b.dataset.v === v; b.classList.toggle("on", on); b.setAttribute("aria-pressed", on ? "true" : "false"); });
  if (v) card.dataset.verdict = v; else delete card.dataset.verdict;
}

function roundCard(o) {
  const lib = LIB[o.use] || {};
  const card = h("article", { class: "card", dataset: { id: o.id } });
  const stage = h("div", { class: "stage" });
  const phone = h("div", { class: "phone" }, h("div", { class: "stage-wrap" }, stage), safeNode());
  const ctl = h("div", { class: "controls" });
  const head = h("div", { class: "card-head" }, h("span", { class: "id", text: o.id }), h("span", { class: "label", text: o.label || lib.label || o.use }));
  if (o.kept) head.append(h("span", { class: "kept-tag", text: "Kept" }));
  const key = docKey("round", o.id);
  const row = verdictRow({ cls: "verdicts", list: [["keep", "Keep"], ["maybe", "Maybe"], ["drop", "Drop"]] }, (v) => {
    const cur = verdictOf("round", o.id, o.kept);
    setMark("round", o.id, { verdict: cur === v ? "" : v }, { verdict: o.kept ? "keep" : "" });
  });
  const ta = h("textarea", { placeholder: "Note", rows: 2, "aria-label": `Note on ${o.id}` });
  ta.addEventListener("input", () => setMark("round", o.id, { note: ta.value }, { verdict: o.kept ? "keep" : "" }));
  card.append(phone, ctl, head, row, ta);
  PAINT[key] = () => {
    paintVerdict(card, row, verdictOf("round", o.id, o.kept));
    const note = noteOf("round", o.id);
    if (document.activeElement !== ta && ta.value !== note) ta.value = note;
  };
  PAINT[key]();
  const p = makePlayer(stage, o);
  p.ui = controls(ctl, p);
  phone.addEventListener("click", () => openBig(o));
  track(phone, p);
  ITEMS.round.push({ el: card, rated: () => !!verdictOf("round", o.id, o.kept) });
  return card;
}

function renderRound() {
  const body = $("#roundBody");
  const secs = (ROUND.sections || []).filter((s) => (s.options || []).length);
  if (!secs.length) { body.replaceChildren(h("p", { class: "empty", text: "Nothing on the page yet." })); return; }
  body.replaceChildren(...secs.map((sec) => {
    const grid = h("div", { class: "grid" }, sec.options.map(roundCard));
    const head = h("div", { class: "sec-head" }, h("h2", { text: sec.name }), h("span", { class: "n", text: `${sec.options.length} option${sec.options.length === 1 ? "" : "s"}` }));
    return h("section", { class: "sec" }, head, typeof sec.use === "string" && sec.use ? h("p", { class: "use", text: sec.use }) : null, grid);
  }));
  const ov = $("#overall"), okey = `stylelab:overall:${EXAMPLE ? "example" : roundNo()}`;
  ov.value = LS.get(okey) || "";
  let t;
  ov.addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => LS.set(okey, ov.value), 400); });
  $("#submitRound").addEventListener("click", () => {
    const options = allOptions().map((o) => ({
      id: o.id, section: o.section, use: o.use, params: o.params || {}, label: o.label || (LIB[o.use] || {}).label || o.use,
      verdict: verdictOf("round", o.id, o.kept) || null, note: noteOf("round", o.id),
    }));
    const payload = { kind: "round", round: roundNo(), submitted_at: new Date().toISOString(), overall: ov.value.trim(), options };
    submit("round", payload, $("#submitRound"), $("#statusRound"), options.filter((x) => x.verdict).length, options.filter((x) => x.note.trim()).length);
  });
}

// ---- the full-size view
let big = null, lastFocus = null;
const modal = $("#modal");
function openBig(opt) {
  lastFocus = document.activeElement;
  modal.hidden = false;
  document.body.style.overflow = "hidden";
  big = makePlayer($(".stage", modal), opt);
  big.ui = controls($(".controls", modal), big);
  big.fit(); big.restart();
  $("#modalClose").focus();
}
function closeBig() {
  if (modal.hidden) return;
  modal.hidden = true;
  document.body.style.overflow = "";
  if (big) big.stop();
  big = null;
  if (lastFocus && lastFocus.focus) lastFocus.focus();
}
$("#modalClose").addEventListener("click", closeBig);
modal.addEventListener("click", (e) => { if (e.target === modal) closeBig(); });
const lightbox = $("#lightbox");
function openPic(src) { $("#lightboxImg").src = src; lightbox.hidden = false; document.body.style.overflow = "hidden"; $("#lightboxClose").focus(); }
function closePic() { if (lightbox.hidden) return; lightbox.hidden = true; $("#lightboxImg").removeAttribute("src"); document.body.style.overflow = ""; }
lightbox.addEventListener("click", closePic);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { closeBig(); closePic(); }
  if (e.key === " " && big && !["TEXTAREA", "INPUT", "BUTTON"].includes(document.activeElement.tagName)) { e.preventDefault(); big.paused ? big.resume() : big.pause(); }
});
window.addEventListener("resize", () => { if (big) big.fit(); });

// =====================================================================================================
// IMAGES TAB: Like / Nope on candidate pictures, grouped by search; a "why" on every Nope
// =====================================================================================================
const picUrl = (rel) => "images/" + encPath(rel);
const words = (t) => String(t || "").replace(/-/g, " ");
const imgKey = (it) => `${it.slug}:${it.id}`;

function imageCard(it) {
  const id = imgKey(it), key = docKey("images", id);
  const img = h("img", { alt: "", decoding: "async", loading: "lazy", src: picUrl(it.file) });
  if (it.w && it.h) { img.width = it.w; img.height = it.h; }
  const pic = h("button", { type: "button", class: "pic", "aria-label": "View big", onclick: () => openPic(img.src) }, img);
  const meta = h("div", { class: "meta" }, h("span", { class: "pid", text: it.id }), h("span", { text: it.source === "cosmos" ? "Cosmos" : "Pinterest" }));
  const page = safeUrl(it.page);
  if (page) meta.append(h("a", { href: page, target: "_blank", rel: "noopener noreferrer", text: "source" }));
  const fig = h("figure", { class: "ic" });
  const extra = { slug: it.slug, pic: it.id };
  const pick = verdictRow({ cls: "pick", list: [["like", "Like"], ["dislike", "Nope"]] }, (v) => {
    const cur = verdictOf("images", id);
    setMark("images", id, { verdict: cur === v ? "" : v }, {}, extra);
    if (cur !== v && v === "dislike") why.focus();
  });
  const why = h("input", { class: "why", type: "text", placeholder: "Why not? (optional)", maxLength: 200, "aria-label": "Why not" });
  why.addEventListener("input", () => setMark("images", id, { note: why.value }, {}, extra));
  fig.append(pic, meta, pick, why);
  PAINT[key] = () => {
    const v = verdictOf("images", id);
    paintVerdict(fig, pick, v);
    if (v) fig.dataset.v = v; else delete fig.dataset.v;
    why.hidden = v !== "dislike";
    const note = noteOf("images", id);
    if (document.activeElement !== why && why.value !== note) why.value = note;
  };
  PAINT[key]();
  ITEMS.images.push({ el: fig, rated: () => !!verdictOf("images", id) });
  return fig;
}
function wallBlock(title, items, caption) {
  if (!items.length) return null;
  const wall = h("div", { class: "wall" }, items.map((it) => {
    const img = h("img", { alt: "", loading: "lazy", decoding: "async", src: picUrl(it.file), onclick: () => openPic(picUrl(it.file)) });
    return h("figure", {}, img, h("figcaption", {}, caption(it)));
  }));
  return h("details", { class: "fold" }, h("summary", {}, h("span", { text: title }), h("span", { class: "n", text: String(items.length) })), wall);
}
function renderImages() {
  const body = $("#imagesBody");
  const parts = [];
  for (const g of CANDS) {
    const items = (g.items || []).map((it) => ({ ...it, slug: it.slug || g.slug })).filter((it) => it.slug && it.id && relPath(it.file));
    if (!items.length) continue;
    const grid = h("div", { class: "igrid" }, items.map(imageCard));
    parts.push(h("section", { class: "group" }, h("div", { class: "group-head" }, h("h3", { text: g.query || words(g.slug) }), h("span", { text: `${items.length} images` })), grid));
  }
  const tag = (it) => [it.id, words(it.slug)].filter(Boolean).join(" · ");
  parts.push(
    wallBlock("Liked so far", (IMGINDEX.liked || []).filter((x) => relPath(x.file)), (it) => tag(it)),
    wallBlock("Nope so far", (IMGINDEX.disliked || []).filter((x) => relPath(x.file)), (it) => [h("b", { text: it.reason || "" }), it.reason ? " " : "", tag(it)]),
  );
  const sheets = (IMGINDEX.recreate || []).filter((x) => relPath(x.file));
  if (sheets.length) {
    parts.push(h("details", { class: "fold" }, h("summary", {}, h("span", { text: "Photos your favourite creators used, found again" }), h("span", { class: "n", text: String(sheets.length) })),
      h("div", { class: "sheets" }, sheets.map((sh) => h("figure", {}, h("img", { alt: sh.name || "", loading: "lazy", decoding: "async", src: picUrl(sh.file), onclick: () => openPic(picUrl(sh.file)) }))))));
  }
  body.replaceChildren(...parts.filter(Boolean));
  $("#submitImages").addEventListener("click", () => {
    const picks = Object.values(MARKS).filter((m) => m.tab === "images" && m.verdict && m.slug && m.pic)
      .map((m) => ({ slug: m.slug, id: m.pic, verdict: m.verdict, reason: m.verdict === "dislike" ? m.note || "" : "" }));
    submit("images", { kind: "images", picks }, $("#submitImages"), $("#statusImages"), picks.length, picks.filter((x) => x.reason.trim()).length);
  });
}
const hasImages = () => CANDS.some((g) => (g.items || []).length) || [IMGINDEX.liked, IMGINDEX.disliked, IMGINDEX.recreate].some((a) => (a || []).length);

// =====================================================================================================
// SOUNDS TAB: each sound plays on a little animation at the level it would sit at in an edit.
// The rule: barely noticeable. If you clearly hear it, it's too loud.
// =====================================================================================================
const NEEDS = {
  cut:   { title: "Hard cut / punch-in", demo: "cut",   anchor: 0 },
  rise:  { title: "Clean rise",          demo: "rise",  anchor: 0.12 },
  blur:  { title: "Blur rise",           demo: "blur",  anchor: 0.12 },
  shine: { title: "Shine",               demo: "shine", anchor: 0.6 },
  tick:  { title: "Ring and ticks",      demo: "ticks", anchor: 0, repeat: [0, 0.32, 0.64] },
  panel: { title: "Panel slide",         demo: "panel", anchor: 0.33 },
  icon:  { title: "App icons rising",    demo: "icons", anchor: 0.1, repeat: [0, 0.18, 0.36] },
  click: { title: "Mouse click / lines drawing on", demo: null },
  hero:  { title: "Hero word landing",   demo: "blur",  anchor: 0.2 },
  "ex-click":  { title: "Click",        demo: "tap",   anchor: 0 },
  "ex-whoosh": { title: "Soft whoosh",  demo: "sweep", anchor: 0.4 },
  "ex-impact": { title: "Low impact",   demo: "thud",  anchor: 0 },
};
const EXPO_EASE = "cubic-bezier(.19,1,.22,1)";
let actx = null;
const sbuf = {};
function audio() {
  if (!actx) {
    actx = new (window.AudioContext || window.webkitAudioContext)();
    try { if (navigator.audioSession) navigator.audioSession.type = "playback"; } catch {}   // so the iPhone silent switch doesn't mute it
  }
  if (actx.state === "suspended") actx.resume();
  return actx;
}
// The example's sounds are made right here, sample by sample.
function synthBuffer(ctx, kind) {
  const sr = ctx.sampleRate, dur = { click: 0.12, whoosh: 0.9, impact: 0.7 }[kind] || 0.3, n = Math.floor(dur * sr);
  const buf = ctx.createBuffer(1, n, sr), d = buf.getChannelData(0);
  let a1 = 0, a2 = 0, prev = 0, phase = 0;
  for (let i = 0; i < n; i++) {
    const t = i / sr, noise = Math.random() * 2 - 1;
    if (kind === "click") {
      const hp = noise - prev; prev = noise;
      d[i] = (hp * 0.5 + Math.sin(2 * Math.PI * 1900 * t) * 0.5) * Math.exp(-t / 0.006);
    } else if (kind === "whoosh") {
      const fc = 250 + 2600 * Math.pow(Math.sin(Math.PI * t / dur), 2), a = 1 - Math.exp(-2 * Math.PI * fc / sr);
      a1 += a * (noise - a1); a2 += a * (a1 - a2);
      d[i] = a2 * Math.pow(Math.sin(Math.PI * t / dur), 1.5) * 3;
    } else {
      phase += 2 * Math.PI * (45 + 90 * Math.exp(-t / 0.07)) / sr;
      a1 += 0.08 * (noise - a1);
      d[i] = Math.sin(phase) * Math.exp(-t / 0.16) + a1 * Math.exp(-t / 0.012) * 0.8;
    }
  }
  let peak = 0;
  for (let i = 0; i < n; i++) peak = Math.max(peak, Math.abs(d[i]));
  for (let i = 0; i < n; i++) d[i] = (d[i] / (peak || 1)) * 0.8;
  return buf;
}
function bufferFor(s) {
  if (!sbuf[s.file]) {
    sbuf[s.file] = (s.synth
      ? Promise.resolve(synthBuffer(audio(), s.synth))
      : fetch("sfx/" + encPath(s.file)).then((r) => { if (!r.ok) throw new Error("missing"); return r.arrayBuffer(); }).then((b) => audio().decodeAudioData(b)))
      .catch((e) => { delete sbuf[s.file]; throw e; });
  }
  return sbuf[s.file];
}
let faceLoopOk = true;   // the plain tile stands in when there is no footage to show
function demoTile(kind) {
  const tile = h("div", { class: "tile" });
  if ((kind === "cut" || kind === "panel") && faceLoopOk) {
    const v = h("video", { muted: true, playsInline: true, preload: "metadata", src: "assets/face-loop.mp4#t=0.5" });
    v.muted = true;
    tile.append(v);
    if (kind === "panel") tile.append(h("div", { class: "panel2" }));
  } else if (kind === "cut" || kind === "panel") {
    tile.classList.add("plain");
    if (kind === "panel") tile.append(h("div", { class: "panel2" }));
  } else if (kind === "rise" || kind === "blur" || kind === "shine") {
    tile.append(h("div", { class: "center" }, h("span", { class: "word", text: "Simple" })));
  } else if (kind === "ticks") {
    tile.append(h("div", { class: "center" }, h("div", {}, h("div", { class: "dot" }), h("div", { class: "dot" }), h("div", { class: "dot" }))));
  } else if (kind === "icons") {
    const ic = (typeof ICONS !== "undefined" ? ICONS : []).slice(0, 3).filter((i) => relPath(i.file));
    tile.append(h("div", { class: "icons" }, ic.map((i) => h("img", { alt: "", src: i.file }))));
  } else if (kind === "tap") {
    tile.classList.add("plain"); tile.append(h("div", { class: "ring" }), h("div", { class: "core" }));
  } else if (kind === "sweep") {
    tile.classList.add("plain"); tile.append(h("div", { class: "bar2" }));
  } else if (kind === "thud") {
    tile.classList.add("plain"); tile.append(h("div", { class: "block" }));
  }
  return tile;
}
function runDemo(tile, kind, step) {
  const q = (sel) => $(sel, tile);
  if (kind === "cut") { const v = q("video"); if (v) { v.style.transition = "transform .9s ease-out"; v.style.transform = "scale(1.15)"; setTimeout(() => { v.style.transform = ""; }, 900); } }
  else if (kind === "rise") q(".word").animate([{ transform: "translateY(46px)", opacity: 0 }, { transform: "translateY(0)", opacity: 1 }], { duration: 850, easing: EXPO_EASE, fill: "forwards" });
  else if (kind === "blur") q(".word").animate([{ transform: "translateY(34px)", opacity: 0, filter: "blur(18px)" }, { transform: "translateY(0)", opacity: 1, filter: "blur(0)" }], { duration: 500, easing: EXPO_EASE, fill: "forwards" });
  else if (kind === "shine") { const w = q(".word"); w.style.opacity = 1; w.animate([{ color: "#fff" }, { color: "#9aa0a6" }, { color: "#fff" }], { duration: 1200 }); }
  else if (kind === "ticks") $$(".dot", tile)[step].classList.add("done");
  else if (kind === "panel") q(".panel2").animate([{ transform: "translateY(-100%)" }, { transform: "translateY(0)" }], { duration: 650, easing: "cubic-bezier(.65,0,.35,1)", fill: "forwards" });
  else if (kind === "icons") { const im = $$(".icons img", tile)[step]; if (im) im.animate([{ transform: "translateY(40px)", opacity: 0 }, { transform: "translateY(0)", opacity: 1 }], { duration: 850, easing: EXPO_EASE, fill: "forwards" }); }
  else if (kind === "tap") { q(".ring").animate([{ transform: "scale(.3)", opacity: 0.9 }, { transform: "scale(2.2)", opacity: 0 }], { duration: 450, easing: "ease-out" }); q(".core").animate([{ transform: "scale(1)" }, { transform: "scale(.6)", offset: 0.3 }, { transform: "scale(1)" }], { duration: 220 }); }
  else if (kind === "sweep") q(".bar2").animate([{ transform: "translateX(-100%)", opacity: 0 }, { opacity: 1, offset: 0.2 }, { opacity: 1, offset: 0.8 }, { transform: "translateX(100%)", opacity: 0 }], { duration: 800, easing: "cubic-bezier(.65,0,.35,1)" });
  else if (kind === "thud") { const b = q(".block"); b.animate([{ transform: "translateY(-120px)" }, { transform: "translateY(0)" }], { duration: 160, easing: "cubic-bezier(.5,0,1,1)" }); b.animate([{ transform: "translateY(0) scale(1.25,.7)" }, { transform: "translateY(0) scale(1)" }], { duration: 260, delay: 160, easing: "ease-out", fill: "backwards" }); }
}
function resetDemo(tile) {
  tile.getAnimations({ subtree: true }).forEach((a) => a.cancel());
  $$(".dot", tile).forEach((d) => d.classList.remove("done"));
  const w = $(".word", tile); if (w) w.style.opacity = "";
}
async function playSound(card, s) {
  const need = NEEDS[s.need] || {}, status = $("#statusSounds");
  let c, buf;
  try { c = audio(); buf = await bufferFor(s); } catch { return say(status, "That sound didn't load."); }
  say(status, "");
  (card._t || []).forEach(clearTimeout); card._t = [];
  const steps = need.repeat || [0], point = s.hit_s ?? s.peak_s ?? 0, d = point - (need.anchor || 0);
  const animDelay = Math.max(d, 0), soundDelay = Math.max(-d, 0), t0 = c.currentTime + 0.06;
  steps.forEach((o) => { const src = c.createBufferSource(), g = c.createGain(); src.buffer = buf; g.gain.value = Math.pow(10, (s.mix_db || 0) / 20); src.connect(g).connect(c.destination); src.start(t0 + soundDelay + o); });
  const tile = $(".tile", card), btn = $(".play", card);
  if (tile) {
    resetDemo(tile);
    steps.forEach((o, i) => card._t.push(setTimeout(() => runDemo(tile, need.demo, i), (0.06 + (c.outputLatency || 0) + animDelay + o) * 1000)));
    card._t.push(setTimeout(() => resetDemo(tile), 3200));
  }
  btn.classList.add("on");
  card._t.push(setTimeout(() => btn.classList.remove("on"), (0.06 + soundDelay + steps[steps.length - 1] + (s.duration_s || 1)) * 1000));
}
function soundCard(s) {
  const need = NEEDS[s.need] || {}, key = docKey("sounds", s.file);
  const card = h("article", { class: "scard" });
  if (need.demo) { const tile = demoTile(need.demo); tile.addEventListener("click", () => playSound(card, s)); card.append(tile); }
  const play = h("button", { type: "button", class: "play", "aria-label": `Play ${s.name}`, onclick: () => playSound(card, s) });
  play.innerHTML = ICON_PLAY;
  const pick = verdictRow({ cls: "pick", list: [["keep", "Keep"], ["drop", "Drop"]] }, (v) => {
    setMark("sounds", s.file, { verdict: verdictOf("sounds", s.file, s.picked) === v ? "" : v }, { verdict: s.picked ? "keep" : "" });
  });
  card.append(h("div", { class: "info" },
    h("div", { class: "row1" }, play, h("div", {}, h("div", { class: "sname", text: s.name || s.file }), h("div", { class: "slen", text: `${(+s.duration_s || 0).toFixed(2)}s · ${s.mix_db == null ? 0 : s.mix_db} dB` }))),
    pick));
  PAINT[key] = () => { const v = verdictOf("sounds", s.file, s.picked); paintVerdict(card, pick, v); if (v) card.dataset.v = v; else delete card.dataset.v; };
  PAINT[key]();
  ITEMS.sounds.push({ el: card, rated: () => !!verdictOf("sounds", s.file, s.picked) });
  return card;
}
function renderSounds() {
  const body = $("#soundsBody");
  const order = [...Object.keys(NEEDS), ...new Set(SFX.map((s) => s.need).filter((n) => n && !NEEDS[n]))];
  const secs = [];
  for (const key of order) {
    const items = SFX.filter((s) => s.need === key);
    if (!items.length) continue;
    const title = (NEEDS[key] || {}).title || words(key);
    secs.push(h("section", { class: "sec" }, h("div", { class: "sec-head" }, h("h2", { text: title }), h("span", { class: "n", text: `${items.length} sound${items.length === 1 ? "" : "s"}` })), h("div", { class: "sgrid" }, items.map(soundCard))));
  }
  body.replaceChildren(...secs);
  $("#submitSounds").addEventListener("click", () => {
    const options = SFX.map((s) => ({ id: s.file, need: s.need, label: s.name, verdict: verdictOf("sounds", s.file, s.picked) || null, note: "" }));
    const payload = { kind: "sfx", round: "sfx", submitted_at: new Date().toISOString(), options };
    submit("sfx", payload, $("#submitSounds"), $("#statusSounds"), options.filter((x) => x.verdict).length, 0);
  });
}

// =====================================================================================================
// CREATORS TAB (read only)
// =====================================================================================================
function renderCreators() {
  const body = $("#creatorsBody");
  body.replaceChildren(...CREATORS.map((c) => {
    const handle = c.handle ? String(c.handle).replace(/^@/, "") : "";
    const link = safeUrl(c.url) || (handle ? safeUrl(`https://www.instagram.com/${encodeURIComponent(handle)}/`) : "");
    const face = relPath(c.pfp || c.image || "");
    const who = h("div", { class: "who" }, face ? h("img", { class: "avatar", alt: "", loading: "lazy", src: face }) : null, h("h2", { text: c.name || handle || "Creator" }));
    if (link) who.append(h("a", { href: link, target: "_blank", rel: "noopener noreferrer", text: handle ? "@" + handle : "Profile" }));
    if (c.fav) who.append(h("span", { class: "fav", text: "Favourite" }));
    const reels = (c.reels || []).map((r) => {
      const href = safeUrl(r.link), poster = relPath(r.poster || r.image || r.thumb || "");
      const art = poster ? h("img", { class: "poster", alt: "", loading: "lazy", decoding: "async", src: poster }) : h("div", { class: "noposter", text: "Reel" });
      return h("div", { class: "reel" },
        href ? h("a", { href, target: "_blank", rel: "noopener noreferrer", "aria-label": r.title || "Open the original" }, art) : art,
        h("div", { class: "cap" }, h("span", { class: "t", text: r.title || "" }), href ? h("a", { href, target: "_blank", rel: "noopener noreferrer", text: "Original" }) : null));
    });
    return h("section", {}, who, c.took ? h("p", { class: "took", text: String(c.took) }) : null, reels.length ? h("div", { class: "reels" }, reels) : null);
  }));
}

// =====================================================================================================
// THE BAR: tabs, "n of m rated", the progress line, Unrated only, Safe zones
// =====================================================================================================
const TAB_NAMES = { round: "Round", images: "Images", sounds: "Sounds", creators: "Creators" };
let SHOWN_TABS = ["round"];
function counts(tab) {
  if (tab === "round") { const all = allOptions(); return { total: all.length, rated: all.filter((o) => verdictOf("round", o.id, o.kept)).length }; }
  const list = ITEMS[tab] || [];
  return { total: list.length, rated: list.filter((i) => i.rated()).length };
}
function updateBar() {
  const tab = ACTIVE, c = tab === "creators" ? null : counts(tab);
  $("#count").textContent = c ? `${c.rated} of ${c.total} rated` : "";
  $("#progressFill").style.width = c && c.total ? `${(c.rated / c.total) * 100}%` : "0%";
  $("#unratedBtn").hidden = !c;
  $(".bar-row").hidden = !c;
  $("#safeBtn").hidden = tab !== "round";
}
function applyFilter() {
  const only = $("#unratedBtn").getAttribute("aria-pressed") === "true";
  for (const tab of ["round", "images", "sounds"]) {
    const panel = $("#tab-" + tab);
    for (const it of ITEMS[tab]) it.el.hidden = only && it.rated();
    for (const sec of $$(".sec, .group", panel)) sec.hidden = only && $$(".card, .ic, .scard", sec).every((x) => x.hidden);
    let note = $(".all-rated", panel);
    const left = ITEMS[tab].some((it) => !it.el.hidden);
    if (only && !left && ITEMS[tab].length) {
      if (!note) { note = h("p", { class: "empty all-rated", text: "Everything here is rated." }); $("#" + tab + "Body").after(note); }
    } else if (note) note.remove();
  }
}
function setToggle(btn, on) { btn.setAttribute("aria-pressed", on ? "true" : "false"); }
function showTab(name) {
  if (!SHOWN_TABS.includes(name)) name = "round";
  ACTIVE = name;
  for (const t of Object.keys(TAB_NAMES)) $("#tab-" + t).hidden = t !== name;
  $$("#tabs button").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === name ? "true" : "false"));
  LS.set("stylelab:tab", name);
  updateBar(); applyFilter();
  const bar = $("#bar");
  if (window.scrollY > bar.offsetTop) window.scrollTo(0, bar.offsetTop);
}
function buildTabs() {
  const tabs = $("#tabs");
  tabs.replaceChildren(...SHOWN_TABS.map((t) => h("button", { type: "button", role: "tab", dataset: { tab: t }, text: TAB_NAMES[t], "aria-selected": "false", onclick: () => showTab(t) })));
  tabs.addEventListener("keydown", (e) => {
    const i = SHOWN_TABS.indexOf(ACTIVE), d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (d) { showTab(SHOWN_TABS[(i + d + SHOWN_TABS.length) % SHOWN_TABS.length]); $(`#tabs [data-tab="${ACTIVE}"]`).focus(); }
  });
}

// =====================================================================================================
// START
// =====================================================================================================
async function init() {
  await loadHas();
  const round = await optJSON("round.json");
  const brand = round ? await optJSON("locked/brand.json") : null;
  EXAMPLE = !(round && Array.isArray(round.sections) && brand && brand.colours && brand.font);
  ROUND = EXAMPLE ? EXAMPLE_ROUND : round;
  BRAND = EXAMPLE ? EXAMPLE_BRAND : brand;
  LS_MARKS = EXAMPLE ? "stylelab:marks:example" : "stylelab:marks";

  if (EXAMPLE) {
    installExampleFootage();
    faceLoopOk = false;
    SFX = EXAMPLE_SOUNDS;
    await applyBrand(BRAND, {});
  } else {
    const [shine, zoom, shadow, icons, site, repo, profile, sfx, cands, picks, index, creators] = await Promise.all([
      optJSON("locked/shine.json"), optJSON("locked/zoom.json"), optJSON("locked/shadow.json"), optJSON("assets/icons/icons.json", []),
      optJSON("assets/site.json"), optJSON("assets/repo.json"), optJSON("profile.json"), optJSON("sfx/sfx.json", []),
      optJSON("images/candidates/index.json"), optJSON("images/picks.json"), optJSON("images/index.json"), optJSON("creators.json"),
    ]);
    await applyBrand(BRAND, { shine, zoom, shadow, icons: Array.isArray(icons) ? icons : [], site, repo });
    await checkAssets();
    PROFILE = profile && typeof profile === "object" ? profile : null;
    faceLoopOk = !(HAS && HAS["assets/face-loop.mp4"] === false);
    SFX = (Array.isArray(sfx) ? sfx : []).filter((s) => s && s.file && relPath(s.file));
    CANDS = (cands && Array.isArray(cands.queries)) ? cands.queries : [];
    IMGINDEX = index && typeof index === "object" ? { liked: [], disliked: [], recreate: [], ...index } : IMGINDEX;
    CREATORS = (creators && Array.isArray(creators.creators)) ? creators.creators : [];
    for (const p of (picks && Array.isArray(picks.picks)) ? picks.picks : []) {   // marks from the last Submit that Claude filed: the starting point
      if (!p || !p.slug || !p.id || !VERDICTS.images.includes(p.verdict)) continue;
      const id = `${p.slug}:${p.id}`;
      MARKS[docKey("images", id)] = { tab: "images", id, slug: String(p.slug), pic: String(p.id), round: roundNo(), verdict: p.verdict, note: String(p.reason || ""), at: 0, by: null };
    }
  }
  SAFE_NODE = buildSafe();
  $("#modal .modal-phone").append(safeNode());
  loadLocal();

  renderHead();
  renderRound();
  if (SFX.length) renderSounds();
  if (!EXAMPLE && hasImages()) renderImages();
  if (!EXAMPLE && CREATORS.length) renderCreators();
  SHOWN_TABS = ["round", ...(!EXAMPLE && hasImages() ? ["images"] : []), ...(SFX.length ? ["sounds"] : []), ...(!EXAMPLE && CREATORS.length ? ["creators"] : [])];
  buildTabs();

  const unrated = $("#unratedBtn"), safeBtn = $("#safeBtn");
  const setSafe = (on) => { document.body.classList.toggle("safe", on); setToggle(safeBtn, on); LS.set("stylelab:safe", on); };
  safeBtn.addEventListener("click", () => setSafe(!document.body.classList.contains("safe")));
  unrated.addEventListener("click", () => { const on = unrated.getAttribute("aria-pressed") !== "true"; setToggle(unrated, on); LS.set("stylelab:unrated", on); applyFilter(); });
  setSafe(!!LS.get("stylelab:safe"));
  setToggle(unrated, !!LS.get("stylelab:unrated"));
  showTab(LS.get("stylelab:tab") || "round");

  requestAnimationFrame(frame);
  document.addEventListener("visibilitychange", () => { if (document.hidden) flushAll(); });
  window.addEventListener("pagehide", () => { flushAll(); });
  window.pageReady = true;
  if (!EXAMPLE) connectDb();   // lights up saving and restoring when Claude is there; the page already works without it
}
init().catch((e) => {
  console.error(e);
  $("#roundBody").replaceChildren(h("p", { class: "empty", text: "This page couldn't load. Go back to Claude and ask it to open the page again." }));
  window.pageReady = true;
});
})();
