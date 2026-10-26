#!/usr/bin/env python3
"""Turn what the person submitted on the artifact page into the files the rest of the skill reads.
Standard library only.

Usage (STYLE = the style folder):
  python3 -I pull_review.py "STYLE" <file.json>

<file.json> holds what you read from the artifact's `submissions` collection (ArtifactData list/get), saved as JSON.
Any of these work: one submission document `{at, by, kind, payload}`, a list of them, or the whole ArtifactData
list result (the documents are found wherever they sit in it; `-` reads standard input, and a folder of
.json files, as written by ArtifactData's out_dir, is read file by file). If several submissions of one kind are
in there, the newest one is used (newest `at`; with no times at all, the first one, because lists come newest first).

What each kind does (the same thing the old local page server did):
  round   -> reviews/round-<round>-<time>.json, copied to reviews/latest.json   (then: make_round.py STYLE next)
  sfx     -> reviews/sfx-<round>-<time>.json, copied to reviews/latest-sfx.json (then: sfx.py apply-review STYLE)
  images  -> every pick is applied like the Like / Nope buttons did, through images.py's pick_image(): the picture
             is copied to images/liked or images/disliked, marked in images/picks.json, listed in images/index.json;
             a copy of the submission is kept as reviews/images-<time>.json
Prints a short plain-English summary.
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # -I does not add this folder by itself

KINDS = ("round", "images", "sfx")


# ---------------------------------------------------------------- finding the submissions in whatever was saved
def to_ts(v):
    """A time as seconds since 1970, from an ISO string or a number of seconds / milliseconds. None when it isn't one."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return v / 1000 if v > 1e11 else float(v)
    if isinstance(v, dict):                                   # {"seconds": ..} / {"_seconds": ..} style stamps
        for k in ("seconds", "_seconds"):
            if isinstance(v.get(k), (int, float)):
                return float(v[k])
        return None
    s = str(v).strip()
    if not s:
        return None
    if re.fullmatch(r"\d{10,13}", s):
        return to_ts(int(s))
    s = re.sub(r"Z$", "+00:00", s)
    s = re.sub(r"(\.\d{1,6})\d*", lambda m: m.group(1).ljust(7, "0"), s)   # fractions python 3.9 can read: exactly 6 digits
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return (d if d.tzinfo else d.astimezone()).timestamp()


class Sub:
    def __init__(self, kind, payload, at=None, by=None, doc_id=None):
        self.kind, self.payload, self.by, self.doc_id = kind, payload, by, doc_id
        self.at = at
        self.ts = to_ts(at) or to_ts(doc_id)


def as_submission(d, doc_id=None):
    """d is a submission document (`{at, by, kind, payload}`), the payload alone, or a wrapper holding one under data/doc/value."""
    if not isinstance(d, dict):
        return None
    doc_id = d.get("doc_id") or d.get("id") or doc_id
    payload = d.get("payload")
    kind = d.get("kind") or (payload.get("kind") if isinstance(payload, dict) else None)
    if kind in KINDS and isinstance(payload, dict):
        return Sub(kind, payload, d.get("at") or payload.get("submitted_at"), d.get("by"), doc_id)
    if kind in KINDS and ("options" in d or "picks" in d):
        return Sub(kind, d, d.get("submitted_at") or d.get("at"), d.get("by"), doc_id)
    for key in ("data", "doc", "document", "value", "fields"):
        if isinstance(d.get(key), dict):
            s = as_submission(d[key], doc_id)
            if s:
                return s
    return None


def find_all(obj, out, doc_id=None):
    if isinstance(obj, list):
        for x in obj:
            find_all(x, out)
    elif isinstance(obj, dict):
        s = as_submission(obj, doc_id)
        if s:
            out.append(s)
            return
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                find_all(v, out, k if isinstance(v, dict) and re.match(r"^[\w:.\-]{6,}$", str(k)) else None)


def newest_per_kind(subs):
    best = {}
    for s in subs:
        cur = best.get(s.kind)
        if cur is None or (s.ts is not None and (cur.ts is None or s.ts > cur.ts)):
            best[s.kind] = s
    return best


def read_input(arg):
    if arg == "-":
        return json.loads(sys.stdin.read())
    p = Path(os.path.expanduser(arg))
    if p.is_dir():
        docs = []
        for f in sorted(p.rglob("*.json")):
            try:
                docs.append({"doc_id": f.stem, "data": json.loads(f.read_text())})
            except ValueError:
                continue
        return docs
    if not p.is_file():
        raise SystemExit(f"I can't find {p}. Save the submissions document from ArtifactData to a .json file and give me that path.")
    try:
        return json.loads(p.read_text())
    except ValueError as e:
        raise SystemExit(f"{p} isn't valid JSON ({e}). Save the document exactly as ArtifactData returned it.")


# ---------------------------------------------------------------- filing each kind
def load(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def stamp(sub):
    t = datetime.fromtimestamp(sub.ts) if sub.ts else datetime.now()
    return t.strftime("%Y-%m-%d-%H%M%S")


def safe(text):
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(text)).strip("-") or "x"


def save_review(style, name, latest, payload):
    folder = style / "reviews"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    (folder / latest).write_text(path.read_text())
    return path


def count_verdicts(opts, names=("keep", "maybe", "drop")):
    c = {n: 0 for n in names}
    c["none"] = 0
    for o in opts:
        v = o.get("verdict")
        c[v if v in names else "none"] += 1
    return c


def file_round(style, sub):
    p = dict(sub.payload)
    p["kind"] = "round"
    p.setdefault("submitted_at", sub.at if isinstance(sub.at, str) else datetime.now().isoformat(timespec="seconds"))
    opts = [dict(o) for o in p.get("options", []) if isinstance(o, dict) and o.get("id")]
    page = load(style / "page" / "round.json", {"sections": []})
    on_page = {o["id"]: (s, o) for s in page.get("sections", []) for o in s.get("options", [])}
    for o in opts:     # make_round.py next prints section and label: fill them in if the page didn't send them
        if o["id"] in on_page:
            sec, opt = on_page[o["id"]]
            o.setdefault("section", sec["name"])
            o.setdefault("use", opt.get("use"))
            o.setdefault("params", opt.get("params", {}))
            o.setdefault("label", opt.get("label") or opt.get("use"))
    p["options"] = opts
    path = save_review(style, f"round-{safe(p.get('round', 'x'))}-{stamp(sub)}.json", "latest.json", p)
    c = count_verdicts(opts)
    notes = sum(1 for o in opts if str(o.get("note") or "").strip())
    lines = [f"ROUND {p.get('round', '?')} review" + (f", sent {sub.at}" if isinstance(sub.at, str) else "") + (f" by {sub.by}" if sub.by else "") + ":",
             f"  kept {c['keep']}, maybe {c['maybe']}, dropped {c['drop']}, not rated {c['none']}.  {notes} note(s) on options.",
             f"  overall note: {str(p.get('overall') or '').strip() or '(none)'}",
             f"  saved reviews/{path.name} and reviews/latest.json"]
    gone = [o["id"] for o in opts if o["id"] not in on_page]
    if gone:
        lines.append(f"  {len(gone)} option(s) in it aren't on the page any more ({', '.join(gone[:6])}): make_round.py next skips them.")
    if str(p.get("round")) != str(page.get("round")) and page.get("sections"):
        lines.append(f"  WARNING: this review is for round {p.get('round')} but the page is on round {page.get('round')}. They may have submitted from an old tab. Ask before acting on it.")
    lines.append('  Next: make_round.py "STYLE" next')
    return lines


def sfx_options(p):
    opts = p.get("options")
    if not isinstance(opts, list):
        picks = p.get("picks") if p.get("picks") is not None else (p.get("sounds") if p.get("sounds") is not None else p.get("marks"))
        if isinstance(picks, dict):
            opts = [{"id": k, "verdict": v.get("verdict") if isinstance(v, dict) else v} for k, v in picks.items()]
        elif isinstance(picks, list):
            opts = [dict(x, id=x.get("id") or x.get("file")) for x in picks if isinstance(x, dict)]
        else:
            opts = []
    out = []
    for o in opts:
        if isinstance(o, dict) and o.get("id"):
            v = o.get("verdict")
            out.append({**o, "verdict": v if v in ("keep", "drop") else None})
    return out


def file_sfx(style, sub):
    p = dict(sub.payload)
    p["kind"] = "sfx"
    p.setdefault("submitted_at", sub.at if isinstance(sub.at, str) else datetime.now().isoformat(timespec="seconds"))
    p["options"] = sfx_options(p)        # sfx.py apply-review reads options: [{id (the sound's file), verdict}]
    path = save_review(style, f"sfx-{safe(p.get('round', 'x'))}-{stamp(sub)}.json", "latest-sfx.json", p)
    c = count_verdicts(p["options"], ("keep", "drop"))
    known = {d.get("file") for d in load(style / "sfx" / "sfx.json", []) if isinstance(d, dict)}
    unknown = [o["id"] for o in p["options"] if o["id"] not in known]
    lines = ["SOUNDS review" + (f", sent {sub.at}" if isinstance(sub.at, str) else "") + ":",
             f"  kept {c['keep']}, dropped {c['drop']}, not marked {c['none']}.",
             f"  saved reviews/{path.name} and reviews/latest-sfx.json"]
    if unknown:
        lines.append(f"  {len(unknown)} sound(s) in it aren't in sfx/sfx.json any more ({', '.join(unknown[:5])}): apply-review skips them.")
    lines.append('  Next: sfx.py apply-review "STYLE"')
    return lines


VERDICT = {"like": "like", "liked": "like", "dislike": "dislike", "disliked": "dislike", "nope": "dislike",
           "": None, "clear": None, "none": None, "null": None}


def file_images(style, sub):
    import images        # scripts/images.py: pick_image() is the one place a Like / Nope is applied
    p = dict(sub.payload)
    p["kind"] = "images"
    picks = [x for x in p.get("picks", []) if isinstance(x, dict)]
    done, skipped = {"like": 0, "dislike": 0, "clear": 0}, []
    for x in picks:
        raw = x.get("verdict")
        key = "" if raw is None else str(raw).strip().lower()
        if key not in VERDICT:
            skipped.append(f"{x.get('slug')}:{x.get('id')} (unknown verdict '{raw}')")
            continue
        verdict = VERDICT[key]
        try:
            images.pick_image(style / "images", x.get("slug"), x.get("id"), verdict, x.get("reason") or "")
            done[verdict or "clear"] += 1
        except images.PickError as e:
            skipped.append(f"{x.get('slug')}:{x.get('id')} ({e})")
    p["applied"] = {"like": done["like"], "dislike": done["dislike"], "clear": done["clear"], "skipped": skipped}
    path = save_review(style, f"images-{stamp(sub)}.json", "latest-images.json", p)
    idx = load(style / "images" / "index.json", {})
    lines = ["IMAGES review" + (f", sent {sub.at}" if isinstance(sub.at, str) else "") + ":",
             f"  {len(picks)} picture(s) marked: liked {done['like']}, nope {done['dislike']}, taken back {done['clear']}"
             + (f", skipped {len(skipped)}" if skipped else "") + ".",
             f"  In total now: {len(idx.get('liked', []))} liked (images/liked/), {len(idx.get('disliked', []))} nope (images/disliked/); marks in images/picks.json.",
             f"  copy of the submission: reviews/{path.name}"]
    for s in skipped[:6]:
        lines.append(f"  skipped: {s}")
    if not picks:
        lines.append("  (it had no picks in it)")
    return lines


def main():
    a = sys.argv[1:]
    if len(a) != 2:
        raise SystemExit(__doc__)
    style = Path(os.path.expanduser(a[0])).resolve()
    if not style.is_dir():
        raise SystemExit(f"I can't find the style folder: {style}")
    subs = []
    find_all(read_input(a[1]), subs)
    best = newest_per_kind(subs)
    if not best:
        raise SystemExit("There is no round, images or sounds submission in that file. Run ArtifactData `list` on `submissions` "
                         "again, and save the result as JSON. (They may not have pressed Submit yet.)")
    handlers = {"round": file_round, "sfx": file_sfx, "images": file_images}
    for kind in KINDS:
        if kind in best:
            extra = sum(1 for s in subs if s.kind == kind) - 1
            print("\n".join(handlers[kind](style, best[kind])) + (f"\n  ({extra} older {kind} submission(s) in the file were ignored)" if extra > 0 else ""))
            print()


if __name__ == "__main__":
    main()
