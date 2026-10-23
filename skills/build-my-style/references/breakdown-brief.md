# Breakdown brief (one sub-agent per reference reel)

Fill the brackets and send one copy per reel, all in one message so they run in parallel (at most 3 at
once; Sonnet is fine, the brief is step by step). `prep_refs.py` has already made every file they need.

Why it's written this way (lessons from the session that built this skill):
- **We learn mechanics, never visuals.** The creator the skill was built for loved a reel's real
  macOS-folder-plus-emoji icons; the first round copied them and he said "that's like a direct copy,
  mate". What carries over is HOW things move and WHEN (timing, easing, layout zones, pacing, sizes,
  real assets vs code-drawn), not what the reference literally shows.
- Agents lose old images from context on long reels. Notes go to a file every 3 sheets.
- Agents can't hear. Sound is "unknown, check by ear" unless it's visible (a waveform isn't).
- Font names are guesses. Describe letter shapes; the font is chosen later by the person in a font round.
- Small thumbnails make numbers drift. Measure on `stills/` (full size).

---

```
You are breaking down the EDITING of ONE short-form reference video so a later step can design a
creator's own editing style. The creator likes this about it: "[WHAT THEY SAID THEY LIKE]".
Your job: an exact, timestamped log of how this edit works. Do not spawn other agents. Do not
re-encode the whole video: prep already did the heavy work. Plain English, no em dashes.

Files (quote paths, they may contain spaces):
- Video: [REEL PATH]   ([W]x[H], [FPS] fps, [DUR] s)
- [A]/info.json      size, fps, length, loudness, cut times
- [A]/sheets/        contact sheets, 4 frames a second, 12 tiles (3 s) each, left to right, top to bottom;
                     the file name gives the time range
- [A]/stills/        full-size frames just after each cut (-cut) and 10 evenly spaced (-even)
- [A]/words.txt      "[seconds] word" per line (may be missing; speech models stretch words over pauses)
- Notes file (yours): [A]/notes.md

Method:
1. Read info.json and words.txt first.
2. Look at EVERY contact sheet in order with the Read tool. Never skip or sample. After every 3 sheets,
   APPEND what you saw to notes.md (time, what changed, the word it lands on). The notes are your memory.
3. For anything that moves (an entrance, a zoom, a transition, a caption animating), make a 12 fps strip
   of that 1-2 s and measure it: how far it travels, how long, the easing (snaps, or fast then slow,
   or slow both ends), blur or not, how it leaves.
   ffmpeg -v error -y -ss T -t 1.5 -i "VIDEO" -vf "fps=12,scale=360:-2,tile=6x3" "[A]/drill/tT.jpg"
4. Positions and sizes: measure on the full-size stills as a share of the frame (e.g. "caption centre at
   y 66%, text height 4% of frame width"). Colours: sample pixels if it matters:
   ffmpeg -v error -ss T -i "VIDEO" -vf "crop=1:1:X:Y" -frames:v 1 -f rawvideo -pix_fmt rgb24 - | xxd -p
5. Fonts: describe the shapes (weight, width, tracking, case), don't name a font as fact.

Write [A]/breakdown.md (build it from notes.md):
1. Summary: length, cuts, an edit event every N seconds, layouts used and their share of the runtime.
2. Timeline table: time | word it lands on | type (cut / zoom / caption / title / graphic / screenshot /
   screen recording / transition / other) | exact details.
3. Systems, one short section each, with numbers: layouts (face full / split / full-screen visual),
   captions (words per chunk, case, size, position, colour, shadow or box, how they enter), accent or
   title text, zooms and framing, graphics (real assets or code-drawn, entrance, exit, where they sit
   relative to the face), transitions, background colours, opening 3 s, ending.
4. The mechanics worth borrowing: 5-8 bullets, each phrased as a rule that could apply to ANY creator's
   brand ("visuals land on the exact word, about 0.1 s before it", "one accent colour only",
   "push-ins on screenshots are under a second"). Never "use folder icons with emoji".
5. What NOT to copy: anything that is this creator's own look (their icons, colours, font, props,
   catchphrases).
6. Unclear: what you couldn't tell. Sound effects and music are "unknown, check by ear".

Reply in under 150 words: the 5 most useful mechanics, and the path to breakdown.md.
```

## After the agents report

Read every breakdown.md yourself. Then tell the person, in plain words and under 120 words:
what all their references share, and which of those mechanics round 1 will use. Never present a
guess as measured or a sound as heard.
