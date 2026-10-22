#!/usr/bin/env python3
"""Keep plan.json and the scenes pointing at the right words after the cut changes.

Usage:
  PY scripts/reindex.py <work_dir> <old_words.json>

Everything downstream refers to spoken words by index (plan.json "w:35", scenes `at(35)`).
Re-cutting re-transcribes, and if Whisper hears one word more or less, every later index
shifts and graphics land on the wrong words. assemble.py saves the previous words as
.prev/words.json; this script lines the old and new word lists up (by text), and rewrites:
  plan.json   "w:N" refs, captions.fix keys, captions.emphasis, captions.keep_together
  scenes/*    at(N) and KW.word(B, N)
A word that disappeared maps to the next surviving word. It prints every change it made.
"""
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path


def norm(w):
    return re.sub(r"[^a-z0-9.]", "", w.lower())


def main():
    work = Path(sys.argv[1]).resolve()
    old = json.loads(Path(sys.argv[2]).read_text())
    new = json.loads((work / "words.json").read_text())
    a, b = [norm(w["w"]) for w in old], [norm(w["w"]) for w in new]
    m = {}
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        for k in range(i1, i2):
            if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
                m[k] = j1 + (k - i1)
            else:  # deleted (or uneven replace): point at the next surviving word
                m[k] = min(j2, len(b) - 1)
    changed = {k: v for k, v in m.items() if k != v}
    if not changed:
        print("Word indices unchanged; nothing to do.")
        return
    print(f"{len(changed)} word indices moved (e.g. " +
          ", ".join(f"{k}->{v}" for k, v in list(changed.items())[:6]) + ")")

    plan_p = work / "plan.json"
    plan = json.loads(plan_p.read_text())
    txt = json.dumps(plan)
    txt = re.sub(r'"w:(\d+)', lambda mm: f'"w:{m.get(int(mm.group(1)), int(mm.group(1)))}', txt)
    plan = json.loads(txt)
    cap = plan.get("captions", {})
    if "fix" in cap:
        cap["fix"] = {str(m.get(int(k), int(k))): v for k, v in cap["fix"].items()}
    if "emphasis" in cap:
        cap["emphasis"] = [m.get(i, i) for i in cap["emphasis"]]
    if "keep_together" in cap:
        cap["keep_together"] = [[m.get(x, x) for x in pair] for pair in cap["keep_together"]]
    plan_p.write_text(json.dumps(plan, indent=1))
    print("  plan.json updated")

    for f in sorted((work / "scenes").glob("*.html")):
        s = f.read_text()
        s2 = re.sub(r"\bat\((\d+)\)", lambda mm: f"at({m.get(int(mm.group(1)), int(mm.group(1)))})", s)
        s2 = re.sub(r"KW\.word\(B,\s*(\d+)\)",
                    lambda mm: f"KW.word(B, {m.get(int(mm.group(1)), int(mm.group(1)))})", s2)
        if s2 != s:
            f.write_text(s2)
            print(f"  {f.name} updated")


if __name__ == "__main__":
    main()
