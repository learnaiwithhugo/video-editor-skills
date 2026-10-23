---
name: edit-my-video
description: Edit raw talking-head clips into a finished vertical Instagram reel in the creator's OWN style, read from a style folder made by build-my-style (STYLE.md, locked shine/zoom/shadow, picked sound effects). Picks the last clean take of every line, shows a storyboard page first (a still per beat, A/B/C options on the key beats, Approve/Change and notes), optionally renders short variations of key moments to pick from, then builds the full edit in HyperFrames, reviews its own render, and turns every note the user gives into a dated rule in their STYLE.md so the next edit is better. Free local tools only. Use whenever someone says "/edit-my-video", "edit my video", "edit these clips", "make this into a reel in my style", "storyboard this edit", drops a folder of raw clips and wants an edit, or gives notes on an edit this skill made ("I don't like the zoom", "make the logos bigger").
---

# /edit-my-video

Raw clips in, a finished 1080x1920 reel out, in the user's style. The user is usually not technical: talk in
short plain messages, one step at a time, do all the technical work yourself, and never make them touch code.
Never use the AskUserQuestion popup (ask in chat). Never post or upload anything anywhere. No em dashes in
anything you write for them or put on screen.

`SK` = this skill's folder. `STYLE` = the style folder (default: the one saved in `SK/config.json`, else the one /build-my-style
made, else `~/edit-style`; if none has a STYLE.md, ask where it is or suggest /build-my-style first). `WORK` = one folder per video,
`<edits folder>/<slug>/` (slug = short kebab-case, e.g. `github-repos`). Quote every path, they have spaces.
Scripts run as `python3 "SK/scripts/<name>.py" ...`; each prints its own usage when run with no arguments.

Read before the first edit of a session: `references/creative-rules.md` (the most important file: how to
design, and the hard taste checks) and `references/engine.md` (the HyperFrames pattern that renders).
Read `references/storyboard.md` before step 4.

## The one rule that matters most
STYLE.md is **guardrails, not a menu**. It fixes the look (colours, font, motion feel, sound levels, safe
zone, what was rejected). It does not limit what you make. For every line, ask what visual would explain
*this* idea best, then design it fresh inside the look. The first test edit copied templates from the style
page (a checklist for "it can only do three things") and the creator called it "extremely restricted" and
"didn't improvise at all". Vary layouts; never the same layout twice in a row; make visuals big.

## Steps (say which one you're on in one short line: "Step 3 of 8: finding your best takes")

### 1. Setup check (seconds)
`python3 "SK/scripts/setup.py" --check`. Show missing items as a short list: what it is, what it's for, the
one-line fix. For anything they must install (ffmpeg, Node, Python, Chrome) tell them to paste the line into
the Terminal app (Command + Space, type Terminal) and say "done". `--install` (faster-whisper, playwright,
HyperFrames, speech model) only after they say yes: "Can I install the free editing tools? About 5 minutes,
one time." Then `python3 "SK/scripts/style.py" check "STYLE"` (is the style folder complete) and
`python3 "SK/scripts/style.py" serve "STYLE"` (starts its page server if it isn't running; note the URL).
First run only: ask where edits should live (suggest the folder next to the style folder, `edits/`) and save
it: `setup.py --save --style "STYLE" --edits "<folder>"`.

### 2. Intake (one message)
Ask only what you don't already have:
- the raw clips folder (often many repeated takes; you'll use the LAST clean take of each line)
- what the video is about, and the script or notes if they have them
- the comment keyword for the call to action
- target length (suggest 25 to 40 s)
- music: only if they name a track. Otherwise none (the creator picks music themselves).
Then `mkdir` WORK and `python3 "SK/scripts/style.py" resolve "STYLE" --out "WORK/style.json"`.
Read STYLE.md in full: especially `Feedback from edits`, `Rejected` and `Kept`, newest first. Those are
the creator's own corrections from past edits and override everything else.

### 3. Takes, cut, words (~1 min per 5 min of footage)
1. `takes.py "WORK" "<clip>" ... --prompt "<names they'll say>"` lists every attempt, retakes marked.
   Read `WORK/takes/*.txt`. Pick the last complete clean take of each line (skip stumbles; trim a bad start
   by moving `in`). Write `WORK/edl.json` (format in `cut.py`'s usage).
2. `cut.py "WORK" --prompt "<names>"`: frame-exact segments into `WORK/hf/assets/v/`, the voice at -16 LUFS,
   tight edges, and `words.json` / `words.txt` with reel times. Look at `progress/01-cut-takes-in-order.jpg`.
3. Read `words.txt` against what they meant. Whisper mishears names: fix them in words.json with
   `captions.py fix "WORK" "49=ArtCraft"` (only ever to match what was really said).
Tell them the cut in one line per beat and the length.

### 4. Storyboard first (the user approves before anything renders)
Follow `references/storyboard.md`: write `WORK/storyboard.json` (a beat per idea: words, times, layout,
visual, animation, caption, sound), build one still per beat on their real footage with the planned visual
composited (real screenshots, real app icons, JPGs), with 2 to 3 alternatives (A/B/C) on the 3 or 4 key
beats (hook, the main idea, the payoff, the CTA). Then
`storyboard.py page "WORK" --style "STYLE"` and open `http://localhost:<port>/storyboards/<slug>/`
(`open <url>`). Say: "Your storyboard is open. Pick A, B or C where there's a choice, Approve or Change each
beat, add a note anywhere, press Submit, then tell me done." **Wait for "done".** Then
`storyboard.py review "WORK" --style "STYLE"` folds their picks and notes into storyboard.json. Rebuild only
the beats they changed and show those again, until everything is approved.

### 5. Variations (optional, offer it once: "Want to see 2 or 3 versions of the hook moving before I build the whole thing?")
For 2 or 3 key moments: build the edit far enough to cover them (step 6), copy `hf/index.html` to
`hf/index-<beat>-B.html` with that beat redesigned, then `render.py slice "WORK" <beat>-A <start> <end>`
and `render.py slice "WORK" <beat>-B <start> <end> --index "WORK/hf/index-<beat>-B.html"` (2 to 4 s each,
~6 s to render). Put `"video": "variations/<name>.mp4"` on those alternatives in storyboard.json,
`storyboard.py page "WORK" --style "STYLE" --variations`, open `.../storyboards/<slug>/variations.html`,
wait for done, `storyboard.py review ... --variations`, keep the winners in index.html.

### 6. Build the edit (the creative part)
1. `render.py new "WORK" --title "<video> v1"`: the pinned HyperFrames project with the style's colours,
   font, caption shadow and the motion kit (`engine/kit.js`) in `WORK/hf/`.
2. Gather real things: `shoot.py web <url> <png> --mobile` (pages after they fully load),
   `shoot.py icon "<App>" <png>` (real macOS app icons), official logos from the tool's site otherwise.
3. Write `WORK/hf/index.html` beat by beat from the approved storyboard (pattern and kit API in
   `references/engine.md`), timing every visual to the word it belongs to in words.txt. Design each beat
   fresh; give every visual scene `data-visual="<what it is>"` and `data-layout="face|split|full"`.
4. Captions: `captions.py make "WORK" --skip <a-b>` (skip moments where on-screen text already says the
   words), then edit `WORK/caps.json` by hand: chunk them so they read naturally (2 to 3 words), set `top`
   so they never sit on the mouth, `cls` per beat, `html` for one accent word. `captions.py inject "WORK"`.
5. Sound: write `WORK/cues.json` (every cut, panel, icon, line, hero word gets its cue at its locked level;
   no double hits), add the music only if they named one, then `mix.py "WORK"` (lands the mix on -16 LUFS).
6. `render.py check "WORK"` (fix every error), `render.py snap "WORK" <times> --name <beat>` and LOOK at the
   frames you changed. Drop a numbered picture into `WORK/progress/` at every step (scripts do most of it).

### 7. Render and review yourself before showing anything
`render.py render "WORK" --out "WORK/<Video name> - v1.mp4"`, then `qa.py "WORK" "<that mp4>"`.
Fix every FAIL. Then actually look at every picture it lists (the 2 fps contact sheets and the full-size
close-ups with the safe zone drawn): text crowding, visuals small or high with empty space, captions on the
mouth, the same layout twice, anything that pops, anything black, numbers/names not matching the words.
The automated checks miss things the eye catches (the first test of this skill passed the checks with a
muddy hero word and empty half-cards). One fix pass, re-render, re-run qa.py, then `open "<mp4>"`.
Tell them in a few lines: where the file is, how long, what happens beat by beat, and anything you guessed.

### 8. Feedback loop (every time they give a note)
Fix it, re-render (a re-render takes ~20 s), re-run qa.py, open it. AND write it into their style so the next
edit already knows:
`python3 "SK/scripts/feedback.py" "STYLE" --video <slug> --rule "<do this from now on>"` (or `--rejected
"<never again>"`, `--kept "<loved this>"`). Use their words, one note per flag; a thing they loved is as
important as a thing they hated. It backs up STYLE.md first and logs it. Say in one line what you added.
If a note is about a locked value (the shine, a zoom curve, the caption shadow), say it lives in their
style page's lab and offer to open it rather than overriding the lock silently.

## Times (M-series Mac, 15 s of finished reel from ~8 min of footage)
takes ~1 min per 5 min of footage · cut + words ~15 s · storyboard stills ~2 min · variation slice ~6 s each ·
render ~20 s · qa ~30 s.
