#!/usr/bin/env python3
"""The storyboard page (and the variations page) the user reviews before anything is rendered.

Usage:
  python3 storyboard.py page   <WORK> [--style <style_dir>] [--page-root <dir>] [--variations]
        WORK/storyboard.json + its frames -> <style>/page/storyboards/<slug>/index.html (frames copied as JPG).
        --variations makes variations.html instead (beats whose alternatives carry a "video").
        --page-root overrides where page/ is (tests use a sandbox so the real style folder isn't touched).
  python3 storyboard.py review <WORK> [--style <style_dir>] [--reviews <dir>] [--variations]
        reads the newest submitted review for this storyboard, writes WORK/storyboard-review.json, folds the picks,
        verdicts and notes into WORK/storyboard.json (approved_pick, verdict, note) and prints what changed.

storyboard.json: see references/storyboard.md. Frame paths in it are relative to WORK (e.g. "frames/b1-A.jpg").
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ENGINE, jdump, jload, style_dir  # noqa: E402


def arg(a, k, d=None):
    return a[a.index(k) + 1] if k in a else d


def page(work, sd, page_root, variations):
    sb = jload(work / "storyboard.json")
    slug = sb.get("slug") or work.name
    tok = jload(work / "style.json") if (work / "style.json").exists() else None
    out = Path(page_root) / "storyboards" / slug
    (out / "frames").mkdir(parents=True, exist_ok=True)
    data = json.loads(json.dumps(sb))
    from PIL import Image

    def ship(rel):
        if not rel:
            return rel
        src = work / rel
        if not src.exists():
            sys.exit(f"Missing frame {src}")
        if src.suffix.lower() in (".mp4", ".webm", ".mov"):
            dst = out / "frames" / src.name
            shutil.copy2(src, dst)
        else:
            dst = out / "frames" / (src.stem + ".jpg")
            im = Image.open(src).convert("RGB")
            if im.width > 1080:
                im = im.resize((1080, round(im.height * 1080 / im.width)))
            im.save(dst, "JPEG", quality=82, optimize=True, progressive=True)
        return "frames/" + dst.name
    for b in data["beats"]:
        b["frame"] = ship(b.get("frame"))
        for alt in b.get("alternatives", []):
            alt["frame"] = ship(alt.get("frame"))
            alt["video"] = ship(alt.get("video"))
    c = (tok or {}).get("colors", {"text": "#10203A", "accent": "#75B4DB", "wash": "#A9C2F2", "deep": "#17408F"})
    fam = (tok or {}).get("font", {}).get("family", "Helvetica Neue")
    faces = ""
    for w, f in sorted(((tok or {}).get("font", {}).get("files") or {}).items()):
        (out / "fonts").mkdir(exist_ok=True)
        shutil.copy2(f, out / "fonts" / Path(f).name)
        faces += f'@font-face{{font-family:"{fam}";src:url("fonts/{Path(f).name}");font-weight:{w}}}'
    rnd = ("variations-" if variations else "storyboard-") + slug
    html = (ENGINE / "storyboard.html").read_text()
    for k, v in {"__TITLE__": sb.get("video", slug) + (" variations" if variations else " storyboard"),
                 "__HEADING__": sb.get("video", slug) + (" · variations" if variations else ""),
                 "__FONTFACES__": faces, "__TEXT__": c["text"], "__ACCENT__": c["accent"], "__WASH__": c["wash"],
                 "__DEEP__": c["deep"], "__FONT__": f'"{fam}"', "__ROUND__": rnd}.items():
        html = html.replace(k, v)
    if variations:
        data["beats"] = [b for b in data["beats"] if any(a.get("video") for a in b.get("alternatives", []))]
    html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    name = "variations.html" if variations else "index.html"
    (out / name).write_text(html)
    size = sum(p.stat().st_size for p in (out / "frames").iterdir()) / 1e6
    print(f"wrote {out / name} ({len(data['beats'])} beats, frames {size:.1f} MB)")
    print(f"open: http://localhost:<port>/storyboards/{slug}/{'' if not variations else 'variations.html'}")


def review(work, reviews_dir, variations):
    sb = jload(work / "storyboard.json")
    slug = sb.get("slug") or work.name
    rnd = ("variations-" if variations else "storyboard-") + slug
    files = sorted(Path(reviews_dir).glob(f"round-{rnd}-*.json"))
    if not files:
        sys.exit(f"No submitted review for {rnd} yet in {reviews_dir}. Ask the user to press Submit, then say done.")
    r = jload(files[-1])
    jdump(r, work / ("variations-review.json" if variations else "storyboard-review.json"))
    by = {o["id"]: o for o in r["options"]}
    changes = []
    for b in sb["beats"]:
        o = by.get(b["id"])
        if not o:
            continue
        if o.get("pick"):
            b["approved_pick"] = o["pick"]
        b["verdict"], b["note"] = o.get("verdict"), o.get("note", "")
        if o.get("verdict") == "change" or o.get("note"):
            changes.append(f"  {b['id']:5} {b['label']}: {o.get('verdict') or 'note'}{' (pick ' + o['pick'] + ')' if o.get('pick') else ''}"
                           f" -> {o.get('note') or '(no note: ask what to change)'}")
    jdump(sb, work / "storyboard.json")
    picks = ", ".join(f"{b['id']}={b['approved_pick']}" for b in sb["beats"] if b.get("approved_pick"))
    done = sum(1 for b in sb["beats"] if b.get("verdict"))
    print(f"Review {files[-1].name}: {done}/{len(sb['beats'])} beats marked. Picks: {picks or 'none'}")
    print("Changes asked for:\n" + ("\n".join(changes) if changes else "  none"))


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    work = Path(a[1]).resolve()
    if a[0] == "page":
        sd = style_dir(arg(a, "--style"))
        page(work, sd, arg(a, "--page-root") or (sd / "page"), "--variations" in a)
    elif a[0] == "review":
        rd = arg(a, "--reviews") or (style_dir(arg(a, "--style")) / "reviews")
        review(work, rd, "--variations" in a)
    else:
        sys.exit(__doc__)
