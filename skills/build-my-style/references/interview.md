# The interview

One question per message. Each question comes with a suggested answer so they can just say "yes".
Plain words, no em dashes. If they've already answered something earlier in the chat, don't ask again.

## 0. Where are they starting from?
"Quick one first: do you already have a brand (colours, a font, a website or a logo), or are we starting
from scratch? Both are totally fine."
- **They have a brand:** "Send me your website (or a screenshot of your logo or a post you like the look
  of) and I'll pull your colours and font from it." For a site: `site_brand.py "<url>"`; read the
  screenshot it saves to check it matches, then say back the paper, ink, accent and font in plain words
  ("white background, dark navy text, your light blue as the accent, and you use Diatype"). For a logo or
  post image: look at it and pick the colours yourself. Their brand is the starting point; offer to make it
  better only where it fights on video (an accent too light for white text, a font that's hard to read
  small), one suggestion at a time.
- **Starting from scratch:** go to 1 and 2 and suggest everything, so all they do is pick.

## 1. Colours
"What colours does your brand use? Paste the codes if you have them (like #FF6B3D), or tell me roughly
('a warm orange and cream') and I'll suggest some."

If they don't have colours, offer 3 small palettes in chat, each one line: paper (background, usually
white), one accent (the colour that pops), and an ink (dark text). Pick from their vibe, their logo or
their website (look at it if they give a link). Recommend one. They need only ONE accent: the rest is
derived (`brand.py` makes soft and deep versions). More than one bright accent fights on screen.
Background: white or a very light tint reads cleanest on video; avoid cream unless they ask.

Then run `brand.py` and read out the contrast line: if white on the accent is under 3:1, say
"White text on your orange is a bit soft to read, so caption boxes will use white with a shadow
instead, or the darker shade." Don't block on it: the person decides.

## 2. Font
"Do you use a font for your brand? If not, I'll show you a few free ones side by side." Free ones that
work for video: Switzer, General Sans (Fontshare), Geist, Instrument Sans (Google Fonts), plus
Helvetica Neue on every Mac. Avoid the AI-default look (Inter, Satoshi, Space Grotesk) unless they ask.
If they name a paid font, say it needs a licence for public use and offer the font round to compare it
with free ones.

## 3. References
"Send me 3 to 5 reels or videos whose editing you love (links or files). For each one, tell me what you
like about it, even just 'clean text' or 'the way logos come in'."
Their reasons go into each breakdown agent's brief. Also ask: "Anything you never want to see in your
edits?" Write the answer straight into STYLE.md under Rejected as their own words.

## 4. Their footage
"Send me a short clip of you talking to camera, 5 to 10 seconds is plenty. It's only for the previews,
so you see every option on your own face." Pick a steady stretch (`--start`). If they have none, any
talking-head clip of theirs works; never use someone else's face.

## 5. A site they talk about, and their apps
"What's one website or tool you talk about a lot?" (for the split-screen and tool-talk previews; use a
normal page, not one that hijacks scrolling). "Which apps do you use most? I'll grab their real icons
from your Mac." (only installed apps work; at least 3 makes the logo options look right).

## 5b. What their videos need (ask, never assume)
Not every niche needs every part. Ask, one at a time, each with a suggested answer:
- "Do you want real photos popping up in your videos now and then, like a quick picture of what you're
  talking about? Lots of creators love it, but it's totally optional." No = leave out the "Real images"
  section and skip the images step.
- Only if they gave no website or tool in 5: "Do you ever talk about apps, websites or tools in your
  videos?" No = leave out "Split screen" and "Tool talk".
Pass what they don't want to `make_round.py "STYLE" first --skip "<Section>" ...`. If they change their
mind later, `make_round.py "STYLE" add` brings any of it back.

## 6. Their words in the previews
Ask nothing extra: build `--lines` from what you know about their content, in their voice:
`{"captions": [3 short chunks], "accent": "a 3-5 word line", "intro": [lead-in, ONE hero word, tail],
"talk": [4 short chunks, the 3rd is where zooms land], "title": [2 short title lines for faded titles
and explainer cards, e.g. ["Content", "Architecture"]]}`. Keep the hero word short (one word, under ~8
letters) so the intro never gets cramped.

## 7. Their own words (all the way through)
Never ask for this: just listen. Every time they say what they like, love, hate or want ("I hate
pop-ins", "that's so clean", "never black backgrounds"), add it word for word to `STYLE/notes/their-words.md`
under a topic heading with the date. That file is the raw record; STYLE.md only gets what they've
finalised (see SKILL.md).

## 8. Sounds (ask later, at the sound step)
"Do you have a folder of sound effects? Tell me where (or drag it in). If not, I'll grab free ones."
