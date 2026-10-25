# Copy-exact mode ("copy that part exactly, in my brand")

Sometimes a person falls for one specific moment in a reel ("the bit where the box turns into the brand
brain", "frames 31 to 38"). Then the job is a near-exact rebuild of THAT moment: same layout, same
timing, same motion, only their colours, font, icons and words. This overrides the normal "learn the
mechanics, don't copy the visuals" rule for the parts they name. Everything else stays theirs.

## Steps
1. **Frame gallery.** `frames.py gallery "STYLE" "STYLE/references/<reel>.mp4"` writes every frame at 2 per
   second, numbered. Open it for them: `http://localhost:<port>/refs/analysis/<reel>-frames/index.html`.
   Say: "Scroll through and tell me the frame numbers of the part you love, like 7 to 16."
   Frame N is at (N - 1) / 2 seconds (`frames.py when ...` does the maths).
2. **Look at the stills yourself** for their range (Read the frames, or a contact sheet). Write down every
   element: what's on screen, its size and position as a fraction of the 1080x1920 frame, colours, which
   things are photos vs drawn shapes.
3. **Study the motion.** Two frames a second hides how things move. For every transition in the range:
   `frames.py study "STYLE" "<reel>" <start> <seconds> --fps 12.5` (or `--fps 25` for under a second, and
   `--crop W:H:X:Y` to zoom on the moving part). Read each sheet and note, per element: when it starts,
   how long it takes, how it enters (fades from faint in place, rises, out of a blur, slides from a side,
   grows from slightly big), whether the camera moves (everything shifts together), hard cut or not, and
   what keeps moving after it lands (gentle float, slow drift). Say what you found in plain words: "the
   three faces of the cube light up one at a time, then it hard-cuts to the split with the tile already there."
4. **Rebuild it** as a `def()` in `page/custom.js` (library.md shows the helpers; the explainer helpers
   `ghost`, `tileIn`, `cam`, `scene`, `splitScene`, `bTitle`, `diamond`, `appTile`, `wires` exist for exactly
   this). Match the timings you measured, in ms. Their colours replace theirs one for one (the creator's
   main colour becomes the person's accent, dark grey becomes their ink), their font, their real app
   icons, their words. Real photos stay real photos (from `images/liked/`, never stock).
5. **Check it against the original** at 3-4 matching moments: scrub their option with `shot.mjs` and
   compare with the reference stills side by side. Fix spacing and timing until it reads the same.
6. Add it to the page (`make_round.py add`), label it with where it came from ("Content box to brand brain
   (their reel, 5-6 s)"), and tell them what you matched in a few bullets.

## Rules
- Only the parts they name get copied exactly. Their own branding (the creator's colours, logo, their
  face) never comes along.
- Images keep the image rules: square corners, no zoom unless the original's zoom is the point.
- If a moment needs a photo, search for one like it (`images.py search`), don't reuse the creator's photo.
