# Graphics recipe book: turning a spoken idea into a Kallaway diagram

## The method (do this for every stage line)
1. **Name the idea in 2-4 words.** "Effort controls thinking." If you can't, the line is a full-layout
   breather, not a graphic.
2. **Pick the shape** from the table below. One graphic per idea, not per sentence.
3. **Write the title**: the idea in bold words + ONE serif accent on the key word; the claim (if
   there is one) on a red box. Keep it under ~6 words a line.
4. **List the beats**: every noun, number, name or verb that can be SHOWN gets an element that lands
   on its word (`at(i)`). Aim for a new element or camera move every ~1-1.5 s. Long gaps get a
   camera move toward what is coming.
5. **Plan the camera**: the scene is one 2D world; push toward each new element (x1.1-1.5),
   pan to the next part of the world for the next idea (with a whoosh).
6. **Nothing leaves.** Old elements stay, get dimmed, struck through or recoloured.
7. **Revisits**: a recurring "home" graphic (the list, the loop) comes back finished and adds one
   new thing within 0.6 s. Build it once and mount it several times with `vars` (plan.json `src`).

## Shapes
| The speaker says... | Shape | Beats |
|---|---|---|
| "X just dropped / launched / released" | the thing as an object (document, app card, phone screen) dropping in, its name as a red pill | drops on the verb, pages fan out on the noun, pill + pulse on the name |
| "N things / N steps / N mistakes" | N big numbered cards in a row = the HOME graphic | cards blur in staggered on the number; the "last one"/key one turns red with a pulse |
| "Number 2..." | revisit the home graphic | card 2 lights red, camera snaps to it, a glass label names the step |
| "Stop doing X" / "don't say X" | a real-looking UI (chat box, email, settings) where X is typed live, then struck through in red | typewriter over the words, red strike on the last word of X, small red "Not needed" tag |
| "It does X on its own / automatically" | a meter, dial or progress bar that moves BY ITSELF | meter appears on the subject, moves low/high/settles across the sentence, pill "On its own" |
| "X is the setting/knob that controls Y" | a slider or dial with labelled stops + the thing it controls growing with it | knob snaps on the value word, the controlled visual scales as the knob sweeps |
| "the sweet spot / trade-off between A and B" | two glowing curves crossing (A rising white, B falling magenta), red dot at the crossing | axes draw, curves draw left to right, dot + "Sweet Spot" pill on the words, A/B label pills on their words |
| "Before vs after" / "old way vs new way" | two columns or a split card; old in grey with a red X, new in white | old side first, strike, new side builds |
| "X grew to N" / numbers | a counter ticking along a curve, red pill with the number | the curve draws while the number counts, lands on the number word |
| "Tell it / give it / include..." (a recipe) | a prompt card that fills like a checklist | each item types in with a red tick on its word; the key item gets a red-bordered field; a serif "Done"-style stamp at the end |
| A named tool or product | its icon big (~270 px) with a red pulse, then shrinks under the title | icon on the name, pulse, then the demo/screen card |
| A process "A then B then C" | nodes on a line with label pills, a stroke drawing between them | node + pill per step on its word, the connecting stroke draws as he moves on |
| A screen recording exists | a screen card (2 px red border) with the real screen scrolling | unfold from a sliver, keep it scrolling the whole time |

## Worked examples (this skill's own proof reel: `template/examples/`)
| Line | File | What it does |
|---|---|---|
| "Anthropic just dropped a prompting guide for Opus 5.5," | `guide.html` | 2-line hook title builds in 0.5 s; guide page drops on "dropped"; two pages fan out on "prompting guide"; red "Opus 5.5" pill + pulse on "Opus"; camera leans in on "5.5" |
| "3 things in it are going to flip how you use it, especially the last one." | `three.html` | numbered cards 1/2/3 blur in on "3 things"; real 3D flip on "flip"; claim words fill a red box; camera pushes to card 3, which turns red on "last" |
| "Number 1/2/3," | `home.html` (mounted 3x with `B.step`) | revisit: card N lights red + camera snaps; finished steps ticked; glass label names the tip |
| "stop telling it to think carefully. Opus 5.5 already decides how much to think on its own." | `tip1.html` | chat composer types "Think carefully about this bug."; red strike + "Not Needed"; pan to sunburst + Opus pill; 12-segment thinking meter moves by itself; "Decides On Its Own" pill |
| "start on medium effort ... the setting that controls how hard Claude thinks ... medium is a sweet spot with performance and speed" | `effort.html` | slider snaps to Medium; title scrambles on the return from the face shot; knob sweeps while thinking bars grow; pan to crossing Performance/Speed curves with a red sweet-spot dot |
| "tell it what done looks like. Give it everything you want to accomplish and what the final outcome slash goal looks like." | `tip3.html` | prompt card fills a checklist with red ticks; red-bordered "Final outcome" field types; red "Goal" pill; tilted serif "Done" stamp with a pulse |

Copy the closest example into `<work>/scenes/`, keep its structure, change the content and the
word indices. Never copy real company logos; a simple orange sunburst for Claude is fine.

## Quality bar (check every scene snapshot at full size)
- One focal point at a time; generous spacing; everything centred or on a clear grid.
- Text a viewer must read >= 28 px; titles 60-74 px; nothing in y > 1200; title top >= 200.
- Real-looking UI beats decorative shapes. No glow blobs, no sparkles, no gradients for decoration.
- If a frame mid-move looks broken (half-scrambled title, element caught mid-blur at a cut), shift
  the beat so the cut doesn't land on it.
