# Locking a style (make edits come out looking like the references)

A new style skill is a first draft until it passes these, in order. Log every number in the style
skill's `references/lock-log.md`. Stop when the numbers stop improving; don't loop forever.

## 1. Match score (minutes)
After the first test edit renders:
`PY "<style>-edit/scripts/match/fingerprint.py" score "<style>-edit/references/style-spec.json" "<edit.mp4>" --out WORK/progress/NN-match.md`
Every FAIL line says what to change (style.json numbers, the kit CSS, or the edit plan). Fix, re-render
(~1.5 min), score again. What it checks: cut rate, average shot, visual changes per second, layout
shares, card position, caption position per layout, caption size, caption pace, accent colour share,
stage background colour, loudness, peak, stereo sound-effect density.
Known limits: a FAIL caused by the footage (a close selfie pushes the full-face caption down, a dark
side fill makes the card read narrower) is reported to the user as a filming note, not "fixed" by
breaking a rule such as covering the face.

## 2. Font match (seconds)
`PY scripts/font_match.py <reference.mp4> <words.json> <out>`: the winner goes in the kit CSS and
style.json (caption_px stays measured; set tracking from the match). Check `font-match.png` by eye.

## 3. Golden test (the real lock, ~20-40 min)
Pick a 5-10 s reference window that shows the style's signature (a graphic layout with a caption, a
layout switch). Rebuild it with the style skill using the reference's own audio and words:
cut that window from the reference into `WORK/golden/cut.mp4` (it is the "raw clip"), take the words
from prep, build the same scene(s) the reference shows with the style's components, and render. For
the face layer, use the reference's own face area where the layout allows (the card region below the
caption never carries captions). Then:
`PY scripts/golden.py <reference.mp4> <start> <end> <recreation.mp4> WORK/golden`
Scores per region (whole frame, stage, caption band, card), SSIM 1.0 = identical; unrelated content
scores ~0.68. Fix the biggest gap first (usually the caption band or the card), re-render, re-score.
Show the user `golden.png` before and after.

## 4. One critic round (one round, then the human)
Hand a fresh sub-agent (Sonnet is fine) the first full edit, the key-frames sheet and the style guide.
Brief: per layout, put our frame next to the closest reference frame and list every visible difference
(position, size, colour, font, motion, density), most visible first. Fix what's real. No second round:
the user decides from here.

## 5. Ear check (the user listens once)
No agent can hear. Ask the user to watch ONE reference reel with sound and answer: "Is there music under
the voice? Do you hear whooshes, pops or clicks when graphics move? Anything else (risers, bass hits,
typing)?" Write the answers into the style's `references/sound-map.md` and `style-rules.md` (Sound), and
the lock log. Then ask them to listen to the test edit: too loud, too quiet, too many, too few.

## 6. Sign-off
Show the user the final test edit, the match score and the golden strip. The style is locked when they
say it looks like the reference. Record it in the lock log.
