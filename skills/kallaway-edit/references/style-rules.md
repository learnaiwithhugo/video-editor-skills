# Style rules (the Kallaway look as build numbers)

Measured frame by frame from three Kallaway reels on 1080x1920 frames. Where the kit already
encodes a number (`template/kit/kw.css`, `kw.js`, `scripts/build.py`), the file is named.

## 1. The whole style in one breath
Two layouts, hard-cut between them on word onsets. **Stage**: a black dotted stage fills the top
two thirds with ONE animated diagram of what is being said right now, a one-chunk caption sits in
the gap, the speaker sits in a rounded card at the bottom with their head popping out over the card
edge. **Full**: the speaker's face fills the frame, no graphics, used as a breather. Something new
on screen about every second. White heavy-grotesk captions, red as the only accent, one serif
italic word for emphasis, no music.

## 2. Layouts (build.py places all of this)
| | Stage (67-80% of the runtime) | Full (16-29%) |
|---|---|---|
| Background | `#020202` edges to `#0A0A0A` centre, dot grid 16 px pitch, ~2.3 px dots, `#464646` at 55% | the footage |
| Speaker | rounded card x 68-1012, top y 1404, radius 40, runs off the bottom; no border, no shadow | face-filling crop, head top ~y 60, eyes ~30%, mouth ~45% |
| Pop-out | cut-out of the speaker drawn over the card edge: head rises ~100 px above y 1404 | off |
| Caption centre | y 1236 (in the gap) | on the chest, just under the chin (build.py measures it, max 1420) |
| Graphics | own y 160-1200, never touch the face | none, ever |

- Horizontal 4K source: the card shows the whole wide frame scaled down; the full layout is a ~3x crop.
- Tight vertical selfie (the usual phone shot): NEVER a face crop in the card (it reads as a zoomed
  selfie). The footage is scaled DOWN so hair-to-chest fits the visible ~516 px (head centred, hair
  popping ~40 px over the edge, chin and shoulders visible) and a blurred, darkened copy of the same
  footage fills the card's sides (dark like Kallaway's room), with soft shadows on the seams.
  build.py decides this automatically from `headtrack.json` (head height x card scale > 75% of the
  visible card) or by `plan.json geometry.card_fit: "head-shoulders" | "fill"`.
- Full layout from a vertical source: a 1.15-1.35x crop anchored to the bottom (head top ~y 60).
- Per shot, the head's highest point is kept under the caption line.
- **Hard cuts only.** No dissolves, wipes, flashes, whip-pans between shots.
- **Cuts land on word onsets**, 0-80 ms before the word, on the first word of a sentence or clause.
- Average shot 3.3-3.9 s. Kallaway hard-cuts between stage scenes too, not only stage/full.
- Full layout lines: connective and personal ("But", "So", "which is...", the problem, the caveat,
  the payoff line). Never while a thing is being shown.

## 3. Captions (build.py writes them)
| | |
|---|---|
| Font | Inter Tight 800 (free stand-in for Helvetica Now Display Bold), 58 px, tracking -0.035 em |
| Colour | white, no stroke, no box, no shadow |
| Chunk | 1-3 words, usually ONE content word; small function words ride with the content word after them ("for Opus 5.5", "a prompting"); product names stay whole |
| Text | exactly as spoken, punctuation kept, digits for numbers ("Number 1,", "3 things", "Opus 5.5") |
| Highlight | none: no colour change, no pill, no karaoke |
| Emphasis | ONE key word per section in Instrument Serif Italic at 66 px (plan.json `captions.emphasis`) |
| Timing | hard swap on each word's onset; a chunk holds through pauses until the next word; laid out centred in advance so unspoken words are invisible gaps |
| Safe zone | never below y 1470, never in the right 100 px below y 1155 |

## 4. Titles (inside scenes)
- Top of the stage, centred, top edge y 200 (clear of Instagram's header): one line 60 px, two
  lines 74 px, line-height 0.92, tracking -0.04 em. Class `kw-title` (`two` for two lines).
- Formula: bold grotesk words + ONE serif italic accent word: "Start On *Medium* Effort".
- The claim goes on a red box (`kw-redbox`, `#C41514`, 6 px radius) or a 5 px red underline drawn
  left to right. Hook titles: two lines, first white, second red text.
- Enter word by word, blur from grey, 0.07-0.25 s apart, timed to speech (`KW.title`). A title swap
  inside a scene is a ~0.45 s letter scramble (`KW.scramble`). Once landed, a title is dead still,
  so titles sit OUTSIDE the scene camera.

## 5. Graphic building blocks (kw.css)
- **Label pill** `kw-pill`: white `#FAF7F9`, black 800 30 px, 7 px radius. Grows out of a sliver
  in 0.2 s, ease-out, landing 0-0.15 s before its word (`KW.pill`).
- **Glass pill** `kw-glass`: frosted dark grey gradient `#4B4949` to `#3B3B3B`, 1.5 px light edge,
  white bold text. Stack vertically for lists.
- **Red pill** `kw-redpill`: glossy red, full round ends, 58 px tall, white bold; scale from a
  sliver plus a letter scramble (0.3 s). One per spoken product/term.
- **Numbered step labels + home graphic**: big numeral + word, on a recurring "home" graphic the
  video returns to at every step (revisits come back finished and add exactly one new thing in 0.6 s).
- **Screen card** `kw-card`: rounded ~20 px, 2 px red border `#B0121E`, real screen content
  scrolling the whole time; unfolds from a horizontal sliver (0.15 s) or slides in from the right.
- **Diagrams**: white axes and node dots, curves drawn left to right (`KW.draw`) with a soft glow.
  Red = the old/bad idea; magenta `#E01BE0`, yellow `#FAE000`, purple `#A703C5` allowed only as
  colour codes INSIDE a diagram.
- **Mockups**: documents (`kw-paper`), chat boxes (`kw-panel`), phones, profile cards with ticking
  counters (`KW.count`). Draw real-looking UI; never copy a real logo pixel for pixel (a simple
  orange sunburst for Claude is fine).
- **Red pulse** `kw-pulse`: soft radial red disc that grows and fades in ~0.45 s when a named
  thing lands (`KW.pulse`).

## 6. Colour
Red `#C41514` is the ONLY accent (boxes, pills, borders, underlines, pulses, the claim). White
`#FCFAFB` for structure and text. Orange `#D97757` only for a Claude-style mark. Never colour in
captions or titles other than white/red.
**Measured share (2026-10-22, `scripts/match/fingerprint.py`):** red is only 25-45 % of the strongly
coloured stage pixels in Kallaway's reels; the rest are per-diagram colour codes (magenta paths
`#E01BE0`, yellow time bars `#FAE000`, purple fills `#A703C5`, gold/green labels, blue screen recordings).
Our first edit hit 93 % red and read as "all red". Give each diagram one non-red colour code for its
data, and keep red for the claim, pills, borders and pulses.

## 7. Motion
- **Enter**: blur-in from ~18 px blur, scale 0.94, grey, `expo.out`, 0.1-0.3 s; strokes draw along
  their path; stagger 0.04-0.15 s.
- **Virtual camera**: each diagram is one 2D world with a camera that pans/zooms x1.1-1.5 to the
  new element: fast start, long settle, motion blur at peak (`KW.cam`).
- **Exit: nothing animates out.** The next cut ends the scene.
- **Density**: a new element or camera move every ~1-1.5 s, timed to words.
- **Face zooms** (rare): a snap punch-in x1.19 in ONE frame on a closing phrase, preceded by a
  0.65 s riser that stops dead on the snap (plan.json `punch`); or a slow push 100-105% across a
  2-4 s full-layout line (shot `push`). Default: locked off.

## 8. Sound
- Voice compressed and loud: -14 LUFS integrated, true peak -1 dBTP (assemble.py and render.py).
- Every animation gets a real recorded sound, landed on its frame, 10-16 dB under the voice:
  whoosh on camera moves and cuts, pop on every pill/label/numeral, click on snaps and ticks, typing
  on typed text, impact on the 2-4 big moments, riser into a punch-in, sparkle on a payoff. The
  full table: `references/sound-map.md`.
- Kallaway uses no music. This skill adds a quiet CC0/CC BY lofi bed by default (ducked 21 dB under
  the voice, faded out over the last second); `music: off` matches Kallaway exactly.

## 9. Opening and ending
- Frame 0 is live: layout in place, the hook starts on frame 0, a title restating it builds word
  by word within 0.5 s. First cut at 1.75-3.7 s. No logo, no intro card.
- Ending: a CTA card ("Comment *Keyword* To Get The ...", keyword in serif italic, second line red)
  holding to the last word; or, with no CTA, end on the payoff line. No outro, no fade.

## 10. Pacing targets
| | Kallaway | check |
|---|---|---|
| Words per minute | ~240 | cut every pause (assemble.py `--max-pause`) |
| Edit event | every ~1 s | count cuts + scene beats |
| Average shot | 3.3-3.9 s | build.json |
| Full-layout share | 16-29% | printed by build.py |
