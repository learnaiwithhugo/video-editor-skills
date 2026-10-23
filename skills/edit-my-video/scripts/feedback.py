#!/usr/bin/env python3
"""The feedback loop: every note the user gives on an edit becomes part of their STYLE.md, so the next edit
already knows. Backs up STYLE.md first (to <style>/archive/), never deletes anything.

Usage:
  python3 feedback.py <style_dir or STYLE.md> --video <slug> [--rule "..."]... [--rejected "..."]... [--kept "..."]...

  --rule      something to do from now on, in their words ("captions sit higher on wide shots")
  --rejected  something they didn't like, so it never comes back ("the checklist for 'three things'")
  --kept      something they loved, so it gets used again ("the repo push-in on the star count")

Rules go under "## Feedback from edits" (newest first), rejections join "## Rejected", loved things join
"## Kept (loved in real edits)". Each line is dated and names the video. A tiny log also lands in
<style>/reviews/feedback-log.jsonl.
"""
import json
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path


def add_to_section(md, title, lines, newest_first=True):
    pat = re.compile(rf"^## {re.escape(title)}[^\n]*\n", re.M)
    m = pat.search(md)
    block = "".join(f"{x}\n" for x in lines)
    if not m:
        return md.rstrip() + f"\n\n## {title}\n\n{block}"
    start = m.end()
    nxt = re.search(r"^## ", md[start:], re.M)
    end = start + nxt.start() if nxt else len(md)
    body = md[start:end]
    lines_ = body.split("\n")
    first = next((i for i, l in enumerate(lines_) if l.startswith("- ")), None)
    if newest_first and first is not None:
        pos = start + sum(len(l) + 1 for l in lines_[:first])
        return md[:pos] + block + md[pos:]
    tail = md[start:end].rstrip("\n")
    sep = "\n" if tail.strip() else "\n"
    rest = md[end:]
    return md[:start] + (tail + sep if tail.strip() else "\n") + block + ("\n" + rest if rest else "")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    target = Path(a[0]).expanduser()
    md_path = target if target.suffix == ".md" else target / "STYLE.md"
    if not md_path.exists():
        sys.exit(f"No STYLE.md at {md_path}")
    get = lambda k: [a[i + 1] for i, x in enumerate(a) if x == k]  # noqa: E731
    video = (get("--video") or ["an edit"])[0]
    rules, rejected, kept = get("--rule"), get("--rejected"), get("--kept")
    if not (rules or rejected or kept):
        sys.exit("Nothing to add: pass --rule, --rejected or --kept.")
    for x in rules + rejected + kept:
        if "—" in x:
            sys.exit("No em dashes, please: rewrite the note with a comma or a full stop.")
    style = md_path.parent
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S-%f")[:-3]
    (style / "archive").mkdir(exist_ok=True)
    shutil.copy2(md_path, style / "archive" / f"STYLE-{stamp}.md")
    md = md_path.read_text()
    d = date.today().isoformat()
    if rules:
        md = add_to_section(md, "Feedback from edits", [f"- **{d}, {video}:** {r}" for r in rules])
    if rejected:
        md = add_to_section(md, "Rejected", [f"- {r} (from the {video} edit, {d})" for r in rejected], newest_first=False)
    if kept:
        md = add_to_section(md, "Kept (loved in real edits)", [f"- {k} ({video}, {d})" for k in kept])
    md_path.write_text(md)
    (style / "reviews").mkdir(exist_ok=True)
    with open(style / "reviews" / "feedback-log.jsonl", "a") as f:
        f.write(json.dumps({"at": stamp, "video": video, "rules": rules, "rejected": rejected, "kept": kept}) + "\n")
    print(f"STYLE.md updated ({len(rules)} rule, {len(rejected)} rejected, {len(kept)} kept). Backup: archive/STYLE-{stamp}.md")
    for x in rules:
        print("  rule:     ", x)
    for x in rejected:
        print("  rejected: ", x)
    for x in kept:
        print("  kept:     ", x)


if __name__ == "__main__":
    main()
