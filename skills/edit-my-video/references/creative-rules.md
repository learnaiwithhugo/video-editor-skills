# Creative rules: how to design an edit

The style folder says how things LOOK and MOVE. You decide WHAT to show, fresh, for every line. The user's
STYLE.md always wins over anything here; the defaults below are the taste this skill was built on (the
creator who built it), and a STYLE.md can switch any of them off.

## Design every beat fresh
For each line, before reaching for any layout, answer three questions:
1. What is the one idea in this line? ("it can only do three things", "GitHub is a giant public Google Drive")
2. What would a viewer need to SEE to get it in one second? A real thing beats a drawing: the real page, the
   real app icon, the real number, their own footage.
3. What did the last beat look like? Do something different now (layout, background, scale, motion).

Ideas are not templates. "Three things" could be three big cards landing one per word, three real icons
dropped into place, a dial snapping between answers, or a sorter dropping items into buckets. A checklist
is only right when the speaker is literally ticking things off. When a template from the style page fits
perfectly, use it; when it's merely available, design something better.

Rhythm across a reel: face / split screen (visual on top, face below) / full-screen visual, switched with
hard cuts. One move per video at most slides (split screen into a full-screen visual, the accent panel
coming down). Something new on screen every 1 to 2 seconds while they talk; let the face breathe on the
personal, punchy lines.

## Make visuals big and well placed
The second test edit's one weakness: full-screen visuals sat small at the top with a big empty space below.
- A full-screen visual owns the frame: its built state spans at least ~40% of the safe height and sits
  around the middle (the self-review checks this). Build top-down if you like, but don't leave an empty
  white card waiting for content; centre what's there and move it up to make room (a quick glide).
- In a split screen the visual fills the top half. Screenshots fill the width; icons are 340 to 460 px.
- Intro text needs air: at least ~30 px between lines, the hero word clearly the biggest thing.

## Hard taste checks (defaults; qa.py enforces the starred ones)
| Rule | Why |
|---|---|
| * No pop-in or scale-overshoot entrances. Use rise / fade / blur rise / focus-in from the kit. | Pop-ins look AI-made. |
| * No black backgrounds behind visuals. Background colour or accent colour. | Not the brand. |
| * No underlining. Emphasis = the accent colour, size, or the locked shine. | Rejected. |
| * No em dashes anywhere on screen. | |
| * Never the same visual layout twice in a row (`data-visual`). | Repetition reads as a template. |
| * Captions only say words the speaker says, spelled right, timed to the words. | Trust. |
| * Every number or name on screen matches what's said. | Trust. |
| * Text inside the Instagram safe zone: not in the top 220 px, not in the bottom 420 px, not under the right-hand buttons (x > 940 between y 1000 and 1500). | The app covers it. |
| * Full-screen visuals big and centred (see above). | |
| Real logos, app icons and screenshots only. Pages screenshotted after they FULLY load (no grey bars). Mac apps: `shoot.py icon`. | Redrawn logos look fake. |
| Logos in pairs are tilted and overlapping (front one about -6 deg, the other +7 deg, tucked behind and lower), never side by side and dead straight. | Uniform looks like a template. |
| Push-ins on visuals are fast: under a second. | Pace. |
| Face zooms are long and smooth: cut in at 120% and glide out over ~3.5 s (the locked main zoom). Now and then a quick clean punch (115% in 0.75 s) or a subtle hard punch on a strong line. | The creator's locked feel. |
| Hard cuts between modes, with at most one slide (split into full screen). | |
| Sound effects barely noticeable, at the levels in sfx.json. If one is clearly audible, it's too loud. | |
| Captions never cover the mouth. On close selfie shots that usually means above the head. | |
| No text shadow under see-through (shine) text: it turns the colour muddy. The kit handles this. | Found in testing. |

## Captions
Default: plain white with the locked shadow, 2 to 3 words, soft fade-up, swapping as they talk. Over a busy
or bright background (a website, a white scene) use the accent box or frosted box (`cls: box | frost`), on
the seam between visual and face in a split screen. One key word may go in the accent colour (`<b>`), but
check it reads on the background behind it (accent on a light wall disappears). Skip captions when on-screen
text already says the words (an intro hero line, a pill that reads the same sentence).

## What the creator loved and rejected (the original style, as examples of taste, not as templates)
Loved: the blur rise, the slowed clean rise, the hero word focus-in with the shine, real app icons tilted and
overlapping, the tree with real thumbnails, frosted accent glass and solid accent boxes on the seam, the fast
push-in, the cut-in-zoomed slow zoom out, the shutter crunch on cuts, the second test edit where every visual
was designed for its line.
Rejected: pop-ins, step-flow diagrams (boring, AI-looking), black and navy boxes, underlines, redrawn logos,
straight side-by-side logos, whip zooms and constant jump cuts, slow drifting push-ins, loud sound effects,
a checklist used just because it existed, small visuals floating at the top of an empty frame, cramped hook
text.
