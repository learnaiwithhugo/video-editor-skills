#!/usr/bin/env python3
"""The Images round: find real photos the person might love, look at them, keep or drop them, and hand
the keepers to the animations. Searching, sheets, use and recreate need the free Python packages "requests" and "Pillow" (pick and index don't).

Usage (always python3 -I, quote every path):
  python3 -I images.py search "<style folder>" "<query>" ["<query>" ...] [--n 8] [--only pinterest|cosmos]
      Top N from Pinterest and from Cosmos for each query, saved in <style>/images/candidates/<query-slug>/
      as p01.jpg.. and c01.jpg.., plus meta.json and the page list candidates/index.json.
      Running the same query again only adds what is missing; numbers never change.
  python3 -I images.py sheet "<style folder>" [<slug>]
      One labelled sheet per query (candidates/<slug>/sheet.jpg): rows PINTEREST and COSMOS, every picture
      with its number (p3, c2) burned in. Without a slug, all of them. This is how Claude looks at them.
  python3 -I images.py pick "<style folder>" <slug> like p1 c2 dislike p3:"too stock" c4:"AI-looking"
      Likes are copied to images/liked/<slug>-<id>.jpg, dislikes to images/disliked/<slug>-<id>-<reason>.jpg.
      Everything is recorded in images/picks.json. "clear p1" takes a mark back.
  python3 -I images.py use "<style folder>" [<liked file name> ...]
      Copies liked photos (all of them if none named) into <style>/page/assets/photos/ and writes photos.json
      there, so animations can use them.
  python3 -I images.py index "<style folder>"
      Rebuilds images/index.json ({liked, disliked, recreate}) and candidates/index.json from the folders.
  python3 -I images.py recreate "<style folder>" <name> <original image> <match> [<match> ...]
      A labelled sheet for the "found again" job: ORIGINAL on the left, matches on the right, saved as
      images/recreate/sheet-<name>.jpg. A match is a picture file or <slug>:<id> (like pins:p3).

Logged out only. No cookies, no browser profile, no keys. Pinterest is an unofficial route: fine for photos
inside their own edits, not for passing the pictures on. Nothing is ever deleted; replaced files go to
images/old/. About 1.5 s between searches so the sites are not hammered.
"""
import argparse
import io
import json
import re
import shutil
import sys
import threading
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

# requests and Pillow are only needed to search, make sheets and show photos. Recording a Like / Nope
# (pick_image below) is plain standard library, so serve.py and pull_review.py can import this file without them.
try:
    import requests
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    HAVE_PACKAGES = True
except ImportError:
    requests = Image = ImageDraw = ImageFont = ImageOps = None
    HAVE_PACKAGES = False


def need_packages():
    if not HAVE_PACKAGES:
        raise SystemExit("This needs two free Python packages: requests and Pillow. Ask Claude to install them "
                         "(pip3 install requests pillow), then run it again.")


UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
MIN_LONG = 700      # shortest allowed "long side" in pixels
MAX_LONG = 2400     # bigger pictures are shrunk to this when saved (the edit is 1080 wide)
SEARCH_PAUSE = 1.5  # seconds between requests to the search pages
IMAGE_PAUSE = 0.6   # seconds between picture downloads (those come from image servers)
SOURCES = ("pinterest", "cosmos")
LETTER = {"pinterest": "p", "cosmos": "c"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


# ---------------------------------------------------------------- small helpers
def slugify(text, limit=60):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:limit].strip("-")


def stamp():
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False))


def images_dir(arg):
    style = Path(arg).expanduser().resolve()
    if not style.is_dir():
        raise SystemExit(f"I can't find the style folder: {style}")
    d = style / "images"
    d.mkdir(exist_ok=True)
    return d


def archive(path, images):
    """Move a file we are about to replace into images/old/ (nothing is ever deleted)."""
    path = Path(path)
    old = images / "old"
    old.mkdir(exist_ok=True)
    dest = old / f"{path.stem}-{stamp()}{path.suffix}"
    n = 1
    while dest.exists():
        n += 1
        dest = old / f"{path.stem}-{stamp()}-{n}{path.suffix}"
    shutil.move(str(path), str(dest))


def norm_id(text):
    m = re.fullmatch(r"([pc])0*(\d{1,3})", str(text).strip().lower())
    if not m:
        raise SystemExit(f"'{text}' isn't a picture number. Use the numbers on the sheet, like p3 or c2.")
    return f"{m.group(1)}{int(m.group(2))}"


def cand_path(images, slug, cid):
    letter, num = cid[0], int(cid[1:])
    return images / "candidates" / slug / f"{letter}{num:02d}.jpg"


# ---------------------------------------------------------------- the two logged-out searches
def pinterest(query):
    data = {"options": {"query": query, "scope": "pins", "page_size": 25}, "context": {}}
    src = "/search/pins/?q=" + urllib.parse.quote(query)
    params = {"source_url": src, "data": json.dumps(data, separators=(",", ":"))}
    h = {
        "User-Agent": UA,
        "X-Pinterest-PWS-Handler": "www/search/[scope].js",
        "Accept": "application/json, text/javascript, */*, q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "X-APP-VERSION": "0",
    }
    r = requests.get("https://www.pinterest.com/resource/BaseSearchResource/get/", params=params, headers=h, timeout=30)
    if r.status_code == 429:           # asked to slow down: wait once and try again
        time.sleep(6)
        r = requests.get("https://www.pinterest.com/resource/BaseSearchResource/get/", params=params, headers=h, timeout=30)
    r.raise_for_status()
    out = []
    for p in r.json()["resource_response"]["data"]["results"]:
        if p.get("type") != "pin" or p.get("is_promoted") or p.get("promoter"):
            continue
        sp = p.get("story_pin_data") or {}
        if p.get("videos") or (sp.get("total_video_duration") or 0) > 0:
            continue
        im = p.get("images") or {}
        small = (im.get("736x") or {}).get("url")
        if not small:
            continue
        o = im.get("orig") or {}
        out.append({
            "key": "pin:%s" % p.get("id"),
            "urls": [u for u in (o.get("url"), small) if u],     # the full-size file first, the 736 wide one as backup
            "page": "https://www.pinterest.com/pin/%s/" % p.get("id"),
            "w": o.get("width"), "h": o.get("height"),
            "caption": (p.get("grid_title") or p.get("title") or p.get("description") or "").strip()[:120],
        })
    return out


def cosmos(query):
    url = "https://www.cosmos.so/search/elements/" + urllib.parse.quote(query)
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    page = r.text
    out, seen = [], set()
    # each element tile carries a media object right after its id; pull them in order
    pattern = (r'"media":\{"__typename":"StaticImage","mediaId":"[^"]+","url":"(https://cdn\.cosmos\.so/[0-9a-f\-]{36})",'
               r'"width":(\d+),"height":(\d+),"notSafeForWorkStatus":"(\w+)","aiGenerated":(true|false)')
    for m in re.finditer(pattern, page):
        u, w, h, nsfw, ai = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
        if u in seen:
            continue
        seen.add(u)
        if nsfw != "SAFE" or ai == "true":
            continue
        before = page[max(0, m.start() - 4000):m.start()]
        share = re.findall(r'"shareUrl":"(https://www\.cosmos\.so/e/\d+)"', before)
        cap = re.findall(r'"generatedCaption":\{"__typename":"ElementCaption","text":"(.*?)"\}', before)
        out.append({
            "key": "cosmos:" + u.rsplit("/", 1)[-1],
            "urls": [u],
            "page": share[-1] if share else url,
            "w": w, "h": h,
            "caption": re.sub(r"\\u003c/?n\\u003e", "", cap[-1]).strip()[:120] if cap else "",
        })
    return out


FINDERS = {"pinterest": pinterest, "cosmos": cosmos}


def get_image(urls):
    """First link that gives a real, still picture. Returns (PIL image, raw bytes, the link used)."""
    last = "no link"
    for u in urls:
        try:
            r = requests.get(u, headers={"User-Agent": UA}, timeout=30)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content))
            im.load()
            if getattr(im, "is_animated", False):
                last = "moving picture"
                continue
            return im, r.content, u
        except Exception as e:
            last = str(e)[:80]
    raise ValueError(last)


def save_jpeg(im, raw, dest):
    """Plain JPEG on disk. The original bytes when they are already a normal JPEG, else a clean re-save."""
    if im.format == "JPEG" and max(im.size) <= MAX_LONG and im.getexif().get(274, 1) == 1:
        Path(dest).write_bytes(raw)
        return im.size
    im = ImageOps.exif_transpose(im).convert("RGB")
    if max(im.size) > MAX_LONG:
        im.thumbnail((MAX_LONG, MAX_LONG), Image.LANCZOS)
    im.save(dest, "JPEG", quality=92)
    return im.size


# ---------------------------------------------------------------- search
def rebuild_candidates_index(images):
    groups = []
    for meta_f in sorted((images / "candidates").glob("*/meta.json")):
        m = read_json(meta_f, None)
        if not m or not m.get("files"):
            continue
        groups.append({"slug": m["slug"], "query": m["query"], "created": m.get("created", ""),
                       "items": [{**f, "slug": m["slug"], "query": m["query"]} for f in m["files"]]})
    groups.sort(key=lambda g: g["created"])
    write_json(images / "candidates" / "index.json", {"queries": groups})
    return sum(len(g["items"]) for g in groups)


def search_one(images, query, n, only):
    slug = slugify(query) or "images"
    folder = images / "candidates" / slug
    folder.mkdir(parents=True, exist_ok=True)
    meta = read_json(folder / "meta.json", {"query": query, "slug": slug, "created": datetime.now().isoformat(timespec="seconds"),
                                              "files": [], "skipped": []})
    have = {f["key"] for f in meta["files"]}
    counts = {}
    for source in SOURCES:
        if only and source != only:
            continue
        mine = [f for f in meta["files"] if f["source"] == source]
        need = n - len(mine)
        counts[source] = len(mine)
        if need <= 0:
            continue
        try:
            found = FINDERS[source](query)
        except Exception as e:
            print(f"  {source.title()} didn't answer ({str(e)[:70]}). Try again in a minute.")
            time.sleep(SEARCH_PAUSE)
            continue
        time.sleep(SEARCH_PAUSE)
        number = max([int(f["id"][1:]) for f in mine] or [0])
        for c in found:
            if need <= 0:
                break
            if c["key"] in have:
                continue
            if c["w"] and c["h"] and max(c["w"], c["h"]) < MIN_LONG:
                continue
            try:
                im, raw, used = get_image(c["urls"])
            except ValueError as e:
                meta["skipped"].append({"source": source, "key": c["key"], "why": str(e)})
                continue
            finally:
                time.sleep(IMAGE_PAUSE)
            if max(im.size) < MIN_LONG:
                meta["skipped"].append({"source": source, "key": c["key"], "why": f"too small {im.size[0]}x{im.size[1]}"})
                continue
            number += 1
            cid = f"{LETTER[source]}{number}"
            dest = folder / f"{LETTER[source]}{number:02d}.jpg"
            w, h = save_jpeg(im, raw, dest)
            meta["files"].append({"id": cid, "source": source, "file": f"candidates/{slug}/{dest.name}", "page": c["page"],
                                  "url": used, "w": w, "h": h, "caption": c["caption"], "query": query, "key": c["key"]})
            have.add(c["key"])
            need -= 1
            counts[source] += 1
    meta["skipped"] = meta["skipped"][-40:]
    write_json(folder / "meta.json", meta)
    return slug, counts


def cmd_search(a):
    need_packages()
    images = images_dir(a.style)
    for q in a.queries:
        slug, counts = search_one(images, q, a.n, a.only)
        parts = ", ".join(f"{counts[s]} from {s.title()}" for s in counts)
        print(f"{q}: {parts}  (name: {slug})")
        time.sleep(SEARCH_PAUSE)
    total = rebuild_candidates_index(images)
    print(f"{total} pictures in images/candidates/. Next: images.py sheet to look at them.")


# ---------------------------------------------------------------- sheets
FONT_FILES = [("/System/Library/Fonts/Helvetica.ttc", 1), ("/System/Library/Fonts/HelveticaNeue.ttc", 1),
              ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0)]


def font(size):
    for path, idx in FONT_FILES:
        try:
            return ImageFont.truetype(path, size, index=idx)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def text_size(draw, text, f):
    l, t, r, b = draw.textbbox((0, 0), text, font=f)
    return r - l, b - t, l, t


def badge(draw, x, y, text, size=44, fill=(0, 0, 0), ink=(255, 255, 255), pad=9):
    f = font(size)
    w, h, ox, oy = text_size(draw, text, f)
    draw.rectangle([x, y, x + w + pad * 2, y + h + pad * 2], fill=fill)
    draw.text((x + pad - ox, y + pad - oy), text, font=f, fill=ink)


def thumb_cell(path, cw, ch):
    cell = Image.new("RGB", (cw, ch), (236, 236, 236))
    try:
        im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        im = ImageOps.contain(im, (cw, ch), Image.LANCZOS)
        cell.paste(im, ((cw - im.width) // 2, (ch - im.height) // 2))
    except Exception:
        pass
    return cell


def make_sheet(images, slug):
    folder = images / "candidates" / slug
    meta = read_json(folder / "meta.json", None)
    if not meta:
        raise SystemExit(f"No pictures found for '{slug}'. Run search first.")
    CW, CH, GAP, PAD, COLS = 270, 340, 12, 22, 4
    width = PAD * 2 + COLS * CW + (COLS - 1) * GAP
    blocks = []
    for source in SOURCES:
        items = [f for f in meta["files"] if f["source"] == source]
        blocks.append((source, items, max(1, -(-len(items) // COLS))))
    title_h, banner_h = 96, 56
    height = PAD + title_h + sum(banner_h + rows * (CH + GAP) + 10 for _, _, rows in blocks) + PAD - GAP
    sheet = Image.new("RGB", (width, height), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, PAD - 4), meta["query"], font=font(40), fill=(20, 20, 20))
    d.text((PAD, PAD + 52), f"name: {slug}", font=font(20), fill=(120, 120, 120))
    y = PAD + title_h
    for source, items, rows in blocks:
        d.rectangle([PAD, y, width - PAD, y + banner_h - 12], fill=(20, 20, 20))
        d.text((PAD + 14, y + 6), f"{source.upper()}   {len(items) or 'none found'}", font=font(26), fill=(255, 255, 255))
        y += banner_h
        for i, f in enumerate(items):
            col, row = i % COLS, i // COLS
            x0, y0 = PAD + col * (CW + GAP), y + row * (CH + GAP)
            sheet.paste(thumb_cell(folder / Path(f["file"]).name, CW, CH), (x0, y0))
            badge(d, x0, y0, f["id"])
        y += rows * (CH + GAP) + 10
    out = folder / "sheet.jpg"
    if out.exists():
        archive(out, images)
    sheet.save(out, "JPEG", quality=88)
    return out


def cmd_sheet(a):
    need_packages()
    images = images_dir(a.style)
    if a.slug:
        slugs = [slugify(a.slug)]
    else:
        slugs = [g["slug"] for g in read_json(images / "candidates" / "index.json", {"queries": []})["queries"]]
    if not slugs:
        raise SystemExit("Nothing to show yet. Run search first.")
    for s in slugs:
        print(make_sheet(images, s))


# ---------------------------------------------------------------- picks (pick_image is shared with engine/serve.py and pull_review.py)
def rebuild_index(images):
    """images/index.json = {liked, disliked, recreate}, rebuilt from the folders. Marks come from picks.json."""
    picks = {p["file"]: p for p in read_json(images / "picks.json", {"picks": []}).get("picks", [])}
    out = {"liked": [], "disliked": [], "recreate": []}
    for kind, folder in (("liked", "liked"), ("disliked", "disliked")):
        for f in sorted((images / folder).glob("*")) if (images / folder).is_dir() else []:
            if f.suffix.lower() not in IMG_EXT:
                continue
            rel = f"{folder}/{f.name}"
            p = picks.get(rel)
            m = re.fullmatch(r"(.+)-([pc]\d+)(?:-(.+))?", f.stem)
            item = {"file": rel,
                    "slug": p["slug"] if p else (m.group(1) if m else None),
                    "id": p["id"] if p else (m.group(2) if m else None)}
            if p:
                reason = p.get("reason", "")
            else:
                reason = (m.group(3) or "").replace("-", " ") if m else ""
            if kind == "disliked" or reason:
                item["reason"] = reason
            out[kind].append(item)
    rec = images / "recreate"
    for f in sorted(rec.glob("sheet-*.jpg")) if rec.is_dir() else []:
        out["recreate"].append({"name": f.stem[len("sheet-"):].replace("-", " "), "file": f"recreate/{f.name}"})
    write_json(images / "index.json", out)
    return out


class PickError(Exception):
    """A Like / Nope that can't be applied. .code is the HTTP-style status (400 bad request, 404 no such picture)."""

    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


PICK_LOCK = threading.Lock()


def pick_image(images, slug, cid, verdict, reason=""):
    """The ONE place a Like / Nope / clear is applied. The page's old buttons (engine/serve.py), a submitted review
    (pull_review.py) and `images.py pick` all call this, so they can't drift apart.
    images = the style folder's images/ folder. verdict: 'like', 'dislike' or None (take the mark back).
    Files go to images/liked or images/disliked, the mark to images/picks.json, the lists to images/index.json.
    Returns {"saved": True, "verdict", "liked": n, "disliked": n}. Raises PickError."""
    images = Path(images)
    slug = str(slug or "")
    m = re.fullmatch(r"([pc])0*(\d{1,3})", str(cid or "").strip().lower())
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug) or not m or verdict not in ("like", "dislike", None):
        raise PickError("bad request", 400)
    cid = f"{m.group(1)}{int(m.group(2))}"
    src = cand_path(images, slug, cid)
    if not src.is_file():
        raise PickError(f"no picture {cid} in {slug}", 404)
    reason = str(reason or "").strip()[:200]
    with PICK_LOCK:
        data = read_json(images / "picks.json", {"picks": []})
        mine = [p for p in data["picks"] if p["slug"] == slug and p["id"] == cid]
        for p in mine:
            old = images / p.get("file", "")
            if p.get("file") and old.is_file():
                archive(old, images)
        data["picks"] = [p for p in data["picks"] if p not in mine]
        if verdict:
            folder = "liked" if verdict == "like" else "disliked"
            rs = slugify(reason, 40) if verdict == "dislike" else ""
            name = f"{slug}-{cid}" + (f"-{rs}" if rs else "") + ".jpg"
            dest = images / folder / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                archive(dest, images)
            shutil.copy2(src, dest)
            data["picks"].append({"slug": slug, "id": cid, "verdict": verdict, "reason": reason,
                                  "file": f"{folder}/{name}", "at": datetime.now().isoformat(timespec="seconds")})
        write_json(images / "picks.json", data)
        idx = rebuild_index(images)
    return {"saved": True, "verdict": verdict, "liked": len(idx["liked"]), "disliked": len(idx["disliked"])}


def apply_pick(images, slug, cid, verdict, reason=""):
    """Command-line wrapper around pick_image: plain-English errors. verdict: 'like', 'dislike' or None."""
    cid = norm_id(cid)
    try:
        pick_image(images, slug, cid, verdict, reason)
    except PickError as e:
        if e.code == 404:
            raise SystemExit(f"There is no {cid} in '{slug}'. Check the number on the sheet.")
        raise SystemExit(f"Can't record that pick ({e}).")
    return verdict or "clear"


def cmd_pick(a):
    images = images_dir(a.style)
    slug = slugify(a.slug)
    if not (images / "candidates" / slug).is_dir():
        raise SystemExit(f"I don't have a search called '{slug}'. Look in images/candidates/ for the names.")
    mode, done = None, {"like": [], "dislike": [], "clear": []}
    for tok in a.marks:
        t = tok.strip()
        if t.lower() in ("like", "dislike", "clear"):
            mode = t.lower()
            continue
        if mode is None:
            raise SystemExit("Say like, dislike or clear first, e.g.  pick STYLE " + slug + " like p1 c2 dislike p3:\"too stock\"")
        cid, _, reason = t.partition(":")
        apply_pick(images, slug, cid, None if mode == "clear" else mode, reason)
        done[mode].append(norm_id(cid))
    idx = read_json(images / "index.json", {})
    bits = [f"{label} {', '.join(ids)}" for label, ids in (("Liked", done["like"]), ("Nope", done["dislike"]), ("Cleared", done["clear"])) if ids]
    print("; ".join(bits) + f".  In total: {len(idx.get('liked', []))} liked, {len(idx.get('disliked', []))} nope (images/picks.json).")


# ---------------------------------------------------------------- use, index, recreate
def cmd_use(a):
    need_packages()
    images = images_dir(a.style)
    liked = images / "liked"
    names = [Path(n).name for n in a.names]
    if not names and liked.is_dir():
        names = sorted(f.name for f in liked.glob("*") if f.suffix.lower() in IMG_EXT)
    if not names:
        raise SystemExit("No liked photos yet. Rate some first.")
    for n in names:
        if not (liked / n).is_file():
            raise SystemExit(f"'{n}' isn't in images/liked/.")
    photos = images.parent / "page" / "assets" / "photos"
    photos.mkdir(parents=True, exist_ok=True)
    for n in names:
        src = liked / n
        dest = photos / n
        if dest.exists() and dest.read_bytes() != src.read_bytes():
            archive_to = photos / "old"
            archive_to.mkdir(exist_ok=True)
            shutil.move(str(dest), str(archive_to / f"{dest.stem}-{stamp()}{dest.suffix}"))
        if not dest.exists():
            shutil.copy2(src, dest)
    index = {i["file"]: i for i in read_json(images / "index.json", {}).get("liked", [])}
    listing = []
    for f in sorted(photos.glob("*")):
        if f.suffix.lower() not in IMG_EXT:
            continue
        try:
            with Image.open(f) as im:
                w, h = im.size
        except Exception:
            continue
        src = index.get(f"liked/{f.name}", {})
        listing.append({"name": f.name, "file": f"assets/photos/{f.name}", "w": w, "h": h, "slug": src.get("slug"), "id": src.get("id")})
    write_json(photos / "photos.json", listing)
    print(f"{len(names)} photo(s) ready for the animations in page/assets/photos/ ({len(listing)} there in total).")


def cmd_index(a):
    images = images_dir(a.style)
    idx = rebuild_index(images)
    total = rebuild_candidates_index(images)
    print(f"images/index.json: {len(idx['liked'])} liked, {len(idx['disliked'])} nope, {len(idx['recreate'])} found-again sheets. "
          f"{total} candidates listed.")


def resolve_match(images, token):
    """A match is a picture file or <name>:<number>. Returns (file, big label, small label)."""
    p = Path(token).expanduser()
    if p.is_file():
        return p, p.stem[:14], ""
    if ":" in token:
        slug, cid = token.rsplit(":", 1)
        cid = norm_id(cid)
        f = cand_path(images, slugify(slug), cid)
        if f.is_file():
            return f, cid, slugify(slug)
    raise SystemExit(f"I can't find the match '{token}'. Give a picture file, or <name>:<number> like pins:p3.")


def cmd_recreate(a):
    need_packages()
    images = images_dir(a.style)
    name = slugify(a.name, 40) or "photo"
    original = Path(a.original).expanduser()
    if not original.is_file():
        raise SystemExit(f"I can't find the original: {original}")
    matches = [resolve_match(images, m) for m in a.matches]
    H, CW, GAP, PAD = 640, 400, 14, 22
    orig = ImageOps.contain(ImageOps.exif_transpose(Image.open(original)).convert("RGB"), (CW + 120, H), Image.LANCZOS)
    width = PAD * 2 + orig.width + GAP * 2 + len(matches) * (CW + GAP) - GAP
    sheet = Image.new("RGB", (width, PAD * 2 + 64 + H), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, PAD - 4), name.replace("-", " "), font=font(34), fill=(20, 20, 20))
    top, x = PAD + 64, PAD
    sheet.paste(orig, (x, top))
    badge(d, x, top, "ORIGINAL", 30, fill=(200, 50, 30))
    x += orig.width + GAP * 2
    for path, big, small in matches:
        sheet.paste(thumb_cell(path, CW, H), (x, top))
        badge(d, x, top, big, 40)
        if small:
            badge(d, x, top + H - 34, small[:30], 18, fill=(255, 255, 255), ink=(60, 60, 60), pad=6)
        x += CW + GAP
    rec = images / "recreate"
    (rec / "originals").mkdir(parents=True, exist_ok=True)
    keep = rec / "originals" / f"{name}{original.suffix.lower() or '.jpg'}"
    if original.resolve() != keep.resolve():
        if keep.exists():
            archive(keep, images)
        shutil.copy2(original, keep)
    out = rec / f"sheet-{name}.jpg"
    if out.exists():
        archive(out, images)
    sheet.save(out, "JPEG", quality=88)
    rebuild_index(images)
    print(out)


# ---------------------------------------------------------------- command line
def main():
    ap = argparse.ArgumentParser(prog="images.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("style")
    s.add_argument("queries", nargs="+")
    s.add_argument("--n", type=int, default=8)
    s.add_argument("--only", choices=SOURCES)
    s.set_defaults(fn=cmd_search)
    s = sub.add_parser("sheet")
    s.add_argument("style")
    s.add_argument("slug", nargs="?")
    s.set_defaults(fn=cmd_sheet)
    s = sub.add_parser("pick")
    s.add_argument("style")
    s.add_argument("slug")
    s.add_argument("marks", nargs="+")
    s.set_defaults(fn=cmd_pick)
    s = sub.add_parser("use")
    s.add_argument("style")
    s.add_argument("names", nargs="*")
    s.set_defaults(fn=cmd_use)
    s = sub.add_parser("index")
    s.add_argument("style")
    s.set_defaults(fn=cmd_index)
    s = sub.add_parser("recreate")
    s.add_argument("style")
    s.add_argument("name")
    s.add_argument("original")
    s.add_argument("matches", nargs="+")
    s.set_defaults(fn=cmd_recreate)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
