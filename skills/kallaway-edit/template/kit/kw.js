/* kallaway-edit motion kit. build.py pastes this inside every scene's script (inside the
   scene's own function, so two scenes never clash). Every helper ADDS tweens to the timeline
   you pass in, at an absolute scene time, and is a pure function of timeline time (no clocks,
   no randomness), so every render is identical.

   Conventions:
   - Anything that appears later starts hidden with class "kw-hide" (opacity 0) in the markup.
   - Entrances are blur-ins (from ~18 px blur, a touch small, grey) with a long ease-out.
   - NOTHING animates out. The next cut ends the scene.
   - `t` is in scene seconds. Use the beat times build.py injects (B.someBeat, B.w[i].t).
*/
const KW = (() => {
  const q = (s) => (typeof s === "string" ? document.querySelector(s) : s);
  const qa = (s) => (typeof s === "string" ? Array.from(document.querySelectorAll(s)) : [].concat(s));
  const OUT = "expo.out";

  // Seeded pseudo-random so a "random" scramble is identical in every render.
  function rng(seed) { let x = seed >>> 0 || 1; return () => ((x = (x * 1664525 + 1013904223) >>> 0) / 4294967296); }

  /** Blur-in: the default entrance for any element. */
  function blurIn(tl, sel, t, o = {}) {
    const els = qa(sel);
    const d = o.dur ?? 0.24, blur = o.blur ?? 18, sc = o.scale ?? 0.94, st = o.stagger ?? 0;
    els.forEach((el, i) => {
      tl.fromTo(el, { opacity: 0, filter: `blur(${blur}px) brightness(${o.grey === false ? 1 : 0.55})`,
        scale: sc, x: o.x ?? 0, y: o.y ?? 0 },
        { opacity: 1, filter: "blur(0px) brightness(1)", scale: 1, x: 0, y: 0, duration: d, ease: OUT,
          immediateRender: false }, t + i * st);
    });
    return t + d + st * (els.length - 1);
  }

  /** Split an element's text into word spans (call once, at build time of the scene). */
  function splitWords(sel) {
    const el = q(sel);
    const walk = (node) => {
      Array.from(node.childNodes).forEach((n) => {
        if (n.nodeType === 3) {
          const parts = n.textContent.split(/(\s+)/).filter((p) => p.length);
          const frag = document.createDocumentFragment();
          parts.forEach((p) => {
            if (/^\s+$/.test(p)) { frag.appendChild(document.createTextNode(p)); return; }
            const s = document.createElement("span"); s.className = "kw-w kw-hide"; s.textContent = p;
            frag.appendChild(s);
          });
          node.replaceChild(frag, n);
        } else if (n.nodeType === 1 && !n.classList.contains("kw-w")) {
          if (n.dataset.kwWhole !== undefined) { n.classList.add("kw-w", "kw-hide"); return; }
          walk(n);
        }
      });
    };
    walk(el);
    return Array.from(el.querySelectorAll(".kw-w"));
  }

  /** Title that builds word by word. `times` = one time per word (spoken), or a start time
      and words follow every `gap` s. Each word blurs in from grey. Returns the last time. */
  function title(tl, sel, times, o = {}) {
    const words = splitWords(sel);
    const gap = o.gap ?? 0.09;
    words.forEach((w, i) => {
      const t = Array.isArray(times) ? (times[i] ?? times[times.length - 1] + gap * (i - times.length + 1))
                                     : times + i * gap;
      tl.fromTo(w, { opacity: 0, filter: "blur(14px) brightness(0.5)", y: 6 },
        { opacity: 1, filter: "blur(0px) brightness(1)", y: 0, duration: o.dur ?? 0.2, ease: OUT,
          immediateRender: false }, t);
    });
    return words;
  }

  /** Letter scramble that resolves into the element's text over `dur`. */
  function scramble(tl, sel, t, o = {}) {
    const el = q(sel); const final = el.textContent; const dur = o.dur ?? 0.32;
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&";
    const r = rng(o.seed ?? final.length * 97 + 13); const noise = Array.from({ length: 64 }, () => r());
    const proxy = { p: 0 };
    tl.fromTo(proxy, { p: 0 }, { p: 1, duration: dur, ease: "none", immediateRender: false,
      onUpdate: () => {
        const p = proxy.p; const fixed = Math.floor(p * final.length);
        let s = "";
        for (let i = 0; i < final.length; i++) {
          if (i < fixed || final[i] === " ") s += final[i];
          else s += chars[Math.floor(noise[(i * 7 + Math.floor(p * 12)) % 64] * chars.length)];
        }
        el.textContent = p >= 1 ? final : s;
      } }, t);
    tl.set(el, { textContent: final }, t + dur + 0.001);
  }

  /** Label pill / red pill: grows out of a sliver (0.2 s, ease-out), optional scramble. */
  function pill(tl, sel, t, o = {}) {
    const el = q(sel);
    tl.fromTo(el, { opacity: 0, scaleX: 0.06, scaleY: 0.7, filter: "blur(6px)" },
      { opacity: 1, scaleX: 1, scaleY: 1, filter: "blur(0px)", duration: o.dur ?? 0.22, ease: "power3.out",
        immediateRender: false, transformOrigin: o.origin ?? "50% 50%" }, t);
    if (o.scramble) scramble(tl, el.querySelector(".kw-txt") || el, t, { dur: 0.3 });
    return t + 0.22;
  }

  /** Soft red disc behind something that just landed: grows and fades in ~0.45 s. */
  function pulse(tl, sel, t, o = {}) {
    tl.fromTo(q(sel), { opacity: 0.0, scale: 0.35 }, { keyframes: [
      { opacity: o.peak ?? 0.9, scale: 0.8, duration: 0.12, ease: "power2.out" },
      { opacity: 0, scale: o.scale ?? 1.6, duration: 0.4, ease: "power2.out" }],
      immediateRender: false }, t);
  }

  /** Draw an SVG stroke along its path (left to right as authored). */
  function draw(tl, sel, t, o = {}) {
    qa(sel).forEach((p, i) => {
      const len = p.getTotalLength();
      p.style.strokeDasharray = `${len} ${len}`;
      p.style.strokeDashoffset = `${len}`;
      tl.fromTo(p, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: o.dur ?? 0.6,
        ease: o.ease ?? "power2.inOut", immediateRender: false }, t + i * (o.stagger ?? 0));
    });
  }

  /** Virtual camera: move the scene's camera wrapper so the new element is framed.
      Fast start, long decelerating settle, motion blur at peak speed. */
  function cam(tl, sel, t, to, o = {}) {
    const d = o.dur ?? 0.75;
    tl.to(q(sel), { x: to.x ?? 0, y: to.y ?? 0, scale: to.scale ?? 1, duration: d, ease: o.ease ?? "expo.out" }, t);
    if (o.blur !== false) {
      tl.fromTo(q(sel), { filter: `blur(${o.blur ?? 7}px)` }, { filter: "blur(0px)", duration: d * 0.45,
        ease: "power2.out", immediateRender: false }, t);
    }
  }

  /** Typewriter: reveal an element's text between t0 and t1 (linear), with a caret element. */
  function type(tl, sel, t0, t1, o = {}) {
    const el = q(sel); const full = o.text ?? el.textContent; const proxy = { n: 0 };
    el.textContent = "";
    tl.fromTo(proxy, { n: 0 }, { n: full.length, duration: Math.max(0.05, t1 - t0), ease: "none",
      immediateRender: false, onUpdate: () => { el.textContent = full.slice(0, Math.round(proxy.n)); } }, t0);
    tl.set(el, { textContent: full }, t1 + 0.001);
  }

  /** Strike-through / underline: a bar that grows left to right. */
  function strike(tl, sel, t, o = {}) {
    tl.fromTo(q(sel), { scaleX: 0, opacity: 1 }, { scaleX: 1, opacity: 1, duration: o.dur ?? 0.22, ease: "power3.out",
      transformOrigin: "0% 50%", immediateRender: false }, t);
  }

  /** Number that ticks from a to b. */
  function count(tl, sel, a, b, t, o = {}) {
    const el = q(sel); const proxy = { v: a }; const fmt = o.fmt ?? ((v) => Math.round(v).toString());
    tl.fromTo(proxy, { v: a }, { v: b, duration: o.dur ?? 0.6, ease: o.ease ?? "power2.out", immediateRender: false,
      onUpdate: () => { el.textContent = fmt(proxy.v); } }, t);
  }

  /** Instant state change on a frame (e.g. a colour swap): lands ON the frame, not one late. */
  function at(tl, sel, t, vars) { tl.set(q(sel), vars, Math.max(0, t - 0.002)); }

  /** Onset of spoken word i (cut-timeline index from words.json) in scene seconds. */
  function word(B, i) { const w = B.w.find((x) => x.i === i); if (!w) throw new Error(`word ${i} is not in this scene`); return w.t; }

  return { word, q, qa, rng, blurIn, splitWords, title, scramble, pill, pulse, draw, cam, type, strike, count, at };
})();
