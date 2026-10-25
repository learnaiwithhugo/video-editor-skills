# The Images round

Real photos on screen are a big part of a good edit, and everyone's taste in them is different. This round
builds the person's own: they like and drop real photos on the Images page, and what they pick (and why)
becomes the Images section of their STYLE.md. Tool: `scripts/images.py`. Page: `/images.html`.

## When
After round 1 is going (brand, interview and reference breakdowns done). Say it in one line: "Now let's
find the kind of photos you'd put in your edits. About 10 minutes, mostly clicking."

## The defaults (they are on the page; the person can change any of them)
1. Images never have rounded corners. Sharp rectangles, no glassy bubble or tile around them.
2. No stock photos (posed, studio-lit, corporate, the Pexels/Unsplash look).
3. Nothing AI-looking (plastic, too perfect, render look).
4. No zooming on images: an image is slapped on screen, sits still, then hard cuts. Zoom only when there is a reason.
5. Real, candid, good-looking photos with real light. Film and pop-culture stills are great for joke moments.
   No text burned in, no watermarks, no magazine covers, no Instagram or Xiaohongshu screenshots.

These came from one creator's corrections ("no rounded corners" was the biggest preference he had). The page
always shows the defaults. When the person reverses one, write the change in STYLE.md (drop or flip the rule
there) and say so; their likes and dislikes become the real guide.

## Steps
1. **Tools.** `python3 -I -c "import requests, PIL"`. If it fails, ask before running `pip3 install requests pillow`.
   Everything is logged out: no cookies, no keys, no browser profile. Pinterest is an unofficial route:
   fine for photos inside their own edits, not for passing the pictures on.
2. **Pick 4 to 6 searches** from their niche, their references (look at the photos the reels show on screen in
   `references/analysis/*/overview.jpg` and the contact sheets) and what they said they love. Describe the
   moment or the mood, not a brand. Mix: 2 about their world ("person working late laptop aesthetic",
   "hands typing film photo", "messy desk morning light"), 1 or 2 mood or colour ("quiet city street
   night film grain"), 1 pop-culture or film still for joke moments ("movie still man staring at screen").
   Never put "stock" in a query.
3. **Search.** `python3 -I "SK/scripts/images.py" search "STYLE" "<q1>" "<q2>" ... --n 8`. About 15 seconds a
   query (it pauses between requests on purpose). Each query becomes a folder in `STYLE/images/candidates/`
   named by the query's slug; pictures are p1.. (Pinterest) and c1.. (Cosmos). Running a query again only adds
   what is missing, numbers never change.
4. **Look first.** `images.py sheet "STYLE"` makes `candidates/<slug>/sheet.jpg` (rows PINTEREST and COSMOS, the
   number burned in each picture). Read every sheet yourself. If a query came back mostly stock or AI-looking,
   search again with better words before the person sees it. Don't pre-mark anything for them. Tell them in
   two lines what you noticed ("p3 has text in the picture, p4 looks AI"), they decide.
5. **Send them to the page.** `server.py start "STYLE" --open`, then give them the address plus `/images.html`.
   "Open the Images page. Hit Like on photos you'd put in your edit, Nope on ones you wouldn't, and type why on
   a Nope if you can (it teaches me). Click a photo to see it big. Tell me 'done'." Every click is saved
   straight away.
6. **Read what they picked.** `STYLE/images/picks.json` (each mark: slug, id, verdict, reason, file) and
   `images/index.json` ({liked, disliked, recreate}). If they talk instead ("I like the 3rd Pinterest one"), do it
   for them: `images.py pick "STYLE" <slug> like p3 dislike c4:"AI-looking"` (`clear p3` takes a mark back).
   When more than one search is on the page, ask which one in a line. Look at the liked files yourself
   (`images/liked/`) and read the reasons (also in the disliked file names).
7. **Learn the taste, then go again.** What do the likes share (light, subject, mood, colours, how close or
   wide, film grain, candid vs staged)? What do the Nope reasons say? Run 2 to 4 new searches in THEIR words,
   sheet, send. Usually 2 rounds are enough: stop when new likes stop teaching you anything.
8. **Write the Images section of STYLE.md** in their words, with the exact things they said: what a good photo
   looks like for them, what they never want (quote the reasons), the rules above as they stand, where photos
   come from (Pinterest first, Cosmos when a photo goes full screen, because it is sharper). A taste, not a
   shopping list: edits search fresh photos for each video, they don't reuse the same few.
9. **Hand the keepers to the animations.** `images.py use "STYLE"` (all liked) or with names from
   `images/liked/`. They land in `page/assets/photos/` with a `photos.json`, which the style page's photo
   options read.

## The "found again" job (optional, a good sub-agent job)
Their reference reels show real photos on screen. Find look-alikes (never the same file, see copy-exact.md)
and let the person see original and matches side by side. The page shows the sheets in a section "Photos
your favourite creators used, found again". Give one sub-agent per reel (Sonnet is fine, at most 3 at once)
this brief, filled in:

```
You are finding real photos that look like the ones a reference reel shows on screen. Plain English, no em
dashes. Do not spawn other agents. Logged out only: never use cookies or a browser profile.

Reel: [REEL PATH]   Analysis folder: [A] = STYLE/references/analysis/[REEL]/   Style folder: [STYLE]
Tool: python3 -I "[SK]/scripts/images.py" ...   (SK = the skill folder; quote every path)

1. Look at EVERY contact sheet in [A]/sheets/ in order with the Read tool, and read [A]/breakdown.md if it
   exists. List every moment a real photograph is on screen, big or small (a photo of a person, place,
   film still, screenshot of a picture). Skip the speaker's own face, app UI, logos and drawn graphics.
   Note the time of each.
2. For each photo: get the full-size frame, then crop it to the photo only.
   ffmpeg -v error -y -ss T -i "[REEL PATH]" -frames:v 1 "[A]/photos/<name>-full.jpg"
   Crop with Pillow (python3 -I) using the box you measured on the still. Save the crop as
   [A]/photos/<name>.jpg. Open it with Read and check it is just the photo. Short names, lowercase, dashes.
3. Describe it in one line: subject, mood, light, how it was shot ("candid film photo, man asleep at a desk,
   warm lamp"). Write 2 differently worded searches from that line and run
   python3 -I "[SK]/scripts/images.py" search "[STYLE]" "<q1>" "<q2>" --n 6
   then python3 -I "[SK]/scripts/images.py" sheet "[STYLE]" <slug> for each, and Read the sheets.
4. Pick the 3 best matches: same subject and mood, real light, candid. Not stock, not AI-looking, no text or
   watermark, no magazine covers. If fewer than 3 are good, pick fewer and say so.
5. Build the sheet:
   python3 -I "[SK]/scripts/images.py" recreate "[STYLE]" <name> "[A]/photos/<name>.jpg" <slug>:<id> <slug>:<id> <slug>:<id>
   (<slug>:<id> is the search name and the number on the sheet, like late-night-desk:p3). Read the finished
   sheet (STYLE/images/recreate/sheet-<name>.jpg): ORIGINAL on the left, matches on the right, each labelled.
6. Wait about 1.5 seconds between searches. Never download from Instagram.
Reply in under 120 words: one line per photo (name, time in the reel, how good the matches are) and the sheet paths.
```

When they are back, tell the person how many photos were found and send them to `/images.html` (the section
appears once there is a sheet). Matches they like are marked the same way as any candidate, because every match
came from a search: `images.py pick "STYLE" <slug> like p3`.

## If something breaks
- A source says "didn't answer": wait a minute and run the same search again (it only fetches what is missing).
  If Pinterest stays down, Cosmos alone still works (`--only cosmos`).
- Clicks on the page don't save ("Couldn't save"): `server.py start "STYLE"` (replaces a stale server), refresh.
  Their marks are kept in `images/picks.json`.
- Re-running `setup.py --init "STYLE"` refreshes the page and server files and keeps everything in `images/`.
- Nothing is ever deleted: replaced files go to `images/old/`.
