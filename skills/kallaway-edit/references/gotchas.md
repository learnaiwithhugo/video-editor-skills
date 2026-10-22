# Gotchas (each one cost a render while building this skill)

## Cutting and timing
- **Pick takes from `takes.py`, not from one long transcript.** Whisper over a rambling clip merges
  retakes and smears word times across pauses ("guide 6.27-8.81 s"). takes.py splits at silences
  and transcribes each chunk alone: exact text per attempt, silence-accurate edges.
- **silencedetect edges include breaths and room noise.** Untreated, a line started 140-200 ms
  before the voice (a silent mouth after every cut). assemble.py now snaps each piece to the first
  10 ms louder than -32 dB (tail: last above -40 dB), then adds 50 ms / 90 ms of air.
- **Whole frames or drift.** Every piece is trimmed to a whole number of frames, the cut is forced
  to constant 30 fps (`setpts=N/30/TB`) with a keyframe every second. The pop-out cut-out must have
  EXACTLY the same frame count as cut.mp4 (cutout.py refuses otherwise); one extra frame and the
  head floats away from the face a little more after every cut.
- **Re-cutting shifts word indices.** Words are referenced by index (`"w:35"`, `at(35)`). A recut
  re-transcribes; if one word appears or disappears, every later graphic lands on the wrong word.
  assemble.py keeps `.prev/words.json`; run `reindex.py <work> <work>/.prev/words.json` after any
  recut. Lock the cut BEFORE building scenes. Sound cues in scenes use `"w:N+0.1"`, never raw
  seconds, so they follow the words too.
- **Whisper is not ground truth for spelling.** "Claude" comes out as "cloud"/"clothing", "5.5"
  as "5" + ".5" (assemble.py glues it), "three" as "3". Fix in `plan.json captions.fix`. When a
  word is truly ambiguous (was "it" said?), probe that stretch with `transcribe.py --range` and go
  with what the majority of transcriptions hear, not with the script.

## GSAP / HyperFrames
- **Renders seek backwards, and GSAP renders a timeline in REVERSE order when it does.** A tween
  still running when a later `tl.set` fires wins on a backward seek. That put the full-layout zoom
  into the next stage shot (his chest in the card for 3 s). Rule: every tween on a property ends
  before the next set/tween on that property starts (build.py ends pushes 2 frames early).
- `tl.set` at a rounded time fires a frame late: set at `t - 0.002` (`KW.at`, build.py `tset`).
- Things that appear later: CSS `opacity:0` (class `kw-hide`) + `fromTo(..., immediateRender:false)`.
  The "to" state must state every property the "from" state changes (KW.strike once forgot
  `opacity:1` and the bar vanished after a backward seek).
- Element ids: prefix with the scene id (`__ID__-`), no apostrophes, unique across the page.
- Host id, scene root `data-composition-id` and the `window.__timelines` key must be the same,
  or every render waits 45 s and shows a frozen scene. build.py writes the host for you.
- Titles inside the camera wrapper move with every camera push and drift into Instagram's header.
  Titles sit outside `kw-cam`.
- Components need the font set on themselves: a pill outside a `.kw` parent rendered in Times.
- Never tween `display/visibility/autoAlpha` on a timed `.clip`; animate a child or a wrapper.
- `backdrop-filter` and lots of big blurs can blank frames: keep blur to entrances and camera moves.
- A 3D flip needs a real back face (`backface-visibility: hidden` + a rotated back), or the
  numeral shows mirrored halfway through.

## The CLI
- **NEVER `npx hyperframes init` or `npx hyperframes skills`**: they install skills into
  `~/.claude/skills` and `~/.agents/skills`. The template is built by hand; every call sets
  `HYPERFRAMES_SKIP_SKILLS=1` and `HYPERFRAMES_NO_TELEMETRY=1`.
- **`snapshot` sends frames to Gemini if `GEMINI_API_KEY` is set** (and installs `@google/genai`).
  Always pass `--describe false`.
- Renders cache extracted frames (~2 GB) in the system temp folder by default. render.py points
  `--frames-cache-dir` inside the work folder and deletes it after each render.
- The container is a few ms longer than the picture (AAC padding): compare the VIDEO stream length.
- Snapshots seek approximately near cuts; only frames pulled from the final render prove a cut
  (qa.py).

## Sound
- HyperFrames' bundled `whoosh.mp3` = `whoosh-short.mp3` and `click.mp3` = `click-soft.mp3` (same
  files). The second whoosh "take" is a 1 s slice of `whoosh-cinematic.mp3`.
- `riser.mp3` is 10 s long but crests at ~3.3 s and dies by 4.2 s (not at the end, despite its
  description): the map plays 2.30-3.55 s so it stops dead on the punch-in.
- Hits sit at different points in each file (pop 0.12 s, whoosh 0.16 s, impact 0.14 s): sounds.py
  places each so its hit, not its start, lands on the picture.
- First pass at -17 to -24 dB peaks measured ~19 dB under the voice: too timid, the animations felt
  dry. -12 to -18 dB peaks land ~15 dB under. Quiet passages of speech make the same effect stand out
  more: audiomap.py flags anything closer than 8 dB.
- Openverse and Freesound previews are free but can be slow or time out: music.py uses curl with
  retries and skips a search that doesn't answer.

## Media
- ffmpeg builds often lack `drawtext` (no freetype): labels on QA sheets are drawn with Pillow.
- Decoding VP9 alpha needs the libvpx decoder before `-i` (`-c:v libvpx-vp9 -i cutout.webm`) and
  `format=yuva420p` before `alphaextract`.
- The cut-out model leaves a rim of the room's colour on hair (a light halo over the black stage
  with a bright wall behind). cutout.py pulls the matte in 2 px and softens it 1 px.
- faster-whisper's own audio decoder (PyAV) breaks across versions: every script decodes with
  ffmpeg and hands Whisper raw samples.
- Python: run scripts with the skill's venv python and `-I`.
