/* edit-my-video motion kit. Load after assets/style.js (window.STYLE, written by scripts/style.py).
 *
 * These are the style's MOTION FEEL as primitives, not a menu of layouts. Design every beat fresh, then use
 * these so it moves the way the creator locked it. Everything is WAAPI at absolute reel seconds (HyperFrames
 * seeks document time), paused by K.done(). window.KIT_T0 shifts every time (used for variation slices).
 *
 *   K.enter(el, at, "rise"|"fade"|"blur")     a part arriving (never a pop-in)
 *   K.words(el, [[word, t], ...], "clean"|"blur")  word-by-word reveal (accent / intro text)
 *   K.wordsAt(el, [t, t, ...], kind)          same, splitting the element's own text into words
 *   K.focusIn(el, at)                          hero word racks into focus
 *   K.glideIn(el, at, from = -1)               line glides in from the left (-1) or right (1)
 *   K.shine(el, at)                            the locked shine on a word (el = a .hero element)
 *   K.draw(svgShape, at, dur)                  line / ring draws itself on
 *   K.push(el, at, {fx, fy, scale, tx, ty, w, h, W, H, dur})  quick push-in to a point, never showing edges
 *   K.scroll(el, at, px, dur)                  slow page scroll (split screen)
 *   K.faceZoom(wrapper, at, dur)               main face zoom: cut in zoomed, glide out
 *   K.punch(wrapper, at), K.hardPunch(wrapper, at, until)   the occasional short punch
 *   K.panel(el, at)                            the one slide: split screen -> full-screen visual
 *   K.leave(el, at, dur)                       a quiet fade out (rarely needed: hard cuts do the work)
 *   K.captions()                               soft fade-up on every .cap clip at its data-start
 *   K.done(duration)                           pause everything, return the timeline: window.__timelines["main"] = K.done(d)
 */
(function () {
  const S = window.STYLE || {};
  const M = S.motion || {};
  const Z = S.zoom || {};
  const t0 = () => window.KIT_T0 || 0;
  const ms = (s) => Math.round((s - t0()) * 1000);
  const $ = (id) => document.getElementById(id);
  const ease = {
    expo: "cubic-bezier(.16,1,.3,1)", glide: "cubic-bezier(.19,1,.22,1)",
    smooth: "cubic-bezier(.65,0,.35,1)", push: "cubic-bezier(.7,0,.15,1)",
  };
  const back = (el, kf, o) => el.animate(kf, Object.assign({ fill: "backwards" }, o));
  const both = (el, kf, at, dur, easing) => el.animate(kf, { duration: dur, delay: ms(at), easing, fill: "both" });
  // moves that start from where the element already is (push, scroll): no effect before they start, so an
  // entrance on the same element still plays
  const fwd = (el, kf, at, dur, easing) => el.animate(kf, { duration: dur, delay: ms(at), easing, fill: "forwards", composite: "add" });

  function enter(el, at, kind) {
    kind = kind || "rise";
    if (kind === "fade") {
      const m = M.enter_fade || { dur_ms: 600 };
      return back(el, [{ opacity: 0 }, { opacity: 1 }], { duration: m.dur_ms, delay: ms(at), easing: "ease-out" });
    }
    if (kind === "blur") {
      const m = M.enter_blur || { rise_px: 34, blur_px: 18, dur_ms: 560, ease: ease.expo };
      back(el, [{ transform: `translateY(${m.rise_px}px)` }, { transform: "translateY(0)" }],
        { duration: m.dur_ms, delay: ms(at), easing: m.ease, composite: "add" });
      return back(el, [{ opacity: 0, filter: `blur(${m.blur_px}px)` }, { opacity: 0.55, filter: `blur(${m.blur_px * 0.4}px)`, offset: 0.4 },
        { opacity: 1, filter: "blur(0px)" }], { duration: m.dur_ms, delay: ms(at), easing: m.ease });
    }
    const m = M.enter_rise || { rise_px: 46, dur_ms: 850, ease: ease.glide };
    back(el, [{ transform: `translateY(${m.rise_px}px)` }, { transform: "translateY(0)" }],
      { duration: m.dur_ms, delay: ms(at), easing: m.ease, composite: "add" });
    return back(el, [{ opacity: 0 }, { opacity: 0.7, offset: 0.45 }, { opacity: 1 }], { duration: m.dur_ms, delay: ms(at), easing: m.ease });
  }

  function word(span, at, kind) {
    if (kind === "blur") {
      const m = M.blur_rise || { rise_px: 26, blur_px: 18, dur_ms: 480, ease: ease.expo };
      return back(span, [{ opacity: 0, transform: `translateY(${m.rise_px}px)`, filter: `blur(${m.blur_px}px)` },
        { opacity: 0.55, filter: `blur(${m.blur_px * 0.4}px)`, offset: 0.4 }, { opacity: 1, transform: "translateY(0)", filter: "blur(0px)" }],
        { duration: m.dur_ms, delay: ms(at), easing: m.ease });
    }
    const m = M.clean_rise || { rise_px: 42, dur_ms: 820, ease: ease.glide };
    return back(span, [{ opacity: 0, transform: `translateY(${m.rise_px}px)` }, { opacity: 0.7, offset: 0.45 }, { opacity: 1, transform: "translateY(0)" }],
      { duration: m.dur_ms, delay: ms(at), easing: m.ease });
  }
  function words(el, list, kind) {
    list.forEach(([w, t], i) => {
      const s = document.createElement("span");
      s.className = "w";
      s.textContent = i < list.length - 1 ? w + " " : w;
      el.appendChild(s);
      word(s, t, kind);
    });
  }
  function wordsAt(el, times, kind) {
    const parts = el.textContent.trim().split(/\s+/);
    el.textContent = "";
    words(el, parts.map((w, i) => [w, times[Math.min(i, times.length - 1)] + (i >= times.length ? (i - times.length + 1) * 0.2 : 0)]), kind);
  }

  function focusIn(el, at) {
    const m = M.focus_in || { from_scale: 1.35, blur_px: 26, dur_ms: 1000, ease: ease.glide };
    return back(el, [{ opacity: 0, transform: `scale(${m.from_scale})`, filter: `blur(${m.blur_px}px)` },
      { opacity: 0.8, filter: `blur(${m.blur_px * 0.23}px)`, offset: 0.45 }, { opacity: 1, transform: "scale(1)", filter: "blur(0px)" }],
      { duration: m.dur_ms, delay: ms(at), easing: m.ease });
  }
  function glideIn(el, at, from) {
    const m = M.glide_in || { from_px: 180, dur_ms: 900, ease: ease.glide };
    return back(el, [{ opacity: 0, transform: `translateX(${(from || -1) * m.from_px}px)` }, { opacity: 1, offset: 0.4 },
      { opacity: 1, transform: "translateX(0)" }], { duration: m.dur_ms, delay: ms(at), easing: m.ease });
  }

  // The locked shine (locked/shine.json): a band clipped to the text, glow on the band only, never the whole word.
  function shine(el, at) {
    const st = S.shine;
    if (!st) return;
    if (!el.querySelector(".shine-word")) {
      const txt = el.textContent;
      el.innerHTML = `<span class="shine-word">${txt}</span><span class="shine-glow" aria-hidden="true">${txt}</span>`;
    }
    const w = el.querySelector(".shine-word"), g = el.querySelector(".shine-glow");
    const peak = `color-mix(in srgb, ${st.shine} ${st.strength}%, ${st.base})`;
    const half = st.width / 2, edge = half * (st.soft / 100);
    const band = (b, p) => [`${b} 0%`, `${b} ${50 - half}%`, `${p} ${50 - half + edge}%`, `${p} ${50 + half - edge}%`, `${b} ${50 + half}%`, `${b} 100%`];
    w.style.backgroundImage = `linear-gradient(${st.angle}deg, ${band(st.base, peak).join(", ")})`;
    g.style.backgroundImage = `linear-gradient(${st.angle}deg, ${band("transparent", st.shine).join(", ")})`;
    [w, g].forEach((x) => { x.style.backgroundSize = "300% 100%"; });
    g.style.filter = `blur(${st.glow}px)`;
    g.style.opacity = st.strength / 100;
    const h = 1.5 * st.width / 100, m = 0.12;
    const from = ((1.5 + h + m) / 2) * 100, to = ((0.5 - h - m) / 2) * 100;
    [w, g].forEach((x) => both(x, [{ backgroundPosition: `${from}% 0` }, { backgroundPosition: `${to}% 0` }], at, st.dur, st.ease));
  }

  function draw(shape, at, dur) {
    shape.setAttribute("pathLength", "1");
    shape.style.strokeDasharray = "1";
    const m = M.draw || { dur_ms: 420, ease: ease.expo };
    return both(shape, [{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], at, dur || m.dur_ms, m.ease);
  }

  // Quick push-in: bring point (fx, fy) of el (natural size W x H) to (tx, ty) of its w x h window at `scale`,
  // clamped so the page edge never shows. Under a second, always.
  function push(el, at, o) {
    const m = M.push || { dur_ms: 800, ease: ease.push, max_ms: 1000 };
    const s = o.scale || 2, W = o.W || el.offsetWidth, H = o.H || el.offsetHeight, w = o.w || 1080, h = o.h || 960;
    const x0 = o.x0 || 0, y0 = o.y0 || 0;   // where el sits in the window before the push
    let x = (o.tx ?? w / 2) - o.fx * s, y = (o.ty ?? h / 2) - o.fy * s;
    x = Math.min(0, Math.max(w - W * s, x));
    y = Math.min(0, Math.max(h - H * s, y));
    el.style.transformOrigin = "0 0";
    const dur = Math.min(o.dur || m.dur_ms, m.max_ms || 1000);
    return fwd(el, [{ transform: `translate(${x0}px, ${y0}px) scale(1)` }, { transform: `translate(${x}px, ${y}px) scale(${s})` }], at, dur, m.ease);
  }
  function scroll(el, at, px, dur) {
    const m = M.scroll || { px: 700, dur_ms: 4200, ease: ease.smooth };
    return fwd(el, [{ transform: "translateY(0)" }, { transform: `translateY(${-(px || m.px)}px)` }], at, dur || m.dur_ms, m.ease);
  }

  function faceZoom(wrap, at, dur) {
    const z = Z.main || { from: 1.2, to: 1, dur_ms: 3500, ease: ease.smooth, origin: "50% 32%" };
    wrap.style.transformOrigin = z.origin;
    return both(wrap, [{ transform: `scale(${z.from})` }, { transform: `scale(${z.to})` }], at, dur || z.dur_ms, z.ease);
  }
  function punch(wrap, at) {
    const z = Z.punch || { to: 1.15, dur_ms: 750, ease: ease.expo };
    wrap.style.transformOrigin = (Z.main && Z.main.origin) || "50% 32%";
    return both(wrap, [{ transform: "scale(1)" }, { transform: `scale(${z.to})` }], at, z.dur_ms, z.ease);
  }
  function hardPunch(wrap, at, until) {
    const z = Z.hard_punch || { to: 1.15 };
    wrap.style.transformOrigin = (Z.main && Z.main.origin) || "50% 32%";
    return wrap.animate([{ transform: `scale(${z.to})` }, { transform: `scale(${z.to})` }],
      { duration: Math.max(1, ms(until) - ms(at)), delay: ms(at), fill: "none" });
  }
  function panel(el, at) {
    const m = M.panel_slide || { dur_ms: 650, ease: ease.glide };
    return back(el, [{ transform: "translateY(-100%)" }, { transform: "translateY(0)" }], { duration: m.dur_ms, delay: ms(at), easing: m.ease });
  }
  function leave(el, at, dur) {
    return both(el, [{ opacity: 1 }, { opacity: 0 }], at, dur || 300, "ease-in");
  }

  function captions() {
    const c = S.caption || { rise_px: 14, dur_ms: 260, ease: ease.expo };
    document.querySelectorAll(".cap[data-start]").forEach((cap) => {
      const t = cap.firstElementChild || cap;
      back(t, [{ opacity: 0, transform: `translateY(${c.rise_px}px)` }, { opacity: 1, transform: "translateY(0)" }],
        { duration: c.dur_ms, delay: ms(parseFloat(cap.dataset.start)), easing: c.ease });
    });
  }

  // Pause every animation and return the paused root timeline. Register it in the page itself (the HyperFrames
  // lint looks for it there):  window.__timelines["main"] = K.done(14.37);
  function done(duration) {
    document.getAnimations().forEach((a) => a.pause());
    window.__timelines = window.__timelines || {};
    const tl = window.gsap ? gsap.timeline({ paused: true }) : null;
    if (tl) tl.set({}, {}, duration);
    return tl;
  }

  window.K = { $, ms, ease, enter, words, wordsAt, focusIn, glideIn, shine, draw, push, scroll, faceZoom, punch,
    hardPunch, panel, leave, captions, done, both, back };
})();
