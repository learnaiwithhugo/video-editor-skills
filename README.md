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

You don't need to know any code. You paste one line into Claude and it does the rest.

1. **Open Claude Code.** Download the Claude app from [claude.ai/download](https://claude.ai/download), sign in with your paid Claude account, click the **Code** tab, choose **Local**, then pick any folder (make a new one called "My videos" if you like). A box to type in appears at the bottom.
2. **Paste this into that box and press Enter:**

   ```
   Install the skills from https://github.com/learnaiwithhugo/video-editor-skills
   ```

   Claude will ask your permission to run a few things. Say yes. If a Mac window pops up asking to install "developer tools", click **Install**, wait for it to finish, then paste the line again.
3. **Start a new chat** (so Claude sees the new skills), type `/build-my-style` and press Enter. Claude takes it from there, one question at a time.
4. When your style is done, type `/edit-my-video` and drop in your clips.

To update later, paste the same line again. Your style and your saved folders stay put.

### First run: what Claude will ask you to install

The first time, Claude checks your Mac and lists anything missing (see "What you need" below). It tells you exactly what to paste. Anything it asks you to paste goes in the **Terminal** app, not in the chat:

- Press **Command + Space**, type **Terminal**, press Enter. A window with a blinking cursor opens.
- Paste with **Command + V**, then press Enter. Wait until the cursor comes back. Some commands take a few minutes. That's normal.
- If it asks for a password, it's your Mac login password. Nothing shows while you type it. Type it and press Enter.

If you'd rather get the tools in before you start, do this once:

1. In Terminal, install Homebrew (the free installer Mac developers use). Copy the line from [brew.sh](https://brew.sh). It takes a few minutes. When it finishes it prints "Next steps": copy and run those lines too, then close Terminal and open it again.
2. Then paste:

   ```
   brew install ffmpeg node python yt-dlp
   ```

And if you don't have Google Chrome, [download it](https://www.google.com/chrome).

## For Claude: how to install

When the user asks you to install (or update) these skills, do exactly this:

1. Clone the repo into a fresh temporary folder:
   `DIR="$(mktemp -d)" && git clone --depth 1 https://github.com/learnaiwithhugo/video-editor-skills "$DIR/video-editor-skills"`
   (if git isn't installed, a Mac window offers to install the developer tools: tell the user to click Install, wait, and tell you when it's done).
2. Run `bash "$DIR/video-editor-skills/install.sh"`. It copies `build-my-style`, `edit-my-video`, `kallaway-edit` and `new-edit-style` into `~/.claude/skills/`, moves any older copy to `~/.claude/skills-backup/` instead of deleting it, and carries over each skill's saved folders.
3. Tell the user, in plain English: the skills are installed, start a new Claude Code session, then type `/build-my-style` to make their style and `/edit-my-video` to edit with it. Mention what they need (below), and that each skill checks it all for them.

Don't change the user's settings or install anything else. Each skill's own setup step handles the tools on first run.

## What you need

- A Mac
- Claude Code (a paid Claude plan)
- About 8 GB of free space
- Free tools: ffmpeg (cuts video and sound), Node.js (runs the renderer), Python (runs the helper scripts) and yt-dlp (downloads reels you want to learn from)
- Google Chrome (for taking screenshots of real websites)

On first run each skill checks your Mac, tells you what's missing in plain English, and asks before installing anything else itself: HyperFrames (the free video renderer), Whisper (hears every word so it can pick takes and write captions) and a few small Python helpers. Those go in their own folder (`~/.claude-video-editor`), never into the Mac's own Python.

## If something goes wrong

- **"command not found: brew"** in Terminal: run the "Next steps" lines Homebrew printed at the end of its install, then close and reopen Terminal.
- **The check says NOT READY:** read the line marked MISSING, run the fix it gives, then tell Claude "done" and it checks again.
- **A page won't load or a button says it failed:** tell Claude. It restarts the little page server for you and gives you a fresh link. Your marks are saved in the browser.
- **Anything else:** copy the red or confusing text, paste it to Claude and ask what it means.

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
