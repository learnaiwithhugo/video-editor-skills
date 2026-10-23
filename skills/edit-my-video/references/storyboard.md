# The storyboard (step 4) and variations (step 5)

The storyboard is cheap (stills, no renders) and catches most "I'm not happy with it" before the edit
exists. Every frame is the beat's key moment on the user's REAL footage with the planned visual on top.

## storyboard.json (WORK/storyboard.json)
```json
{
  "video": "GitHub repos that replace SaaS tools",
  "slug": "github-repos",
  "folder": "/path/to/raw clips",
  "length_s": 32.9,
  "notes": ["Takes: last clean take of each line ...", "Left out: ... (the hook says 10)"],
  "beats": [
    {"id": "b2", "section": "Hook", "label": "Save money", "start": 3.27, "end": 4.9,
     "words": "These will save you so much money.",
     "source": {"clip": "01 - hooks (IMG_4712).MOV", "in": 104.885, "out": 106.518, "in_tc": "1:44.89", "out_tc": "1:46.52"},
     "layout": "face", "on_screen": "Just his face. Caption above his head.",
     "entrance": "Soft fade-up captions.", "zoom_cut": "Hard cut, cut in at 120% and glide out.",
     "caption": "Plain white with the locked shadow, 'money' in the accent colour.",
     "sfx": "cut (shutter) on the cut", "frame": "frames/b2.jpg"},
    {"id": "b1", "section": "Hook", "label": "Hook", "start": 0, "end": 3.27, "words": "...", "source": {...},
     "recommended": "A",
     "alternatives": [
       {"pick": "A", "name": "Hero word FREE", "layout": "face", "on_screen": "...", "entrance": "...",
        "zoom_cut": "...", "caption": "...", "sfx": "...", "frame": "frames/b1-A.jpg"},
       {"pick": "B", "name": "...", "frame": "frames/b1-B.jpg"},
       {"pick": "C", "name": "...", "frame": "frames/b1-C.jpg"}],
     "note": "optional line shown under the plan (e.g. 'Pick C changes the whole list')"}
  ]
}
```
- `start`/`end` are reel seconds (from segments.json once cut; estimates before). `source` is the take used.
- `layout`: face | split | full (a full-screen visual) | footage (screen recording).
- Write the plan in plain words: the person reading it isn't technical.
- A/B/C only on the 3 or 4 key beats, and make them genuinely different ideas, not three colours of one.
  Put your recommendation in `recommended`; it's labelled "my pick" on the page.
- After review, `storyboard.py review` adds `approved_pick`, `verdict` (approve | change) and `note` to each
  beat. `cut.py --from-storyboard` reads `approved_pick` (else `recommended`) to decide each segment's kind.

## Making the stills
1. Footage stills: `shoot.py frame "<clip>" <seconds> "WORK/storyboard/assets/footage/<beat>.jpg"` at each
   beat's key moment (a frame where the mouth is mid-word looks natural).
2. `python3 SK/scripts/style.py project "STYLE" "WORK/storyboard"` puts style.css, kit.css and fonts into
   `WORK/storyboard/assets/` so stills look exactly like the edit will.
3. Copy `SK/engine/still.html` to `WORK/storyboard/src/<beat>.html` (or `<beat>-A.html`), compose the visual
   at its key moment (the end state of its animation) over the footage, with the caption where it will sit.
   Real screenshots (`shoot.py web <url> <png> --mobile`) and real icons (`shoot.py icon "<App>" <png>`).
4. `shoot.py html "WORK/storyboard/src/b1-A.html" "WORK/frames/b1-A.jpg" ...` (many pairs in one call).
   JPGs keep the page fast (big PNGs made the first storyboard page crawl).
5. Look at every frame yourself before showing the page: same checks as the edit (creative-rules.md).

## The page
`storyboard.py page "WORK" --style "STYLE"` writes `STYLE/page/storyboards/<slug>/index.html` and copies the
frames. It's the page the creator liked: a row per beat with the frame(s), time, their exact words, the
take it came from, Visual / Animation / Caption / Sound, Approve / Change, a note box, Pick buttons on A/B/C,
a big view on click, Submit at the top. Submit posts to the style folder's server (`/api/review`), which
saves `STYLE/reviews/round-storyboard-<slug>-<time>.json`. Everything they click is remembered in the
browser until they submit. Start the server with `style.py serve "STYLE"` if it isn't running.

## Variations (the @viiolini idea, kept cheap)
The same moment rendered 2 or 3 ways side by side, on the real footage. Only for 2 or 3 key moments, each
2 to 4 s: `render.py slice` renders just that window of the edit (or of a variant copy of index.html) at
draft quality in ~6 s. Add `"video": "variations/<name>.mp4"` to those alternatives and build
`storyboard.py page ... --variations` (variations.html, videos autoplay on loop). Review the same way.
