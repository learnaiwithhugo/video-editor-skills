// The animation library. Every option on the style page is one of these, drawn on a 1080x1920 stage
// (real video pixels) in the creator's brand. round.json picks which ones show and with what params.
//
// def(id, { section, label, loop, params, build(s, P) })   registers an option.
//   s = stage helper (s.el, s.img, s.video, s.at)    P = default params merged with round.json params.
// Custom options Claude designs for one person go in custom.js using the same def().
//
// Taste rules baked in (from the session that built this): no pop-in or scale-overshoot entrances
// anywhere, no black backgrounds behind visuals, no underlined words, real app icons only, logos tilted
// and overlapping (never a straight uniform row as the only choice), push-ins on visuals under a second,
// zooms on faces long and smooth, intro text never cramped, captions inside Instagram's safe zone.

let C = {}, FONT = "", W8 = { title: 700, caption: 600, label: 500 }, CAP_SHADOW = "0 4px 24px rgba(0,0,0,.45)";
let ICONS = [], SHINE = null, ZOOM = null, LINES = {};
const LIB = {};
function def(id, spec) { LIB[id] = { id, params: {}, loop: 4000, ...spec }; }

// Called once by app.js after brand.json (and any locked labs) have loaded.
function setBrand(b, extra = {}) {
  const c = b.colours || {};
  C = { paper: c.paper || "#FFFFFF", accent: c.accent, soft: c.accent_soft, deep: c.accent_deep, ink: c.ink, text: b.caption_colour || "#FFFFFF" };
  FONT = `"${b.font.family}", "Helvetica Neue", Helvetica, Arial, sans-serif`;
  W8 = { ...W8, ...(b.font.weights || {}) };
  ICONS = extra.icons || [];
  SHINE = extra.shine || null;
  ZOOM = extra.zoom || null;
  if (extra.shadow && extra.shadow.text_shadow) CAP_SHADOW = extra.shadow.text_shadow;
  LINES = { ...DEFAULT_LINES, ...(b.lines || {}) };
  if (extra.site) SITE = { ...SITE, ...extra.site };
  if (extra.repo) REPO = { ...REPO, ...extra.repo };
}
const DEFAULT_LINES = {
  captions: ["here's the thing", "most people", "get this wrong"],
  accent: "Make it look easy",
  intro: ["The simplest way to", "edit", "your videos"],
  talk: ["most people", "get this", "completely wrong", "here's why"],   // the 3rd chunk is where zooms land
};
const rgba = (hex, a) => { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };
const icon = (i) => (ICONS[i % Math.max(ICONS.length, 1)] || {}).file;

// ---- easing (measured off Apple-style After Effects text, frame by frame)
const EXPO = "cubic-bezier(.16,1,.3,1)";       // fast, then a long soft settle
const GLIDE = "cubic-bezier(.19,1,.22,1)";
const SMOOTH = "cubic-bezier(.65,0,.35,1)";    // slow at both ends
const PUNCH = "cubic-bezier(.7,0,.15,1)";      // quick in, firm landing

// ---- small helpers
function footage(s, css = {}) {   // the creator's own talking-head clip
  return s.video("assets/face-loop.mp4", { position: "absolute", left: "0", top: "0", width: "1080px", height: "1920px", objectFit: "cover", objectPosition: "50% 30%", transformOrigin: "50% 32%", ...css });
}
function faceBottom(s) { return footage(s, { top: "960px", height: "960px" }); }
function textLine(s, { top = 960, size = 88, weight = W8.title, align = "center", pad = 0, colour = C.text, shadow = CAP_SHADOW } = {}) {
  return s.el("div", {
    position: "absolute", left: pad + "px", right: pad + "px", top: top + "px", transform: "translateY(-50%)",
    textAlign: align, color: colour, fontFamily: FONT, fontWeight: String(weight), fontSize: size + "px",
    lineHeight: "1.05", letterSpacing: size > 150 ? "-0.045em" : "-0.02em", whiteSpace: "nowrap", textShadow: shadow,
  });
}
function words(s, parent, text) {
  const ws = text.split(" ");
  return ws.map((w, i) => s.el("span", { display: "inline-block", whiteSpace: "pre" }, parent, i < ws.length - 1 ? w + " " : w));
}
function hideAt(el, t) { el.animate([{ opacity: 0 }, { opacity: 0 }], { duration: 600000, delay: t, fill: "forwards" }); }
function exitUp(el, at) {
  el.animate([{ transform: "translateY(0)" }, { transform: "translateY(-30px)" }], { duration: 300, delay: at, easing: "cubic-bezier(.7,0,.84,0)", fill: "forwards", composite: "add" });
  el.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 300, delay: at, easing: "cubic-bezier(.7,0,.84,0)", fill: "forwards" });
}

// ---- the three text motions
function cleanRise(el, delay, d = 820, dist = 42) {   // premium and unhurried, no blur
  el.animate([{ opacity: 0, transform: `translateY(${dist}px)` }, { opacity: .7, offset: .45 }, { opacity: 1, transform: "translateY(0)" }],
    { duration: d, delay, easing: GLIDE, fill: "backwards" });
}
function blurRise(el, delay, d = 480) {   // starts heavily blurred and faint, sharpens as it rises
  el.animate([{ opacity: 0, transform: "translateY(26px)", filter: "blur(18px)" }, { opacity: .55, filter: "blur(7px)", offset: .4 }, { opacity: 1, transform: "translateY(0)", filter: "blur(0)" }],
    { duration: d, delay, easing: EXPO, fill: "backwards" });
}
// Calm entrances for visual parts. Movement is added on top of each element's own transform.
function enter(el, delay, kind = "rise") {
  if (kind === "fade") {
    el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 600, delay, easing: "ease-out", fill: "backwards" });
  } else if (kind === "blur") {
    el.animate([{ transform: "translateY(34px)" }, { transform: "translateY(0)" }], { duration: 560, delay, easing: EXPO, fill: "backwards", composite: "add" });
    el.animate([{ opacity: 0, filter: "blur(18px)" }, { opacity: .55, filter: "blur(7px)", offset: .4 }, { opacity: 1, filter: "blur(0)" }], { duration: 560, delay, easing: EXPO, fill: "backwards" });
  } else {
    const d = kind === "slow" ? 1500 : 850;
    el.animate([{ transform: "translateY(46px)" }, { transform: "translateY(0)" }], { duration: d, delay, easing: GLIDE, fill: "backwards", composite: "add" });
    el.animate([{ opacity: 0 }, { opacity: .7, offset: .45 }, { opacity: 1 }], { duration: d, delay, easing: GLIDE, fill: "backwards" });
  }
}
// Default caption chunks that swap as you talk. Every chunk is built up front so the scrub bar works.
function chunks(s, list, { top = 1240, size = 84, enterFx, end }) {
  list.forEach(([text, on], i) => {
    const l = textLine(s, { top, size, weight: W8.caption });
    const sp = words(s, l, text);
    enterFx(l, sp, on);
    hideAt(l, (list[i + 1] || [0, end])[1]);
  });
}
const softFade = (l, _, at) => l.animate([{ opacity: 0, transform: "translateY(calc(-50% + 14px))" }, { opacity: 1, transform: "translateY(-50%)" }], { duration: 260, delay: at, easing: EXPO, fill: "backwards" });
const timed = (arr, start, gap) => arr.map((t, i) => [t, start + i * gap]);

// ---- shine: a band of light clipped to the text (exact settings come from locked/shine.json once locked)
function shine(el, delay, base = C.text) {
  const sh = SHINE || { width: 14, strength: 70, soft: 45, glow: 0, angle: 100, dur: 1400, ease: "cubic-bezier(.45,0,.2,1)", shine: C.text, base: C.accent };
  const b = sh.base || base, peak = `color-mix(in srgb, ${sh.shine} ${sh.strength}%, ${b})`;
  const half = sh.width / 2, edge = half * (sh.soft / 100);
  Object.assign(el.style, {
    backgroundImage: `linear-gradient(${sh.angle}deg, ${b} 0%, ${b} ${50 - half}%, ${peak} ${50 - half + edge}%, ${peak} ${50 + half - edge}%, ${b} ${50 + half}%, ${b} 100%)`,
    backgroundSize: "300% 100%", webkitBackgroundClip: "text", backgroundClip: "text", color: "transparent", textShadow: "none",
  });
  const h = 1.5 * sh.width / 100, m = 0.12;
  el.animate([{ backgroundPosition: `${((1.5 + h + m) / 2) * 100}% 0` }, { backgroundPosition: `${((0.5 - h - m) / 2) * 100}% 0` }], { duration: sh.dur, delay, easing: sh.ease, fill: "both" });
}

// ---- cards, pills, lines, rings
const SHADOW = (a = .22) => `0 18px 50px ${rgba(C.ink, a)}`;
function panel(s, css, parent) { return s.el("div", { position: "absolute", background: C.paper, borderRadius: "40px", boxShadow: SHADOW(), overflow: "hidden", ...css }, parent); }
function pill(s, parent, x, y, text, css = {}) {
  return s.el("div", { position: "absolute", left: x + "px", top: y + "px", transform: "translate(-50%,-50%)", background: C.paper, color: C.ink,
    border: `3px solid ${rgba(C.ink, .1)}`, borderRadius: "999px", padding: "16px 30px", fontFamily: FONT, fontWeight: String(W8.title), fontSize: "38px",
    whiteSpace: "nowrap", boxShadow: `0 8px 22px ${rgba(C.ink, .1)}`, ...css }, parent, text);
}
function lines(s, parent, w, h, paths, start, gap = 90, colour = C.accent) {   // trim-path draw-on
  const box = s.el("div", { position: "absolute", left: "0", top: "0", width: w + "px", height: h + "px" }, parent);
  box.innerHTML = `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" fill="none">${paths.map(d => `<path d="${d}" pathLength="1" stroke="${colour}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1" stroke-dashoffset="1"/>`).join("")}</svg>`;
  box.querySelectorAll("path").forEach((p, i) => p.animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], { duration: 420, delay: start + i * gap, easing: EXPO, fill: "forwards" }));
}
function ring(s, parent, x, y, w, h, delay, colour = C.accent) {
  const box = s.el("div", { position: "absolute", left: x - 14 + "px", top: y - 14 + "px", width: w + 28 + "px", height: h + 28 + "px" }, parent);
  box.innerHTML = `<svg width="100%" height="100%" viewBox="0 0 ${w + 28} ${h + 28}" fill="none"><rect x="5" y="5" width="${w + 18}" height="${h + 18}" rx="18" pathLength="1" stroke="${colour}" stroke-width="8" stroke-dasharray="1" stroke-dashoffset="1"/></svg>`;
  box.querySelector("rect").animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], { duration: 700, delay, easing: EXPO, fill: "both" });
}
function node(s, parent, cx, cy, { icon: ic, label, sub, w = 300, dark = false } = {}) {
  const n = s.el("div", { position: "absolute", left: cx + "px", top: cy + "px", width: w + "px", transform: "translate(-50%,-50%)", display: "flex", alignItems: "center",
    gap: "18px", padding: "18px 22px", borderRadius: "24px", fontFamily: FONT, background: dark ? C.deep : C.paper, color: dark ? "#fff" : C.ink,
    border: dark ? "0" : `2px solid ${rgba(C.ink, .1)}`, boxShadow: `0 14px 34px ${rgba(C.ink, .16)}`, boxSizing: "border-box" }, parent);
  if (ic) s.img(ic, { width: "64px", height: "64px", flex: "none" }, n);
  const t = s.el("div", { minWidth: "0" }, n);
  s.el("div", { fontSize: "34px", fontWeight: String(W8.title), letterSpacing: "-0.02em", lineHeight: "1.1" }, t, label);
  if (sub) s.el("div", { fontSize: "24px", fontWeight: String(W8.label), opacity: ".6", marginTop: "4px" }, t, sub);
  return n;
}
function topHalf(s, bg) { return s.el("div", { position: "absolute", left: "0", top: "0", width: "1080px", height: "960px", background: bg, overflow: "hidden" }); }
function diagTitle(s, parent, tag, title, onAccent, t0, centre = false) {
  const t = s.el("div", centre ? { position: "absolute", left: "0", right: "0", top: "70px", textAlign: "center", fontFamily: FONT } : { position: "absolute", left: "72px", top: "70px", fontFamily: FONT }, parent);
  if (tag) s.el("div", { display: "inline-block", background: onAccent ? C.paper : C.deep, color: onAccent ? C.deep : "#fff", fontSize: "22px", fontWeight: String(W8.title), letterSpacing: "0.08em", padding: "8px 14px", borderRadius: "8px", marginBottom: "14px" }, t, tag);
  s.el("div", { fontSize: "64px", fontWeight: String(W8.caption), letterSpacing: "-0.03em", color: onAccent ? "#fff" : C.ink }, t, title);
  enter(t, t0, "rise");
}

// =====================================================================================================
// TEXT
// =====================================================================================================
def("cap-soft-fade", { section: "Default captions", label: "Soft fade-up", params: { top: 1240, size: 84 },
  build(s, P) { footage(s); chunks(s, timed(LINES.captions, 300, 950), { ...P, enterFx: softFade, end: 3400 }); } });
def("cap-word-fade", { section: "Default captions", label: "Quick word fade", params: { top: 1240, size: 84 },
  build(s, P) { footage(s); chunks(s, timed(LINES.captions, 300, 950), { ...P, end: 3400, enterFx: (l, sp, at) => sp.forEach((w, i) => w.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 180, delay: at + i * 90, fill: "backwards" })) }); } });
def("cap-cut", { section: "Default captions", label: "Straight cut, no motion", params: { top: 1240, size: 84 },
  build(s, P) { footage(s); chunks(s, timed(LINES.captions, 300, 950), { ...P, end: 3400, enterFx: (l, _, at) => l.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 1, delay: at, fill: "backwards" }) }); } });

def("accent-clean-rise", { section: "Accent text", label: "Clean rise", params: { gap: 230, dur: 820, size: 92 },
  build(s, P) { const l = textLine(s, { size: P.size }); words(s, l, LINES.accent).forEach((w, i) => cleanRise(w, 300 + i * P.gap, P.dur)); exitUp(l, 3100); } });
def("accent-blur-rise", { section: "Accent text", label: "Blur rise", params: { gap: 170, dur: 480, size: 92 },
  build(s, P) { const l = textLine(s, { size: P.size }); words(s, l, LINES.accent).forEach((w, i) => blurRise(w, 300 + i * P.gap, P.dur)); exitUp(l, 3100); } });

// Intro / hook text: small lead-in, one huge hero word with its own effect, a last line gliding in.
// Spacing is generous on purpose: cramped hook text was the first note on both test edits.
function intro(s, P, heroFx) {
  const [lead, hero, tail] = LINES.intro;
  const a = textLine(s, { top: 640, size: 72 }), b = textLine(s, { top: 860, size: P.heroSize, colour: P.heroColour === "text" ? C.text : C.accent }), c = textLine(s, { top: 1110, size: 112 });
  words(s, a, lead).forEach((w, i) => cleanRise(w, 300 + i * 230));
  const h = s.el("span", { display: "inline-block" }, b, hero);
  heroFx(h, b);
  const g = s.el("span", { display: "inline-block" }, c, tail);
  g.animate([{ opacity: 0, transform: `translateX(${P.from * 180}px)` }, { opacity: 1, offset: .4 }, { opacity: 1, transform: "translateX(0)" }], { duration: 900, delay: 1750, easing: GLIDE, fill: "backwards" });
  [a, b, c].forEach(l => exitUp(l, 4100));
}
def("intro-shine", { section: "Intro text", label: "Hero word shine", loop: 5000, params: { heroSize: 240, from: -1, heroColour: "accent" },
  build(s, P) { intro(s, P, (h) => { blurRise(h, 1000); shine(h, 1500, P.heroColour === "text" ? C.text : C.accent); }); } });
def("intro-focus", { section: "Intro text", label: "Hero word focus-in", loop: 5000, params: { heroSize: 240, from: -1, heroColour: "accent" },
  build(s, P) { intro(s, P, (h) => h.animate([{ opacity: 0, transform: "scale(1.35)", filter: "blur(26px)" }, { opacity: .8, filter: "blur(6px)", offset: .45 }, { opacity: 1, transform: "scale(1)", filter: "blur(0)" }], { duration: 1000, delay: 1000, easing: GLIDE, fill: "backwards" })); } });

// Font comparison: same line, same clean rise, only the font changes. params.family + params.css
def("font-compare", { section: "Fonts", label: "Font", params: { family: "Helvetica Neue", css: "" },
  build(s, P) {
    if (P.css && !document.querySelector(`link[href="${P.css}"]`)) document.head.insertAdjacentHTML("beforeend", `<link rel="stylesheet" href="${P.css}">`);
    const l = textLine(s, { size: 96 }); l.style.fontFamily = `"${P.family}", Helvetica, sans-serif`;
    words(s, l, LINES.accent).forEach((w, i) => cleanRise(w, 300 + i * 230));
    const sub = textLine(s, { top: 1110, size: 46, weight: W8.label }); sub.style.fontFamily = l.style.fontFamily; sub.style.opacity = ".75"; sub.textContent = P.family;
    exitUp(l, 3100); exitUp(sub, 3100);
  } });

// White text drop shadows over the hardest case: a bright, busy screenshot on top, the face below.
def("shadow", { section: "White text drop shadows", label: "Shadow", loop: 5200, params: { css: "0 4px 24px rgba(0,0,0,.5)" },
  build(s, P) {
    const top = topHalf(s, "#fff");
    const im = s.img("assets/bright.png", { position: "absolute", left: "0", top: "0", width: "1080px", minHeight: "1240px", objectFit: "cover", objectPosition: "top" }, top);
    im.animate([{ transform: "translateY(0)" }, { transform: "translateY(-260px)" }], { duration: 5200, easing: "linear", fill: "both" });
    faceBottom(s);
    [[LINES.talk[0], 300, 620], [LINES.talk[1], 1150, 620], [LINES.talk[2], 2000, 1240], [LINES.talk[3], 2850, 1240]].forEach(([t, on, y], i, a) => {
      const l = textLine(s, { top: y, size: 84, weight: W8.caption, shadow: P.css }); l.textContent = t; softFade(l, 0, on); hideAt(l, (a[i + 1] || [0, 0, 5200])[1]);
    });
  } });

// Caption placement on the real footage. Toggle "Safe zones" in the header to see Instagram's UI.
def("place", { section: "Caption placement", label: "Placement", loop: 5200, params: { top: 1240, size: 84 },
  build(s, P) { footage(s); chunks(s, timed(LINES.talk, 300, 800), { ...P, enterFx: softFade, end: 5200 }); } });

// =====================================================================================================
// ZOOMS ON THE FACE (long and smooth between cuts, a short punch now and then)
// =====================================================================================================
function talk(s) { const v = footage(s); chunks(s, timed(LINES.talk, 300, 800), { top: 1300, size: 84, enterFx: softFade, end: 5200 }); return v; }
def("zoom-long-out", { section: "Zooms on your face", label: "Cut in zoomed, slow zoom out", loop: 6500, params: { from: 1.2, dur: 3500 },
  build(s, P) {
    const z = ZOOM && ZOOM.dir === "out" ? { from: ZOOM.amount / 100, dur: ZOOM.dur, ease: ZOOM.easing } : { from: P.from, dur: P.dur, ease: SMOOTH };
    const v = footage(s);
    const b = s.el("div", { position: "absolute", inset: "0", background: C.accent, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: FONT, fontWeight: String(W8.title), fontSize: "120px", letterSpacing: "-0.04em", color: "#fff" }, null, LINES.intro[1]);
    hideAt(b, 1200);
    v.animate([{ transform: `scale(${z.from})` }, { transform: "scale(1)" }], { duration: z.dur, delay: 1200, easing: z.ease, fill: "both" });
  } });
def("zoom-quick-punch", { section: "Zooms on your face", label: "Quick clean punch-in", loop: 5200, params: { to: 1.15, dur: 750 },
  build(s, P) { const v = talk(s); v.animate([{ transform: "scale(1)" }, { transform: `scale(${P.to})` }], { duration: P.dur, delay: 1900, easing: EXPO, fill: "forwards" }); v.animate([{ transform: `scale(${P.to})` }, { transform: "scale(1)" }], { duration: 1, delay: 3400, fill: "forwards" }); } });
def("zoom-hard-punch", { section: "Zooms on your face", label: "Hard punch-in, subtle", loop: 5200, params: { to: 1.15 },
  build(s, P) { const v = talk(s); v.animate([{ transform: "scale(1)" }, { transform: `scale(${P.to})` }], { duration: 1, delay: 1900, fill: "forwards" }); v.animate([{ transform: `scale(${P.to})` }, { transform: "scale(1)" }], { duration: 1, delay: 3400, fill: "forwards" }); } });

// =====================================================================================================
// DIAGRAMS (no pop-ins: each part fades, rises or blur-rises in, lines draw on)
// =====================================================================================================
// Full-screen backgrounds behind visuals rotate between paper and the accent. Never black.
function backdrop(s, bg) { return s.el("div", { position: "absolute", inset: "0", background: bg === "accent" ? C.accent : bg === "soft" ? C.soft : C.paper }); }
def("tree", { section: "Diagrams", label: "Tree with your videos", params: { entrance: "rise", title: "my videos", bg: "accent" },
  build(s, P) {
    const k = P.entrance;
    backdrop(s, P.bg);
    const p = panel(s, { left: "60px", top: "560px", width: "960px", height: "760px", border: P.bg === "paper" ? `2px solid ${rgba(C.ink, .08)}` : "0" }); enter(p, 150, k);
    const xs = [150, 370, 590, 810];
    lines(s, p, 960, 760, ["M480 170 L480 230", ...xs.map(x => `M480 230 L${x} 230 L${x} 290`)], 700, 70);
    enter(pill(s, p, 480, 110, P.title, { background: C.accent, color: "#fff", border: "0", fontSize: "44px", padding: "20px 36px" }), 420, k);
    xs.forEach((x, i) => {
      const t = s.el("div", { position: "absolute", left: x - 95 + "px", top: "300px", width: "190px", height: "338px", borderRadius: "24px", overflow: "hidden", border: `5px solid ${C.accent}`, boxShadow: `0 8px 22px ${rgba(C.ink, .15)}` }, p);
      s.img(`assets/thumb-${i + 1}.jpg`, { width: "100%", height: "100%", objectFit: "cover", display: "block" }, t);
      enter(t, 1000 + i * 130, k);
    });
  } });
def("mindmap", { section: "Diagrams", label: "Mind map", params: { entrance: "rise", centre: "My edit style", topics: ["Fonts", "Colours", "Captions", "Motion", "Sounds"], bg: "paper" },
  build(s, P) {
    const k = P.entrance;
    backdrop(s, P.bg);
    const p = panel(s, { left: "60px", top: "610px", width: "960px", height: "700px", border: P.bg === "paper" ? `2px solid ${rgba(C.ink, .08)}` : "0" }); enter(p, 150, k);
    const pos = [[480, 110], [180, 240], [780, 240], [210, 560], [750, 560]].slice(0, P.topics.length);
    lines(s, p, 960, 700, pos.map(([x, y]) => `M480 380 L${x} ${y}`), 700);
    enter(pill(s, p, 480, 380, P.centre, { background: C.deep, color: "#fff", border: "0", fontSize: "44px", padding: "22px 38px" }), 420, k);
    P.topics.forEach((t, i) => enter(pill(s, p, pos[i][0], pos[i][1], t), 1000 + i * 120, k));
  } });
function fanOut(s, top, t0, P, onAccent) {
  const ys = [330, 455, 580, 705, 830], col = onAccent ? "#fff" : C.accent;
  diagTitle(s, top, P.tag, P.title, onAccent, t0);
  lines(s, top, 1080, 960, ys.map(y => `M290 580 C 380 580, 380 ${y}, 440 ${y}`), t0 + 900, 80, col);
  lines(s, top, 1080, 960, ys.map(y => `M640 ${y} C 700 ${y}, 700 580, 790 580`), t0 + 1800, 80, col);
  enter(node(s, top, 175, 580, { icon: icon(0), label: P.from, w: 230 }), t0 + 300);
  P.items.forEach((t, i) => enter(node(s, top, 540, ys[i], { label: t, w: 210 }), t0 + 1100 + i * 100));
  enter(node(s, top, 910, 580, { label: P.to, w: 240, dark: true }), t0 + 2200);
}
const FAN = { tag: "PARALLEL", title: "Five jobs at once", from: "Idea", items: ["Script", "Film", "Edit", "Caption", "Post"], to: "One reel" };
def("split-fanout", { section: "Split-screen diagrams", label: "Fan out and merge", loop: 6500, params: { ...FAN, bg: "accent" },
  build(s, P) { faceBottom(s); fanOut(s, topHalf(s, P.bg === "accent" ? C.accent : C.paper), 600, P, P.bg === "accent"); } });
def("split-hub", { section: "Split-screen diagrams", label: "Plugged into your apps", loop: 6500, params: { tag: "TOOLS", title: "One hub, your apps", bg: "paper" },
  build(s, P) {
    faceBottom(s);
    const onA = P.bg === "accent", top = topHalf(s, onA ? C.accent : C.paper);
    diagTitle(s, top, P.tag, P.title, onA, 250);
    const hub = ICONS[0] || {};
    enter(node(s, top, 540, 400, { icon: hub.file, label: hub.name || "Hub", w: 360 }), 600);
    const xs = [220, 540, 860];
    lines(s, top, 1080, 960, xs.map(x => `M540 465 C 540 560, ${x} 560, ${x} 640`), 1300, 120, onA ? "#fff" : C.accent);
    xs.forEach((x, i) => {
      const a = s.el("div", { position: "absolute", left: x + "px", top: "735px", transform: "translate(-50%,-50%)", textAlign: "center", fontFamily: FONT, fontSize: "30px", fontWeight: String(W8.caption), color: onA ? "#fff" : C.ink }, top);
      const ic = ICONS[(i + 1) % Math.max(ICONS.length, 1)] || {};
      s.img(ic.file, { width: "150px", height: "150px", display: "block", margin: "0 auto 6px", filter: `drop-shadow(0 12px 20px ${rgba(C.ink, .18)})` }, a);
      s.el("div", {}, a, ic.name || "");
      enter(a, 1650 + i * 220);
    });
  } });

// =====================================================================================================
// LOGOS (real app icons only, pulled from the person's own Mac)
// =====================================================================================================
const appIcon = (s, src, css) => s.img(src, { position: "absolute", width: "340px", height: "340px", filter: "drop-shadow(0 18px 30px rgba(0,0,0,.35))", ...css });
def("logos-tilt", { section: "Logos", label: "Tilted and overlapping", params: { speed: "rise", top: 230 },
  build(s, P) { footage(s); enter(appIcon(s, icon(1), { left: "455px", top: P.top + 70 + "px", transform: "rotate(7deg)", zIndex: "1" }), 520, P.speed); enter(appIcon(s, icon(0), { left: "240px", top: P.top + "px", transform: "rotate(-6deg)", zIndex: "2" }), 300, P.speed); } });
def("logos-row", { section: "Logos", label: "Row of icons rising one by one", params: { count: 3, top: 330 },
  build(s, P) {
    footage(s);
    for (let i = 0; i < P.count; i++) {
      const im = s.img(icon(i), { position: "absolute", left: 540 + (i - (P.count - 1) / 2) * 240 - 100 + "px", top: P.top + "px", width: "200px", height: "200px", transform: `rotate(${[-4, 3, -2, 5][i % 4]}deg)`, filter: "drop-shadow(0 14px 24px rgba(0,0,0,.35))" });
      enter(im, 400 + i * 200);
    }
  } });

// =====================================================================================================
// SPLIT SCREEN (a real page from the internet on top, the face below; never black behind it)
// =====================================================================================================
let SITE = { w: 1080, h: 4000, target: [40, 600, 400, 160], name: "" }, REPO = { w: 1800, h: 1500, target: [1500, 180, 260, 70] };
function cardTop(s, bg) {
  const top = topHalf(s, bg);
  const W = 960, H = Math.round(W * Math.min(REPO.h, 1500) / REPO.w), x = 60, y = Math.max(40, Math.round((960 - H) / 2));
  const card = s.el("div", { position: "absolute", left: x + "px", top: y + "px", width: W + "px", height: H + "px", borderRadius: "26px", overflow: "hidden", boxShadow: SHADOW(.28), background: "#fff" }, top);
  s.img("assets/repo.png", { width: W + "px", display: "block" }, card);
  return { c: card, W, H, x, y, k: W / REPO.w };
}
def("split-scroll", { section: "Split screen", label: "Full-width page, slow scroll", loop: 5000, params: { distance: 700 },
  build(s, P) {
    faceBottom(s);
    const top = topHalf(s, "#fff"), img = s.img("assets/site.png", { position: "absolute", left: "0", top: "0", width: "1080px" }, top);
    img.animate([{ transform: "translateY(0)" }, { transform: `translateY(-${P.distance}px)` }], { duration: 4200, delay: 500, easing: "cubic-bezier(.45,0,.35,1)", fill: "both" });
    enter(top, 100, "fade");
  } });
def("split-push", { section: "Split screen", label: "Fast push-in to the key detail", loop: 5000, params: { bg: "accent", zoom: 2.3 },
  build(s, P) {
    faceBottom(s);
    const { c, W, H, x, y, k: f } = cardTop(s, P.bg === "accent" ? C.accent : C.paper);
    c.animate([{ transform: "translateY(60px)" }, { transform: "translateY(0)" }], { duration: 400, delay: 150, easing: EXPO, fill: "backwards", composite: "add" });
    c.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 250, delay: 150, fill: "backwards" });
    const [tx0, ty0, tw, th] = REPO.target.map(n => n * f), k = P.zoom, sx = tx0 + tw / 2, sy = ty0 + th / 2;
    c.style.transformOrigin = "0 0";
    const tx = Math.min(-x, Math.max(1080 - x - k * W, 540 - x - k * sx)), ty = Math.min(-y, Math.max(960 - y - k * H, 480 - y - k * sy));
    c.animate([{ transform: "translate(0,0) scale(1)" }, { transform: `translate(${tx}px, ${ty}px) scale(${k})` }], { duration: 800, delay: 650, easing: PUNCH, fill: "both", composite: "add" });
  } });
def("split-ring", { section: "Split screen", label: "Card with a ring on the key detail", loop: 5000, params: { bg: "paper" },
  build(s, P) {
    faceBottom(s);
    const onA = P.bg === "accent", { c, k: f } = cardTop(s, onA ? C.accent : C.paper);
    enter(c, 250);
    const [a, b, w, h] = REPO.target.map(n => n * f);
    ring(s, c, a, b, w, h, 1500, onA ? C.deep : C.accent);
  } });

// Tool talk: the site on top, face below, every caption in a box right on the seam so it reads over both.
def("tool-box", { section: "Tool talk", label: "Caption box on the seam", loop: 10000, params: { box: "frosted", caps: null },
  build(s, P) {
    faceBottom(s);
    const top = topHalf(s, "#fff"), page = s.el("div", { position: "absolute", left: "0", top: "0", width: "1080px" }, top);
    s.img("assets/site.png", { width: "1080px", display: "block" }, page);
    enter(top, 100, "fade");
    const [tx, ty, tw, th] = SITE.target, scrollTo = Math.max(0, Math.min(ty - 380, SITE.h - 960));
    page.animate([{ transform: "translateY(0)" }, { transform: `translateY(-${scrollTo}px)` }], { duration: 2600, delay: 3200, easing: "cubic-bezier(.45,0,.2,1)", fill: "both" });
    ring(s, page, tx, ty, tw, th, 6600, C.deep);
    const box = P.box === "frosted"
      ? { background: rgba(C.accent, .62), backdropFilter: "blur(20px) saturate(1.4)", webkitBackdropFilter: "blur(20px) saturate(1.4)", color: "#fff", border: "1.5px solid rgba(255,255,255,.35)", textShadow: `0 2px 10px ${rgba(C.ink, .25)}` }
      : { background: C.accent, color: "#fff", boxShadow: `0 12px 30px ${rgba(C.ink, .22)}`, textShadow: `0 2px 8px ${rgba(C.ink, .2)}` };
    const caps = P.caps || [`this is ${SITE.name || "the site"}`, "it does one thing", "really, really well", "and it's free", "go try it"];
    caps.forEach((text, i) => {
      const on = 300 + i * 1900, off = i < caps.length - 1 ? on + 1900 : 10000;
      const c = s.el("div", { position: "absolute", left: "50%", top: "960px", transform: "translate(-50%,-50%)", whiteSpace: "nowrap", fontFamily: FONT, fontWeight: String(W8.caption), fontSize: "70px", letterSpacing: "-0.02em", lineHeight: "1", padding: "22px 34px", borderRadius: "24px", ...box }, null, text);
      c.animate([{ opacity: 0, transform: "translate(-50%, calc(-50% + 14px))" }, { opacity: 1, transform: "translate(-50%,-50%)" }], { duration: 260, delay: on, easing: EXPO, fill: "backwards" });
      hideAt(c, off);
    });
  } });

// =====================================================================================================
// MODE SWITCHING: face -> split (diagram on top) -> full-screen diagram -> face
// =====================================================================================================
function holdFrames(prop, values, times, total, ease) {
  const f = [{ [prop]: values[0], offset: 0 }];
  times.forEach((t, i) => { const e = Array.isArray(ease) ? ease[i] : ease; f.push({ [prop]: values[i], offset: t / total }); f.push({ [prop]: values[i + 1], offset: Math.min(1, (t + e) / total) }); });
  f.push({ [prop]: values[values.length - 1], offset: 1 });
  return f;
}
def("modes", { section: "Switching modes", label: "Hard cuts, one slide into full screen", loop: 10000, params: { slide: true },
  build(s, P) {
    const T = 10000, AT = [2600, 5600, 8600], ease = P.slide ? [1, 650, 1] : 1, sub = P.slide ? GLIDE : "linear", o = { duration: T, fill: "both", easing: "linear" };
    const v = s.video("assets/face-loop.mp4", { position: "absolute", left: "0", width: "1080px", objectFit: "cover", objectPosition: "50% 30%" });
    v.animate(holdFrames("top", ["0px", "960px", "1920px", "0px"], AT, T, ease).map(f => ({ ...f, easing: sub })), o);
    v.animate(holdFrames("height", ["1920px", "960px", "960px", "1920px"], AT, T, ease).map(f => ({ ...f, easing: sub })), o);
    const pan = s.el("div", { position: "absolute", left: "0", top: "0", width: "1080px", background: C.accent, overflow: "hidden" });
    pan.animate(holdFrames("height", ["0px", "960px", "1920px", "0px"], AT, T, ease).map(f => ({ ...f, easing: sub })), o);
    const split = s.el("div", { position: "absolute", left: "0", top: "0", width: "1080px", height: "960px" }, pan);
    fanOut(s, split, AT[0], FAN, true);
    split.animate([{ opacity: 1 }, { opacity: 0 }], { duration: P.slide ? 250 : 1, delay: AT[1], fill: "forwards" });
    const full = s.el("div", { position: "absolute", left: "0", top: "0", width: "1080px", height: "1920px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "40px", fontFamily: FONT, color: "#fff" }, pan);
    const big = s.el("div", { fontSize: "150px", fontWeight: String(W8.title), letterSpacing: "-0.045em" }, full, FAN.to);
    const row = s.el("div", { display: "flex", gap: "30px" }, full);
    enter(big, AT[1] + 350);
    ICONS.slice(0, 3).forEach((ic, i) => enter(s.img(ic.file, { width: "190px", height: "190px", transform: `rotate(${[-5, 3, -2][i]}deg)`, filter: "drop-shadow(0 14px 24px rgba(0,0,0,.25))" }, row), AT[1] + 700 + i * 180));
    [[LINES.talk[0], 300, 1400], [LINES.talk[1], 1400, AT[0]], [LINES.talk[3], AT[2] + 300, T]].forEach(([t, on, off]) => {
      const l = textLine(s, { top: 1300, size: 84, weight: W8.caption }); l.textContent = t; softFade(l, 0, on); hideAt(l, off);
    });
  } });
