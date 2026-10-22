---
name: new-edit-style
description: Create a new editing-style skill from 2-3 reference reels of one creator or style (e.g. "make me a skill that edits like @creator"). Downloads the reels, measures them frame by frame, has one agent break down each reel, merges the breakdowns into a style guide plus a measurable style spec, clones the proven editing engine into a new /<style>-edit skill, then locks the style with a match score, pixel font matching, a golden recreation test, one critic round and the user's ear check. Free local tools only. Use when someone says "/new-edit-style", "make an edit style skill", "copy this creator's editing style", "I want to edit like X", or drops several reels from one creator and asks for their style.
---

# /new-edit-style

Reference reels in, a locked `/<style>-edit` skill out, so every edit made with it looks like the
references. This is the process that built `/kallaway-edit`, written down and sharpened. The person
using it is usually NOT technical: plain English, one short message per step, never make them touch code.

`SK` = `${CLAUDE_SKILL_DIR}`, this skill's folder. `ENGINE` = `${CLAUDE_SKILL_DIR}/../kallaway-edit`,
the proven editing skill it builds on (it carries the setup wizard, transcription, cutting, cut-out, sound,
build, render and QA). Never write into SK or ENGINE: an update replaces both.
`DATA` = `$HOME/.claude-video-editor`, the editor's own folder that survives updates (settings, Python, sound
effects, font cache). `ROOT` = the project folder (`projectRoot` in `DATA/config.json`).
Run every script through one of these, exactly as written, so it finds the user's settings:
`PY` = `VIDEO_EDITOR_DATA="$HOME/.claude-video-editor" "$HOME/.claude-video-editor/venv/bin/python" -I`
`SYS` = `VIDEO_EDITOR_DATA="$HOME/.claude-video-editor" python3 -I` (before setup has run)
`STYLE` = short kebab-case name ("kallaway"). `SDIR` = `ROOT/references/<STYLE>/`.
`WORK` = `ROOT/work/new-edit-style/<STYLE>/` (progress PNGs go in `WORK/progress/`, numbered).

## Hard rules
- Free tools only (ffmpeg, Python, faster-whisper, HyperFrames, OFL fonts). No paid APIs, no sign-ins.
  Download reference links logged out (`yt-dlp --no-cookies`); never use a browser's cookies.
- Never touch the user's original files; never delete anything (move old versions to `ROOT/archive/`).
- Never run `npx hyperframes init` or `npx hyperframes skills`; nothing may be added to
  `~/.claude/skills` or `~/.agents/skills`.
- Never present a guess as measured, or a sound as heard. Agents can't hear; the user's ear check decides.
- Copying an editing STYLE is fine; never copy the creator's footage, logos, music or text into an edit.
- Sub-agents: one per reference reel for the breakdowns (Sonnet is fine), at most 3 at once, briefed
  with `references/breakdown-brief.md`. Everything that needs judgement or eyes, you do yourself.

## Workflow

### 0. Setup (first time only)
If `DATA/config.json` lacks `"setupComplete": true`, run the editor's setup wizard first: invoke the
`kallaway-edit` skill with `setup` (or read `ENGINE/SKILL.md` step 0, where
`${CLAUDE_SKILL_DIR}` means ENGINE and `$HOME/.claude-video-editor` means DATA): Claude Code check, tool
check, project folders, install. If ENGINE is missing, say: "This needs the kallaway-edit skill installed next to it (it carries the editing engine).
Reinstall both from https://github.com/learnaiwithhugo/video-editor-skills, then run /new-edit-style
again." Then stop. This skill also needs yt-dlp (it downloads the reference reels), so always check
with `SYS "ENGINE/scripts/setup.py" --check --for new-edit-style`, on the first run and later ones. If
yt-dlp is missing, give the user its fix line (`brew install yt-dlp`, pasted in the Terminal app), wait
until they say it's done, and check again.

### 1. Intake (~2 min)
Ask, in one message: "Send me 2 or 3 reels (links or files) from ONE creator whose editing you want to
copy, ideally your favourite edits of theirs, and a short name for the style." 3 is best: rules come
from what all of them share. Then:
`SYS "SK/scripts/fetch.py" STYLE "ROOT" <link or file> ...` -> `SDIR/STYLE-1.mp4` ...
Say: "Got them. Measuring every frame now (about 2 minutes)."

### 2. Prep, all scripted (~30 s per reel)
`PY "SK/scripts/prep.py" "SDIR" SDIR/STYLE-*.mp4`
Per reel in `SDIR/prep/<reel>/`: word-timed transcript, every-frame cut scan, 4 fps contact sheets with
times, full-size stills, spectrogram, stereo sound-effect hits, loudness, and `fingerprint.json` (the
measured style numbers). Plus `SDIR/style-check.png` and `SDIR/style-spec.json`.
**Look at `style-check.png` now.** If one reel clearly doesn't share the others' look (different layout,
captions, colours), tell the user and ask for a replacement before spending agents. Copy it to
`WORK/progress/01-style-check.png`.

### 3. Breakdowns, one agent per reel, in parallel (~15 min)
Fill `references/breakdown-brief.md` once per reel and launch them in one message. Each writes
`SDIR/prep/<reel>/edit-log.md`. While they run, do step 4's font match.

### 4. Font match (~20 s)
`PY "SK/scripts/font_match.py" SDIR/STYLE-1.mp4 SDIR/prep/STYLE-1/transcripts/STYLE-1.words.json "SDIR/font"`
Look at `font-match.png`: the winner must visibly match. Run it on a second reel if the top two are within
0.01. (Kallaway: Archivo 800 at -0.045 em scored 0.773, above Helvetica Neue Bold's 0.759.)

### 5. Merge into the style guide (you, ~10 min)
Follow `references/merge-guide.md`: consensus rules, measured numbers, a key-frames sheet you look at
yourself, and the filming section. Output `SDIR/STYLE-style-guide.md` + `SDIR/STYLE-key-frames.png`.
Open the key-frames sheet for the user and give them the one-paragraph summary.

### 6. Make the style skill (~2 min + your rewrite, ~30 min)
`SYS "SK/scripts/make_style_skill.py" STYLE "SDIR" --title "Display Name"`
It clones the proven engine (ENGINE, found next to this skill) into `ROOT/.claude/skills/STYLE-edit/`:
a project skill in the user's own video folder, never in the global skills folder, so updates never touch it.
The copy shares DATA (no second install). It adds the match tools (`scripts/match/`), writes `style.json`
from the measured spec, and prints the checklist of
style files to rewrite from the style guide (SKILL.md style rules, style-rules.md, graphics-recipes.md,
sound-map.md, filming-guide.md, the kit CSS/JS, and build.py's layouts only if the style has
different layouts). Rewrite every item on the list. Engine scripts stay untouched unless a layout needs it.

### 7. Lock the style (~45-60 min)
Follow `references/lock.md`: a test edit on the user's footage -> match score -> fix -> golden
recreation of a reference window -> fix -> one critic round -> ear check -> sign-off. Log every number
in `STYLE-edit/references/lock-log.md`.

### 8. Deliver
Tell the user: the new command (`/STYLE-edit`, available whenever Claude Code is opened in ROOT; if it
doesn't show up yet, restart Claude Code there), what it does in one paragraph, the match score and
golden numbers, how to film for it (3-4 bullets from the filming section), and what still doesn't match.

## Timings (on an M4 Pro Mac, 3 reels of ~1.5 min)
fetch 1 min · prep 1.5 min · breakdowns 15-18 min (parallel) · font match 20 s · merge 10 min ·
make skill 2 min + rewrite 30 min · lock 45-60 min. About 2 hours end to end, mostly agents and renders.

## Files
`scripts/`: fetch.py, prep.py, fingerprint.py (measure / spec / score), font_match.py, golden.py,
make_style_skill.py, engine.py (finds ENGINE). `references/`: breakdown-brief.md, merge-guide.md,
lock.md. `templates/`: style-rules.md, graphics-recipes.md, lock-log.md (copied into new style skills).
