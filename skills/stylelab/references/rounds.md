# Running rounds

How the page and the database work: `artifact.md`. Read it once per chat.

## Making a round
- Round 1 is built ONLY from their brief: the sections they asked for first, in their colours, font and
  words, with the moves they described. `make_round.py "STYLE" first --sections "<Section>" ...` (run it
  with no `--sections` to see the catalogue; some sections hold more than six, so `remove` the ones that
  don't fit their brief, and `add` variations that do). Three to six options per section, and change ONE thing per
  option (speed, entrance, size, colour, position) so the comparison is fair. Same words and footage across
  a section. If they said "show me" on movement, give each feel (snappy, smooth, bouncy, filmic) one option.
- Nothing on the page breaks a "Slop we cut" rule in STYLE.md (`slop-menu.md`). `remove` catalogue options
  that do; don't bring one back unless they drop that rule.
- Give each section a one-line job: `make_round.py "STYLE" section-note "<Section>" "<what it's for>"`.
- Say what changed since last round in one line each: `make_round.py "STYLE" round-notes "..." "..."`.
- Locked sections stay on the page as kept cards, so the whole style is in one place.

## Publishing it
1. Check it locally first (below).
2. `publish.py "STYLE"` prints `file_path`, `root` and the `files` map. Publish with the Artifact tool:
   first time with `capabilities: {"db": {}, "user": {}}` and `icon: "video"`, then save the link with
   `publish.py "STYLE" --url <url>`. After that, the same `file_path` + `url` from `artifact.json` + only the
   changed files. In a new chat, `Artifact` `read` the link first. When the publish worked:
   `publish.py "STYLE" --mark-published`.
3. Send the link: "Round N is up: <link>. Play each one, tap it to see it big, mark Keep, Maybe or Drop and
   leave a note on anything close. Press Submit review at the bottom, then come back here and say done."

## When they say "done"
1. `ArtifactData` `list` of `submissions`, save the newest round one to a JSON file, then
   `pull_review.py "STYLE" <file>` (it files it as `reviews/latest.json`).
2. `make_round.py "STYLE" next`: drops leave the page for good (recorded for Rejected), keeps stay
   (recorded in `locked/kept.json` with exact params), maybes stay with `fix` = their note. It warns if the
   review is from an old round: ask before acting on it.
3. Tell them in a few lines what they kept, what they dropped, and any pattern in their notes.
4. Fix every Maybe exactly the way the note says. Nothing extra. Read notes on Keeps and unrated options
   too: "keep but slower" is a change request. Push the Keeps further with a few new variations.
5. Add what they asked for, and nothing they didn't. A note like "make the hero blue" is about that
   option; don't restyle the whole section.
6. Update STYLE.md: keeps under Locked (what it looks like, exact timings and sizes, when to use it),
   drops under Rejected with their reason, open questions. Then `style_md.py "STYLE"` for the auto blocks.
7. Build and publish the next round. Repeat until nothing is on Maybe.

When a section has one clear Keep and they say "go with that", `keep-only "<Section>" <id>` and write it
up in STYLE.md. When they talk in chat instead of submitting ("drop the second logo one"), act on the chat
with `remove` / `keep-only` / `set`; don't ask them to submit.

## Fine-tuning (only when they ask)
There are no lab pages any more. When they want to fine-tune one thing ("I want to play with the zoom
speed", "can the shadow be softer"), make it a section of 3-6 variations of that one setting and publish
it like any round. When they keep one, `make_round.py "STYLE" lock <option id> <zoom|shine|shadow|text_fade>`
saves it to `locked/` so edits use it.

## Tweaking options
- `make_round.py "STYLE" set R1-K2 '{"heroSize": 300}'` changes params (see library.md for each option's
  params). Labels: pass a new label as the 3rd argument when the meaning changed ("slow rise").
- `make_round.py "STYLE" add "Diagrams" tree '{"entrance": "blur", "bg": "accent"}' "Tree, blur rise, on your colour"`
- Something the library can't do: write it in `page/custom.js` with `def()` (library.md shows the helpers),
  then `add` it. It follows their brief, not yours.
- Timings: "slower" usually means about 1.5-2x the duration; "a touch quicker" about 0.8x. Say the numbers
  back to them ("now 1.3 s instead of 0.85 s").

## Craft checks (quality, not taste)
- Text that nearly touches looks broken: give stacked lines room.
- A visual that sits small in empty space looks unfinished: size it for the frame.
- White text on a white scene disappears: check every option on its real background.
- Ask "what visual explains THIS idea best?" A checklist is rarely the answer.

## Checking the page before you publish
`server.py start "STYLE"` serves `page/` locally (no database there, which is fine for a look). Then:

```
node "SK/scripts/shot.mjs" --url http://localhost:<port>/ --out /tmp/round.png --width 1400 --height 1000 --wait-for "window.pageReady" --wait 1500
```
`errors` must be empty. Check at `--width 390` too (phones). To look at one option mid-animation, scroll to
it and drag its scrub bar:
```
--eval "(()=>{const c=document.querySelector('.card[data-id=\"R2-D1\"]');c.scrollIntoView();scrollBy(0,-80);const b=c.querySelector('.scrub');b.value=2400;b.dispatchEvent(new Event('input'))})()" --after 800
```
Read the PNG and look at it. Fix what you see before publishing.

## If something breaks
- Submit says it can't reach Claude: they're on a copy that isn't the artifact, or signed out. Send the
  link again; their marks are kept in the browser.
- A card says `Missing option "x"`: the id isn't in library.js or custom.js. Fix the name or write it.
- Fonts look wrong: `brand.py "STYLE" --font "<name>"` downloads it again, then republish.
- A publish is refused because the chat hasn't read the artifact: `Artifact` `read` the link, then publish.
