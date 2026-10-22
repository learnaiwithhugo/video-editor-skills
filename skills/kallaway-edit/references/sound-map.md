# Sound map: every animation gets its sound

The animations feel flat without sound. Every visible action gets one real, recorded effect, landed
on the frame the visual lands (the effect's hit plays one frame after the picture), clean and tight,
always well under the voice. The numbers live in `scripts/sounds.py` (`MAP`); keep this table and
that file in step.

## Where the sounds come from
HyperFrames' media-use kit ships recorded effects (Pixabay, Pixabay Content License: free to use
inside videos, commercial too, but the files must not be redistributed on their own). This skill
never bundles them: `setup.py` / `sounds.py` copy them from a HyperFrames media-use skill on the
Mac, or download them from `https://raw.githubusercontent.com/heygen-com/hyperframes/main/skills/media-use/audio/assets/sfx/<name>.mp3`
into the editor's data folder, `DATA/sfx/` (never the skill folder). build.py copies the ones a reel uses into its project.

## The map
Gain is the target PEAK of the effect in the mix (voice peaks sit around -1 dBFS, voice loudness
-14 LUFS); `sounds.py` measures each file and sets the volume to hit it. That lands effects about
10-16 dB under the voice's local peak (audiomap.py checks it). Trim a single cue with `"db": -3`.

| Animation | Cue | File (window) | Peak | Notes |
|---|---|---|---|---|
| Virtual-camera move (push, pan, pull back) | `whoosh` | whoosh.mp3 | -13 dB | on the move's start (its fastest frame) |
| Hard cut from one stage scene to the next | `whoosh` | whoosh.mp3 | -13 dB | automatic (build.py) |
| Cut from the face (full) INTO the stage | `whoosh-big` | whoosh-cinematic.mp3 (2.05-3.10 s) | -12 dB | automatic (build.py) |
| Title swap (letter scramble) | `whoosh` at -4 dB, or `whoosh-big` | | | on the swap frame |
| Pill, label, tag, numeral, card, answer landing | `pop` | pop.mp3 | -14 dB | one per element; trim -2 to -5 dB when several land close together |
| Slider snap, checklist tick, strike-through, counter step, meter level | `click` | click.mp3 | -15 dB | on the snap/tick frame |
| One typed character, a slash | `key` | key-press.mp3 | -18 dB | |
| Text typed into a chat box | `typing` | typing.mp3 (trimmed) | -18 dB | `"dur": "w:40"` trims it to the typing; starts with the first letter |
| THE big moments: the "3 things" numerals, the claim landing in the red box, the hook's product pill, a stamp | `impact` | impact-bass-1.mp3 (0-1.4 s) | -12 dB | 2-4 per reel; trim -3/-4 dB for the secondary ones |
| Snap punch-in on the face | `riser` | riser.mp3 (2.30-3.55 s, its crest) | -12 dB | automatic from plan.json `punch`; stops dead ON the snap |
| A payoff ("sweet spot", "done") | `sparkle` | sparkle.mp3 (0-1.2 s) | -20 dB | sparingly: 1-2 per reel |
| A positive confirmation | `chime` | chime.mp3 (0-1.6 s) | -18 dB | sparingly; usually pick sparkle OR chime |

Rules build.py enforces: two cues within 2.5 frames never both play (the higher priority wins:
riser > impact > whoosh-big > whoosh > pop > click > key/typing > sparkle/chime); cues are placed so
the file's hit (measured once) lands one frame after the picture; every effect has a 12-40 ms fade-out.

## Music (optional, ON by default)
Kallaway uses none; this skill adds a quiet bed unless the user says `music: off`.
- `scripts/music.py <work>`: searches Openverse (free, no account) for CC0 / CC BY instrumental
  tracks (lofi / chill electronic), downloads up to 4, rejects any with vocals (Whisper listens),
  picks the steadiest (lowest loudness range), CC0 first, and finds the steadiest stretch to start
  from. `--file <song>` uses the user's own track; `--pick 2` takes the runner-up; `--off` disables.
- It writes `work/<slug>/music-credit.txt`. CC BY = that line goes in the post caption.
- build.py ducks it with a `data-automation` volume lane (the same envelope HyperFrames' media-use
  `audio-duck.mjs` writes): 21 dB under the voice while he talks (target 18-24), +5 dB in pauses of
  0.35 s or more, a 0.12 s fade in, a 1 s fade out at the end. The level is measured on the stretch
  that actually plays.
- Never sign in to HeyGen for music, never generate music locally (disk, quality), never use a
  track without a CC0/CC BY licence or the user's own rights.

## Check it
`PY scripts/audiomap.py <work> --out progress/NN-audio-map.png` rebuilds the stems and reports:
music under the voice (median, closest), each effect under the local voice peak, double hits.
render.py then levels the whole mix to -14 LUFS, -1 dBTP. All of it is measured, not listened to:
say so, and ask the user to listen once on a phone.
