# Merging the breakdowns into one style guide

You (the lead) do this yourself: it needs judgement and your own eyes. Inputs: the 2-3 `edit-log.md`
files, `prep/*/fingerprint.json`, `style-spec.json`, `font-match.md`, and the stills.

## Rules for merging
- **All reels agree = a rule.** Two of three = a rule with the exception named. One reel only = an
  "optional move", never a rule.
- **Numbers come from measurements**, in this order: `style-spec.json` (measured the same way on every
  reel) > full-size still measurements in the logs > anything read off contact sheets.
- **Look before you write.** Build a key-frames sheet (8 frames covering every layout and graphic type,
  from `stills/`, tiled 4x2 with ffmpeg xstack) and look at it at full size. If a log says something you
  can't see, it doesn't go in.
- **Sound:** stereo hits from `audio.json` say effects exist and roughly where; whether there's music
  and what the effects sound like waits for the ear check. Never state sound as heard.
- **Fonts:** take the `font_match.py` winner (free font, weight, tracking) and say how close it scored
  against the reference (and the benchmark).

## The style guide's sections (write `<style>-style-guide.md` in this order)
1. The whole style in one paragraph.
2. Layouts: each with geometry in px and %, share of runtime, when it's used, how it switches.
3. Captions: table (font match, size, colour, chunk, text rules, highlight, emphasis, animation).
4. Graphics: the core rule, titles, every building block with exact colours, colour roles, motion.
5. Zooms on the face. 6. B-roll. 7. Sound (inferred, until the ear check). 8. Look.
9. Opening and ending. 10. Pacing numbers per reel (table).
11. **What this means for filming**: what the footage must look like for this style to work (framing,
    orientation and resolution for crops, light, background, wardrobe). This section mattered most on
    the first build: the edit was right, the footage was the gap.
12. Not certain.

Save it as `ROOT/references/<style>/<style>-style-guide.md` and the sheet as `<style>-key-frames.png`.
Show the user the key-frames sheet (open it on their Mac) and the one-paragraph summary.
