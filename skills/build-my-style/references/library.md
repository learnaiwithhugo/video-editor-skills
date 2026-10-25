# The animation library (`page/library.js`)

Every option is drawn on a 1080x1920 stage (real video pixels) in the person's brand. `C.paper`,
`C.accent`, `C.soft`, `C.deep`, `C.ink`, `C.text` (caption colour) and `FONT` come from brand.json;
`W8.title/caption/label` are font weights; `CAP_SHADOW` is their locked caption shadow; `SHINE` and `ZOOM`
are their locked labs (used automatically once locked); `ICONS` their app icons; `LINES` the preview words
(`captions`, `accent`, `intro`, `talk`, plus `headline` [2 lines], `word` [one short word], `stack` [lines, the last one in the
accent], `title` [2 lines] and `hook` [the words round their first app's name]; `brand.py --lines` sets any of them, and `stack` and
`word` are made from `intro` when not given). New sections reuse these, so their niche's words show up everywhere.

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
| behind-headline | Text behind your head | top 260, caps true, lines [small line, huge line] | big headline behind your head: small white line over a huge accent line (layers: footage, text, then the cut-out of you on top) |
| behind-word | Text behind your head | top 300, size 250, caps true, word | one huge white word behind your head (shrinks to fit, never wider than 940px) |
| behind-stack | Text behind your head | top 280, rise blur/clean, lines | white lines on top, the last line in the accent underneath, behind your head |
| behind-site | Text behind your head | top 250, shot site/repo | your website screenshot as a rounded card behind your head |
| hook-behind-head | Text behind your head | top 250, name (first app), hook [before, after] | a small line, your first app's name huge in the accent, a small line, all behind your head, with the real app icon floating in front |
| headline-stack | Headline: white on top, accent underneath | rise blur/clean, three false/true, top 260, lines | no box: white top line(s), the last line bigger in the accent, locked caption shadow. `three` = the intro words as small white / big white / accent |
| explain-layers | Clean explainers | title, lead "and there's 3 layers", part "Layer One", rows[3], glyph, bg, caps | full-screen concept card, a cube whose 3 layers light up one by one, hard cut to a split with a diamond tile and a title that ghosts in, title and tile shrink up and a 3-row card rises under them |
| explain-path | Clean explainers | bg, caps, caps2 | their first app icon, a light beam sweeping, a winding road drawing up with flags, hard cut to a split with a goal marker |
| explain-pills | Clean explainers | title "The Plan", glyph, pills[2], bg, caps | title and diamond, the camera glides, two dark pills branch off, a card of their thumbnails and photos fills in |
| explain-tool | Clean explainers | name (first app), icon 0, bezel false, bg, caps | tool intro: clean screen, the real app icon in the middle, its name ghosts in above, then profile pills and a grid of video tiles build underneath as the camera glides |
| explain-folder | Clean explainers | file, left, right, one, bg paper, caps, caps2, caps3 | a real Mac folder (assets/folder.png, drawn one if missing) with two files sticking out that flashes red, then "40 files" vs "100 apps" sliding in from each side of a line with tags, hard cut to "Just One" and a single app tile |
| photos-flash | Real images | count 4, every 1300, top 250, caps | square photos flash above your head with hard cuts every ~1.3 s, white captions under. No photos yet = neutral boxes saying "your photos go here" |
| hook-logos-photo | Real images | top 260, sub, title | the hook: two real app icons (as they are, only a drop shadow) and a real photo (square, just appears) over a title |
| text-fade | Text fades | from ink/deep/accent/text, to paper/accent/soft, start 52, size 210, top 730, lines | a 2-line title, solid at the top of each line, melting into paper or the accent at the bottom |
| text-fade-locked | Text fades | lines | uses `locked/text_fade.json` exactly (its `background_image`, size, height, weight, spacing, background). Add it to a round only after they locked a text fade; without the lock it shows the plain fade with a "text not locked yet" label |
| cta-keyword | CTA | keyword "STYLE", lead "comment", top 280, size 230 | `comment "STYLE"` over your face: quote marks in the accent, the keyword white, blur rise |

`entrance` values: `fade` (600ms), `rise` (46px glide, 850ms), `slow` (the same glide over 1.5 s),
`blur` (34px + 18px blur to sharp, 560ms). `bg`: `paper`, `accent`, `soft`. Never black. The clean explainers also take
`bg: "tint"` (their paper with 7% ink in it, the default there) and use dark cards made from their ink.

**Images, always:** photos, thumbnails and screenshots used as photos have square corners (`border-radius: 0`) and never
zoom or push in; they appear with a hard cut (`cutWindow`) or a plain fade. Only a card for a website or a screen may be
rounded. App icons are shown as they are, with only a drop shadow (no tile, bubble or frame round them).

**Optional assets other scripts make** (checked once per page load; a missing one never breaks an option, it shows a neutral
stand-in and a small label): `assets/face-cutout.webm` (Chrome) and `face-cutout.mov` (Safari), the person cut out of
`face-loop.mp4` with see-through background, for the "Text behind your head" options; `assets/photos/photos.json` (a list of the
file names in that folder) for "Real images" and the card in `explain-pills`; `assets/folder.png` for `explain-folder`;
`locked/text_fade.json` for `text-fade-locked`. A missing file shows up as a 404 line in `shot.mjs`'s `errors`: that is the
check telling you the asset isn't made yet, not a bug in the page. After an asset is made the person refreshes the page (it is
checked once per load).

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
moment (never `setTimeout` for anything you can see). Easing names: `EXPO`, `GLIDE`, `SMOOTH`, `PUNCH`.

### Helpers added with the newer sections (all in `library.js`)
Colour and text: `mixHex(a, b, t)` (t of a, the rest of b), `onAccent()` (white or ink, whichever reads on the accent),
`sceneBg("tint"|"paper"|"soft")` (their paper or a very light tint of it, never black), `darkFill()` (dark cards from their ink),
`fitSize(text or [lines], size, {maxW 940, weight, ls})` (shrinks until the widest line fits, measured with their real font),
`fadeFill(el, from, to, start)` (text solid on top, melting into `to`), `wordsRise(s, parent, text, at, gap, "clean"|"blur")`,
`evenCaps(list, a, b)` (spreads caption chunks over a time range as `[text, on, off]`).
Optional assets: `ASSET` (what exists), `PHOTOS` / `photoAt(i)` (their photos), `photoBox(s, parent, src, css, pos, slot)`
(square-cornered photo, or a "your photos go here" box), `notice(s, text, top)` (small honest label for a missing piece).
Text behind your head: `behindHead(s, () => headline(...))` (footage, then your text, then `cutout(s, footage)` on top, kept in
sync with the footage; says "cut-out not made yet" if the file isn't there), `headline(s, [[text, size, colour], ...], {top, rise, gap})`.
Clean explainers: motions `cutWindow(el, a, b, T)` (hard cut in at a, out at b), `camera(el, T, [[at, dur, "translate() scale()"]])`
(the camera glides then holds), `ghost(el, delay)` (a word appears faint and soft in place, then firms up, no movement),
`tileIn(el, delay)` (comes out of a blur settling from slightly big, no overshoot; not for photos), `slideIn(el, delay, x, y)`,
`floatIdle(el, delay, amp, dur)` (finished pieces float gently); pieces `fullScene(s, T, a, b, bg)`, `splitScene(s, T, a, b, bg, face)`
(returns the top half to draw in), `camLayer(s, parent, origin)`, `ghostTitle(s, parent, [lines], top, size, at, gap)`,
`diamond(s, parent, cx, cy, w, glyph)` (glyphs: book, brain, spark, target, bolt, chat), `appTile(s, parent, cx, cy, size, src, {bezel})`,
`wires(s, parent, [paths], start, gap, colour)`, `darkPill`, `tagLabel`, `capPill(s, parent, top, [[text, on, off]])` (caption pill in
the accent), `fileDoc`, `folderArt(s, parent, size)` (its `.flash` is the red overlay), `layerCube(s, parent, cx, cy, size, at)`.
