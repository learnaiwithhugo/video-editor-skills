# Sound effects

**The rule: barely noticeable.** In the session this skill comes from, the creator's words were: "as long
as it's really low volume and you can't really hear it ... if it's too obvious, it ruins it." Default
levels in `sfx.py` are quiet on purpose (cuts -8 dB, ticks and taps -12, whooshes -16, shine -18,
relative to each file's peak, under a voice at about -16 LUFS). The Sounds page plays every sound at that
level, so what they hear there is what lands in an edit.

## The moments that need a sound
cut (hard cuts and punch-ins, used a lot) · rise (clean rise; often no sound at all, swooshes felt harsh)
· blur (blur rise) · shine · tick (rings, ticks) · panel (a colour panel sliding over the face) · icon
(app icons rising: a soft tap, never a pop) · click (mouse clicks anywhere, lines drawing on) · hero
(hero word landing: a soft deep whoosh or nothing). Not every moment needs one: "none" is a fine pick.

## Where sounds come from
1. **Their own library first.** Ask where it is. `sfx.py scan "<folder>"` lists likely candidates per
   moment by file name, shortest first. Only read and copy: never move or rename their files. If they
   name a favourite, use it and say so.
2. **Free, no-attribution sounds, fetched on their Mac.** Mixkit's free sound effects licence allows use
   in videos with no credit. Find candidates on mixkit.co (search the site, e.g. "whoosh", "camera
   shutter", "interface click", "sparkle"); each sound page has an id, and the file is
   `https://assets.mixkit.co/active_storage/sfx/<id>/<id>.wav`. Then
   `sfx.py fetch "STYLE" <that url> --need shine --name "Sparkle sweep" --licence "Mixkit Sound Effects Free License (no attribution)"`.
   Pixabay sounds are also free with no attribution, but downloads need a browser: ask them to download
   and hand you the file, then `sfx.py add` with `--licence "Pixabay Content License"`.
   Never put third-party sounds inside this skill folder or anything shared: each person fetches their own.
3. 2-3 options per moment is plenty. More is noise.

## Picking
You can't hear. You can look at length and peak position (`sfx.py add` prints them), so pick candidates by
name, length and shape, then say plainly: "I can't hear these, so they're picks by shape. Have a listen."
They Keep / Drop on the Sounds page and press Send picks (`sfx.py apply-review "STYLE"`), or tell you in
chat (`sfx.py pick` / `drop`). Dropped files move to `sfx/old/` and their names land in STYLE.md's Rejected list.
"Too loud" means `sfx.py level "STYLE" <file> <dB lower by 4-6>`. "Can't hear it" means up by 3.
After every change: `style_md.py "STYLE"` refreshes the table in STYLE.md.
