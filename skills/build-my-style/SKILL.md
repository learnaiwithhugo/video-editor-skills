---
name: build-my-style
description: Style Studio. Walks a creator (usually non-technical) through building their OWN video editing style on an interactive page in their browser - their colours and font, reference reels they love broken down frame by frame, then rounds of real animated options (captions, accent and intro text, zooms, diagrams, logos, split screen, tool talk, sound effects) they mark Keep / Maybe / Drop, plus Shine, Zoom and Shadow labs with Lock buttons. Ends with a STYLE.md guide and locked settings that /edit-my-video uses. Use whenever someone says "/build-my-style", "build my style", "make my editing style", "style studio", "I want my own edit style", "copy the editing style of these reels", "make my brand style for videos", sends reels they want their edits to look like, or comes back to carry on their style (rounds, labs, sounds). Also the STYLE keyword giveaway.
---

# /build-my-style (Style Studio)

The person ends up with their own editing style: a page in their browser where they watch real
animations in their own brand, keep what they love, drop what they don't, and lock the details. You do
all the technical work. They watch, click and talk.

**Who you're talking to:** a creator who is usually NOT technical. Every message is short and plain,
one question at a time, no jargon, no code, no em dashes. Never use the AskUserQuestion popup; ask in
chat. Ask before installing anything. Never ask them to edit a file.

`SK` = this skill's folder. `STYLE` = their style folder (default `~/edit-style`, or where they choose;
remembered in `SK/config.json` as `styleDir`). Run scripts as `python3 -I "SK/scripts/<name>.py"`.
Quote every path: they often contain spaces.

## What the style folder holds (other skills read this, keep the layout)
`STYLE.md` (the guide) · `locked/brand.json`, `shine.json`, `zoom.json`, `shadow.json`, `kept.json` ·
`sfx/sfx.json` + WAVs (`sfx/old/` for dropped ones) · `page/` (their copy of the page: `round.json` is
what's on it, `library.js` + `custom.js` the animation code, `assets/` their clip, icons, screenshots,
fonts) · `reviews/` (what they submitted) · `references/` (their reels + breakdowns) · `serve.py`.

## Hard rules (each one comes from a real correction)
- **Guardrails, not a menu.** STYLE.md fixes the look, not what gets made. The first test edit built
  from a guide like this only used the page's options and the creator said it felt "extremely
  restricted". Write that into the guide (the template already does) and never present options as a list to pick from in edits.
- **Learn mechanics from references, never copy their visuals.** Round 1 once reused a reference's
  folder-and-emoji icons and the creator said it was a direct copy. Timing, easing, layout, pacing: yes.
  Their icons, colours, fonts, props: no.
- **Their brand from round 1.** Every option is already in their colours and font. No generic demo look.
- **Ground rules** (in the STYLE.md template): no pop-in or scale-overshoot entrances, never black
  behind visuals, no underlined words, real app icons and real screenshots only (fully loaded), logos
  tilted and overlapping, push-ins on visuals under a second, face zooms long and smooth with an
  occasional punch, visuals big and well placed, intro text never cramped, sound effects barely
  noticeable, text inside Instagram's safe zone. Drop any rule the person reverses.
- **The page only shows what's still in play.** Drops never come back. Keeps stay. Maybes get fixed
  exactly the way the note says, nothing extra.
- **When they name what to keep, that IS the decision.** "Get rid of anyone that isn't R2-L6" means
  `keep-only`. If a sentence could mean two things, ask in one line before changing anything.
- **Check it the way they'll see it.** Before saying a round or lab is ready, run `shot.mjs` on the page
  (no console errors) and look at a scrubbed frame of anything you changed. Never say "done" off a guess.
- **Agents can't hear.** Sounds are picked by the person's ears on the Sounds page. Say so.
- **Never bundle third-party sounds or fonts in this skill.** Fetch them on their Mac. Their own
  library is only read and copied, never moved or changed. Download links logged out (no cookies).
- **Never delete their stuff.** Old versions go to `old/` folders (the scripts do this).

## Workflow

### 0. Welcome back? (every run)
If `SK/config.json` has a `styleDir` that exists: `server.py start "STYLE" --open`, then
`make_round.py "STYLE" show` and `style_md.py "STYLE" --check`, and tell them in two lines where they
are and what's next. Otherwise start at step 1.

### 1. Setup (first time, ~5 min)
Say: "Welcome to Style Studio! First I'll check your Mac has the free tools (about a minute)."
- Must be Claude Code with a local folder (you can run commands). If not: "Open the Claude desktop app,
  click Code, choose Local, pick a folder, then type /build-my-style again." Stop.
- `setup.py --check`. Show a short table: tool, found, what it's for. For anything missing give the one
  line from the fix and say where to paste it (Terminal: Command + Space, type Terminal). Their Mac
  password goes in Terminal, never in this chat. HyperFrames is only needed later for editing: offer
  "Want me to install the video renderer too? One command, about 2 minutes." On yes:
  `setup.py --install-hyperframes`. Re-check until READY (HyperFrames may stay missing if they said no).
- Ask where their style should live (suggest `~/edit-style`). `setup.py --init "<folder>"`.

### 2. Interview, one question at a time (~5 min). Read `references/interview.md` first.
Colours (or help them pick), font, 3-5 reference reels plus what they love in each, what they never
want, a 5-10 s clip of their own talking-head footage, one website or tool they talk about, the apps
they use, their own sound effects folder (if any). Then:
`brand.py "STYLE" --name ... --accent ... [--paper --soft --deep --ink] [--lines '{...}']` (their niche's
words in the previews, see interview.md), `make_assets.py "STYLE" face "<clip>"`,
`make_assets.py "STYLE" icons <apps...>`, `make_assets.py "STYLE" site <url> --find "<a word on it>"`,
`make_assets.py "STYLE" repo <a busy bright page, e.g. a GitHub repo> --find "Star"`. Look at site.png and
repo.png yourself: if a site came back as one screen (some sites scroll inside a box), pick another page.
Warn in one line if contrast is low (white on a light accent).

### 3. Reference breakdown (~10-15 min, agents). This replaces "copy any creator's style".
`fetch_refs.py "STYLE" <links or files>` (logged out; for long YouTube videos add `--section 0-30`;
Instagram sometimes refuses logged-out downloads: then ask them to save the video and give you the file).
`prep_refs.py "STYLE"` (frames, contact sheets, stills, cuts, loudness, optional transcript). Look at
`references/analysis/overview.jpg`. Then one sub-agent per reel (Sonnet is fine, at most 3 at once) with
`references/breakdown-brief.md`, filled in with what they said they love. While they run, do the font round.
When they're back, read every `breakdown.md` and tell them in under 120 words what their references
share and which mechanics round 1 leans on. Put those findings in STYLE.md "Notes from rounds".

### 4. Font round (optional, ~3 min)
If they're unsure about the font: `make_round.py "STYLE" fonts "<their font>" "Switzer" "General Sans"
"Geist" "Instrument Sans" "Helvetica Neue"` (avoid Inter, Satoshi and other AI-default looks unless they ask).
`server.py start "STYLE" --open`. Same line, same motion, only the font changes. After their pick:
`brand.py "STYLE" --font "<pick>"`, then `make_round.py "STYLE" next` (records the rejected fonts).

### 5. Round 1 and every round after. Read `references/rounds.md` and `references/library.md`.
`make_round.py "STYLE" first`, then shape it with the breakdown findings (tweak params with `set`, add
your own designs to `page/custom.js` with `add`). Check it renders (`shot.mjs`, see rounds.md), then:
"Your style page is open. Every clip is a real animation in your colours: play, pause, drag the bar,
click one to see it big. Hit Keep, Maybe or Drop on each, add a note on anything close ('slower',
'bigger'). Press Submit review, then tell me 'done'."
On "done": `make_round.py "STYLE" next`, read EVERY note (keeps and unrated ones can carry notes too),
fix maybes exactly as asked, design anything new they asked for, update STYLE.md's prose sections and
`style_md.py "STYLE"`, check the page, tell them what changed in a few bullets. Repeat until nothing is
on Maybe (usually 3-4 rounds). If they say things in chat instead of submitting, act on the chat.

### 6. Labs (when a section is close)
Shine Lab (`shine.html`), Zoom Lab (`zoom.html`: drag the curve, direction, up to 5 s), Shadow Lab
(`shadow.html`: over a bright page and their face). Each has a Lock button that saves `locked/<name>.json`
(the old one goes to `locked/old/`). After they lock: read the file, tell them the values in plain words,
`style_md.py "STYLE"`. If they say Lock failed: `server.py start "STYLE"` (it replaces a stale server),
then have them refresh: their slider settings are remembered in the browser.

### 7. Sound effects (~15 min). Read `references/sound.md`.
Ask where their sound library is (or none). `sfx.py scan "<folder>"` to shortlist, plus free
no-attribution sounds fetched on their Mac (Mixkit) where they have gaps. `sfx.py add` / `fetch` 2-3
options per moment. Send them to the Sounds page (`/sfx.html`): each sound plays with its animation at
its real edit level. They Keep / Drop and press Send picks (or tell you in chat): `sfx.py apply-review`.
Adjust levels with `sfx.py level`. Rule: if you can clearly hear it, it's too loud.

### 8. Finish
`style_md.py "STYLE" --check` until nothing important is open; every section in plain English with the
exact numbers (the auto blocks hold the locked values). Music: they pick per edit unless they say
otherwise. Then: "Your style is done and saved in <folder>. Want to try it on a real video? Say
/edit-my-video and drop in a clip." Stop the page server only if they're finished for the day
(`server.py stop "STYLE"`).

## Files
`scripts/`: setup.py (check, init, HyperFrames install) · server.py (start/stop/status, never stale) ·
brand.py (colours, fonts, contrast) · make_assets.py (face clip, icons, screenshots) · shot.mjs
(headless Chrome: full-load screenshots, text boxes, console errors, scrub-and-shoot) · fetch_refs.py,
prep_refs.py (reference reels) · make_round.py (rounds) · sfx.py (sounds) · style_md.py (STYLE.md auto blocks).
`engine/`: the page (copied into each style folder) and first-round.json. `templates/STYLE.md`.
`references/`: interview.md, breakdown-brief.md, rounds.md, library.md, sound.md.
