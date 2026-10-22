#!/usr/bin/env python3
"""Clone the proven editing engine into a new style skill, with a starting style pack.

Usage:
  python3 -I scripts/make_style_skill.py <style-name> <style_dir> [--title "Display Name"]
                                         [--engine <name or path>] [--dest <skills folder>]

  <style-name>  short kebab-case, e.g. "kallaway". The skill becomes ROOT/.claude/skills/<style-name>-edit/,
                a project skill in the USER's video folder (ROOT = projectRoot from the setup wizard), so it
                is never inside the plugin folder that updates replace. Run it as /<style-name>-edit with
                Claude Code opened in that folder.
  <style_dir>   ROOT/references/<style-name>/ (holds <style>-style-guide.md, style-spec.json, key frames)
  --engine      the engine skill (default: kallaway-edit next to this skill, i.e. the plugin's own copy)
  --dest        another skills folder instead of ROOT/.claude/skills (dry runs)

Copies the ENGINE (setup wizard, transcribe, takes, cut, cut-out, music, sound effects, build, render,
QA, audio map, the HyperFrames template, fonts) and the style-match tools (scripts/match/). The copy
shares the editor's DATA folder (settings, Python, sound effects) through data-dir.txt, so it needs no
second install. Writes a STARTING style pack from the measured spec (style.json numbers, the spec, the style guide, a lock log)
and prints the checklist of style files the lead must now rewrite from the style guide. Never touches
the engine skill it copies from, and refuses to overwrite an existing style skill.
"""
import json
import re
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # never write into the skill folder: a plugin update replaces it
sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402

ENGINE_SKIP = {".venv", ".sfx", "config.json", "data-dir.txt", "__pycache__", ".DS_Store", "style.json",
               "style-rules.md", "graphics-recipes.md", "style-spec.json", "lock-log.md"}
PROJECT_SKILL_EDITS = [  # the copy lives in the user's project, not in the plugin: it can keep its own lock log
    ("(never write into it: an update replaces it)", "(the style pack lives here)"),
    ("(`SK/references/lock-log.md` holds\nthe style's measured history; leave it as it is)",
     "(also log the score in\n`SK/references/lock-log.md`)"),
]
REWRITE = [
    ("SKILL.md", "the description line and every style-specific rule (colours, caption look, layouts, "
                 "titles, what goes where). Keep the workflow, setup wizard and safety rules as they are."),
    ("references/style-rules.md", "the look as build rules with exact numbers, from the style guide."),
    ("references/graphics-recipes.md", "how a spoken idea becomes this style's on-screen graphic, with examples."),
    ("references/sound-map.md", "which sound goes on which animation, and the levels (from the ear check)."),
    ("references/filming-guide.md", "how to film for this style (framing, light, camera)."),
    ("template/kit/kw.css + kw.js", "this style's fonts, colours and components (the class names can stay)."),
    ("style.json", "check the starting numbers against the style guide (layout geometry, caption size)."),
    ("scripts/build.py layouts()", "ONLY if this style uses layouts other than 'stage + card' and 'full face'."),
    ("template/examples/", "replace with this style's own scenes after the first edit."),
]


def style_numbers(spec):
    """Starting style.json from the measured spec (medians of the reference reels)."""
    med = lambda k: sorted(spec["ranges"][k]["refs"])[len(spec["ranges"][k]["refs"]) // 2]  # noqa: E731
    out = {}
    r = spec["ranges"]
    if "card_top_pct" in r and "card_x0_pct" in r:
        x0 = round(med("card_x0_pct") / 100 * 1080)
        out["card"] = {"x0": x0, "x1": 1080 - x0, "top": round(med("card_top_pct") / 100 * 1920), "r": 40}
    if "cap_y_stage_pct" in r:
        out["caption_y_stage"] = round(med("cap_y_stage_pct") / 100 * 1920)
    if "cap_y_full_pct" in r:
        y = round(med("cap_y_full_pct") / 100 * 1920)
        out["caption_y_full_min"], out["caption_y_full_max"] = y, y + 160
    if "cap_h_pct" in r:  # text ink height -> font size (heavy grotesk: ~1.38x the ink height of mixed words)
        out["caption_px"] = round(med("cap_h_pct") / 100 * 1920 * 1.38)
        out["caption_em_px"] = round(out["caption_px"] * 1.14)
    return out


def main():
    a = sys.argv[1:]
    title = a[a.index("--title") + 1] if "--title" in a else None
    eng_name = a[a.index("--engine") + 1] if "--engine" in a else None
    name, sdir = a[0].strip().lower(), Path(a[1])
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise SystemExit("Style name must be short kebab-case, like 'kallaway' or 'clean-minimal'.")
    title = title or name.replace("-", " ").title()
    eng = engine.engine_dir(eng_name)
    st = engine.state(eng)
    skills = (Path(a[a.index("--dest") + 1]).expanduser() if "--dest" in a
              else engine.project_root(eng) / ".claude" / "skills")
    dst = skills / f"{name}-edit"
    print(f"Engine: {eng}\nShared data folder: {st.DATA}\n")
    if dst.exists():
        raise SystemExit(f"{dst} already exists. Pick another name, or move the old one to archive/ first.")
    guide = next(sdir.glob("*style-guide.md"), None)
    spec_p = sdir / "style-spec.json"
    if not guide or not spec_p.exists():
        raise SystemExit(f"Need {sdir}/<name>-style-guide.md and style-spec.json first (steps 3-5).")

    skills.mkdir(parents=True, exist_ok=True)
    shutil.copytree(eng, dst, ignore=lambda d, names: [n for n in names if n in ENGINE_SKIP])
    (dst / "data-dir.txt").write_text(str(st.DATA) + "\n")  # share the editor's settings, Python, sounds
    match = dst / "scripts" / "match"
    match.mkdir(exist_ok=True)
    for f in ("engine.py", "prep.py", "fingerprint.py", "font_match.py", "golden.py"):
        shutil.copy2(engine.HERE / "scripts" / f, match / f)
    spec = json.loads(spec_p.read_text())
    sj = {"_about": f"The {title} style's numbers, measured from the reference reels. build.py reads this; "
                    "change the look here, never in the scripts."}
    sj.update(style_numbers(spec))
    (dst / "style.json").write_text(json.dumps(sj, indent=1))
    refs = dst / "references"
    shutil.copy2(spec_p, refs / "style-spec.json")
    shutil.copy2(guide, refs / "style-guide.md")
    kf = next(sdir.glob("*key-frames.png"), None)
    if kf:
        shutil.copy2(kf, refs / "key-frames.png")
    tpl = engine.HERE / "templates"
    for f in ("style-rules.md", "graphics-recipes.md", "lock-log.md"):
        (refs / f).write_text((tpl / f).read_text().replace("{{TITLE}}", title).replace("{{NAME}}", name))

    old = eng.name.replace("-edit", "")
    md = (dst / "SKILL.md").read_text()
    # a project skill: no plugin prefix, and no ${CLAUDE_PLUGIN_DATA} (Claude Code fills that in for plugin
    # skills only), so the shared data folder is written in as a plain path
    md = md.replace(f"/video-editor:{old}-edit", f"/{name}-edit").replace("${CLAUDE_PLUGIN_DATA}", str(st.DATA))
    for a_, b_ in PROJECT_SKILL_EDITS:
        md = md.replace(a_, b_)
    md = md.replace(f"{old}-edit", f"{name}-edit").replace(f"/{old}-edit", f"/{name}-edit")
    md = re.sub(old.capitalize() + r"(?=['’]s|\b)", title, md)
    (dst / "SKILL.md").write_text(md)

    print(f"Made {dst}  (run it as /{name}-edit with Claude Code opened in {skills.parent.parent})\n\nStarting style.json: {json.dumps({k: v for k, v in sj.items() if k != '_about'})}\n")
    print("Now rewrite these from the style guide (the engine parts are done and proven):")
    for f, what in REWRITE:
        print(f"  - {f}: {what}")


if __name__ == "__main__":
    main()
