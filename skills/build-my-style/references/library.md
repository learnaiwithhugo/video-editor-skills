# The animation library (`page/library.js`)

Every option is drawn on a 1080x1920 stage (real video pixels) in the person's brand. `C.paper`,
`C.accent`, `C.soft`, `C.deep`, `C.ink`, `C.text` (caption colour) and `FONT` come from brand.json;
`W8.title/caption/label` are font weights; `CAP_SHADOW` is their locked caption shadow; `SHINE` and `ZOOM`
are their locked labs (used automatically once locked); `ICONS` their app icons; `LINES` the preview words.

| id | Section | Params (defaults) | What it is |
|---|---|---|---|
| cap-soft-fade | Default captions | top 1240, size 84 | 2-3 word chunks, each fades in drifting up 14px over 260ms (expo ease), old chunk gone instantly |
| cap-word-fade | Default captions | top, size | words fade in one after another, no movement |
| cap-cut | Default captions | top, size | chunks just cut in |
| accent-clean-rise | Accent text | gap 230, dur 820, size 92 | each word glides up 42px and fades in, no blur, premium and unhurried |
| accent-blur-rise | Accent text | gap 170, dur 480, size 92 | each word rises out of an 18px blur |
| intro-shine | Intro text | heroSize 240, from -1, heroColour "accent" | small lead-in (clean rise), huge hero word (blur rise + the shine), last line glides in from the side (from -1 left, 1 right) |
| intro-focus | Intro text | same | hero word racks focus: starts 135% and blurred, settles sharp |
| font-compare | Fonts | family, css | the accent line in one font |
| zoom-long-out | Zooms on your face | from 1.2, dur 3500 | full-screen colour visual, hard cut to the face already at 120%, glides out over 3.5 s, slow at both ends (uses locked zoom.json if direction is "out") |
| zoom-quick-punch | Zooms on your face | to 1.15, dur 750 | quick clean push-in on the key word, cut back |
| zoom-hard-punch | Zooms on your face | to 1.15 | instant cut-in punch, for a strong point |
| tree | Diagrams | entrance rise, title, bg accent | card with a pill, lines drawing on, 4 thumbnails of their videos |
| mindmap | Diagrams | entrance, centre, topics[5], bg paper | centre pill, lines drawing out, topic pills |
| split-fanout | Split-screen diagrams | tag, title, from, items[5], to, bg | diagram in the top half, face below: one thing fans out to 5 and merges |
| split-hub | Split-screen diagrams | tag, title, bg | their first app icon connected to three more |
| logos-tilt | Logos | speed rise/slow, top 230 | two real app icons, tilted -6/+7 degrees, overlapping, front one first |
| logos-row | Logos | count 3, top 330 | icons rising one by one, each slightly tilted |
| split-scroll | Split screen | distance 700 | real page fills the top half and slowly scrolls |
| split-push | Split screen | bg accent, zoom 2.3 | page card snaps up (0.4 s) then punches into the key detail (0.8 s), never showing the page edge |
| split-ring | Split screen | bg paper/accent | page card with a ring drawing round the key detail |
| tool-box | Tool talk | box frosted/solid, caps[] | site on top, face below, captions in a box on the seam (frosted glass tinted with the accent, or solid accent) |
| modes | Switching modes | slide true/false | face, hard cut to split screen, slide (or cut) into a full-screen diagram, hard cut back |
| place | Caption placement | top, size | captions on their face at a height |
| shadow | White text drop shadows | css | white captions over a bright busy page and their face |

`entrance` values: `fade` (600ms), `rise` (46px glide, 850ms), `slow` (the same glide over 1.5 s),
`blur` (34px + 18px blur to sharp, 560ms). `bg`: `paper`, `accent`, `soft`. Never black.

## Writing a new option (`page/custom.js`)
```js
def("three-cards", { section: "Diagrams", label: "Three big cards", loop: 5000, params: { items: ["Yes / no", "Category", "Score"], bg: "accent" },
  build(s, P) {
    backdrop(s, P.bg);
    P.items.forEach((t, i) => {
      const card = panel(s, { left: "90px", top: 420 + i * 380 + "px", width: "900px", height: "320px", display: "flex", alignItems: "center", justifyContent: "center" });
      s.el("div", { fontFamily: FONT, fontWeight: String(W8.title), fontSize: "96px", color: C.ink, letterSpacing: "-0.03em" }, card, t);
      enter(card, 300 + i * 450, "rise");
    });
  } });
```
Stage helper: `s.el(tag, css, parent, text)`, `s.img(src, css, parent)`, `s.video(src, css, parent)`.
Helpers you can reuse: `footage(s)` (their face, full screen), `faceBottom(s)`, `topHalf(s, bg)`,
`backdrop(s, bg)`, `panel(s, css, parent)`, `pill(s, parent, x, y, text, css)`, `node(s, parent, cx, cy, {icon, label, sub, w, dark})`,
`lines(s, parent, w, h, [svg paths], start, gap, colour)` (draw-on), `ring(s, parent, x, y, w, h, delay, colour)`,
`textLine(s, {top, size, weight, colour, shadow})`, `words(s, line, text)`, `cleanRise(el, delay)`, `blurRise(el, delay)`,
`enter(el, delay, kind)`, `shine(el, delay)`, `chunks(s, [[text, ms]], {top, size, enterFx: softFade, end})`, `hideAt(el, ms)`, `icon(i)`.
Use Web Animations (`el.animate`) with `fill: "backwards"` for entrances so the scrub bar can park any
moment. Easing names: `EXPO`, `GLIDE`, `SMOOTH`, `PUNCH`.
