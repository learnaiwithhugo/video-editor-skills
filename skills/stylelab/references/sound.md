# Sound effects

Sounds live in `STYLE/sfx/` (the WAVs) and `sfx/sfx.json` (the list the Sounds tab plays and the editor reads).
Everything here starts from scratch for each person. Never assume how loud, how many, or which moments.

## Ask how they should feel
"How should your sounds feel: barely there, noticeable, or punchy?" Then set it:
`sfx.py feel "STYLE" barely|noticeable|punchy`. Write their answer, word for word, in `notes/their-words.md`.

Levels are dB under each sound's own peak (every file is stored with its peak at -1 dB), for a voice at about
-16 LUFS. The Sounds tab plays each sound at that level, so what they hear there is what lands in an edit.

| moment | barely there | noticeable (the neutral start) | punchy |
|---|---|---|---|
| cut | -12 | -6 | -2 |
| rise, blur, panel | -16 | -10 | -6 |
| shine | -18 | -12 | -8 |
| tick, icon, click, hero | -14 | -8 | -4 |

"Noticeable" means you hear it, but the voice stays in front. `feel` only moves sounds nobody has adjusted by
hand (add `--all` to move every one), and every sound added later starts at their feel. After that, tune single
sounds: "too loud" is `sfx.py level "STYLE" <file> <dB, 4-6 lower>`, "can't hear it" is up by 3. Nothing goes
above -2.

## The moments that can have a sound
cut (hard cuts and punch-ins) · rise (a clean rise) · blur (a blur rise) · shine · tick (rings, ticks) · panel
(a colour panel sliding over the face) · icon (app icons rising in) · click (mouse clicks, lines drawing on) ·
hero (the hero word landing). Ask which moments they want sounds on. "None" is a fine answer for any of them.

Search words that work per moment: cut "camera shutter", rise "swoosh", blur "air whoosh", shine "sparkle",
tick "ui tick", panel "slide whoosh", icon "soft pop", click "mouse click", hero "deep impact".

## Where sounds come from
1. **Their own library first.** Ask where it is. `sfx.py scan "<folder>"` lists likely candidates per moment by
   file name, shortest first. Only read and copy: never move or rename their files. If they name a favourite,
   use it and say so.
2. **None, or a gap? Offer these three, one line each** (say what each is, then let them choose):
   - **Openverse:** "a free search engine for sounds other people shared for anyone to use. I take short ones
     that need no credit." No account, nothing to install.
     `sfx.py openverse "STYLE" "whoosh" --need blur --n 4 --max-seconds 3` (cc0 only, no credit needed). It
     searches by words and length, skips titles that look like packs, downloads on their Mac, and files each
     as a candidate with its licence, link and creator. Free use is 20 searches a minute and 200 a day: if it
     says to slow down, wait and run it again, or use Mixkit meanwhile. `--licence by` also allows CC BY, but
     then the creator has to be credited in the post: only with their yes, then `sfx.py credits "STYLE"` prints
     the lines for the picked ones.
   - **Earshot:** "a free tool that makes sounds from code instead of recordings, so there is no licence to
     think about." It needs a one-time install (about 1 GB; designing a brand-new sound adds a 1.1 GB download
     the first time) and an Apple Silicon Mac. It is the only thing here that installs software, so **always
     ask first**: say what it is, how big, and wait for a yes. `sfx.py earshot-help` prints the install lines
     and every command. Read it, tell them in plain words, run the install only after the yes. What it makes
     goes in with `sfx.py add` (trims, fades, sets the peak): pass `--licence "Made in code with Earshot (MIT),
     no credit needed"`. It's new software (v0.4.0), so if the install fails, say so and move on to Openverse.
   - **Mixkit:** "free sound effects you can use in videos with no credit." Find candidates on mixkit.co
     (search the site, e.g. "whoosh", "camera shutter", "interface click", "sparkle"); each sound page has an
     id, and the file is `https://assets.mixkit.co/active_storage/sfx/<id>/<id>.wav`. Then
     `sfx.py fetch "STYLE" <that url> --need shine --name "Sparkle sweep" --licence "Mixkit Sound Effects Free License (no attribution)"`.
     Mixkit is the fallback when Openverse is busy or has nothing short enough.
   Pixabay sounds are also free with no credit, but downloads need a browser: ask them to download one and
   hand you the file, then `sfx.py add` with `--licence "Pixabay Content License"`.
   Never put third-party sounds inside this skill folder or anything shared: each person fetches their own,
   logged out (no cookies, no browser profiles).
3. 2-3 options per moment is plenty. More is noise.

Not a source: Real SFX (a free Claude Code skill by Clipwing) places sounds from your own library on exact
frames. It comes without a sound library, and `/edit-my-video` already places sounds from `sfx.json`, so it
isn't part of this.

## Picking
You can't hear. You can look at length and peak position (`sfx.py add` prints them), so pick candidates by
name, length and shape, then say plainly: "I can't hear these, so they're picks by shape. Have a listen."
They Keep / Drop on the Sounds tab and submit, or tell you in chat (`sfx.py pick` / `drop`). Pulling their
picks is `sfx.py apply-review "STYLE"`. Dropped files move to `sfx/old/` and their names land in STYLE.md's
Rejected list. After every change: `style_md.py "STYLE"` refreshes the table in STYLE.md.
