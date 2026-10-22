# Breakdown brief (one sub-agent per reference reel)

Fill the brackets and send one copy per reel, all in one message so they run in parallel (Sonnet is
fine: this brief is step by step). Prep has already made every file they need, so they never run
heavy tools. This brief is the one that produced the Kallaway breakdowns, plus fixes for what went
wrong then.

What we learned from the first run (already built into the brief below):
- Agents lost the first ~17 contact sheets from context on a 36-sheet reel and had to re-check from
  stills. Fix: write notes to a file after EVERY 3 sheets, and build the final log from the notes file,
  never from memory.
- Agents can't hear. Sound claims come from `audio.json` (stereo sound-effect hits, loudness), stated as
  inferred, plus the user's ear check later.
- Font names were guesses (50-65 % confidence). Fonts are now matched by pixels in a later step
  (`font_match.py`), so agents describe the letter shapes and don't need to name the font.
- Numbers drifted when read off small thumbnails. Use `stills/` (full size) and `fingerprint.json`
  (measured) for every position, size and colour.

---

```
You are breaking down the editing style of ONE short-form reel by [CREATOR / STYLE NAME], so a later
step can write a Claude Code skill that recreates this editing style exactly. Your job: a complete,
exact, timestamped log of every editing decision in this ONE reel. You do not write the skill. Do not
spawn other agents. Do not run ffmpeg on the whole video again: prep already did the heavy work.

Files (prep made them; quote paths, they may contain spaces):
- Video: [REEL PATH]   ([W]x[H], [FPS] fps, [DUR] s)
- [PREP]/words.txt            one word per line "[seconds] word" (speech model: words can be stretched
                               over pauses by up to ~0.3 s)
- [PREP]/cuts.txt              hard cuts found on every frame; [PREP]/events.txt smaller visual changes
- [PREP]/sheets/sheet_NNN.png  4 frames a second, 12 tiles (3 s) per sheet, time printed on each tile
- [PREP]/stills/               full-size frames just after every cut + 12 evenly spaced
- [PREP]/audio.json            loudness, stereo sound-effect hits (inferred), music: unknown
- [PREP]/fingerprint.json      measured numbers: layout shares, caption position/size, card geometry,
                               cut rate, accent share. Use these instead of eyeballing positions.
- Notes file (yours): [PREP]/notes.md

Method:
1. Read words.txt, cuts.txt, events.txt, audio.json, fingerprint.json first.
2. Look at EVERY contact sheet in order with the Read tool. Never skip or sample. After every 3 sheets,
   APPEND what you saw to notes.md (time, what changed, which word it lands on). Your context may drop
   old images; the notes file is your memory.
3. For anything that moves or appears (zoom, graphic entering, transition, caption animation), make a
   12 fps strip of that 1-2 s at 540 px into [PREP]/drill/
   (ffmpeg -ss T -t 1.5 -i VIDEO -vf "fps=12,scale=540:-1,tile=6x3" drill/tT.png) and measure: how far,
   how long, easing (snap or smooth), how it enters and exits.
4. Positions, sizes, colours: measure on full-size stills (sample pixels with
   ffmpeg -ss T -i VIDEO -vf "crop=1:1:X:Y" -frames:v 1 -f rawvideo -pix_fmt rgb24 - | xxd -p),
   and cross-check against fingerprint.json.
5. Describe letter shapes (weight, width, tracking, i-dots, single/double-storey a and g, italic serif?)
   rather than naming fonts.

Write [PREP]/edit-log.md (from notes.md):
1. Summary numbers: length, real cuts, average shot, layout shares, zooms, graphics/B-roll inserts, an
   edit event every N seconds, sound (from audio.json, marked inferred).
2. Timeline table, every event in order:
   time (s) | word it lands on (from words.txt) | type (cut / zoom / punch-in / caption change /
   text hook / graphic / B-roll / screen recording / transition / SFX / colour / other) | exact details
3. Systems, one section each with exact numbers and still filenames: layouts, captions, zooms and
   framing, graphics (every type: look, entrance, dwell, exit, position vs the face), B-roll and screen
   recordings, transitions, sound, look (background, light, grade, camera, wardrobe), opening (first
   3 s) and ending (CTA).
4. Patterns: what repeats and the rule behind it ("every list item gets a label").
5. Unclear: what you couldn't determine. Never present a guess as fact.

Reply in under 200 words: the 5 most distinctive things about this edit, and the path to edit-log.md.
```
