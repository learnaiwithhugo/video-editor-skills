# The slop menu (brief question 7)

A short list of the things that make an edit look AI-made or cheap. It runs at question 7 of the brief,
before "What do you never want to see?", so round 1 is built without the ones they pick. It's an offer,
not taste you push: nothing is picked for them.

## How to run it
Say: "Here are some sloppy things Claude does when it edits videos. Pick which ones you want
automatically excluded from your edits, and add any of your own." Then show the menu below in chat, numbered
(the short name and the one-line why). Never the AskUserQuestion popup.

They answer in words ("1, 3 and 5", "all of them", "none"). Read their picks back once, then:
- Every line they picked goes into STYLE.md "Slop we cut" as its rule (below), word for word, with the date.
- Anything they add goes in the same section, in their words, written as a rule someone else could follow.
- Lines they didn't pick go into `notes/their-words.md` ("not cut: ..."). Don't offer them again.
- Then ask question 7 as normal for anything else they never want.

From then on every round respects "Slop we cut": never build an option that breaks one of its rules
(no rounded option when corners are cut, no bounce-in when pop-ups are cut). If they later want one back,
move that rule to `old/` notes and say so in one line.

## The menu

| # | Short name | Why it looks cheap | The rule that goes into STYLE.md |
|---|---|---|---|
| 1 | Over-animated captions | Every word bouncing or flashing is tiring to read | Captions show 3 words at a time at most. No bouncing, no wobbling. |
| 2 | The generic italic font | The default italic that every auto-edit uses | No default italic edit font. Text uses TikTok Classic, or one font that's theirs. |
| 3 | Emojis and icons | Clip-art stands in for the real thing | No emojis or stock icons. Show the real thing: a screenshot, or a real photo found on Google or Pinterest (app logos are the real icon from the app). |
| 4 | Rounded corners | Every box, image and pill rounded is the template look | Square corners on every box and image. No pills. |
| 5 | Dead space | Gaps and breaths make it drag | Cut every gap over 0.1 s. |
| 6 | Generic scale-up pop-ups | Every AI edit has the same scale-up pop | Nothing pops in by scaling up. Things cut in, or come in a way locked in the rounds. |
| 7 | Animating what should just cut in | Motion on everything means motion means nothing | The default entrance is a hard cut. Something only animates in when the move itself says something. |
