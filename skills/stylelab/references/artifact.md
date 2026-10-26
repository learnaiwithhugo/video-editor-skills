# The StyleLab page as an artifact

The style page is a private Claude artifact: one link the person opens on claude.ai, on a laptop or a phone.
Claude makes and renders everything on the Mac; the page only shows it and collects Keep / Maybe / Drop.

## The bundle: `STYLE/page/` is exactly what gets published
```
page/index.html          the page (tabs: Round, Images, Sounds, Creators; brand locked at the top)
page/app.js boot.js style.css library.js custom.js
page/round.json          the round on the page (make_round.py writes it). Missing = the example round
page/locked/brand.json   colours + font (+ text_fade.json if one is kept). Missing = the example round
page/profile.json        {"handle": "...", "name": "...", "pfp": "assets/pfp.jpg"} or missing (optional)
page/assets/...          their face clip, cut-out, icons, screenshots, photos, fonts
page/assets/has.json     {"assets/face-cutout.webm": true, ...}: which optional files exist
page/sfx/sfx.json + the sound files on the Sounds tab
page/images/candidates/index.json + <slug>/pNN.jpg|cNN.jpg, images/picks.json, images/index.json
page/creators.json + creators/<posters>
```
`publish.py "STYLE"` copies the style folder's own files into `page/` (sfx/, images/, creators.json, locked/,
profile), writes `assets/has.json`, and prints what to send: the page, `root`, and a `files` map of only what
changed since the last publish (`null` for anything removed). Every path in the page is RELATIVE (`sfx/sfx.json`,
never `/sfx/sfx.json`), so the same folder also works from a plain local server for checks.

The style folder has to sit inside the folder Claude Code was opened in (the Artifact tool only publishes
files from there). Setup suggests `./my-style`.

## Publishing (Claude does this with the Artifact tool)
- First time: publish `page/index.html` with `root: "<STYLE>/page"`, the `files` map from publish.py,
  `capabilities: {"db": {}, "user": {}}`, `icon: "video"`. Save the URL: `publish.py "STYLE" --url <url>`
  writes `STYLE/artifact.json`.
- After that: publish the same file path with `url` from `artifact.json` and only the changed files.
  In a new chat, read the artifact first (`action: "read"`, or a `scope: "files"` listing): a publish to an
  artifact this chat hasn't read is refused.
- Limits: 15 MB per binary file, 255 files per publish. publish.py shrinks the face clip and previews to fit
  and splits a big first publish into batches when needed (it prints them).

## The database (what the page writes, what Claude reads)
- `marks/<tab>:<id>`: `{tab: "round"|"images"|"sounds", id, round, verdict, note, at, by}`: saved as they click and
  type, so a note survives switching devices. `verdict` is keep | maybe | drop for rounds, like | dislike for
  images, keep | drop for sounds, or "" for none.
- `submissions/<time>`: written by each tab's Submit button: `{at, by, kind, payload}`. `payload` is exactly what
  the old local page used to POST, so the scripts read it unchanged:
  - kind `round`: `{kind: "round", round, submitted_at, overall, options: [{id, section, use, params, label, verdict, note}]}`
  - kind `images`: `{kind: "images", picks: [{slug, id, verdict, reason}]}` (every picture they marked)
  - kind `sfx`: the Sounds tab's picks, same shape the old Sounds page sent.

## When they say "done"
1. `ArtifactData` `list` of `submissions` (newest first; take the newest of the kind they finished).
2. Save that document as JSON to a file and run `pull_review.py "STYLE" <file>`. It files a round review to
   `reviews/latest.json`, applies image picks like the old Like / Nope buttons did (`images/liked`, `disliked`,
   `picks.json`), and files sound picks to `reviews/latest-sfx.json` for `sfx.py apply-review`.
3. Carry on as before: `make_round.py "STYLE" next`, `images.py ...`, `sfx.py apply-review`.

## Without Claude (a plain local server, or signed out)
The page still renders and plays everything, marks are kept in the browser, and Submit says it can't reach
Claude. That's how `shot.mjs` checks a round before it's published: `server.py start "STYLE"` serves `page/`.
