# Video editing skills for Claude Code

Build your own video editing style, then let Claude edit your raw talking-head clips into finished vertical reels in it. Everything runs on your own Mac with free tools.

## The two main skills

**1. /build-my-style** makes your editing style on a page in your browser.

- Tell it your colours, your font, and a few reels you love. It breaks those reels down frame by frame to learn the timing and pacing (never copying their look).
- Your page fills with real animations in your own brand: captions, intro text, zooms on your face, diagrams, logos, split screens. Mark each one **Keep**, **Maybe** or **Drop**, add a note like "slower" or "bigger", and press Submit. Each round only shows what's still in play.
- Fine-tune the details in the **Shine**, **Zoom** and **Shadow** labs and press Lock when it looks right.
- Pick your sound effects by ear on the Sounds page.
- You end up with a style folder (a plain-English `STYLE.md` plus your locked settings) that /edit-my-video reads.

**2. /edit-my-video** edits your raw clips in that style.

- Drop in a folder of clips (repeated takes are fine, it picks the last clean take of every line).
- It shows you a **storyboard first**: a still for every beat, with A, B or C options on the key moments. Approve or change each one before anything renders.
- Then it builds the full edit, checks its own render, and opens the video for you.
- Every note you give ("make the logos bigger", "I don't like that zoom") gets fixed AND saved into your style, so the next edit already knows.

## Install

Open Claude Code (the Code tab in the Claude desktop app works), paste this and press Enter:

```
Install the skills from https://github.com/learnaiwithhugo/video-editor-skills
```

Then start a new session and type `/build-my-style`. When your style is done, type `/edit-my-video`.

To update later, paste the same line again. Your style and your saved folders stay put.

## For Claude: how to install

When the user asks you to install (or update) these skills, do exactly this:

1. Clone the repo into a temporary folder:
   `git clone --depth 1 https://github.com/learnaiwithhugo/video-editor-skills "$TMPDIR/video-editor-skills"`
   (if that folder already exists from an earlier run, delete it first).
2. Run `bash "$TMPDIR/video-editor-skills/install.sh"`. It copies `build-my-style`, `edit-my-video`, `kallaway-edit` and `new-edit-style` into `~/.claude/skills/`, moves any older copy to `~/.claude/skills-backup/` instead of deleting it, and carries over each skill's saved folders.
3. Tell the user, in plain English: the skills are installed, start a new Claude Code session, then type `/build-my-style` to make their style and `/edit-my-video` to edit with it. Mention what they need (below), and that each skill checks it all for them.

Don't change the user's settings or install anything else. Each skill's own setup step handles the tools on first run.

## What you need

- A Mac
- Claude Code (a paid Claude plan)
- About 8 GB of free space
- Free tools: ffmpeg, Node.js, Python and yt-dlp. The easy way: install Homebrew from [brew.sh](https://brew.sh), then paste this into the Terminal app:

  ```
  brew install ffmpeg node python yt-dlp
  ```

- Google Chrome (for taking screenshots of real websites)

On first run each skill checks your Mac, tells you what's missing in plain English, and asks before installing anything else itself: HyperFrames (the free video renderer), Whisper (hears every word so it can pick takes and write captions) and a few small Python helpers.

## Nothing third-party is bundled

Your font is downloaded from Fontshare or Google Fonts on your Mac. Sound effects come from your own library or are downloaded on your Mac from free, no-credit-needed sites. App icons are taken from the apps already on your Mac. Your own face clip is used for the previews. None of it is included in this repo.

## Where things live

- The skills: `~/.claude/skills/` (`build-my-style`, `edit-my-video`, `kallaway-edit`, `new-edit-style`)
- Your style: the folder you pick (suggested: `~/edit-style`)
- Your edits: the folder you pick on the first /edit-my-video run (one folder per video)

## Extras: two more skills

- **/kallaway-edit** edits your clips in a ready-made style inspired by Kallaway: a black stage with a live animated diagram for every idea, your face in a card with your head popping out over the edge, one-word captions, hard cuts on your words, a sound effect on every animation and quiet background music. Its settings and sounds live in `~/.claude-video-editor`.
- **/new-edit-style** builds a new editing style from 2 or 3 reels of any creator you like and turns it into its own `/<name>-edit` skill, saved inside your video folder at `.claude/skills/<name>-edit`.

## Credits

The /kallaway-edit style is inspired by Kallaway ([@kallawaymarketing](https://www.instagram.com/kallawaymarketing/)). Not affiliated with or endorsed by him. Rendering is done by [HyperFrames](https://github.com/heygen-com/hyperframes) by HeyGen. /kallaway-edit's sound effects come from HyperFrames' free sound kit and are downloaded at setup, not included here.

Made by Hugo Manning ([Learn AI with Hugo](https://learnaiwithhugo.com)).
