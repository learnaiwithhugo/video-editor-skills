#!/usr/bin/env python3
"""Turn plan.json + the scene files into a HyperFrames project, ready to preview or render.

Usage:
  PY scripts/build.py <work_dir> [--safe]

Inputs (all in <work_dir>):
  plan.json        shots (layouts + cut points), scenes (which graphic plays when, beats),
                   captions (fixes, emphasis words), punch-ins, extra sound cues
  scenes/*.html    one file per graphic scene (written from template/scene-starter.html)
  cut.mp4, cutout.webm, words.json, segments.json, headtrack.json   (from earlier steps)
Output: <work_dir>/project/  (index.html, compositions/, assets/)  -> render.py renders it.
--project <dir> builds into another folder instead of <work_dir>/project.
--safe draws the Instagram no-go zones in red, for checking snapshots only (never render it).

Time references used anywhere in plan.json:
  12.4        seconds on the cut
  "line:3"    the first frame of EDL line 3 (a clean join between takes)
  "w:35"      the onset of word 35 (snapped to the quietest point just before it, on a frame)
  "w:35.end"  the end of word 35;   any ref + "+0.2" / "-0.1" adds an offset
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

SK = Path(__file__).resolve().parent.parent
FPS = 30
W, H = 1080, 1920
# The style's numbers live in SK/style.json (the style pack); these defaults are the Kallaway values,
# so a skill without a style.json still builds exactly as before.
STYLE = {"card": {"x0": 68, "x1": 1012, "top": 1404, "r": 40}, "caption_y_stage": 1236, "pop": 104,
         "caption_y_full_min": 1160, "caption_y_full_max": 1420, "caption_px": 58, "caption_em_px": 66,
         "caption_tracking_em": -0.035, "music_under_voice_db": 21, "music_gap_lift_db": 5}
if (SK / "style.json").exists():
    STYLE.update(json.loads((SK / "style.json").read_text()))
CARD = STYLE["card"]
CAP_STAGE_Y = STYLE["caption_y_stage"]   # caption centre in the stage layout (Kallaway: y 1241-1262)
POP = STYLE["pop"]                       # how far the head should rise above the card edge
sys.dont_write_bytecode = True  # never write into the skill folder: a plugin update replaces it
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sounds  # noqa: E402  the sound-effect map (references/sound-map.md)

MUSIC_UNDER_VOICE_DB = STYLE["music_under_voice_db"]  # music this far under the voice (brief: 18-24)
MUSIC_GAP_LIFT_DB = STYLE["music_gap_lift_db"]        # and up this much in pauses of 0.35 s or more
FUNCTION_WORDS = set("""a an the to of in on at for and or but so it its it's is are was be been
how you your we our i my me this that these those with as by from just which what their there
they them he she his her will would can could do does did get going gonna not no if than then
very really much more most also into about out up""".split())


def fr(t):
    return round(t * FPS) / FPS


class Clock:
    """Resolves time references against the words, the pieces and the audio."""

    def __init__(self, work: Path):
        self.words = json.loads((work / "words.json").read_text())
        self.seg = json.loads((work / "segments.json").read_text())
        self.dur = self.seg["frames"] / FPS
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(work / "cut.mp4"), "-vn", "-ac", "1",
                              "-ar", "8000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
        a = np.frombuffer(raw, dtype=np.float32)
        hop = 80  # 10 ms
        n = len(a) // hop
        self.rms = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
        self.line_start = {}
        for p in self.seg["pieces"]:
            self.line_start.setdefault(p["line"], p["start"])

    def onset(self, i):
        """Frame on which word i really starts: the quietest 10 ms in the 160 ms before
        Whisper's start, then back to that frame boundary (cuts land 0-60 ms before the word)."""
        w = self.words[i]
        lo = int(max(0, w["start"] - 0.16) * 100)
        hi = int((w["start"] + 0.04) * 100)
        if i > 0:
            lo = max(lo, int(self.words[i - 1]["start"] * 100) + 5)
        seg = self.rms[lo:hi] if hi > lo else self.rms[hi:hi + 1]
        t = (lo + int(np.argmin(seg))) / 100 if len(seg) else w["start"]
        return int(t * FPS) / FPS  # floor to the frame at or before the quiet point

    def __call__(self, ref):
        if isinstance(ref, (int, float)):
            return float(ref)
        m = re.match(r"^\s*(line|w):(\d+)(\.end)?\s*([+-]\s*[\d.]+)?\s*$", str(ref))
        if not m:
            raise ValueError(f"bad time ref {ref!r}")
        kind, n, end, off = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        if kind == "line":
            t = self.line_start[n]
        else:
            t = self.words[n]["end"] if end else self.onset(n)
        if off:
            t += float(off.replace(" ", ""))
        return round(t, 4)


def layouts(work: Path, plan: dict, clock: Clock):
    """Camera placement for each layout, from where the head actually is."""
    ht = json.loads((work / "headtrack.json").read_text())
    samples = [s for s in ht["samples"] if s["top"] is not None]
    med_top = ht["summary"]["head_top_median"]
    cx = ht["summary"]["head_cx_median"]
    g = plan.get("geometry", {})
    widths = [x["right"] - x["left"] for x in samples]
    head_h = 1.55 * float(np.median(widths))          # hair top to chin, in source pixels
    card_w, visible = CARD["x1"] - CARD["x0"], H - CARD["top"]
    s_fill = card_w / W
    # A wide shot (Kallaway's 4K) fills the card and still shows head, shoulders and room. A tight
    # vertical selfie would show forehead-to-nose: a zoomed selfie, not a card. Then the footage is
    # scaled DOWN so hair-to-chest fits the visible card, and blurred footage fills the sides.
    tight = g.get("card_fit", "auto") == "head-shoulders" or (
        g.get("card_fit", "auto") == "auto" and head_h * s_fill > 0.75 * visible)
    pop = g.get("pop", 40 if tight else POP)
    s = min(s_fill, (visible + pop) / (1.45 * head_h)) if tight else s_fill

    def stage_for(t0, t1):
        tops = [x["top"] for x in samples if t0 - 0.1 <= x["t"] <= t1 + 0.1] or [med_top]
        top_med, top_min = float(np.median(tops)), float(min(tops))
        # the head rises ~pop above the card edge on average, but its HIGHEST moment in the shot
        # must stay under the caption (so take the lower of the two placements)
        y = max(CARD["top"] - pop - s * top_med, (CAP_STAGE_Y + 50) - s * top_min)
        if tight:
            x = max(CARD["x0"], min(CARD["x1"] - W * s, W / 2 - s * cx))   # head centred, frame inside the card
        else:
            x = CARD["x0"]
            y = max(y, H - H * s)                   # the card must stay filled to the bottom
        return {"x": round(x, 1), "y": round(y, 1), "scale": round(s, 4)}

    # Full layout: a face-filling crop anchored to the bottom of the frame (Kallaway: eyes ~32%,
    # mouth ~43%, caption on the chest ~60-70%). Head top lands near target_top.
    target_top = g.get("full_head_top", 60)
    f = max(1.0, (H - target_top) / (H - med_top))
    f = min(f, g.get("full_max_scale", 1.35))
    fy = max(target_top - f * med_top, H - H * f)
    fx = min(0.0, max(W - W * f, W / 2 - f * cx))
    full = {"x": round(fx, 1), "y": round(fy, 1), "scale": round(f, 4)}
    chin_raw = med_top + head_h
    cap_full = min(STYLE["caption_y_full_max"], max(STYLE["caption_y_full_min"], fy + f * chin_raw + 95))
    cap_full = g.get("full_caption_y", cap_full)
    card = {"tight": tight, "scale": s, "cy": med_top + 0.55 * head_h, "cx": cx}
    return stage_for, full, round(cap_full), card


def make_card_bg(work: Path, proj: Path):
    """Blurred, darkened copy of the cut that fills the card's sides when the footage is scaled
    down (tight selfie). Small (360 wide), frame-for-frame with cut.mp4, baked by ffmpeg because
    HyperFrames grades/blurs footage only through its own treatments, never CSS filters."""
    src, dst = work / "cut.mp4", work / "cut-bg.mp4"
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-an", "-vf",
                        "scale=360:640,boxblur=22:3,eq=brightness=-0.30:saturation=0.55:contrast=0.9,setsar=1",
                        "-r", str(FPS), "-c:v", "libx264", "-crf", "26", "-pix_fmt", "yuv420p", "-g", str(FPS),
                        str(dst)], check=True)
    link = proj / "assets" / "cut-bg.mp4"
    if link.exists():
        link.unlink()
    try:
        link.hardlink_to(dst)
    except OSError:
        shutil.copy(dst, link)


def caption_chunks(words, cuts, plan):
    """1-3 words per chunk, broken at punctuation, pauses and cuts; product names stay whole."""
    cap = plan.get("captions", {})
    fixes = {int(k): v for k, v in cap.get("fix", {}).items()}
    glue = [tuple(x) for x in cap.get("keep_together", [])]
    toks = []
    for w in words:
        toks.append(dict(w, w=fixes.get(w["i"], w["w"])))
    toks = [t for t in toks if t["w"]]
    glued = {i for a, b in glue for i in range(a, b)}  # word i glues to i+1
    chunks, cur = [], []

    def content(t):
        return re.sub(r"[^a-z']", "", t["w"].lower()) not in FUNCTION_WORDS

    # Kallaway chunking: usually ONE content word per chunk; small function words ride along
    # with the content word that follows them ("for Opus 5.5", "a prompting"); never more than 3.
    for k, t in enumerate(toks):
        prev = toks[k - 1] if k else None
        if cur and prev is not None:
            crosses_cut = any(prev["start"] < c <= t["start"] + 0.02 for c in cuts)
            pause = t["start"] - prev["end"] > 0.3
            if len(cur) >= 3 or crosses_cut or pause:
                chunks.append(cur)
                cur = []
        cur.append(t)
        nxt = toks[k + 1] if k + 1 < len(toks) else None
        glue_next = nxt is not None and (t["i"] in glued or re.match(r"^\d", nxt["w"]) is not None)
        if glue_next and not re.search(r"[.,!?;:]$", t["w"]):
            continue
        if content(t) or re.search(r"[.,!?;:]$", t["w"]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def scene_files(work: Path, plan: dict, clock: Clock, proj: Path, kw_css: str, kw_js: str):
    out = []
    for sc in plan["scenes"]:
        sid, src = sc["id"], sc.get("src", sc["id"])
        t0, t1 = clock(sc["from"]), clock(sc["to"])
        text = (work / "scenes" / f"{src}.html").read_text()
        beats = {"dur": round(t1 - t0, 4)}
        for name, ref in sc.get("beats", {}).items():
            beats[name] = round(clock(ref) - t0, 4)
        beats["w"] = [{"i": w["i"], "w": w["w"], "t": round(clock(f"w:{w['i']}") - t0, 4),
                       "e": round(w["end"] - t0, 4)}
                      for w in clock.words if t0 - 0.05 <= w["start"] < t1]
        beats.update(sc.get("vars", {}))
        text = text.replace("__ID__", sid)
        text = text.replace("/*KW:CSS*/", kw_css).replace("/*KW:JS*/", kw_js)
        text = re.sub(r"/\*KW:BEATS\*/.*?/\*END\*/", "/*KW:BEATS*/" + json.dumps(beats) + "/*END*/",
                      text, flags=re.S)
        (proj / "compositions" / f"{sid}.html").write_text(text)
        sfx = []
        m = re.search(r"<!--KW:SFX(.*?)-->", text, flags=re.S)
        if m:
            spec = m.group(1).strip()
            # cues may name beats: {"t":"B.cam2","s":"whoosh"}
            for cue in json.loads(spec):
                def ref(v):
                    """scene seconds for: a number, "w:12-0.04" (a spoken word), "B.name+0.1" (a beat)
                    or "B.w1" (the scene's 2nd word: for scenes mounted several times)."""
                    if isinstance(v, (int, float)):
                        return float(v)
                    if re.match(r"^(w|line):", v):
                        return clock(v) - t0     # follows the words if the cut changes
                    mm = re.match(r"^B\.(\w+?)(\d*)\s*([+-]\s*[\d.]+)?$", v)
                    name, num, off = mm.group(1), mm.group(2), mm.group(3)
                    base = beats["w"][int(num)]["t"] if name == "w" and num else beats[name + num]
                    return base + (float(off.replace(" ", "")) if off else 0.0)
                tt = ref(cue["t"])
                dur = cue.get("dur")
                if isinstance(dur, str):         # "dur": "w:40" = until that word
                    dur = max(0.1, ref(dur) - tt)
                sfx.append({"t": t0 + tt, "s": cue["s"], "db": cue.get("db", 0), "dur": dur})
        out.append({"id": sid, "start": t0, "dur": t1 - t0, "sfx": sfx})
    return out


def main():
    work = Path(sys.argv[1]).resolve()
    safe = "--safe" in sys.argv
    plan = json.loads((work / "plan.json").read_text())
    clock = Clock(work)
    proj = work / "project"
    if "--project" in sys.argv:  # build into another folder (lets two people/agents work at once)
        proj = Path(sys.argv[sys.argv.index("--project") + 1]).resolve()
    (proj / "compositions").mkdir(parents=True, exist_ok=True)
    # assets: kit files copied fresh each build; media hard-linked (no extra disk)
    tpl = SK / "template"
    for sub in ["fonts", "vendor"]:
        shutil.copytree(tpl / "assets" / sub, proj / "assets" / sub, dirs_exist_ok=True)
    for f in ["hyperframes.json"]:
        shutil.copy(tpl / f, proj / f)
    for name in ["cut.mp4", "cutout.webm"]:
        dst = proj / "assets" / name
        if dst.exists():
            dst.unlink()
        try:
            dst.hardlink_to(work / name)
        except OSError:
            shutil.copy(work / name, dst)
    kw_css = (tpl / "kit" / "kw.css").read_text()
    kw_js = (tpl / "kit" / "kw.js").read_text()

    D = clock.dur
    stage_for, full, cap_full, card = layouts(work, plan, clock)
    if card["tight"]:
        make_card_bg(work, proj)

    # ---------------- shots ----------------
    shots = []
    for i, sh in enumerate(plan["shots"]):
        t0 = clock(sh["at"])
        t1 = clock(plan["shots"][i + 1]["at"]) if i + 1 < len(plan["shots"]) else D
        shots.append(dict(sh, t0=t0, t1=t1))
    cuts = [s["t0"] for s in shots[1:]]

    def layout_at(t):
        for s in shots:
            if s["t0"] - 1e-3 <= t < s["t1"] - 1e-3:
                return s["layout"]
        return shots[-1]["layout"]

    def tset(t):  # a set that lands ON the frame
        return max(0.0, round(t - 0.002, 4))

    root_js = []
    sfx_cues = []
    prev_layout = None
    for s in shots:
        if s["layout"] == "stage":
            cam = stage_for(s["t0"], s["t1"])
            clip = (f"path('M{CARD['x0']} {CARD['top'] + CARD['r']} A{CARD['r']} {CARD['r']} 0 0 1 "
                    f"{CARD['x0'] + CARD['r']} {CARD['top']} L{CARD['x1'] - CARD['r']} {CARD['top']} "
                    f"A{CARD['r']} {CARD['r']} 0 0 1 {CARD['x1']} {CARD['top'] + CARD['r']} "
                    f"L{CARD['x1']} {H + 10} L{CARD['x0']} {H + 10} Z')")
            pop = 1
        else:
            cam = dict(full)
            clip = "none"
            pop = 0
        root_js.append(f"tl.set('#cam-xf',{json.dumps(cam)},{tset(s['t0'])});")
        root_js.append(f"tl.set('#pop-xf',{json.dumps(cam)},{tset(s['t0'])});")
        root_js.append(f"tl.set('#cam-mask',{{clipPath:\"{clip}\"}},{tset(s['t0'])});")
        root_js.append(f"tl.set('#pop-mask',{{opacity:{pop}}},{tset(s['t0'])});")
        if card["tight"]:
            root_js.append(f"tl.set('#bg-xf',{{opacity:{pop}}},{tset(s['t0'])});")
            if pop:
                xl = cam["x"]; xr = cam["x"] + W * cam["scale"]
                root_js.append(f"tl.set('#seam-l',{{x:{xl - 40:.1f},opacity:1}},{tset(s['t0'])});")
                root_js.append(f"tl.set('#seam-r',{{x:{xr - 40:.1f},opacity:1}},{tset(s['t0'])});")
            else:
                root_js.append(f"tl.set(['#seam-l','#seam-r'],{{opacity:0}},{tset(s['t0'])});")
        if s["layout"] == "full" and s.get("push"):
            k = s["push"]
            px, py = W / 2, 700
            z = {"scale": round(cam["scale"] * k, 4), "x": round(px - (px - cam["x"]) * k, 1),
                 "y": round(py - (py - cam["y"]) * k, 1)}
            # End 2 frames BEFORE the next cut. GSAP renders a timeline backwards when the renderer
            # seeks back, so a tween still running at the next shot's set would overwrite it.
            root_js.append(f"tl.to('#cam-xf',{{...{json.dumps(z)},duration:{s['t1'] - s['t0'] - 2 / FPS:.3f},"
                           f"ease:'power1.inOut'}},{s['t0']:.4f});")
        if prev_layout and plan.get("auto_sfx", True) and s["layout"] == "stage":
            # into the stage from the face: the big whoosh; stage to a new stage scene: a whoosh
            sfx_cues.append({"t": s["t0"], "s": "whoosh-big" if prev_layout == "full" else "whoosh"})
        prev_layout = s["layout"]

    for p in plan.get("punch", []):
        t = clock(p["at"])
        sh = next(s for s in shots if s["t0"] - 1e-3 <= t < s["t1"])
        base = full if sh["layout"] == "full" else stage_for(sh["t0"], sh["t1"])
        k = p.get("scale", 1.19)
        # zoom about the chin line so the face grows upward and never into the caption
        px, py = W / 2, p.get("y", cap_full - 90 if sh["layout"] == "full" else 1500)
        z = {"scale": round(base["scale"] * k, 4), "x": round(px - (px - base["x"]) * k, 1),
             "y": round(py - (py - base["y"]) * k, 1)}
        root_js.append(f"tl.set('#cam-xf',{json.dumps(z)},{tset(t)});")
        if p.get("riser", True):
            sfx_cues.append({"t": t, "s": "riser"})

    # ---------------- scenes ----------------
    scenes = scene_files(work, plan, clock, proj, kw_css, kw_js)
    for sc in scenes:
        sfx_cues += sc["sfx"]
    for c in plan.get("sfx", []):
        sfx_cues.append({"t": clock(c["at"]), "s": c["s"], "db": c.get("db", 0), "dur": c.get("dur")})

    # ---------------- captions ----------------
    chunks = caption_chunks(clock.words, cuts, plan)
    emph = set(plan.get("captions", {}).get("emphasis", []))
    cap_html, cap_js = [], []
    for ci, ch in enumerate(chunks):
        def shown_at(w):
            """A word's caption time: its onset, but never a few frames before the cut that
            introduces it (the caption would flash in the old layout's position)."""
            t = clock(f"w:{w['i']}")
            for c in cuts:
                if c - 0.2 <= t < c and w["start"] >= c - 0.12:
                    return c
            return t
        t_in = shown_at(ch[0])
        t_out = shown_at(chunks[ci + 1][0]) if ci + 1 < len(chunks) else D
        lay = layout_at(t_in + 0.01)
        cap_y = lambda l: CAP_STAGE_Y if l == "stage" else cap_full
        y = cap_y(lay)
        spans = []
        for w in ch:
            cls = "cw em" if w["i"] in emph else "cw"
            txt = w["w"].replace("&", "&amp;").replace("<", "&lt;")
            spans.append(f'<span id="cw{w["i"]}" class="{cls}">{txt}</span>')
        cap_html.append(f'<div id="cc{ci}" class="cc" style="top:{y - 40}px">{" ".join(spans)}</div>')
        cap_js.append(f"tl.set('#cc{ci}',{{opacity:1}},{tset(t_in)});")
        for j, w in enumerate(ch):
            tw = t_in if j == 0 else max(t_in, shown_at(w))
            cap_js.append(f"tl.set('#cw{w['i']}',{{opacity:1}},{tset(tw)});")
        # a chunk still on screen when the layout changes moves to the new layout's caption line
        for c in cuts:
            if t_in < c < t_out and layout_at(c + 0.01) != lay:
                cap_js.append(f"tl.set('#cc{ci}',{{y:{cap_y(layout_at(c + 0.01)) - y}}},{tset(c)});")
        cap_js.append(f"tl.set('#cc{ci}',{{opacity:0}},{tset(t_out)});")
    cap_doc = f"""<template>
<style>
{kw_css}
#root {{ position: absolute; inset: 0; }}
.cc {{ position: absolute; left: 0; width: {W}px; height: 80px; line-height: 80px; text-align: center;
  font-family: "KW Grotesk", sans-serif; font-weight: 800; font-size: {STYLE["caption_px"]}px;
  letter-spacing: {STYLE["caption_tracking_em"]}em; color: #fff; opacity: 0; white-space: nowrap; }}
.cw {{ opacity: 0; display: inline-block; }}
.cw.em {{ font-family: "KW Serif", serif; font-style: italic; font-weight: 400; font-size: {STYLE["caption_em_px"]}px;
  letter-spacing: -0.01em; }}
</style>
<div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}">
{chr(10).join(cap_html)}
</div>
<script>
(function(){{
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(cap_js)}
window.__timelines["captions"] = tl;
}})();
</script>
</template>
"""
    (proj / "compositions" / "captions.html").write_text(cap_doc)

    # ---------------- sound effects ----------------
    sounds.ensure_library(quiet=True)
    lv = sounds.measure()
    (proj / "assets" / "sfx").mkdir(parents=True, exist_ok=True)
    for f in sounds.NEEDED:
        shutil.copy(sounds.LIB / f, proj / "assets" / "sfx" / f)
    alias = {"swoosh-big": "whoosh-big", "type": "key"}
    cues = []
    for c in sfx_cues:
        c = dict(c, s=alias.get(c["s"], c["s"]))
        if c["s"] not in sounds.MAP:
            print(f"  ! unknown sound cue {c['s']!r} (see references/sound-map.md); skipped")
            continue
        cues.append(c)
    # never two hits on (almost) the same frame: the higher-priority sound wins
    kept = []
    for c in sorted(cues, key=lambda c: c["t"]):
        if kept and c["t"] - kept[-1]["t"] < 2.5 / FPS:
            if sounds.MAP[c["s"]][4] > sounds.MAP[kept[-1]["s"]][4]:
                kept[-1] = c
            continue
        kept.append(c)
    sfx_html, lanes, sfx_list = [], [], []
    for k, c in enumerate(kept):
        f, win, hit, _peak, _prio = sounds.MAP[c["s"]]
        length = float(c.get("dur") or lv[c["s"]]["dur"])
        start = c["t"] - hit + 1 / FPS          # the hit lands one frame after the picture
        if c["s"] == "riser":
            start = c["t"] - length             # a riser stops dead ON the punch-in
        mstart = (win[0] if win else 0.0)
        if start < 0:                            # clipped at the very start: skip into the file
            mstart -= start; length += start; start = 0.0
        if length <= 0.02:
            continue
        lane = next((i for i, end in enumerate(lanes) if end <= start), None)
        if lane is None:
            lanes.append(0); lane = len(lanes) - 1
        lanes[lane] = start + length
        vol = sounds.volume(c["s"], lv, float(c.get("db") or 0))
        fade = 0.012 if c["s"] == "riser" else 0.04
        sfx_html.append(f'<audio id="sfx{k}" class="clip" src="assets/sfx/{f}" data-start="{start:.4f}" '
                        f'data-duration="{length:.4f}" data-media-start="{mstart:.4f}" data-volume="{vol}" '
                        f'data-fade-out="{fade}" data-track-index="{20 + lane}"></audio>')
        sfx_list.append({"t": round(c["t"], 3), "s": c["s"], "vol": vol})

    # ---------------- music (optional, on by default once music.py picked a track) ----------------
    music_html, music_lane = "", []
    mus = plan.get("music", {})
    if mus.get("on") and mus.get("file") and (work / mus["file"]).exists():
        src = work / mus["file"]
        dst = proj / "assets" / "music" / src.name
        dst.parent.mkdir(exist_ok=True)
        shutil.copy(src, dst)
        voice_lufs = -14.0
        # loudness of the stretch that will actually play (a track's average can mislead)
        err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", str(mus.get("start", 0)), "-t", f"{D:.2f}",
                              "-i", str(src), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
        mm = re.search(r"I:\s+(-?[\d.]+) LUFS", err[err.rfind("Summary:"):])
        m_lufs = float(mm.group(1)) if mm else mus.get("lufs", -16.0)
        v_speech = min(1.0, 10 ** ((voice_lufs - MUSIC_UNDER_VOICE_DB - m_lufs) / 20))
        v_gap = v_speech * 10 ** (MUSIC_GAP_LIFT_DB / 20)
        spans = []
        for w in clock.words:
            if spans and w["start"] - spans[-1][1] < 0.35:
                spans[-1][1] = max(spans[-1][1], w["end"])
            else:
                spans.append([w["start"], w["end"]])
        pts = [{"t": 0, "v": 0}, {"t": 0.12, "v": round(v_speech, 4)}]
        for (a0, a1), (b0, _b1) in zip(spans, spans[1:]):
            pts += [{"t": round(a1 + 0.08, 3), "v": round(v_speech, 4)},
                    {"t": round(a1 + 0.2, 3), "v": round(v_gap, 4)},
                    {"t": round(max(a1 + 0.2, b0 - 0.12), 3), "v": round(v_gap, 4)},
                    {"t": round(b0 - 0.02, 3), "v": round(v_speech, 4)}]
        pts += [{"t": round(D - 1.0, 3), "v": round(v_speech, 4)}, {"t": round(D, 3), "v": 0}]
        pts = [p for i, p in enumerate(pts) if i == 0 or p["t"] > pts[i - 1]["t"]]
        music_lane = pts
        lane_json = json.dumps({"version": 1, "lanes": [{"target": "volume", "points": pts}]}).replace('"', "&quot;")
        music_html = (f'<audio id="music" class="clip" src="assets/music/{src.name}" data-start="0" '
                      f'data-duration="{D:.4f}" data-media-start="{float(mus.get("start", 0)):.3f}" '
                      f'data-volume="1" data-automation="{lane_json}" data-track-index="19" '
                      f'data-timeline-role="music"></audio>')

    # ---------------- root ----------------
    hosts = []
    for z, sc in enumerate(scenes):
        hosts.append(f'<div id="{sc["id"]}" data-composition-id="{sc["id"]}" '
                     f'data-composition-src="compositions/{sc["id"]}.html" data-start="{sc["start"]:.4f}" '
                     f'data-duration="{sc["dur"]:.4f}" data-track-index="{2 + z}" data-track-kind="graphics" '
                     f'data-width="{W}" data-height="{H}" style="position:absolute;inset:0;z-index:2"></div>')
    safe_div = ""
    if safe:
        safe_div = ('<div id="safe" style="position:absolute;inset:0;z-index:99;pointer-events:none">'
                    '<div style="position:absolute;left:0;top:0;width:1080px;height:220px;background:rgba(255,0,0,.28)"></div>'
                    '<div style="position:absolute;left:0;top:1470px;width:1080px;height:450px;background:rgba(255,0,0,.28)"></div>'
                    '<div style="position:absolute;left:980px;top:1155px;width:100px;height:315px;background:rgba(255,0,0,.28)"></div>'
                    '</div>')
    vid_style = f"position:absolute;left:0;top:0;width:{W}px;height:{H}px"
    bg_html = seam_html = ""
    if card["tight"]:
        k = (CARD["x1"] - CARD["x0"]) / 360            # cut-bg.mp4 is 360x640: cover the card's width
        by = (CARD["top"] + H) / 2 - k * card["cy"] / 3
        bg_html = (f'<div id="bg-xf" style="position:absolute;left:{CARD["x0"]}px;top:{by:.1f}px;width:360px;'
                   f'height:640px;transform-origin:0 0;transform:scale({k:.4f})">'
                   f'<video id="cambg" class="clip" src="assets/cut-bg.mp4" data-start="0" data-duration="{D:.4f}" '
                   f'data-media-start="0" data-track-index="2" muted playsinline '
                   f'style="position:absolute;left:0;top:0;width:360px;height:640px"></video></div>')
        seam = ("position:absolute;left:0;top:{t}px;width:80px;height:{h}px;opacity:0;"
                "background:linear-gradient(90deg,rgba(0,0,0,0) 0%,rgba(0,0,0,0.55) 50%,rgba(0,0,0,0) 100%)")
        seam_html = (f'<div id="seam-l" style="{seam.format(t=CARD["top"], h=H - CARD["top"])}"></div>'
                     f'<div id="seam-r" style="{seam.format(t=CARD["top"], h=H - CARD["top"])}"></div>')
    index = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<script src="assets/vendor/gsap.min.js"></script>
<style>
{kw_css}
html, body {{ margin: 0; background: #020202; }}
#root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; background: #020202; }}
#stage {{ position: absolute; inset: 0; z-index: 0;
  background:
    radial-gradient(circle at 50% 50%, rgba(70,70,70,0.55) 0 1.15px, transparent 1.6px) 0 0 / 16px 16px,
    radial-gradient(ellipse 75% 60% at 50% 38%, #0B0B0B 0%, #060606 60%, #020202 100%); }}
#stage-fade {{ position: absolute; inset: 0; z-index: 0;
  background: radial-gradient(ellipse 80% 65% at 50% 38%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.75) 100%); }}
#cam-mask, #pop-mask {{ position: absolute; inset: 0; }}
#cam-mask {{ z-index: 5; }}
#pop-mask {{ z-index: 6; clip-path: path(evenodd, 'M0 0 H{W} V{H} H0 Z M{CARD['x0']} {CARD['top'] + 6} H{CARD['x1']} V{H + 10} H{CARD['x0']} Z'); }}
#cam-xf, #pop-xf {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; transform-origin: 0 0; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{D:.4f}" data-width="{W}" data-height="{H}" data-fps="{FPS}">
  <div id="stage"></div>
  <div id="stage-fade"></div>
  {chr(10).join('  ' + h for h in hosts)}
  <div id="cam-mask">{bg_html}<div id="cam-xf">
    <video id="cam" class="clip" src="assets/cut.mp4" data-start="0" data-duration="{D:.4f}" data-media-start="0" data-track-index="1" data-has-audio="true" playsinline style="{vid_style}"></video>
  </div>{seam_html}</div>
  <div id="pop-mask"><div id="pop-xf">
    <video id="pop" class="clip" src="assets/cutout.webm" data-start="0" data-duration="{D:.4f}" data-media-start="0" data-track-index="0" muted playsinline style="{vid_style}" data-layout-allow-occlusion></video>
  </div></div>
  <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{D:.4f}" data-track-index="15" data-track-kind="captions" data-width="{W}" data-height="{H}" style="position:absolute;inset:0;z-index:8"></div>
  {music_html}
  {chr(10).join('  ' + s for s in sfx_html)}
  {safe_div}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(root_js)}
window.__timelines["main"] = tl;
</script>
</body>
</html>
"""
    (proj / "index.html").write_text(index)
    # a machine-readable summary for QA
    summary = {"duration": D, "cuts": cuts, "shots": [{k: s[k] for k in ("t0", "t1", "layout")} for s in shots],
               "scenes": [{k: sc[k] for k in ("id", "start", "dur")} for sc in scenes],
               "chunks": [{"t": clock(f"w:{c[0]['i']}"), "text": " ".join(w["w"] for w in c)} for c in chunks],
               "sfx": sfx_list, "music_lane": music_lane, "card_fit": "head-shoulders" if card["tight"] else "fill",
               "card_scale": round(card["scale"], 4), "full_layout": full, "full_caption_y": cap_full}
    (work / "build.json").write_text(json.dumps(summary, indent=1))
    full_share = sum(s["t1"] - s["t0"] for s in shots if s["layout"] == "full") / D
    print(f"Built {proj}: {D:.2f} s, {len(shots)} shots ({full_share:.0%} full layout), "
          f"{len(scenes)} scenes, {len(chunks)} caption chunks, {len(sfx_html)} sound effects.")


if __name__ == "__main__":
    main()
