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
// zooms on faces long and smooth, intro text never cramped, captions inside Instagram's safe zone (text stays
// out of the top 220px and the bottom 420px). Photos, thumbnails and screenshots used as photos always have
// square corners and never zoom or push in (cards for a website or screen may be rounded).

let C = {}, FONT = "", W8 = { title: 700, caption: 600, label: 500 }, CAP_SHADOW = "0 4px 24px rgba(0,0,0,.45)";
let ICONS = [], SHINE = null, ZOOM = null, LINES = {}, TEXT_FADE = null;
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
  const bl = b.lines || {};
  LINES = { ...DEFAULT_LINES, ...bl };
  // The newer sections reuse the person's own intro words unless they gave lines for them.
  if (!bl.stack && bl.intro) LINES.stack = [bl.intro[0], `${bl.intro[1]} ${bl.intro[2] || ""}`.trim()];
  if (!bl.word && bl.intro) LINES.word = bl.intro[1];
  if (extra.site) SITE = { ...SITE, ...extra.site };
  if (extra.repo) REPO = { ...REPO, ...extra.repo };
  if (extra.text_fade) TEXT_FADE = extra.text_fade;
}
const DEFAULT_LINES = {
  captions: ["here's the thing", "most people", "get this wrong"],
  accent: "Make it look easy",
  intro: ["The simplest way to", "edit", "your videos"],
  talk: ["most people", "get this", "completely wrong", "here's why"],   // the 3rd chunk is where zooms land
  // used by the sections added later (text behind your head, white-and-accent headlines, clean explainers, fades)
  headline: ["Do this", "first"],                   // big headline behind your head: small line, then a huge one
  word: "edit",                                     // the one huge word behind your head (short, under ~8 letters)
  stack: ["The simplest way to", "edit your videos"],   // white lines on top, the last line in your accent
  title: ["The Big", "Idea"],                       // 2-line titles: text fades and the explainers
  hook: ["Meet", "your new favourite tool"],        // wraps round the name of your first app
};
const rgba = (hex, a) => { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };
const icon = (i) => (ICONS[i % Math.max(ICONS.length, 1)] || {}).file;

// ---- easing (measured off Apple-style After Effects text, frame by frame)
const EXPO = "cubic-bezier(.16,1,.3,1)";       // fast, then a long soft settle
const GLIDE = "cubic-bezier(.19,1,.22,1)";
const SMOOTH = "cubic-bezier(.65,0,.35,1)";    // slow at both ends
const PUNCH = "cubic-bezier(.7,0,.15,1)";      // quick in, firm landing

// ---- small helpers
function footage(s, css = {}, parent) {   // the creator's own talking-head clip
  return s.video("assets/face-loop.mp4", { position: "absolute", left: "0", top: "0", width: "1080px", height: "1920px", objectFit: "cover", objectPosition: "50% 30%", transformOrigin: "50% 32%", ...css }, parent);
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
      const t = s.el("div", { position: "absolute", left: x - 95 + "px", top: "300px", width: "190px", height: "338px", borderRadius: "0", overflow: "hidden", border: `5px solid ${C.accent}`, boxShadow: `0 8px 22px ${rgba(C.ink, .15)}` }, p);
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

// =====================================================================================================
// NEWER SECTIONS, SHARED PIECES
// Colour maths, optional assets (cut-out, photos, folder, locked text fade), text fitting, the motions
// of the clean explainers (ghost words, tiles that settle, a camera that glides), scenes, diamonds, cubes.
// =====================================================================================================
const hexRgb = (h) => { h = String(h || "#000000").replace("#", ""); if (h.length === 3) h = [...h].map(c => c + c).join(""); const n = parseInt(h, 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
function mixHex(a, b, t) { const x = hexRgb(a), y = hexRgb(b); return "#" + x.map((v, i) => Math.round(v * t + y[i] * (1 - t)).toString(16).padStart(2, "0")).join(""); }   // t of a, the rest of b
function lumOf(h) { const [r, g, b] = hexRgb(h).map(v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }); return .2126 * r + .7152 * g + .0722 * b; }
const onAccent = () => (lumOf(C.accent) > .45 ? C.ink : "#fff");   // readable text on their accent colour
const sceneBg = (k = "tint") => (k === "paper" ? C.paper : k === "soft" ? mixHex(C.soft, C.paper, .4) : mixHex(C.paper, C.ink, .93));   // their paper, or a very light tint of it. Never black.
const darkFill = () => mixHex(C.ink, C.accent, .86);   // dark cards: their ink with a breath of accent

// Text that has to fit: measures with their real font and shrinks the size until the widest line fits.
let _measure;
function textWidth(text, size, weight) { _measure = _measure || document.createElement("canvas").getContext("2d"); _measure.font = `${weight} ${size}px ${FONT}`; return _measure.measureText(text).width; }
function fitSize(text, size, { maxW = 940, weight = W8.title, ls = -0.035 } = {}) {
  const list = (Array.isArray(text) ? text : [text]).filter(Boolean);
  if (!list.length) return size;
  const w = Math.max(...list.map(t => textWidth(t, size, weight) + t.length * ls * size));
  return w > maxW ? Math.floor(size * maxW / w) : size;
}

// Optional assets other scripts make (cut-out video, folder picture, photos). Checked once per page load, so a
// missing one never breaks an option: it shows a neutral stand-in and a small label instead.
const ASSET = {};   // undefined while still asking, then true (it's there) or false
let PHOTOS = [];    // paths of their photos; assets/photos/photos.json lists the file names
const IS_SAFARI = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
const cutoutSrc = () => (IS_SAFARI ? "assets/face-cutout.mov" : "assets/face-cutout.webm");   // Chrome shows see-through video as WebM, Safari as HEVC .mov
function checkAssets() {
  const ask = (key, url) => fetch("/api/has?f=" + encodeURIComponent(url), { cache: "no-store" }).then(r => r.json()).then(j => { ASSET[key] = !!j.exists; }, () => { ASSET[key] = false; });
  ask("cutout", cutoutSrc()); ask("folder", "assets/folder.png");
  fetch("assets/photos/photos.json", { cache: "no-store" }).then(r => (r.ok ? r.json() : [])).then(list => {
    PHOTOS = (Array.isArray(list) ? list : []).map(f => (typeof f === "string" ? f : (f && (f.file || f.name)) || "")).filter(Boolean).map(f => (f.includes("/") ? f : "assets/photos/" + f));
  }).catch(() => {});
  // the text fade they locked in the Text lab (the server answers "null" until something is locked)
  fetch("/locked/text_fade.json", { cache: "no-store" }).then(r => (r.ok ? r.json() : null)).then(j => { if (j && j.background_image) TEXT_FADE = j; }).catch(() => {});
}
const photoAt = (i) => (PHOTOS.length ? PHOTOS[i % PHOTOS.length] : null);
function notice(s, text, top = 1330) {   // a small honest label for a piece that isn't made yet
  return s.el("div", { position: "absolute", left: "50%", top: top + "px", transform: "translateX(-50%)", zIndex: "50", fontFamily: FONT, fontWeight: String(W8.label), fontSize: "30px", color: C.ink,
    background: "rgba(255,255,255,.9)", padding: "10px 22px", borderRadius: "999px", whiteSpace: "nowrap", boxShadow: `0 6px 18px ${rgba(C.ink, .18)}` }, null, text);
}
// A real photo cropped to its box: square corners, always, and it never zooms. No photo yet = a neutral box saying so.
function photoBox(s, parent, src, css = {}, pos = "50% 50%", slot = 0, labelSize = 34) {
  const box = s.el("div", { position: "absolute", overflow: "hidden", ...css, borderRadius: "0" }, parent);
  if (src) { s.img(src, { width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, display: "block" }, box); return box; }
  box.style.background = [C.soft, mixHex(C.soft, C.paper, .55), mixHex(C.soft, C.accent, .6), mixHex(C.soft, C.ink, .85)][slot % 4];
  s.el("div", { position: "absolute", inset: "0", display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 6%", fontFamily: FONT, fontWeight: String(W8.label), fontSize: labelSize + "px", color: rgba(C.ink, .55), lineHeight: "1.15" }, box, "your photos go here");
  return box;
}

// ---- motions of the clean explainers (all calm: no pop-ins, no overshoot)
function cutWindow(el, a, b, T) {   // hard cut in at a, hard cut out at b (ms on a T-long loop). These scenes cut, they never fade.
  const k = [{ opacity: a > 0 ? 0 : 1, offset: 0 }];
  if (a > 0) k.push({ opacity: 0, offset: a / T }, { opacity: 1, offset: a / T });
  if (b < T) k.push({ opacity: 1, offset: b / T }, { opacity: 0, offset: b / T });
  k.push({ opacity: b < T ? 0 : 1, offset: 1 });
  el.animate(k, { duration: T, fill: "both" });
}
function camera(el, T, moves, ease = SMOOTH) {   // the "camera": the whole group glides to a new framing as new pieces arrive, then holds. moves: [[at, dur, "translate(..) scale(..)"]]
  let cur = "translate(0px,0px) scale(1)";
  const k = [{ transform: cur, offset: 0 }];
  moves.forEach(([at, dur, to]) => { k.push({ transform: cur, offset: at / T, easing: ease }, { transform: to, offset: Math.min(1, (at + dur) / T) }); cur = to; });
  k.push({ transform: cur, offset: 1 });
  el.animate(k, { duration: T, fill: "both" });
}
function ghost(el, delay, dur = 380) {   // a word appears faint and soft right where it sits, then firms up. No movement.
  el.animate([{ opacity: 0, filter: "blur(6px)" }, { opacity: .3, filter: "blur(3px)", offset: .2 }, { opacity: 1, filter: "blur(0px)" }], { duration: dur, delay, easing: "ease-out", fill: "backwards" });
}
function tileIn(el, delay, from = 1.08, dur = 520) {   // tiles and cards come out of a soft blur while settling from slightly big. No overshoot. Not for photos.
  el.animate([{ transform: `scale(${from})` }, { transform: "scale(1)" }], { duration: dur, delay, easing: EXPO, fill: "backwards", composite: "add" });
  el.animate([{ opacity: 0, filter: "blur(16px)" }, { opacity: 1, filter: "blur(0px)" }], { duration: dur, delay, easing: EXPO, fill: "backwards" });
}
function slideIn(el, delay, x, y, dur = 560) {
  el.animate([{ transform: `translate(${x}px,${y}px)` }, { transform: "translate(0px,0px)" }], { duration: dur, delay, easing: EXPO, fill: "backwards", composite: "add" });
  el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: dur * .6, delay, easing: "ease-out", fill: "backwards" });
}
function floatIdle(el, delay, amp = 10, dur = 3200) {   // finished pieces float gently instead of freezing
  el.animate([{ transform: "translateY(0)" }, { transform: `translateY(-${amp}px)` }], { duration: dur, delay, iterations: Infinity, direction: "alternate", easing: "ease-in-out", composite: "add" });
}
function fadeFill(el, from, to, start = 52) {   // solid colour at the top of each line, melting into `to` at the bottom
  Object.assign(el.style, { display: "inline-block", backgroundImage: `linear-gradient(180deg, ${from} 0%, ${from} ${start}%, ${to} 100%)`, webkitBackgroundClip: "text", backgroundClip: "text", color: "transparent", paddingBottom: "0.06em", textShadow: "none" });
  return el;
}
function wordsRise(s, parent, text, at, gap, kind = "clean") {   // words rise one after another (cleaner than whole lines)
  words(s, parent, text).forEach((w, i) => (kind === "blur" ? blurRise : cleanRise)(w, at + i * (gap || (kind === "blur" ? 170 : 230))));
}
function evenCaps(list, a, b) {   // spread caption chunks over [a, b]; longer chunks stay up longer
  const w = list.map(t => Math.max(8, t.length)), sum = w.reduce((x, y) => x + y, 0);
  let t = a;
  return list.map((txt, i) => { const on = t; t += (b - a) * w[i] / sum; return [txt, Math.round(on), i === list.length - 1 ? b : Math.round(t)]; });
}

// ---- text behind your head: the footage, then the text, then the person cut out of the same footage on top
function cutout(s, bg) {
  if (ASSET.cutout === false) { notice(s, "cut-out not made yet"); return null; }
  const v = s.video(cutoutSrc(), { position: "absolute", left: "0", top: "0", width: "1080px", height: "1920px", objectFit: "cover", objectPosition: "50% 30%" });
  v.addEventListener("error", () => { if (!v.isConnected) return; v.remove(); notice(s, "cut-out not made yet"); }, { once: true });
  (function sync() {   // keep the cut-out locked to the footage underneath
    if (!v.isConnected) return;
    // only nudge when it has really drifted, and never while it's still catching up (that would stall it)
    if (bg && !v.seeking && v.readyState >= 2 && Math.abs(v.currentTime - bg.currentTime) > 0.12) v.currentTime = bg.currentTime;
    requestAnimationFrame(sync);
  })();
  return v;
}
function behindHead(s, drawText) { const bg = footage(s); drawText(bg); cutout(s, bg); }
// lines: [[text, size, colour], ...]. Each line comes in on its own (blur rise or clean rise), one after another.
function headline(s, lns, { top = 260, rise = "blur", parent = null, gap = 0 } = {}) {
  const box = s.el("div", { position: "absolute", left: "0", right: "0", top: top + "px", textAlign: "center", fontFamily: FONT, fontWeight: String(W8.title), lineHeight: "0.98", textShadow: CAP_SHADOW }, parent);
  lns.forEach(([text, size, colour], i) => {   // letter-spacing goes on each line, so it scales with that line's size
    const l = s.el("div", { fontSize: fitSize(text, size) + "px", letterSpacing: "-0.035em", color: colour, marginTop: i ? gap + "px" : "0", whiteSpace: "nowrap" }, box, text);
    (rise === "clean" ? cleanRise : blurRise)(l, 300 + i * 260);
  });
  return box;
}

// ---- clean explainers: scenes, titles, diamond tiles, wires, pills, cubes, files, folders
function fullScene(s, T, a, b, bg) {
  const sc = s.el("div", { position: "absolute", left: "0", top: "0", width: "1080px", height: "1920px", background: bg, overflow: "hidden" });
  cutWindow(sc, a, b, T);
  return sc;
}
function splitScene(s, T, a, b, bg, face = true) {   // graphic on top, the person below. Returns the top half to draw in. face:false when one shared face runs underneath.
  const sc = s.el("div", { position: "absolute", left: "0", top: "0", width: "1080px", height: "1920px", overflow: "hidden" });
  cutWindow(sc, a, b, T);
  const top = s.el("div", { position: "absolute", left: "0", top: "0", width: "1080px", height: "960px", background: bg, overflow: "hidden" }, sc);
  if (face) footage(s, { top: "960px", height: "960px" }, sc);
  return top;
}
function camLayer(s, parent, origin = "540px 960px") { return s.el("div", { position: "absolute", left: "0", top: "0", width: "1080px", height: "1920px", transformOrigin: origin }, parent); }
// Big title: every word ghosts in one after another; solid ink on top, melting to faint at the bottom of each line.
function ghostTitle(s, parent, lns, top, size, at, gap = 330) {
  const sz = fitSize(lns, size, { ls: -0.045 }), t = s.el("div", { position: "absolute", left: "0", right: "0", top: top + "px", textAlign: "center", fontFamily: FONT, fontWeight: String(W8.title), fontSize: sz + "px", letterSpacing: "-0.045em", lineHeight: ".86", whiteSpace: "nowrap" }, parent);
  let n = 0;
  lns.forEach(l => {
    const row = s.el("div", {}, t);
    l.split(" ").forEach((w, i, all) => {
      const sp = fadeFill(s.el("span", {}, row, w), C.ink, rgba(C.ink, .28), 46);
      if (i < all.length - 1) sp.style.marginRight = ".2em";
      ghost(sp, at + n++ * gap);
    });
  });
  return t;
}
function glyphSvg(name) {   // flat icons drawn in their ink, for the diamond tiles
  const k = C.ink, v = (d) => `<svg viewBox="0 0 48 48" width="100%" height="100%">${d}</svg>`;
  return ({
    book: v(`<path d="M6 12c6-2.6 12-2.6 17 .6V38c-5-3.2-11-3.2-17-.6z M42 12c-6-2.6-12-2.6-17 .6V38c5-3.2 11-3.2 17-.6z" fill="${k}"/>`),
    brain: v(`<path d="M21 5C12.5 5 6 11.2 6 19.4c0 4.9 2.2 8.6 5 11.3V43h16v-6h4.5c2.2 0 3.6-1.4 3.6-3.6v-4.7l3.6-1.2c1.2-.4 1.6-1.6.9-2.6L36 19.1C35.6 11 29.3 5 21 5z" fill="${k}"/><path d="M21.5 13v14M17 19.5c2 0 4.5 1 4.5 3M26 16.5c-1.6 1-4.5 1.1-4.5 3.5" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/>`),
    spark: v(`<path d="M24 3C26 17 31 22 45 24 31 26 26 31 24 45 22 31 17 26 3 24 17 22 22 17 24 3z" fill="${k}"/>`),
    target: v(`<circle cx="24" cy="24" r="18" fill="none" stroke="${k}" stroke-width="5"/><circle cx="24" cy="24" r="9" fill="none" stroke="${k}" stroke-width="5"/><circle cx="24" cy="24" r="2.8" fill="${k}"/>`),
    bolt: v(`<path d="M28 3L10 27h12l-3 18 19-25H26z" fill="${k}"/>`),
    chat: v(`<path d="M9 9h30a5 5 0 0 1 5 5v16a5 5 0 0 1-5 5H21l-9 8v-8H9a5 5 0 0 1-5-5V14a5 5 0 0 1 5-5z" fill="${k}"/>`),
  })[name] || glyphSvg("spark");
}
// Flat isometric diamond tile in their accent with an upright ink icon on top (the signature piece of these explainers)
function diamond(s, parent, cx, cy, w, glyph = "spark") {
  const h = w * .6, id = "dg" + Math.random().toString(36).slice(2, 7), A = C.accent, side = mixHex(A, C.ink, .8);
  const d = s.el("div", { position: "absolute", left: cx - w / 2 + "px", top: cy - h / 2 + "px", width: w + "px", height: h + "px", filter: `drop-shadow(0 14px 18px ${rgba(C.ink, .16)})` }, parent);
  d.innerHTML = `<svg viewBox="0 0 200 120" width="100%" height="100%"><defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${mixHex(A, "#ffffff", .45)}"/><stop offset="1" stop-color="${A}"/></linearGradient></defs>
    <path d="M8 58 L100 108 L192 58 L192 68 L100 118 L8 68Z" fill="${side}" stroke="${side}" stroke-width="6" stroke-linejoin="round"/>
    <path d="M100 8 L192 58 L100 108 L8 58Z" fill="url(#${id})" stroke="url(#${id})" stroke-width="10" stroke-linejoin="round"/>
    <path d="M14 56 L100 10 L186 56" fill="none" stroke="rgba(255,255,255,.6)" stroke-width="2" stroke-linejoin="round"/></svg>`;
  s.el("div", { position: "absolute", left: "50%", top: "44%", width: h * .6 + "px", height: h * .6 + "px", transform: "translate(-50%,-50%)" }, d).innerHTML = glyphSvg(glyph);
  return d;
}
// A real app icon as it is (it already has its own shape), or with a white bezel round it (bezel:true) for flat logos
function appTile(s, parent, cx, cy, size, src, { bezel = false, pad = .2 } = {}) {
  const box = s.el("div", { position: "absolute", left: cx - size / 2 + "px", top: cy - size / 2 + "px", width: size + "px", height: size + "px" }, parent);
  if (!bezel) { s.img(src, { width: "100%", height: "100%", objectFit: "contain", filter: `drop-shadow(0 ${size * .09}px ${size * .16}px ${rgba(C.ink, .26)})` }, box); return box; }
  Object.assign(box.style, { borderRadius: size * .22 + "px", background: "#fff", boxShadow: `inset 0 0 0 ${size * .025}px ${rgba(C.ink, .1)}, 0 ${size * .09}px ${size * .2}px ${rgba(C.ink, .22)}`, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" });
  s.img(src, { width: (1 - 2 * pad) * 100 + "%", height: (1 - 2 * pad) * 100 + "%", objectFit: "contain" }, box);
  return box;
}
function wires(s, parent, paths, start, gap = 0, colour = rgba(C.ink, .28), width = 3) {   // thin lines that draw on
  const box = s.el("div", { position: "absolute", left: "0", top: "0", width: "1080px", height: "1920px" }, parent);
  box.innerHTML = `<svg width="1080" height="1920" viewBox="0 0 1080 1920" fill="none">${paths.map(d => `<path d="${d}" pathLength="1" stroke="${colour}" stroke-width="${width}" stroke-linecap="round" stroke-dasharray="1" stroke-dashoffset="1"/>`).join("")}</svg>`;
  box.querySelectorAll("path").forEach((p, i) => p.animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], { duration: 380, delay: start + i * gap, easing: EXPO, fill: "both" }));
  return box;
}
function darkPill(s, parent, cx, cy, w, h, css = {}) {   // dark rounded pill that holds an icon and a few words
  return s.el("div", { position: "absolute", left: cx - w / 2 + "px", top: cy - h / 2 + "px", width: w + "px", height: h + "px", boxSizing: "border-box", borderRadius: "16px", background: darkFill(), boxShadow: `0 12px 22px ${rgba(C.ink, .18)}`,
    display: "flex", alignItems: "center", gap: "14px", padding: "0 16px", fontFamily: FONT, fontWeight: String(W8.caption), fontSize: "26px", color: "#fff", whiteSpace: "nowrap", ...css }, parent);
}
function tagLabel(s, parent, cx, cy, text) {   // small label in the accent that drops in over a group
  return s.el("div", { position: "absolute", left: cx + "px", top: cy + "px", transform: "translate(-50%,-50%)", fontFamily: FONT, fontWeight: String(W8.title), fontSize: "30px", color: onAccent(), background: C.accent, padding: "8px 18px", borderRadius: "10px", whiteSpace: "nowrap", boxShadow: `0 8px 16px ${rgba(C.ink, .14)}` }, parent, text);
}
function capPill(s, parent, top, list, size = 50) {   // caption pill in their accent, swaps chunk by chunk with the soft fade-up. list: [[text, on, off], ...]
  list.forEach(([text, on, off]) => {
    const c = s.el("div", { position: "absolute", left: "50%", top: top + "px", transform: "translate(-50%,-50%)", whiteSpace: "nowrap", fontFamily: FONT, fontWeight: String(W8.caption), fontSize: size + "px", letterSpacing: "-0.02em",
      color: onAccent(), background: C.accent, padding: "14px 28px", borderRadius: "18px", boxShadow: `inset 0 0 0 1.5px rgba(255,255,255,.3), 0 10px 24px ${rgba(C.ink, .16)}` }, parent, text);
    c.animate([{ opacity: 0, transform: "translate(-50%, calc(-50% + 14px))" }, { opacity: 1, transform: "translate(-50%,-50%)" }], { duration: 260, delay: on, easing: EXPO, fill: "backwards" });
    hideAt(c, off);
  });
}
function fileDoc(s, parent, x, y, w = 92, css = {}, label = "Notes") {   // a paper file icon with a label
  const d = s.el("div", { position: "absolute", left: x + "px", top: y + "px", width: w + "px", height: w * 1.25 + "px", filter: `drop-shadow(0 6px 10px ${rgba(C.ink, .12)})`, ...css }, parent);
  const edge = mixHex(C.paper, C.ink, .82);
  d.innerHTML = `<svg viewBox="0 0 92 115" width="100%" height="100%"><path d="M8 3h52l29 29v74a6 6 0 0 1-6 6H8a6 6 0 0 1-6-6V9a6 6 0 0 1 6-6z" fill="#fff" stroke="${edge}" stroke-width="2.5"/><path d="M60 3v23a6 6 0 0 0 6 6h23" fill="${mixHex(C.paper, C.ink, .94)}" stroke="${edge}" stroke-width="2.5" stroke-linejoin="round"/></svg>`;
  s.el("div", { position: "absolute", left: "0", right: "0", top: "62%", textAlign: "center", fontFamily: FONT, fontWeight: String(W8.caption), fontSize: w * .15 + "px", color: rgba(C.ink, .5) }, d, label);
  return d;
}
// A Mac folder (assets/folder.png). If that picture isn't there yet, a simple drawn folder stands in. box.flash is the red overlay.
function folderArt(s, parent, size) {
  const box = s.el("div", { position: "absolute", width: size + "px", height: size + "px" }, parent), RED = "#E5484D";
  const svg = (back, front) => `<svg viewBox="0 0 300 300" width="100%" height="100%"><path d="M24 78a16 16 0 0 1 16-16h66a16 16 0 0 1 11 4.5l15 15.5h128a16 16 0 0 1 16 16v118a16 16 0 0 1-16 16H40a16 16 0 0 1-16-16z" fill="${back}"/><path d="M24 108a16 16 0 0 1 16-16h220a16 16 0 0 1 16 16v110a16 16 0 0 1-16 16H40a16 16 0 0 1-16-16z" fill="${front}"/></svg>`;
  const flash = box.flash = s.el("div", { position: "absolute", inset: "0" }, box);
  const drawn = () => { box.querySelector("img")?.remove(); box.insertAdjacentHTML("afterbegin", `<div style="position:absolute;inset:0;filter:drop-shadow(0 14px 18px ${rgba(C.ink, .16)})">${svg(mixHex(C.accent, C.ink, .8), mixHex(C.accent, "#ffffff", .8))}</div>`); Object.assign(flash.style, { background: "none", webkitMaskImage: "none", maskImage: "none" }); flash.innerHTML = svg(RED, RED); };
  if (ASSET.folder === false) { drawn(); return box; }
  const im = s.img("assets/folder.png", { position: "absolute", left: "0", top: "0", width: "100%", height: "100%", filter: `drop-shadow(0 14px 18px ${rgba(C.ink, .16)})` });
  box.insertBefore(im, flash);
  Object.assign(flash.style, { background: RED, webkitMaskImage: "url(assets/folder.png)", maskImage: "url(assets/folder.png)", webkitMaskSize: "100% 100%", maskSize: "100% 100%" });
  im.addEventListener("error", () => { if (box.isConnected) drawn(); }, { once: true });
  return box;
}
// Isometric cube whose three faces light up one at a time ("there are 3 layers"), with a glow on the bright moment
function layerCube(s, parent, cx, cy, size, at) {
  const id = "lc" + Math.random().toString(36).slice(2, 7), A = C.accent, W = "#ffffff";
  const wrap = s.el("div", { position: "absolute", left: cx - size / 2 + "px", top: cy - size / 2 + "px", width: size + "px", height: size * 1.18 + "px" }, parent);
  const floor = s.el("div", { position: "absolute", left: "18%", width: "64%", top: size * 1.02 + "px", height: size * .12 + "px", borderRadius: "50%", background: `radial-gradient(ellipse, ${rgba(C.ink, .22)}, ${rgba(C.ink, 0)} 70%)` }, wrap);
  const c = s.el("div", { position: "absolute", left: "0", top: "0", width: size + "px", height: size + "px" }, wrap);
  const F = { left: "10,30 50,52 50,96 10,74", top: "50,8 90,30 50,52 10,30", right: "90,30 50,52 50,96 90,74" };
  c.innerHTML = `<svg viewBox="0 0 100 100" width="100%" height="100%" style="overflow:visible"><defs>
    <linearGradient id="${id}t" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${mixHex(A, W, .35)}"/><stop offset="1" stop-color="${mixHex(A, W, .55)}"/></linearGradient>
    <linearGradient id="${id}l" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${mixHex(A, W, .82)}"/><stop offset="1" stop-color="${mixHex(A, C.ink, .93)}"/></linearGradient>
    <linearGradient id="${id}r" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${mixHex(A, C.ink, .84)}"/><stop offset="1" stop-color="${mixHex(A, C.ink, .7)}"/></linearGradient></defs>
    <polygon points="${F.top}" fill="url(#${id}t)"/><polygon points="${F.left}" fill="url(#${id}l)"/><polygon points="${F.right}" fill="url(#${id}r)"/>
    ${["left", "top", "right"].map(f => `<polygon class="hl-${f}" points="${F[f]}" fill="${C.deep}" opacity="0"/>`).join("")}
    <polyline points="10,30 50,52 90,30" fill="none" stroke="rgba(255,255,255,.75)" stroke-width="0.9"/><line x1="50" y1="52" x2="50" y2="96" stroke="rgba(255,255,255,.4)" stroke-width="0.8"/></svg>`;
  // one face at a time: left, top (the brightest moment, with the glow), right, then back to plain
  [["left", 0, 330], ["top", 330, 720], ["right", 720, 1080]].forEach(([f, a, b]) => {
    c.querySelector(".hl-" + f).animate([{ opacity: 0 }, { opacity: .92, offset: .2 }, { opacity: .92, offset: .8 }, { opacity: 0 }], { duration: b - a + 90, delay: at + a, easing: "ease-in-out", fill: "both" });
  });
  const glow = `drop-shadow(0 0 26px ${rgba(A, .95)})`, none = `drop-shadow(0 0 0 ${rgba(A, 0)})`;
  c.animate([{ filter: none }, { filter: glow, offset: .25 }, { filter: glow, offset: .7 }, { filter: none }], { duration: 1200, delay: at, easing: "ease-in-out", fill: "both" });
  c.float = (delay) => { floatIdle(c, delay, 12, 2600); floor.animate([{ transform: "scale(1)", opacity: 1 }, { transform: "scale(.88)", opacity: .75 }], { duration: 2600, delay, iterations: Infinity, direction: "alternate", easing: "ease-in-out" }); };
  return { wrap, c };
}

// =====================================================================================================
// TEXT BEHIND YOUR HEAD
// Layers: their footage, then the text, then the person cut out of the same footage on top
// (assets/face-cutout.webm for Chrome, face-cutout.mov for Safari, lined up with assets/face-loop.mp4).
// No cut-out file yet = the text sits over the face and a small label says so.
// =====================================================================================================
const up = (t, on) => (on ? String(t).toUpperCase() : String(t));
def("behind-headline", { section: "Text behind your head", label: "Big headline behind your head", loop: 5200, params: { top: 260, caps: true, lines: null },
  build(s, P) {
    const L = P.lines || LINES.headline;
    behindHead(s, () => headline(s, [[up(L[0], P.caps), 150, C.text], [up(L[1] || "", P.caps), 250, C.accent]], { top: P.top }));
  } });
def("behind-word", { section: "Text behind your head", label: "One huge word behind your head", loop: 5200, params: { top: 300, size: 250, caps: true, word: null },
  build(s, P) { behindHead(s, () => headline(s, [[up(P.word || LINES.word, P.caps), P.size, C.text]], { top: P.top })); } });
def("behind-stack", { section: "Text behind your head", label: "White on top, accent underneath, behind your head", loop: 5200, params: { top: 280, rise: "blur", lines: null },
  build(s, P) {
    const L = P.lines || LINES.stack;
    behindHead(s, () => headline(s, L.map((t, i) => (i < L.length - 1 ? [t, 96, C.text] : [t, 140, C.accent])), { top: P.top, gap: 8, rise: P.rise }));
  } });
def("behind-site", { section: "Text behind your head", label: "Your website behind your head", loop: 5200, params: { top: 250, shot: "site" },
  build(s, P) {
    behindHead(s, () => {
      const card = s.el("div", { position: "absolute", left: "70px", top: P.top + "px", width: "940px", height: "740px", borderRadius: "30px", overflow: "hidden", boxShadow: "0 30px 70px rgba(0,0,0,.35)", background: "#fff" });
      s.img(P.shot === "repo" ? "assets/repo.png" : "assets/site.png", { width: "100%", height: "100%", objectFit: "cover", objectPosition: "top", display: "block" }, card);
      enter(card, 300, "rise");
    });
  } });
// The hook: a small line, the name of their first app huge in the accent, a small line; the real app icon sits in front of everything.
def("hook-behind-head", { section: "Text behind your head", label: "Hook: title behind your head with your real app icon", loop: 6000, params: { top: 250, name: null, hook: null },
  build(s, P) {
    const H = P.hook || LINES.hook, name = P.name || (ICONS[0] || {}).name || LINES.word;
    behindHead(s, () => headline(s, [[H[0], 70, C.text], [name, 270, C.accent], [H[1] || "", 64, C.text]], { top: P.top, gap: 4 }));
    if (!icon(0)) return;
    const shadow = "drop-shadow(0 18px 30px rgba(0,0,0,.35))";
    const im = s.img(icon(0), { position: "absolute", left: "70px", top: "900px", width: "230px", height: "230px", transform: "rotate(-8deg)", filter: shadow });
    // settles from a steeper tilt while it comes out of a blur, then floats
    im.animate([{ transform: "translateY(50px) rotate(-10deg)" }, { transform: "translateY(0) rotate(0deg)" }], { duration: 700, delay: 1100, easing: EXPO, fill: "backwards", composite: "add" });
    im.animate([{ opacity: 0, filter: `blur(14px) ${shadow}` }, { opacity: 1, filter: `blur(0px) ${shadow}` }], { duration: 700, delay: 1100, easing: EXPO, fill: "backwards" });
    floatIdle(im, 1800, 10, 2400);
  } });

// =====================================================================================================
// HEADLINE: WHITE ON TOP, ACCENT UNDERNEATH (no box; the locked caption shadow keeps it readable)
// rise "blur" or "clean"; three:true = the intro words as small white / big white / accent
// =====================================================================================================
def("headline-stack", { section: "Headline: white on top, accent underneath", label: "Two lines, accent line bigger", loop: 5200, params: { rise: "blur", three: false, top: 260, lines: null },
  build(s, P) {
    footage(s);
    const L = P.lines || (P.three ? LINES.intro : LINES.stack);
    const rows = P.three && L.length >= 3 ? [[L[0], 96, C.text], [L[1], 180, C.text], [L[2], 96, C.accent]] : L.map((t, i) => (i < L.length - 1 ? [t, 96, C.text] : [t, 150, C.accent]));
    headline(s, rows, { top: P.top, gap: P.three ? 4 : 6, rise: P.rise });
  } });

// =====================================================================================================
// CLEAN EXPLAINERS (light screens, ghost words, diamond tiles, a camera that glides, finished pieces float)
// Hard cuts between full screen and split, never crossfades. Captions are pills in the accent.
// =====================================================================================================
def("explain-layers", { section: "Clean explainers", label: "Concept card, its three layers light up, cut to a split", loop: 8600,
  params: { title: null, lead: "and there's 3 layers", part: "Layer One", rows: ["Who it's for", "What it does", "How it works"], glyph: "spark", bg: "tint", caps: null },
  build(s, P) {
    const T = 8600, CUT = 3000, tl = P.title || LINES.title, bg = sceneBg(P.bg);
    // 1. full-screen card: the title ghosts in, a cube floats up and its three layers light up one by one
    const a = fullScene(s, T, 0, CUT, bg);
    ghostTitle(s, a, tl, 440, 142, 150, 300);
    const cb = layerCube(s, a, 540, 1010, 360, 1250);
    tileIn(cb.wrap, 300); cb.c.float(900);
    capPill(s, a, 1400, evenCaps([...tl, P.lead], 0, CUT));
    // 2. hard cut to the split: the first layer's name and tile are already there, the words ghost in
    const top = splitScene(s, T, CUT, T, bg);
    const g = s.el("div", { position: "absolute", left: "0", top: "0", width: "1080px", height: "960px", transformOrigin: "540px 290px" }, top);
    ghostTitle(s, g, [P.part], 290, 100, CUT + 60, 330);
    const dm = diamond(s, g, 540, 560, 420, P.glyph);
    dm.animate([{ transform: "translateY(0) rotate(0deg)" }, { transform: "translateY(-10px) rotate(-1.5deg)", offset: .5 }, { transform: "translateY(0) rotate(0deg)" }], { duration: 2600, delay: CUT, iterations: Infinity, easing: "ease-in-out" });
    // title and tile shrink up out of the way, a card with three rows rises in under them
    camera(g, T, [[4100, 560, "translate(0px,-30px) scale(.5)"]]);
    wires(s, top, ["M505 462 L470 494", "M575 462 L610 494"], 4500, 60, C.accent, 3).style.opacity = ".7";
    const card = s.el("div", { position: "absolute", left: "260px", top: "494px", width: "560px", boxSizing: "border-box", padding: "18px", borderRadius: "30px", background: mixHex(C.accent, "#ffffff", .12), border: `9px solid ${C.accent}`, boxShadow: `0 18px 36px ${rgba(C.ink, .14)}`, display: "flex", flexDirection: "column", gap: "14px" }, top);
    slideIn(card, 4300, 0, 180, 700);
    floatIdle(card, 5200, 6, 2800);
    P.rows.forEach(q => {
      const r = s.el("div", { display: "flex", alignItems: "center", gap: "16px", background: C.paper, borderRadius: "14px", padding: "18px 20px", fontFamily: FONT, fontWeight: String(W8.caption), fontSize: "34px", color: C.ink, boxShadow: `0 4px 10px ${rgba(C.ink, .06)}` }, card);
      s.el("div", { width: "32px", height: "32px", borderRadius: "50%", border: `3px solid ${C.accent}`, boxSizing: "border-box", flex: "none" }, r);
      s.el("span", {}, r, q);
    });
    capPill(s, null, 960, evenCaps(P.caps || ["Layer 1", "is the", P.part, "three simple things", "that explain", "who it's for", "what it does", "and how it works"], CUT, T));
  } });

def("explain-path", { section: "Clean explainers", label: "Your first app looks around, then a winding road to the goal", loop: 7600, params: { bg: "tint", caps: null, caps2: null },
  build(s, P) {
    const T = 7600, CUT = 2600, bg = sceneBg(P.bg), A = C.accent, name = (ICONS[0] || {}).name || "your app";
    fullScene(s, T, 0, CUT, bg);
    splitScene(s, T, CUT, T, bg);
    // everything lives on one layer; at the cut it jumps up into the top half, smaller
    const art = camLayer(s, null, "540px 1060px");
    const pivot = s.el("div", { position: "absolute", left: "540px", top: "1060px", width: "0", height: "0" }, art);
    const cone = s.el("div", { position: "absolute", left: "-360px", top: "-940px", width: "720px", height: "940px", background: `linear-gradient(to top, ${rgba(A, 1)}, ${rgba(A, .75)} 35%, ${rgba(A, 0)} 92%)`, clipPath: "polygon(47% 100%, 53% 100%, 100% 0, 0 0)", transformOrigin: "50% 100%", filter: "blur(2px)" }, pivot);
    // the beam switches on pointing right, sweeps up and over to the left, then switches off
    cone.animate([{ transform: "rotate(90deg)", opacity: 0 }, { transform: "rotate(90deg)", opacity: 1, offset: .14 }, { transform: "rotate(84deg)", opacity: 1, offset: .24, easing: "cubic-bezier(.45,0,.3,1)" }, { transform: "rotate(-62deg)", opacity: 1, offset: .86 }, { transform: "rotate(-66deg)", opacity: 0 }], { duration: 1400, delay: 250, fill: "both" });
    const ic = s.img(icon(0), { position: "absolute", left: "425px", top: "945px", width: "230px", height: "230px", filter: `drop-shadow(0 18px 24px ${rgba(C.ink, .24)})` }, art);
    tileIn(ic, 100); floatIdle(ic, 700, 6, 2400);
    // then a winding road draws up from the icon, with a flag at every turn
    const road = "M540 940 C 540 880, 385 895, 385 830 C 385 770, 470 760, 590 760 C 740 760, 765 715, 720 680 C 670 645, 395 665, 385 600 C 378 548, 470 540, 615 540";
    const rb = s.el("div", { position: "absolute", left: "0", top: "0", width: "1080px", height: "1920px" }, art);
    rb.innerHTML = `<svg width="1080" height="1920" viewBox="0 0 1080 1920" fill="none"><path d="${road}" pathLength="1" stroke="${A}" stroke-width="15" stroke-linecap="round" stroke-dasharray="1" stroke-dashoffset="1"/></svg>`;
    rb.querySelector("path").animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], { duration: 950, delay: 1650, easing: "cubic-bezier(.45,0,.25,1)", fill: "both" });
    [[372, 830, .2], [748, 720, .5], [372, 610, .78], [628, 545, .97]].forEach(([x, y, f]) => {
      const fl = s.el("div", { position: "absolute", left: x - 6 + "px", top: y - 52 + "px", width: "38px", height: "52px" }, art);
      fl.innerHTML = `<svg viewBox="0 0 30 40" width="100%" height="100%"><rect x="3" y="2" width="3.4" height="37" rx="1.7" fill="${C.ink}"/><path d="M6.4 3h18l-5 6 5 6h-18z" fill="${C.ink}"/></svg>`;
      ghost(fl, 1650 + f * 950, 260);
    });
    // the goal appears at the end of the road once we're in the split
    const goal = s.el("div", { position: "absolute", left: "632px", top: "478px", width: "64px", height: "64px", borderRadius: "50%", background: A, boxShadow: `inset 0 0 0 9px #fff, inset 0 0 0 18px ${A}, 0 6px 12px ${rgba(C.ink, .18)}` }, art);
    s.el("div", { position: "absolute", left: "24px", top: "24px", width: "16px", height: "16px", borderRadius: "50%", background: C.ink }, goal);
    tileIn(goal, CUT + 250, 1.2, 420);
    camera(art, T, [[1650, 950, "translate(0px,60px) scale(1)"], [CUT, 0, "translate(0px,-250px) scale(.8)"]]);
    capPill(s, null, 1420, evenCaps(P.caps || ["this shows", name, "exactly", "where to go", "next"], 0, CUT));
    capPill(s, null, 960, evenCaps(P.caps2 || ["so every step", "points straight at", "your goal"], CUT, T));
  } });

def("explain-pills", { section: "Clean explainers", label: "Title and tile, two pills branch off, a card of your videos fills in", loop: 7000,
  params: { title: "The Plan", glyph: "target", pills: ["Rules", "Examples"], bg: "tint", caps: null },
  build(s, P) {
    const T = 7000;
    fullScene(s, T, 0, T, sceneBg(P.bg));
    const w = camLayer(s, null);
    const t = ghostTitle(s, w, [P.title], 545, 112, 150);
    const dm = diamond(s, w, 540, 800, 330, P.glyph);
    tileIn(dm, 100, 1.04, 380); floatIdle(dm, 600, 7, 2600);
    // the camera glides down as each new piece arrives; the title melts away as it leaves the safe area
    camera(w, T, [[1500, 450, "translate(0px,-120px) scale(1)"], [2900, 520, "translate(0px,-450px) scale(1)"]]);
    t.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 400, delay: 2900, fill: "forwards" });
    wires(s, w, ["M520 892 L385 985", "M560 892 L695 985"], 1600, 40);
    [[385, 1650, P.pills[0]], [695, 1760, P.pills[1] || P.pills[0]]].forEach(([x, at, label]) => {
      const p = darkPill(s, w, x, 1020, 290, 66);
      s.el("span", { width: "22px", height: "22px", borderRadius: "50%", border: `2.5px solid ${C.accent}`, color: C.accent, fontSize: "14px", lineHeight: "17px", textAlign: "center", flex: "none", boxSizing: "border-box" }, p, "i");
      s.el("span", {}, p, label);
      ghost(p, at, 300);
    });
    wires(s, w, ["M385 1053 L540 1145", "M695 1053 L540 1145"], 3300, 40);
    // a ghost card appears, then fills in as a dark card of their real videos and photos
    const card = s.el("div", { position: "absolute", left: "330px", top: "1150px", width: "420px", height: "378px", borderRadius: "26px", background: darkFill(), boxShadow: `0 22px 40px ${rgba(C.ink, .22)}`, padding: "22px", boxSizing: "border-box", display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "14px" }, w);
    card.animate([{ background: rgba(C.ink, .10), boxShadow: `0 0 0 ${rgba(C.ink, 0)}` }, { background: darkFill(), boxShadow: `0 22px 40px ${rgba(C.ink, .22)}` }], { duration: 300, delay: 3800, easing: "ease-out", fill: "backwards" });
    ghost(card, 3500, 300);
    const th = (n) => `assets/thumb-${n}.jpg`, pics = [th(1), photoAt(0) || th(3), th(2), th(4), photoAt(1) || th(1), th(3)];
    pics.forEach((src, i) => {
      const cell = photoBox(s, card, src, { position: "relative", height: "156px" });
      ghost(cell, 3820 + i * 70, 300);
      if (i === 2) {   // one tile swaps to another video while they talk (a hard swap, no zoom)
        const sw = s.img(photoAt(2) || th(4), { position: "absolute", inset: "0", width: "100%", height: "100%", objectFit: "cover" }, cell);
        sw.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, delay: 5600, fill: "both" });
      }
    });
    capPill(s, null, 1240, evenCaps(P.caps || ["step two", `is ${P.title.toLowerCase()}`, "so every move", "has a clear", "set of rules", "behind it", "built from", "what already works"], 0, T));
  } });

def("explain-tool", { section: "Clean explainers", label: "Tool intro: your real app icon, its name, then what it does", loop: 6600, params: { name: null, icon: 0, bezel: false, bg: "tint", caps: null },
  build(s, P) {
    const T = 6600, ap = ICONS[P.icon % Math.max(ICONS.length, 1)] || {}, name = P.name || ap.name || "Your tool";
    fullScene(s, T, 0, T, sceneBg(P.bg));
    const w = camLayer(s, null);
    const t = appTile(s, w, 540, 900, 200, ap.file, { bezel: P.bezel });
    tileIn(t, 100); floatIdle(t, 700, 5, 2400);
    ghostTitle(s, w, [name], 650, 112, 420);
    camera(w, T, [[1300, 420, "translate(0px,-120px) scale(1)"], [2350, 480, "translate(0px,-420px) scale(1)"]]);
    wires(s, w, ["M520 1004 L385 1084", "M560 1004 L695 1084"], 1450, 60);
    // two profile pills slide in from the sides
    [[385, 1450, -60], [695, 1600, 60]].forEach(([x, at, dx]) => {
      const p = darkPill(s, w, x, 1124, 290, 84, { borderRadius: "18px" });
      s.el("div", { width: "52px", height: "52px", borderRadius: "50%", background: mixHex(C.paper, C.ink, .9), flex: "none", overflow: "hidden" }, p).innerHTML = `<svg viewBox="0 0 48 48" width="100%" height="100%"><circle cx="24" cy="19" r="8" fill="${mixHex(C.ink, C.paper, .4)}"/><path d="M8 46c1.5-9 8-13.5 16-13.5S38.5 37 40 46z" fill="${mixHex(C.ink, C.paper, .4)}"/></svg>`;
      const bars = s.el("div", { display: "flex", flexDirection: "column", gap: "10px" }, p);
      s.el("div", { width: "150px", height: "10px", borderRadius: "5px", background: "rgba(255,255,255,.75)" }, bars);
      s.el("div", { width: "105px", height: "10px", borderRadius: "5px", background: "rgba(255,255,255,.35)" }, bars);
      slideIn(p, at, dx, 40, 520);
    });
    wires(s, w, ["M385 1166 L540 1254", "M695 1166 L540 1254"], 2500, 40);
    // a grid of video tiles builds underneath
    const card = s.el("div", { position: "absolute", left: "345px", top: "1256px", width: "390px", height: "290px", borderRadius: "24px", background: darkFill(), padding: "20px", boxSizing: "border-box", display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px", boxShadow: `0 20px 36px ${rgba(C.ink, .22)}` }, w);
    card.animate([{ background: rgba(C.ink, .12), boxShadow: `0 0 0 ${rgba(C.ink, 0)}` }, { background: darkFill(), boxShadow: `0 20px 36px ${rgba(C.ink, .22)}` }], { duration: 360, delay: 2950, easing: "ease-out", fill: "backwards" });
    ghost(card, 2700, 300);
    for (let i = 0; i < 6; i++) {
      const v = s.el("div", { position: "relative", borderRadius: "12px", background: `linear-gradient(160deg, ${mixHex("#ffffff", darkFill(), .14)}, ${mixHex("#ffffff", darkFill(), .06)})`, boxShadow: "inset 0 0 0 1.5px rgba(255,255,255,.08)" }, card);
      v.innerHTML = `<svg viewBox="0 0 24 24" width="34" height="34" style="position:absolute;left:50%;top:50%;transform:translate(-45%,-50%)"><path d="M7 4.5v15l12.5-7.5z" fill="#fff"/></svg>`;
      ghost(v, 2950 + i * 80, 320);
    }
    capPill(s, null, 1250, evenCaps(P.caps || [name, "does one job", "really well", "you give it", "a simple input", "and it hands back", "the finished work"], 0, T));
  } });

def("explain-folder", { section: "Clean explainers", label: "A folder with files sticking out, too many things, then just one", loop: 8200,
  params: { file: "Notes", left: "40 files", right: "100 apps", one: "Just One", bg: "paper", caps: null, caps2: null, caps3: null },
  build(s, P) {
    const T = 8200, B = 3200, C2 = 6200, bg = sceneBg(P.bg), shadow = `drop-shadow(0 14px 18px ${rgba(C.ink, .16)})`;
    faceBottom(s);   // one face under all three scenes, so it never jumps at the cuts
    // 1. a real Mac folder with two files sticking out; it flashes red
    const a = splitScene(s, T, 0, B, bg, false);
    const fg = s.el("div", { position: "absolute", left: "350px", top: "400px", width: "380px", height: "380px" }, a);
    fileDoc(s, fg, 90, -34, 120, { transform: "rotate(-7deg)" }, P.file);
    fileDoc(s, fg, 178, -46, 120, { transform: "rotate(6deg)" }, P.file);
    const fa = folderArt(s, fg, 380);
    fa.flash.animate([{ opacity: 0 }, { opacity: .92, offset: .12 }, { opacity: .92, offset: .4 }, { opacity: 0 }], { duration: 900, delay: 1750, easing: "ease-out", fill: "both" });
    fg.animate([{ transform: "translateY(36px)", opacity: 0, filter: "saturate(.3) brightness(1.25)" }, { transform: "translateY(0)", opacity: 1, filter: "saturate(1) brightness(1)" }], { duration: 650, delay: 120, easing: EXPO, fill: "backwards" });
    floatIdle(fg, 800, 8, 2400);
    // 2. a line splits the screen: files slide in from the left, apps from the right, each group with a tag
    const b = splitScene(s, T, B, C2, bg, false);
    wires(s, b, ["M540 130 L540 900"], B + 60, 0, rgba(C.ink, .22), 3);
    for (let r = 0; r < 3; r++) for (let c = 0; c < 2; c++) {
      slideIn(fileDoc(s, b, 150 + c * 140, 330 + r * 190, 96, {}, P.file), B + 150 + c * 90, -420, 0, 600);
      slideIn(s.img(icon(0), { position: "absolute", left: 700 + c * 170 + "px", top: 322 + r * 190 + "px", width: "130px", height: "130px", filter: shadow }, b), B + 220 + c * 90, 420, 0, 600);
    }
    slideIn(tagLabel(s, b, 270, 262, P.left), B + 650, 0, -30, 420);
    slideIn(tagLabel(s, b, 785, 262, P.right), B + 1050, 0, -30, 420);
    // 3. hard cut: just one
    const c = splitScene(s, T, C2, T, bg, false);
    ghostTitle(s, c, [P.one], 330, 100, C2 + 60, 300);
    tileIn(appTile(s, c, 540, 640, 260, icon(0)), C2 + 40);
    capPill(s, null, 960, [
      ...evenCaps(P.caps || ["1. Stop collecting", "stuff", "you're never", "going to use"], 0, B),
      ...evenCaps(P.caps2 || [`You don't need ${P.left}`, `or ${P.right}`, "you need"], B, C2),
      ...evenCaps(P.caps3 || ["just one", "that does it all"], C2, T)]);
  } });

// =====================================================================================================
// REAL IMAGES (photos come from assets/photos/photos.json; none yet = neutral boxes saying so)
// Photos: square corners, hard cuts, never any zoom. Logos are shown as they are, only a drop shadow.
// =====================================================================================================
def("photos-flash", { section: "Real images", label: "Photos flash above your head, hard cuts", loop: 5200, params: { count: 4, every: 1300, top: 250, caps: null },
  build(s, P) {
    const T = 5200;
    footage(s);
    const frame = s.el("div", { position: "absolute", left: "250px", top: P.top + "px", width: "580px", height: "400px", overflow: "hidden", borderRadius: "0", boxShadow: "0 16px 34px rgba(0,0,0,.35)" });
    for (let i = 0; i < P.count; i++) {
      const p = photoBox(s, frame, photoAt(i), { left: "0", top: "0", width: "100%", height: "100%" }, "50% 45%", i);
      cutWindow(p, i * P.every, i === P.count - 1 ? T : (i + 1) * P.every, T);
    }
    chunks(s, timed(P.caps || LINES.talk, 0, P.every), { top: 1240, size: 76, enterFx: softFade, end: T });
  } });
def("hook-logos-photo", { section: "Real images", label: "Hook: real logos and a real photo over the title", loop: 5200, params: { top: 260, sub: "(here's the whole system)", title: null },
  build(s, P) {
    footage(s);
    const row = s.el("div", { position: "absolute", left: "0", right: "0", top: P.top + "px", display: "flex", justifyContent: "center", gap: "18px" });
    // the app icons exactly as they are (only a drop shadow, no tile or bubble round them); the photo has square corners and just appears
    [["img", icon(0)], ["photo", photoAt(0)], ["img", icon(1)]].forEach(([k, src], i) => {
      if (k === "photo") { const ph = photoBox(s, row, src, { position: "relative", width: "200px", height: "200px", boxShadow: "0 14px 30px rgba(0,0,0,.35)" }, "50% 40%", 0, 26); cutWindow(ph, 120 + i * 110, 5200, 5200); }
      else tileIn(s.img(src, { width: "200px", height: "200px", objectFit: "contain", filter: "drop-shadow(0 14px 22px rgba(0,0,0,.35))" }, row), 120 + i * 110);
    });
    const t = s.el("div", { position: "absolute", left: "80px", right: "80px", top: P.top + 250 + "px", textAlign: "center", fontFamily: FONT, fontWeight: String(W8.title), fontSize: "92px", letterSpacing: "-0.04em", color: C.text, textShadow: CAP_SHADOW, lineHeight: "1.02" });
    wordsRise(s, s.el("div", {}, t), P.title || LINES.accent, 450, 170, "blur");
    const sub = s.el("div", { fontSize: "36px", fontWeight: String(W8.caption), letterSpacing: "-0.01em", marginTop: "14px" }, t, P.sub);
    cleanRise(sub, 1150);
  } });

// =====================================================================================================
// TEXT FADES (solid at the top of each line, melting away at the bottom)
// from: ink | deep | text      to: paper | accent | soft      start: where the fade begins (% down the line)
// =====================================================================================================
def("text-fade", { section: "Text fades", label: "Title that melts away", loop: 6000, params: { from: "ink", to: "paper", start: 52, size: 210, top: 730, lines: null },
  build(s, P) {
    const from = { ink: C.ink, deep: C.deep, accent: C.accent, text: C.text }[P.from] || C.ink, to = { paper: C.paper, accent: C.accent, soft: C.soft }[P.to] || C.paper;
    s.el("div", { position: "absolute", inset: "0", background: C.paper });
    const lns = P.lines || LINES.title, sz = fitSize(lns, P.size, { ls: -0.045 });
    const t = s.el("div", { position: "absolute", left: "0", right: "0", top: P.top + "px", textAlign: "center", fontFamily: FONT, fontWeight: String(W8.title), fontSize: sz + "px", letterSpacing: "-0.045em", lineHeight: ".95" });
    lns.forEach((txt, i) => cleanRise(fadeFill(s.el("span", { whiteSpace: "nowrap" }, s.el("div", {}, t), txt), from, to, P.start), 250 + i * 200));
  } });
// Uses the text fade they locked in the Text lab (locked/text_fade.json): its background_image exactly, plus its size, height, weight and spacing.
def("text-fade-locked", { section: "Text fades", label: "Your locked text fade", loop: 6000, params: { lines: null },
  build(s, P) {
    const L = TEXT_FADE;
    if (L && L.bg === "face") footage(s); else s.el("div", { position: "absolute", inset: "0", background: L && L.bg === "blue" ? C.accent : C.paper });
    const lns = P.lines || LINES.title, weight = (L && L.weight) || W8.title, track = L ? (L.track != null ? L.track : -45) / 1000 : -0.045;
    const sz = fitSize(lns, (L && L.size) || 210, { weight, ls: track });
    const t = s.el("div", { position: "absolute", left: "0", right: "0", top: ((L && L.top) || 730) + "px", textAlign: "center", fontFamily: FONT, fontWeight: String(weight), fontSize: sz + "px", letterSpacing: track + "em", lineHeight: ".95",
      filter: L && L.shadow === "on" ? "drop-shadow(0 8px 13px rgba(0,0,0,.44))" : "none" });
    lns.forEach((txt, i) => {
      const sp = s.el("span", { whiteSpace: "nowrap" }, s.el("div", {}, t), txt);
      if (!L) fadeFill(sp, C.ink, C.paper, 52);
      else {
        const fades = L.only !== "yes" || i === lns.length - 1;
        Object.assign(sp.style, { display: "inline-block", webkitBackgroundClip: "text", backgroundClip: "text", color: "transparent", paddingBottom: ".06em", backgroundImage: fades ? L.background_image : `linear-gradient(${L.from}, ${L.from})` });
      }
      cleanRise(sp, 250 + i * 200);
    });
    if (!L) notice(s, "text not locked yet", 1440);
  } });

// =====================================================================================================
// CTA
// =====================================================================================================
def("cta-keyword", { section: "CTA", label: "Quoted keyword over your face", loop: 6000, params: { keyword: "STYLE", lead: "comment", top: 280, size: 230 },
  build(s, P) {
    footage(s);
    const box = s.el("div", { position: "absolute", left: "0", right: "0", top: P.top + "px", textAlign: "center", fontFamily: FONT, fontWeight: String(W8.title), lineHeight: ".98", textShadow: CAP_SHADOW, color: C.text });
    cleanRise(s.el("div", { fontSize: "60px", fontWeight: String(W8.caption), letterSpacing: "-0.02em" }, box, P.lead), 250);
    const big = s.el("div", { fontSize: fitSize("“" + P.keyword + "”", P.size, { ls: -0.04 }) + "px", letterSpacing: "-0.04em", whiteSpace: "nowrap" }, box);
    [["“", C.accent], [P.keyword, C.text], ["”", C.accent]].forEach(([ch, col], i) => blurRise(s.el("span", { display: "inline-block", color: col }, big, ch), 500 + i * 120));
  } });

checkAssets();
