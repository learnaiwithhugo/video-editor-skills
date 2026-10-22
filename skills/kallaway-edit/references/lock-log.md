# Kallaway style: lock log

How close /kallaway-edit gets to the 3 Kallaway reference reels, measured. Add a dated entry every time
the style pack changes (style.json, template/kit, references). Tools: `scripts/match/`.

## Match score (scripts/match/fingerprint.py score, spec = references/style-spec.json)
| Date | Edit | Score | Fails | What changed |
|---|---|---|---|---|
| 2026-10-22 | opus-tips v2 | 11/16 | changes_per_s 1.0 (refs 0.54-0.62); card_x0 9.3% (refs 6.3-6.7, dark blurred side fill reads as background); cap_y_full 68.3% (refs 60-65, close selfie: caption follows the chin); cap_changes_per_s 3.05 (refs 2.3-2.5); red_share 0.93 (refs 0.25-0.45) | first measured run |

What the v2 fails mean:
- **red_share 0.93:** "red is the only accent" was over-applied. Kallaway's stage graphics also carry
  per-scene colour codes (magenta paths, yellow time bars, purple/gold/green labels, blue screen
  recordings, orange brand marks); red stays the claim/accent colour but is ~25-45 % of the coloured
  pixels, not 93 %. Next edit: give each diagram one non-red colour code.
- **changes_per_s 1.0:** our scenes have ~1.7x Kallaway's visual beats. Fewer, bigger beats per scene.
- **cap_changes_per_s 3.05:** slightly more one-word chunks than Kallaway; pair function words more.
- **cap_y_full / card_x0:** caused by the close vertical selfie footage. Filming to
  `filming-guide.md` (wide, locked, horizontal 4K) fixes both.

## Golden test (scripts/match/golden.py)
| Date | Reference window | frame | stage | caption | card | What changed |
|---|---|---|---|---|---|---|
| 2026-10-22 | (tool check) v2 vs its own re-render 10-16 s | 0.997 | 0.998 | 0.999 | 0.994 | identical renders score ~1.0 |
| 2026-10-22 | (floor) kallaway-3 44-50 s vs v2 14-20 s, unrelated content | 0.678 | 0.672 | 0.757 | 0.659 | a recreation must sit clearly above this |
Not yet run: a true recreation of a Kallaway window (see new-edit-style/references/lock.md step 3).

## Font match (scripts/match/font_match.py, kallaway-2, 11 matched caption words)
| Date | Winner | Weight | Tracking | Score | Current font |
|---|---|---|---|---|---|
| 2026-10-22 | Archivo | 800 | -0.045 em | 0.773 | Inter Tight 800 / -0.035 em scores 0.720; Helvetica Neue Bold (benchmark, not free) 0.759 |
Not applied yet (the v2 look was approved as it is). To apply: add Archivo (OFL, Google Fonts) to
template/assets/fonts, point "KW Grotesk" 800 at it in template/kit/kw.css, set caption_tracking_em
-0.045 in style.json, re-render, re-score.

## Ear check (the user listened)
| Date | Sound effects? | Music? | Notes |
|---|---|---|---|
| (pending) | stereo hits measured in all 3 references (reel 1: 5, matching 6 verified by hand) | Kallaway: none detected; ours: on by choice | Our effects are mixed near-mono (v2: 2 stereo hits vs reels' 4-38/min); consider stereo effect files or slight panning |

## Refactor note
2026-10-22: style numbers moved from build.py constants into style.json (same values). Proof: the
original opus-tips project and a fresh build render bit-identical audio and match on video at SSIM
0.998 (the same as rendering one project twice).
