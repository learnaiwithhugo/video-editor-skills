# Running rounds

## The loop
1. The page shows `page/round.json`. They mark Keep / Maybe / Drop with notes and press Submit review.
   The server saves `reviews/latest.json`. They tell you "done".
2. `make_round.py "STYLE" next`: drops leave the page for good (recorded for STYLE.md's Rejected list),
   keeps stay (recorded in `locked/kept.json` with exact params), maybes stay with `fix` = their note.
   It warns if the review is from an old round (an old tab): ask before acting on it.
3. Fix every Maybe exactly the way the note says. Nothing extra. Read notes on Keeps and unrated
   options too: "keep but slower" is a change request.
4. Add what they asked for, and nothing they didn't. A note like "make the hero blue" is about that
   option; don't restyle the whole section.
5. Update STYLE.md: rewrite the plain-English section for anything decided this round (what it looks
   like, exact timings and sizes, when to use it), then `style_md.py "STYLE"` to refresh the auto blocks.
6. Check the page (below), then tell them what changed in 3-6 bullets and what's next.

When a section has one clear Keep and they say "go with that", `keep-only "<Section>" <id>` and lock it
in STYLE.md. When they talk in chat instead of submitting ("drop the second logo one"), act on the chat
with `remove` / `keep-only` / `set`; don't ask them to submit.

## Tweaking options
- `make_round.py "STYLE" set R1-K2 '{"heroSize": 300}'` changes params (see library.md for each
  option's params). Labels: pass a new label as the 3rd argument when the meaning changed ("slow rise").
- `make_round.py "STYLE" add "Diagrams" tree '{"entrance": "blur", "bg": "accent"}' "Tree, blur rise, on your colour"`
- Something the library can't do: write it in `page/custom.js` with `def()` (library.md shows the
  helpers), then `add` it. Keep their taste: clean entrances, their colours, real assets.
- Timings: "slower" usually means about 1.5-2x the duration; "a touch quicker" about 0.8x. Say the
  numbers back to them ("now 1.3 s instead of 0.85 s").

## What the first test edits taught (apply when designing options)
- Hook text gets cramped: give intro lines generous gaps, never let lines nearly touch.
- Full-screen visuals that sit small near the top look empty: make them big and centred.
- White captions vanish on white scenes: use the locked shadow, or a box only on very busy backgrounds.
- Ask "what visual explains THIS idea best?" A checklist is rarely the answer.

## Checking the page before you hand it over
Restart cleanly when the engine changed: `setup.py --init "STYLE"` (refreshes engine files, keeps theirs)
then `server.py start "STYLE"`. Then:

```
node "SK/scripts/shot.mjs" --url http://localhost:<port>/ --out /tmp/round.png --width 1400 --height 1000 --wait-for "window.pageReady" --wait 1500
```
`errors` must be empty. To look at one option mid-animation, scroll to it and drag its scrub bar:
```
--eval "(()=>{const c=document.querySelector('.card[data-id=\"R2-D1\"]');c.scrollIntoView();scrollBy(0,-80);const b=c.querySelector('.scrub');b.value=2400;b.dispatchEvent(new Event('input'))})()" --after 800
```
Read the PNG and look at it. Fix what you see before telling them it's ready. Labs: same with
`/shine.html`, `/zoom.html`, `/shadow.html`, `/sfx.html`.

## If something breaks
- "Couldn't send" or Lock fails: `server.py start "STYLE"` (replaces stale servers), then they refresh.
  Their marks and slider settings are kept in the browser.
- A card says `Missing option "x"`: the id isn't in library.js or custom.js. Fix the name or write it.
- Fonts look wrong: `brand.py "STYLE" --font "<name>"` downloads it again.
