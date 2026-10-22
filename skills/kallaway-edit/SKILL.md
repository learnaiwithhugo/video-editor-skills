---
name: kallaway-edit
description: Edit a raw talking-head clip into a finished Instagram reel in Kallaway's editing style (black dotted stage with one live diagram per idea, rounded face card with the head popping out over its edge, one-word white captions, red as the only accent, hard cuts on word onsets, a real sound effect on every animation, optional quiet ducked background music). Free local tools only (ffmpeg, Whisper, HyperFrames). Use when someone says "/kallaway-edit", "edit this like Kallaway", "make this reel in the Kallaway style", or drops raw clips and asks for a Kallaway-style edit.
---

# /kallaway-edit

Raw clips in, finished vertical reel out (1080x1920, 30 fps, -14 LUFS), in Kallaway's style.
Everything runs on the user's Mac with free tools. The person using this is usually NOT technical:
talk to them in plain English, one short message per step, and never make them touch code.

`SK` = `${CLAUDE_SKILL_DIR}`, this skill's folder (never write into it: an update replaces it).
`DATA` = `$HOME/.claude-video-editor`, the editor's own folder, kept across updates: the
user's settings (`DATA/config.json`), the editor's Python (`DATA/venv`), the sound effects (`DATA/sfx`).
`ROOT` = the project folder (has `raw/`, `exports/`): the `projectRoot` in `DATA/config.json`, saved by
the setup wizard (step 0). `WORK` = `ROOT/work/<slug>/` (one folder per reel; the slug is short
kebab-case, e.g. `opus-tips`). Quote every path: they often contain spaces.
Run every script through one of these two, exactly as written, so it finds the user's settings:
`PY` = `VIDEO_EDITOR_DATA="$HOME/.claude-video-editor" "$HOME/.claude-video-editor/venv/bin/python" -I` (after setup)
`SETUP` = `VIDEO_EDITOR_DATA="$HOME/.claude-video-editor" python3 -I "${CLAUDE_SKILL_DIR}/scripts/setup.py"`
Read these before building: `references/style-rules.md` (the look, as
numbers), `references/graphics-recipes.md` (how a spoken idea becomes a diagram), `references/gotchas.md`.

## Hard rules
- **Free tools only.** ffmpeg, Node 22+, Python, HyperFrames (`npx hyperframes@<pinned>`), faster-whisper,
  HyperFrames' local background removal, the bundled OFL fonts, HyperFrames media-use's recorded sound
  effects (fetched at setup, never bundled: Pixabay licence) and CC0/CC BY music from Openverse or the
  user's own track. No paid APIs, no HeyGen sign-in, no music generation, nothing copyrighted.
- **Options** the user can give: `music: on|off` (default: the choice saved at setup), `music: <path to
  their own track>`, `setup` (re-run the setup wizard).
- **Never run `npx hyperframes init` or `npx hyperframes skills`** (they install skills into
  `~/.claude/skills`). Every HyperFrames call: `HYPERFRAMES_SKIP_SKILLS=1 HYPERFRAMES_NO_TELEMETRY=1`.
  Always `snapshot ... --describe false` (otherwise frames are uploaded to Gemini).
- **Never touch the user's original footage.** Work from copies in `raw/`. Working files go in WORK;
  only finished reels go in `exports/`. Never delete the user's files.
- Captions show what was actually said, spelled right ("Claude", "Opus 5.5"), digits for numbers.
- Graphics never cover the face; text never below y 1470 or in the right 100 px below y 1155.
- Nothing animates out. Red `#C41514` is the only accent. One serif italic word per title and per section.
- Show your work: drop a numbered PNG into `WORK/progress/` at every step (01-takes-picked.png, ...).
- Check the FINAL render with `qa.py`, at full size, before saying it's done. Be honest about what
  doesn't match.

## The workflow

### 0. Setup wizard (first time only, ~5-10 min)
Read `DATA/config.json`. If it has `"setupComplete": true` and its `projectRoot` folder exists, run
`SETUP --check` (seconds, installs nothing); on READY go to step 1, on NOT READY fix what it names (after
an update that needs a new tool version, that is just `SETUP` again: the user's folders and choices are
kept). Otherwise (first run, or the user says "/kallaway-edit setup") run the wizard. Tell
them which step you're on in one short line ("Step 2 of 5: checking your tools").

1. **Welcome.** "Welcome to the Kallaway editor! Let's get you set up. This takes about 5-10 minutes and
   only happens once."
2. **Are we in Claude Code?** This needs Claude Code (the terminal app, the Code tab in the Claude
   desktop app, or an IDE extension), opened in a local folder, because it edits real video files. If
   you can run shell commands and read local files, you are. If you can't (an ordinary chat), say:
   "Open the Claude desktop app, click Code, choose Local, select a folder (or make one called
   AI video editor), then type /kallaway-edit again." Then stop.
3. **Tool check.** `SETUP --check`. Show the result as a short table: tool,
   found yes/no, what it's for (ffmpeg cuts and mixes sound; Node.js runs HyperFrames; HyperFrames turns
   the edit into a video; faster-whisper hears every word; Python runs the helper scripts; yt-dlp is
   optional here, it downloads reels from links, and /new-edit-style needs it). For anything
   the user must install themselves (ffmpeg, Node.js, Python), give the one line its fix names and say
   where to paste it: the Terminal app (Mac: Command + Space, type Terminal). If it asks for their Mac
   password, they type it there themselves, never in this chat. Wait until they say it's done, then
   check again. Items marked "the full setup installs it" need nothing from them.
4. **Where things live.** Ask in one message, each with a suggested answer:
   - "Where should I make your videos?" Suggest the current folder if it's empty or already a video
     folder (show its full path), otherwise `~/Desktop/AI video editor`.
   - "Where does your footage usually land?" Suggest `~/Downloads` (where AirDrop puts phone clips),
     or "I'll drop clips into the raw folder myself".
   - "Background music under your voice: on or off?" Suggest on (they can change it per video).
   Then offer the folders: "Want me to set up your project folder? I'll make raw/ (your clips),
   references/ (videos whose style you like), exports/ (finished reels), work/ (my working files) and
   archive/ (old versions). Anything already there stays untouched." On yes:
   `SETUP --project "<folder>" --clips-from "<folder or omit>" --music on|off`.
   It only creates missing folders and saves the answers to `DATA/config.json`.
5. **Install.** "Installing the free editing tools now (one time, about 5 minutes: a transcription
   engine, the video renderer, sound effects and a speech model)." Run `SETUP` in the background and
   relay its progress lines in plain words. It installs only into DATA (nothing global, nothing in the
   skill folder, so updates never undo it) and marks setup complete when it finishes.
6. **Done.** Give the 4 filming tips from `references/filming-guide.md` (locked camera, wide shot, dark
   room with a warm light on your face, repeat a line until it lands), then: "You're set. Drop your
   clips in raw/ (or tell me which files in <clipsFrom>) and say /kallaway-edit." If they already gave
   clips, carry straight on to step 1.

Intake on every run: clips are the files the user names; otherwise ask, offering the newest video files
in `clipsFrom`. **Copy** them into `ROOT/raw/` (never move or change the originals). Music follows the
saved `music` choice unless the user says otherwise.

### 1. Find every take (~1 min per minute of footage)
`PY "SK/scripts/takes.py" "WORK" "ROOT/raw/clip1.MOV" "ROOT/raw/clip2.MOV"` (add `--fast` for a quicker,
less accurate pass). Read `WORK/takes/*.takes.txt`: every attempt with its time range, retakes marked.
Ask for (or find in the clips) the script if there is one. Say: "Listening to your clips and finding
the best take of every line."

### 2. Pick takes and cut (~1 min)
Write `WORK/edl.json` (format: `SK/template/examples/edl.json`): one segment per line, in script order,
usually the LAST complete clean take. Use `{"clip","chunk"}` or `{"clip","start","end"}` (to skip a
stumble inside a chunk; check word times with `transcribe.py --range a-b --model medium.en --no-vad`).
Target 20-30 s; going a little over (to ~38 s) beats breaking a promise the hook makes. Skip CTAs
unless asked. Then `PY "SK/scripts/assemble.py" "WORK"`: cut.mp4 (CFR, tight to the voice, compressed,
-14 LUFS), segments.json, words.json, words.txt. Read words.txt: every line must say what was meant.
`PY "SK/scripts/qa.py" "WORK" --takes` writes progress/01-takes-picked.png.
Say: "Here's the cut: <the lines>. <N> seconds."
**Lock the cut before building graphics.** If you recut later: `PY "SK/scripts/reindex.py" "WORK"
"WORK/.prev/words.json"` keeps every graphic on its word.

### 3. Cut the speaker out (~3-4 min, run in the background)
`PY "SK/scripts/cutout.py" "WORK"`: cutout.webm (frame-matched, edge cleaned) + headtrack.json.
While it runs, plan the edit (step 4). Then look at one frame composited over black for halos and
save it as progress/02-cutout-check.png.

### 3b. Music (unless `music: off`; ~2-6 min, run in the background)
`PY "SK/scripts/music.py" "WORK"` (or `--file "<their song>"`, or `--off`). It picks a free CC0/CC BY
instrumental from Openverse, rejects vocals, and writes `WORK/music-credit.txt`. Tell the user what it
picked and, for CC BY, that the credit line goes in the caption.

### 4. Plan the edit, line by line
Write `WORK/plan.json` (format: `SK/template/examples/plan.json`):
- `shots`: where each layout starts (`0`, `"line:N"` = first frame of EDL line N, `"w:N"` = onset of
  word N). Stage for anything that can be shown; full for connective/personal lines and the payoff
  (16-29% of runtime). Hard-cut between stage scenes too. First cut by ~3.5 s.
- `scenes`: which graphic plays when (`id`, `from`, `to`, optional `src` + `vars` to mount one scene
  file several times, e.g. a recurring numbered "home" graphic). A scene may run under a full shot
  and come back (a revisit adds one new thing in 0.6 s).
- `punch`: snap punch-ins (x1.19, riser into it) on a closing phrase, at most one or two.
- `captions`: `fix` (word index -> correct text), `emphasis` (one serif word per section),
  `keep_together` (word index pairs, e.g. "Number" + "1,").
Use graphics-recipes.md: every idea gets a shape, a title (bold + one serif accent, the claim on a red
box), and beats on its words, something new every ~1 s. Say the plan back in one line per shot.

### 5. Build the scenes (~15-25 min)
Each scene is `WORK/scenes/<name>.html`, started from `SK/template/scene-starter.html` or the closest
file in `SK/template/examples/` (six real scenes). The kit (`template/kit/kw.css`, `kw.js`) gives the
stage look and motion helpers (`KW.title`, `blurIn`, `pill`, `pulse`, `draw`, `cam`, `type`, `strike`,
`count`, `scramble`; `at(i)` = onset of word i). EVERY animation gets its sound cue in the scene's
`<!--KW:SFX [...] -->` comment, e.g. `{"t": "w:24-0.02", "s": "whoosh"}`, following
`references/sound-map.md` (camera move = whoosh, pill = pop, snap/tick = click, typed text = typing,
big moment = impact, payoff = sparkle). If you have the Agent tool and more than ~3 scenes,
hand scenes to up to 2 parallel agents with: the scene's exact word list and times, the idea, this
skill's references, and `build.py ... --project WORK/project-<letter>` so they never collide.
`PY "SK/scripts/build.py" "WORK"` writes `WORK/project/` (root: dotted stage, face card, pop-out
layer, caption track, scene hosts, SFX lane, all generated). Then in `WORK/project`:
`npx -y hyperframes@<pin> lint` (0 errors) and `snapshot --at <times> --no-end --describe false -o
snaps/x`, read the PNGs, fix, repeat. Save each scene's sheet as progress/03-scene-<name>.png.

### 6. Render (~1 min) and check (~1 min)
`PY "SK/scripts/render.py" "WORK" --name draft` (fast), then
`PY "SK/scripts/qa.py" "WORK" "WORK/renders/draft.mp4"` and LOOK at `qa/cuts.png` (frame before/after
every cut), `qa/beats.png` (every caption chunk), `qa/report.txt` (cut-to-speech gaps, loudness).
Check: pop-out has no halo or drift after cuts; the card shows head AND shoulders (never a face
crop); no caption or graphic on the face; captions match the words; every line cut lands 0-80 ms
before speech; nothing in the Instagram no-go zones. Then
`PY "SK/scripts/audiomap.py" "WORK" --out progress/NN-audio-map.png`: music 18-24 dB under the voice,
effects ~10-16 dB under its local peak, no double hits; fix any flagged cue with `"db": -3`.
**Style match:** `PY "SK/scripts/match/fingerprint.py" score "SK/references/style-spec.json"
"WORK/renders/draft.mp4" --out "WORK/progress/NN-style-match.md"` measures the edit the same way the 3
Kallaway reels were measured (cut rate, visual changes per second, layout shares, card and caption
position, caption size and pace, accent colour share, loudness, stereo sound effects) and says what to
fix for each FAIL. Fix what the edit controls; a FAIL caused by the footage (a close selfie) goes to the
user as a filming note. The report in `WORK/progress/` is the record (`SK/references/lock-log.md` holds
the style's measured history; leave it as it is).
Fix and re-render (a rebuild + re-render takes ~1.5 min).

### 7. Deliver
`PY "SK/scripts/render.py" "WORK" --final` -> `exports/<slug>-kallaway-vN.mp4` (1080x1920) plus
`-720p.mp4` phone copy. Run qa.py on the export. If the user has a Kallaway reel of their own saved in
`ROOT/references/` (none ships with this skill), add a side-by-side (`--ref <that reel> --ref-at <t> --at <t>`)
and save it as progress/NN-side-by-side.png.
Say: where the file is, how long it is, what's in it scene by scene, and what still doesn't look
like Kallaway (be specific and honest).

## Timings (on an M4 Pro Mac, 35 s reel from ~8 min of raw footage)
setup 5 min (first time) · takes 7 min (medium model; `--fast` ~3) · cut 1 min · cut-out 3.5 min ·
music 2-6 min (in the background; Openverse/Freesound can be slow) · scenes 15-25 min ·
draft render 50 s · final render 70 s · re-render after an edit ~1.5 min.

## Filming
Give `references/filming-guide.md` to anyone about to film: locked-off wide shot (horizontal 4K is
best), dark room with a warm key light, dark top, plain background behind the head, repeat a line
until it lands.
