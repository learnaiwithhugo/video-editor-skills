---
name: stylelab
description: StyleLab. Walks a creator (usually non-technical) through building their OWN video editing style from scratch, on a private StyleLab page (a Claude artifact they open on their laptop or phone). A short brief first (what it's for, who's watching, their brand, 3-5 reference videos broken down frame by frame, what they never want, how things should move, whether they want visuals, photos and sound effects), then rounds of real animated options in their colours and font (captions, titles, text behind the head, zooms, diagrams, logos, split screen, photos, sounds) they mark Keep / Maybe / Drop with notes and submit, until it's locked. Optional Images (their photo taste from Pinterest and Cosmos) and Sounds (their own library, or free ones from Openverse and Mixkit, or made in code with Earshot). Ends with a STYLE.md (brief, locked, rejected) and locked settings that /edit-my-video uses. Use whenever someone says "/stylelab", "build my style", "make my editing style", "stylelab", "style lab", "I want my own edit style", "copy the editing style of these reels", "copy this part exactly", "make my brand style for videos", sends reels they want their edits to look like, or comes back to carry on their style (rounds, images, sounds, "done"). Also the STYLE keyword giveaway.
---

# /stylelab (StyleLab)

The person ends up with their own editing style, built from nothing: a private StyleLab page (a Claude
artifact) where they watch real animations in their own colours and font, keep what they love, drop what
they don't, and press Submit. You do all the technical work on their Mac. They watch, click and talk.

**Who you're talking to:** a creator who is usually NOT technical. **You lead.** Every message is short and
plain, one question at a time. At the end of every step say in one line what happens next and do it when
they say go. No jargon, no code, no em dashes. Never use the AskUserQuestion popup; ask in chat. Ask before
installing anything. Never ask them to edit a file.

`SK` = this skill's folder. `STYLE` = their style folder (default `./my-style` inside the folder Claude Code
was opened in, because the page is published from there; remembered in `SK/config.json` as `styleDir`).
Run scripts as `python3 -I "SK/scripts/<name>.py"`. Quote every path: they often contain spaces.

## What the style folder holds (other skills read this, keep the layout)
`STYLE.md` (the guide: brief, locked, rejected, open questions) · `artifact.json` (their page's link) ·
`locked/brand.json`, `kept.json` (+ `zoom.json`, `shine.json`, `shadow.json`, `text_fade.json` when they
fine-tune one) · `sfx/sfx.json` + sound files (`sfx/old/` for dropped ones) · `page/` (the published page:
`round.json`, `library.js` + `custom.js`, `assets/` their clip, cut-out, icons, screenshots, photos, fonts;
see `references/artifact.md`) · `images/` · `profile.json` (optional) · `creators.json` · `reviews/` ·
`references/` (their reels + breakdowns + frame galleries) · `notes/their-words.md`.

## Hard rules (each one comes from a real correction)
- **Start from scratch. No taste comes with the skill.** Every look, move, corner, sound level and rule
  comes from their brief and their rounds. The first version of this skill came with its builder's taste
  baked in ("ground rules", image rules, a fixed round 1) and new people were shown his style instead of
  finding their own. The only fixed rules: text inside the safe zone, real logos and screenshots, and copy
  what references DO rather than what they show (STYLE.md template). The one starting list is the slop
  menu (`references/slop-menu.md`), an offer they pick from themselves.
- **Ask, don't add.** Visuals, photos, sound effects, text behind the head, their Instagram: offer each once,
  in plain words, and leave it out if they say no. Never push a section they didn't ask for.
- **Guardrails, not a menu.** STYLE.md fixes the look, not what gets made. An edit built only from the
  page's options felt "extremely restricted". The template says so.
- **Learn the mechanics from references, don't copy their visuals**, with one exception: when the person
  names a moment ("copy frames 7 to 16 exactly"), rebuild THAT part near-exactly in their brand
  (`references/copy-exact.md`). Never bring a creator's own colours, logo or face along.
- **Their brand from round 1, locked at the top of the page.** Every option is in their colours, font and words.
- **Their words are recorded, STYLE.md holds only what's finished.** Everything they say they like or
  hate goes word for word into `notes/their-words.md` (topic headings, dated) as it happens. STYLE.md gets
  a section only once they've decided it.
- **The page only shows what's still in play.** Drops never come back. Keeps stay. Maybes get fixed
  exactly the way the note says, nothing extra.
- **When they name what to keep, that IS the decision.** "Get rid of anything that isn't R2-L6" means
  `keep-only`. If a sentence could mean two things, ask in one line before changing anything.
- **Check it the way they'll see it.** Before publishing a round, run `shot.mjs` on the local copy (no
  console errors, every image loaded, at laptop and phone width) and look at a scrubbed frame of anything
  you changed. After publishing, `ArtifactData` `list` the collections to confirm the page is talking to
  the database. Never say "done" off a guess.
- **Agents can't hear.** Sounds are picked by the person's ears on the Sounds tab. Say so.
- **Never bundle third-party sounds, fonts or photos in this skill.** Fetch them on their Mac, logged out
  (no cookies, no browser profiles). Their own library is only read and copied, never moved or changed.
- **Never delete their stuff.** Old versions go to `old/` folders (the scripts do this).

## Workflow (you lead; they only answer)
Rough time: about an hour for the first sitting, then a few short rounds whenever they like.

### 0. Welcome back? (every run)
If `SK/config.json` has a `styleDir` that exists: read `artifact.json`, `Artifact` `read` the link (a new
chat must read it before it can publish to it), `make_round.py "STYLE" show` and `style_md.py "STYLE"
--check`, then tell them in two lines where they are and what's next, with the link. If they say "done",
go to the matching step's "done". A style folder from the old local-page version (no `artifact.json`):
`setup.py --init "STYLE"` refreshes the page files and keeps theirs, then publish it as in step 1 and say
in one line: "Your style page is now a link you can open on your phone too." Otherwise start at step 1.

### 1. Setup (first time, ~5 min)
Say: "Welcome to StyleLab! First I'll check your Mac has the free tools (about a minute)."
- Must be Claude Code with a local folder (you can run commands). If not: "Open the Claude desktop app,
  click Code, choose Local, pick a folder, then type /stylelab again." Stop.
- `setup.py --check`. Show a short table: tool, found, what it's for. For anything missing give the one
  line from the fix and say where to paste it (Terminal: Command + Space, type Terminal). Their Mac
  password goes in Terminal, never in this chat. HyperFrames is only needed later for editing: offer
  "Want me to install the video renderer too? One command, about 2 minutes." On yes:
  `setup.py --install-hyperframes`. Re-check until READY (HyperFrames may stay missing if they said no).
- `setup.py --init "./my-style"` (or a folder they name inside this one). Create
  `STYLE/notes/their-words.md` with a one-line header.
- **Publish their page straight away** (it opens on an example round): `publish.py "STYLE"`, then the
  Artifact tool as `references/artifact.md` says (first time: `capabilities: {"db": {}, "user": {}}`,
  `icon: "video"`), then `publish.py "STYLE" --url <url>` and `--mark-published`. Send the link: "This is
  your StyleLab page. It's showing an example round for now. Have a look: tap one to see it big. Next I'll
  ask you a few questions so your first real round is made for you."

### 2. The brief, one question at a time (~10 min). Read `references/interview.md` first.
Their Instagram (optional), what it's for and why they edit, where and what shape, who's watching and the
first second, their brand (website or from scratch, colours, font), 3-5 references and what they love in
each, the slop menu then what they never want (`references/slop-menu.md`), how things should move, whether they want visuals on screen (screenshots,
logos, diagrams, photos), sound effects (theirs, or offer to get them) and how they should feel, what to
build first, and a 5-10 s clip of their face. Write it into STYLE.md "The brief", read it back in five
lines, wait for their OK. Then, only for what they said yes to:
`brand.py "STYLE" --name ... --accent ... [--paper --soft --deep --ink] [--lines '{...}']`,
`make_assets.py "STYLE" face "<clip>"` (also makes the head cut-out, about a minute on a Mac),
`make_assets.py "STYLE" icons <apps...>`, `make_assets.py "STYLE" folder`,
`make_assets.py "STYLE" site <url> --find "<a word on it>"`, `make_assets.py "STYLE" repo <a busy bright
page> --find "Star"`. Look at site.png and repo.png yourself: if a site came back as one screen, pick
another page.

### 3. Reference breakdown (~10-15 min, agents)
`fetch_refs.py "STYLE" <links or files>` (logged out; for long YouTube videos add `--section 0-30`;
Instagram sometimes refuses logged-out downloads: then ask them to save the video and give you the file).
`prep_refs.py "STYLE"` (frames, contact sheets, stills, cuts, loudness, optional transcript). Look at
`references/analysis/overview.jpg`. Then one sub-agent per reel (Sonnet is fine, at most 3 at once) with
`references/breakdown-brief.md`, filled in with what they said they love. While they run, do the font round
if they need one. When they're back, read every `breakdown.md` and tell them in under 120 words what their
references share and which of those mechanics round 1 tries. Put the findings in STYLE.md "Notes from rounds".
Record each creator: `creators.py add "STYLE" --name ... --handle ... --took "<what we took>" --reel
"<file>" "<link>" "<title>"` (links are in `references/sources.json`). They show on the Creators tab, with the
links they gave, so their references are always there.
Then offer once: "If one moment in any of these really stood out, I can pull every frame so you can point
at it and I'll copy it exactly in your brand." On yes: step 7.

### 4. Font round (optional, ~3 min)
Only if they're unsure about the font: `make_round.py "STYLE" fonts "<their font>" "Switzer" "General Sans"
"Geist" "Instrument Sans" "Helvetica Neue"`, publish, send the link. Same line, same motion, only the font
changes. After "done": pull the review, `brand.py "STYLE" --font "<pick>"`, `make_round.py "STYLE" next`.

### 5. Round 1 and every round after. Read `references/rounds.md` and `references/library.md`.
Build round 1 from the brief only: `make_round.py "STYLE" first --sections "<what they want first>" ...`,
three to six options per section, one change per option, shaped by their answers and the breakdown
(`set` to tweak params, your own designs in `page/custom.js` with `add`). Never build an option that breaks
a "Slop we cut" rule: `remove` any catalogue option that does. Their colours and font sit
locked at the top of the page. Check it locally, publish, send the link:
"Round 1 is up: <link>. Every one is a real animation in your colours: tap to see it big. Mark Keep, Maybe
or Drop and leave a note on anything close ('slower', 'bigger'). Press Submit review at the bottom, then
come back here and say done."
On "done": `ArtifactData` `list` `submissions`, save the newest round one to a file, `pull_review.py
"STYLE" <file>`, `make_round.py "STYLE" next`, read EVERY note (keeps and unrated ones can carry notes
too), tell them in a few lines what they kept, dropped and any pattern, fix maybes exactly as asked, push
keeps further with new variations, add what they said to `notes/their-words.md`, update STYLE.md (Locked,
Rejected with their reason, Open questions) and `style_md.py "STYLE"`, check, publish, send the link.
Repeat until nothing is on Maybe. If they say things in chat instead of submitting, act on the chat.
When everything in a section is locked, write it up in STYLE.md as rules someone else could follow: fonts
and sizes, colours, how things move and how long, which sounds go on what, and what never to do.

### 6. Images (~10 min, only if they want real photos). Read `references/images.md`.
Ask how photos should sit and move first (no built-in rules). `images.py search "STYLE" "<query>" ...`
(4-6 searches from their niche and references), look at the sheets, publish, send them to the Images tab:
"Like or Nope each photo, add a reason on a Nope if you can, then Submit." On "done": pull the review,
learn the taste, search again in their words. `images.py use "STYLE"` puts the liked ones into the photo
options. Offer the "found again" job (photos like the ones their favourite creators used) as a sub-agent.
Write their image taste into STYLE.md in their words once they're happy.

### 7. Copy-exact (whenever they ask). Read `references/copy-exact.md`.
`frames.py gallery` for the reel, they name frame numbers, `frames.py study` the motion at 12.5-25 fps,
rebuild it in `custom.js` in their brand, check it against the original stills, add it to the round.

### 8. Fine-tuning (only when they ask)
No lab pages. "I want to play with the zoom" = a section of 3-6 variations of that one setting, published
like any round. When they keep one: `make_round.py "STYLE" lock <option id> <zoom|shine|shadow|text_fade>`
so edits use it, then tell them the values in plain words and `style_md.py "STYLE"`.

### 9. Sound effects (~15 min, only if they want them). Read `references/sound.md`.
Their own library first (`sfx.py scan "<folder>"`). None, or a gap: offer Openverse (free, no credit),
Mixkit (free, no credit) or Earshot (made in code, a one-time install: ask first). 2-3 options per moment,
at the level their brief asked for. Publish and send them to the Sounds tab: each sound plays on its
animation at its real edit level. They Keep / Drop and Submit. On "done": pull the review,
`sfx.py apply-review`, adjust levels with `sfx.py level` if they say louder or quieter.

### 10. Finish
Turn `notes/their-words.md` into a short numbered list of plain preferences (one line each) and let them
pick which go into STYLE.md; write those in. `style_md.py "STYLE" --check` until nothing important is
open; every section in plain English with the exact numbers. Music: they pick per edit unless they say
otherwise. Then: "Your style is done and saved in <folder>, and your StyleLab page keeps it all in one
place: <link>. Want to try it on a real video? Say /edit-my-video and drop in a clip."

## Files
`scripts/`: setup.py (check, init, HyperFrames install) · publish.py (bring the page bundle up to date,
say what to publish) · pull_review.py (file a submission from the page) · server.py (a local copy of the
page for checks) · brand.py (colours, fonts, contrast) · site_brand.py (read an existing brand off a
website) · make_assets.py (face clip + cut-out, icons, Mac folder icon, screenshots) · personmask.swift
(the on-device person cut-out) · shot.mjs (headless Chrome: full-load screenshots, text boxes, console
errors, scrub-and-shoot) · fetch_refs.py, prep_refs.py (reference reels) · frames.py (frame galleries and
motion study for copy-exact) · creators.py (the creators list) · images.py (photo search on
Pinterest/Cosmos, picks, the liked set) · make_round.py (rounds, locks) · sfx.py (sounds: their library,
Openverse, Mixkit, Earshot) · style_md.py (STYLE.md auto blocks).
`engine/`: the page (copied into each style folder's `page/`) and first-round.json (the catalogue round 1
picks from). `templates/STYLE.md`.
`references/`: artifact.md, interview.md, slop-menu.md, breakdown-brief.md, rounds.md, library.md,
images.md, copy-exact.md, sound.md.
