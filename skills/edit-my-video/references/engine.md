# The engine: how an edit is built and rendered

One HyperFrames project per video in `WORK/hf/`, a single `index.html` (the pattern both test edits rendered
with). `render.py new` makes it; you write the beats. Invoke the `hyperframes` skill once before the first
render of a session (render contract), and `hyperframes-cli` if a command misbehaves.

## Files
```
WORK/
  style.json          tokens from the style folder (style.py resolve): colours, font files, caption, shine,
                      zooms, motion, picked sounds with levels, safe zone, taste switches
  takes/  edl.json  segments.json  words.json  words.txt  caps.json  cues.json  storyboard.json
  audio/voice.wav     the joined voice at -16 LUFS
  hf/index.html       the edit
  hf/assets/          v/<seg>.mp4 (cut footage), img/, fonts/, style.css, style.js, kit.css, kit.js, mix.wav
  progress/           numbered pictures of every step (the user follows along here)
  qa/report.md        the self-review
  variations/         short slices for A/B/C
```

## index.html shape (start from what render.py new writes)
- Root: `<div id="root" data-composition-id="main" data-start="0" data-duration="<cut length>">`.
- Face footage: one `.scene` per segment, an untimed `.zoom` wrapper (it gets the zooms) around the timed
  `<video class="clip" data-start data-duration src="assets/v/sNN.mp4" muted>`. Split screen: the same, in a
  `.scene` placed at `top: 960px; height: 960px` with the video shifted up (e.g. `top: -560px`) so the face
  sits in the bottom half. Videos are always muted: the sound is the one `<audio id="mix">`.
- Visuals: one timed `.scene.clip` per beat with `data-visual="<name of this design>"` and
  `data-layout="face|split|full"`. Higher `z-index` paints on top.
- Captions: written by `captions.py inject` between the CAPTIONS markers. Don't hand-edit them there; edit
  caps.json and inject again.
- Script at the end: per beat, kit calls at absolute reel seconds taken from words.txt; then
  `K.captions(); window.__timelines = window.__timelines || {}; window.__timelines["main"] = K.done(<length>);`
  (the registration must be written in the page itself or HyperFrames' lint fails).

## The kit (engine/kit.js, loaded as assets/kit.js)
The style's motion feel as calls. All times are reel seconds.
| Call | Use |
|---|---|
| `K.enter(el, t, "rise"/"fade"/"blur")` | any part arriving (cards, icons, pills, thumbnails) |
| `K.words(el, [[w, t], ...], "clean"/"blur")`, `K.wordsAt(el, [t...], kind)` | word-by-word accent or intro lines |
| `K.focusIn(el, t)` then `K.shine(el, t2)` | the hero word (el = `<span class="hero">WORD</span>`, accent colour, locked shine) |
| `K.glideIn(el, t, -1 or 1)` | a line gliding in from the left or right |
| `K.draw(path, t, ms)` | lines and rings drawing on (any SVG shape with a stroke) |
| `K.push(el, t, {fx, fy, scale, tx, ty, W, H, w, h})` | fast push-in to point (fx, fy) of el, clamped so edges never show |
| `K.scroll(el, t, px, ms)` | a page scrolling slowly in a split screen |
| `K.faceZoom(zoomWrapper, t)` | after a hard cut to the face: starts zoomed, glides out (locked main zoom) |
| `K.punch(zoomWrapper, t)` / `K.hardPunch(zoomWrapper, t, until)` | the occasional short punch |
| `K.panel(scene, t)` | the one slide: the full-screen visual comes down over the split |
| `K.both(el, keyframes, t, ms, ease)` / `K.back(...)` | anything custom (fill both / fill backwards) |
Classes in kit.css: `.scene .layer .half-top .half-bottom .zoom .icon .card .shot .pill .label .intro .hero
.cap.plain/.box/.frost/.ink` and colour classes `.bg-main .bg-accent .bg-wash`. Colours as CSS variables:
`--bg --accent --wash --deep --text --font --cap-size --cap-shadow --frost`.

## Gotchas found while building this
- An entrance and a move on the same element: `push`/`scroll` are additive and start from where the element
  is, so an entrance before them still plays. A custom `K.both` with `fill: both` before another animation
  freezes the first frame until it starts (that's what `faceZoom` wants, not what an entrance wants).
- A parent's `text-shadow` under shine text (transparent text with a gradient) turns it grey and muddy; the
  kit's `.hero` turns it off. Same for any custom see-through text.
- Inline-block text that grows (e.g. "Adobe" then "-> ArtCraft") should animate `maxWidth`, so the box
  doesn't sit lopsided around an invisible word.
- Icons that rotate in CSS keep their rotation through `K.enter` (its transform is additive).
- Real GitHub pages have a black header bar: start the screenshot below it (no black on screen).
- Contact-sheet frames are every 0.5 s and can be up to 0.25 s off the label; check exact moments with
  `render.py snap "WORK" 12.18 --name x`.
- `render.py check` hides two warnings that are fine for a one-file reel (dense tracks, nested scenes) and
  contrast warnings on footage are expected; errors must be zero.
- Every HyperFrames call runs with `HYPERFRAMES_SKIP_SKILLS=1 HYPERFRAMES_NO_TELEMETRY=1` and snapshots use
  `--describe false` (nothing is uploaded). Never run `npx hyperframes init` or `skills` (they install skills
  globally).

## cues.json (sound)
`{"cues": [{"t": 3.27, "sfx": "cut", "why": "hard cut"}, ...], "music": {"file": "...", "db": -20}}`.
`sfx` is the role in the sound file's name (`01-cut-shutter-crunch.wav` -> `cut`), or the file name. `t` is
when it should HIT; mix.py lines the file's hit point up to it and plays it at its locked `mix_db`. A `db`
nudge per cue only if one pokes out. Typical: cut on every hard cut and punch, panel on the slide, icon per
app icon, line for lines drawing and clicks, blur for blur rises, hero when a hero word lands, shine as the
shine passes the middle of the word, tick for rings and ticks. Clean rises get no sound.
