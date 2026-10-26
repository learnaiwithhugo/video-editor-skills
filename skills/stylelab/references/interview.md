# The brief (the interview)

One question per message. Wait for the answer before the next one. When an answer is vague ("clean",
"modern", "like that guy"), follow up once: "What does clean look like to you? Name one video, or tell me
what you'd see on screen." Plain words, no em dashes. If they've already answered something earlier in the
chat, don't ask again.

**Start from nothing.** Never suggest a taste: no "most creators like...", no "I'd go with...". Where a
question lists choices, list them evenly and let them pick. Their answers are the only source of the style.
(The first version of this skill came pre-loaded with one creator's taste and new people got his style
instead of their own. Don't do that.)

## The questions, in order

**1. Their Instagram (optional).** "Want your previews to look like your own Instagram? Tell me your handle
and I'll show your picture and name on the safe-zone preview. Totally optional, you can skip it."
- Handle given: open `https://www.instagram.com/<handle>/` logged out (no cookies), its `og:image` is their
  picture and `og:title` their name. Save the picture to `STYLE/page/assets/pfp.jpg` and write
  `STYLE/profile.json` `{"handle", "name", "pfp": "assets/pfp.jpg"}`. If Instagram won't show it logged out,
  just save the handle.
- Skipped: move on, never ask again.

**2. What's it for?** "What's this style for? Your own videos, a brand, a client, something else? And why do
you edit: what do you want the editing to do for your videos?"

**3. Where and what shape?** "Where will these videos live, and what shape are they? Vertical 9:16 (Reels,
TikTok, Shorts), wide 16:9 (YouTube), or square?"

**4. Who's watching?** "Who's watching, and what should they feel in the first second?"

**5. Their brand.** "Do you already have a brand (colours, a font, a website or a logo), or are we starting
from scratch? Both are fine."
- They have one: "Send me your website, or a screenshot of your logo or a post you like the look of, and
  I'll pull your colours and font from it." Website: `site_brand.py "<url>"`, look at the screenshot it saves,
  say the colours and font back in plain words and confirm. Image: look at it and pick the colours yourself.
- From scratch: ask what colours they're drawn to (or a mood, "warm and earthy", "black and electric"), then
  offer 3 small palettes in one line each (paper, one accent, ink) that fit THEIR answer. They pick.
- Font: "Do you use a font? If not, I'll show you a few side by side." Free fonts that work on video:
  Switzer, General Sans (Fontshare), Geist, Instrument Sans (Google Fonts), Helvetica Neue on every Mac. A
  paid font needs a licence for public use: say so once. The font round (SKILL.md step 4) settles it.
- `brand.py` and read out its contrast line in plain words. Don't block on it: they decide.
- Their colours and font are locked at the top of their StyleLab page from now on.

**6. References.** "Send me 3 to 5 videos whose editing you love (links or files). For each one, tell me
what you love about it, even just 'clean text' or 'the way logos come in'." Ask about each one they send:
"What's the moment in this one you'd steal?" Their reasons go into each breakdown agent's brief, and every
reference ends up on the Creators tab (SKILL.md step 3).

**7. Never.** "What do you never want to see in your edits?" Write the answer straight into STYLE.md's
Rejected list as their own words.

**8. How should things move?** "How should things move: snappy, smooth, bouncy, filmic, physical, glitchy,
or 'show me'?" "Show me" = round 1 holds one option of each feel for the same moment.

**9. Visuals on screen.** "Do you want visuals popping up while you talk? Like screenshots of what you're
talking about, app logos, diagrams, or real photos." Then only what they said yes to:
- Websites or tools: "What's one website or tool you talk about a lot?" (for split screens; a normal page,
  not one that hijacks scrolling).
- App logos: "Which apps do you talk about most? I'll grab their real icons from your Mac."
- Real photos: the Images step (SKILL.md step 6) runs later. "What kind of photos: your world, moody,
  funny film stills, something else?"
- No to all of it: no visuals sections in round 1, no Images step. They can ask any time later.

**10. Sounds.** "Do you have your own sound effects? If so, tell me the folder (or drag it in)." If not:
"No problem. I can get them for you: free ones from Openverse or Mixkit, or have them made in code with a
tool called Earshot (a one-time install). Want me to?" Then: "How should your sounds feel: barely there,
noticeable, or punchy?" See `sound.md`.

**11. What first?** "What should we build first? Captions, titles, transitions, zooms, visuals, sounds, or
should I pick?" If they say pick, choose from their brief and say why in one line.

**12. Their footage.** "Last one: send me a short clip of you talking to camera, 5 to 10 seconds is plenty.
It's only so every option plays on your own face." Pick a steady stretch (`--start`). Never use someone
else's face. No clip yet = options without the face until they send one.

## Then: the brief back to them
Write the answers into STYLE.md "The brief" (one bullet each, their words), then read it back in five lines
and wait for their OK before round 1. Change anything they correct.

## Their words in the previews
Ask nothing extra: build `--lines` for `brand.py` from what you know about their content, in their voice:
`{"captions": [3 short chunks], "accent": "a 3-5 word line", "intro": [lead-in, ONE hero word, tail],
"talk": [4 short chunks, the 3rd is where zooms land], "title": [2 short title lines]}`. Keep the hero
word short (one word, under ~8 letters) so the intro never gets cramped.

## Their own words (all the way through)
Never ask for this: just listen. Every time they say what they like, love, hate or want, add it word for
word to `STYLE/notes/their-words.md` under a topic heading with the date. That file is the raw record;
STYLE.md only gets what they've finalised.
