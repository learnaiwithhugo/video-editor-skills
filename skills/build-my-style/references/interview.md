# The interview

One question per message. Each question comes with a suggested answer so they can just say "yes".
Plain words, no em dashes. If they've already answered something earlier in the chat, don't ask again.

## 1. Colours
"What colours does your brand use? Paste the codes if you have them (like #FF6B3D), or tell me roughly
('a warm orange and cream') and I'll suggest some."

If they don't have colours, offer 3 small palettes in chat, each one line: paper (background, usually
white), one accent (the colour that pops), and an ink (dark text). Pick from their vibe, their logo or
their website (look at it if they give a link). Recommend one. They need only ONE accent: the rest is
derived (`brand.py` makes soft and deep versions). More than one bright accent fights on screen.

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

## 6. Their words in the previews
Ask nothing extra: build `--lines` from what you know about their content, in their voice:
`{"captions": [3 short chunks], "accent": "a 3-5 word line", "intro": [lead-in, ONE hero word, tail],
"talk": [4 short chunks, the 3rd is where zooms land]}`. Keep the hero word short (one word, under ~8
letters) so the intro never gets cramped.

## 7. Sounds (ask later, at step 7)
"Do you have a folder of sound effects? Tell me where (or drag it in). If not, I'll grab free ones."
