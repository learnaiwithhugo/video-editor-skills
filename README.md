# Video editing skills for Claude Code

Turn your raw talking-head clips into finished vertical reels, edited in a creator's style, on your own Mac with free tools.

- **/kallaway-edit** edits your clips in a style inspired by Kallaway: a black stage with a live animated diagram for every idea, your face in a card with your head popping out over the edge, one-word captions, hard cuts on your words, a sound effect on every animation and quiet background music.
- **/new-edit-style** builds a new editing style from 2 or 3 reels of any creator you like. It studies them frame by frame and makes a new `/<name>-edit` skill you can use on your own footage.

## Install

Open Claude Code (the Code tab in the Claude desktop app works), paste this and press Enter:

```
Install the skills from https://github.com/learnaiwithhugo/video-editor-skills
```

Then start a new session and type `/kallaway-edit`. The first run walks you through a short setup.

To update later, paste the same line again.

## For Claude: how to install

When the user asks you to install (or update) these skills, do exactly this:

1. Clone the repo into a temporary folder:
   `git clone --depth 1 https://github.com/learnaiwithhugo/video-editor-skills "$TMPDIR/video-editor-skills"`
   (if that folder already exists from an earlier run, delete it first).
2. Run `bash "$TMPDIR/video-editor-skills/install.sh"`. It copies `kallaway-edit` and `new-edit-style` into `~/.claude/skills/`, and moves any older copy to `~/.claude/skills-backup/` instead of deleting it.
3. Tell the user, in plain English: both skills are installed, start a new Claude Code session, then type `/kallaway-edit` and the setup wizard does the rest. Mention what they need (below), and that the wizard checks it all for them.

Don't change the user's settings or install anything else. The skills' own setup wizard handles the tools on first run.

## What you need

- A Mac
- A paid Claude plan with Claude Code (Pro or higher)
- About 8 GB of free space
- Four free tools: ffmpeg, Node.js, Python and yt-dlp. The easy way: install Homebrew from [brew.sh](https://brew.sh), then paste this into the Terminal app:

  ```
  brew install ffmpeg node python yt-dlp
  ```

On first run, the setup wizard checks all of this, tells you if anything's missing, and installs the rest itself: HyperFrames (the video renderer), Whisper (hears every word so it can cut bad takes and write captions) and the sound effects.

## Where things live

- The skills: `~/.claude/skills/kallaway-edit` and `~/.claude/skills/new-edit-style`
- Your settings, the editor's tools and the sound effects: `~/.claude-video-editor` (updates never touch it)
- Your videos: the folder you pick in setup, with `raw/`, `references/`, `exports/`, `work/` and `archive/`
- Styles you make with /new-edit-style: inside your video folder, at `.claude/skills/<name>-edit`

## Credits

The /kallaway-edit style is inspired by Kallaway ([@kallawaymarketing](https://www.instagram.com/kallawaymarketing/)). Not affiliated with or endorsed by him. Rendering is done by [HyperFrames](https://github.com/heygen-com/hyperframes) by HeyGen. Sound effects come from HyperFrames' free sound kit and are downloaded at setup, not included here.

Made by Hugo Manning ([Learn AI with Hugo](https://learnaiwithhugo.com)).
