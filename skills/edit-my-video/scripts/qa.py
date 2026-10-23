#!/usr/bin/env python3
"""Self-review before the user sees anything. Run on the FINAL render; fix every FAIL, look at every picture.

Usage:
  python3 qa.py <WORK> <render.mp4> [--at 1.2,5.5] [--name v1]

What it does (writes WORK/qa/report.md and pictures into WORK/progress/):
  1. Contact sheet at 2 fps of the render (every half second, numbered).
  2. Close-ups at full size: the middle of every visual, every face shot with captions (+ any --at times),
     with the Instagram safe zone drawn on (top 220 px, bottom 420 px, the button column on the right).
  3. A page probe (headless Chrome steps through index.html every 0.25 s) that measures:
       text outside the safe zone or off the frame; full-screen visuals that sit small or high with empty space;
       big black backgrounds; em dashes on screen; numbers on screen that are never said; the same visual
       layout (data-visual) twice in a row.
  4. Captions vs the audio: every caption word must be a word that was said, starting within 0.25 s of it.
  5. Taste lint of the code: overshoot / bouncy easing (pop-ins), underlines, black backgrounds.
  6. Loudness of the render (target -16 LUFS integrated, true peak under -1 dBTP).
Exit code 1 if anything FAILs. WARNs are for your eyes: look, then decide.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHROME, ffprobe_duration, jload, loudness  # noqa: E402
from progress import progress_path  # noqa: E402

FAILS, WARNS, NOTES = [], [], []
NUMWORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
            "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
            "hundred": 100, "thousand": 1000}


def norm(t):
    return re.sub(r"[^a-z0-9]", "", t.lower().replace("\u2019", "'"))


# ------------------------------------------------------------------ 1. contact sheet
def contact_sheet(work, mp4, dur):
    from PIL import Image, ImageDraw
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vf", "fps=2,scale=216:384", str(tmp / "f%04d.png")], check=True)
    frames = sorted(tmp.glob("f*.png"))
    per = 30
    outs = []
    for page in range(0, len(frames), per):
        chunk = frames[page:page + per]
        cols = 10
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 222, rows * 410), "white")
        d = ImageDraw.Draw(sheet)
        for i, f in enumerate(chunk):
            x, y = (i % cols) * 222, (i // cols) * 410
            sheet.paste(Image.open(f), (x + 3, y + 22))
            d.text((x + 6, y + 4), f"{(page + i) * 0.5:.1f}s", fill=(16, 32, 58))
        a, b = page * 0.5, min(dur, (page + len(chunk)) * 0.5)
        out = progress_path(work, f"review-2fps-{a:.0f}-{b:.0f}s.jpg")
        sheet.save(out, quality=85)
        outs.append(out)
    return outs


# ------------------------------------------------------------------ 2. close-ups with the safe zone
def closeups(work, mp4, times, safe):
    from PIL import Image, ImageDraw
    tmp = Path(tempfile.mkdtemp())
    ims = []
    for t in times:
        p = tmp / f"t{t:.2f}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(mp4), "-frames:v", "1", str(p)], check=True)
        im = Image.open(p).convert("RGB")
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        red = (230, 60, 60, 70)
        d.rectangle([0, 0, 1080, safe["top"]], fill=red)
        d.rectangle([0, 1920 - safe["bottom"], 1080, 1920], fill=red)
        d.rectangle([safe["right_x"], safe["right_y0"], 1080, safe["right_y1"]], fill=red)
        im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
        ImageDraw.Draw(im).text((20, 20), f"{t:.2f}s", fill=(255, 255, 255))
        ims.append(im.resize((540, 960)))
    outs = []
    for k in range(0, len(ims), 6):
        part = ims[k:k + 6]
        sheet = Image.new("RGB", (len(part) * 550, 960), "white")
        for i, im in enumerate(part):
            sheet.paste(im, (i * 550, 0))
        out = progress_path(work, f"review-closeups-safe-zone-{k // 6 + 1}.jpg")
        sheet.save(out, quality=88)
        outs.append(out)
    return outs


# ------------------------------------------------------------------ 3. page probe
PROBE_JS = r"""
async ([times, safe]) => {
  const clips = [...document.querySelectorAll('[data-start]')].filter(e => !e.matches('[data-composition-id]'));
  const anims = document.getAnimations();
  const out = [];
  const L = parseFloat(document.querySelector('[data-composition-id]').dataset.duration);
  const t0 = (window.KIT_T0 || 0);
  for (const t of times) {
    clips.forEach(e => {
      const s = parseFloat(e.dataset.start), d = parseFloat(e.dataset.duration || 1e9);
      e.style.display = (t >= s && t < s + d) ? '' : 'none';
    });
    anims.forEach(a => { try { a.currentTime = t * 1000; } catch (e) {} });
    await new Promise(r => requestAnimationFrame(r));
    const vis = (el) => { let o = 1; for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
        const cs = getComputedStyle(n); if (cs.display === 'none' || cs.visibility === 'hidden') return 0; o *= parseFloat(cs.opacity); }
      return o; };
    const texts = [];
    const walker = document.createTreeWalker(document.getElementById('root'), NodeFilter.SHOW_TEXT);
    let n;
    while ((n = walker.nextNode())) {
      const txt = n.textContent.trim();
      if (!txt || n.parentElement.closest('script,style,svg')) continue;
      const o = vis(n.parentElement); if (o < 0.25) continue;
      const r = document.createRange(); r.selectNodeContents(n);
      const rects = [...r.getClientRects()].filter(q => q.width > 2 && q.height > 2);
      if (!rects.length) continue;
      const b = { x: Math.min(...rects.map(q => q.left)), y: Math.min(...rects.map(q => q.top)), r: Math.max(...rects.map(q => q.right)), b: Math.max(...rects.map(q => q.bottom)) };
      texts.push({ txt, ...b, cap: !!n.parentElement.closest('.cap') });
    }
    const scenes = clips.filter(e => e.dataset.visual && e.style.display !== 'none').map(e => {
      const sr = e.getBoundingClientRect();
      let box = null;
      e.querySelectorAll('img,svg,video,.card,.pill,.intro,canvas,[data-content]').forEach(c => {
        if (vis(c) < 0.25) return;
        const q = c.getBoundingClientRect();
        if (q.width < 4 || q.height < 4) return;
        if (q.width * q.height > 0.85 * sr.width * sr.height) return;   // a background, not content
        const x = Math.max(q.left, sr.left), y = Math.max(q.top, sr.top), r = Math.min(q.right, sr.right), bb = Math.min(q.bottom, sr.bottom);
        if (r <= x || bb <= y) return;
        box = box ? { x: Math.min(box.x, x), y: Math.min(box.y, y), r: Math.max(box.r, r), b: Math.max(box.b, bb) } : { x, y, r, b: bb };
      });
      const bg = getComputedStyle(e).backgroundColor, opaque = bg && !/rgba\(.*, 0\)|transparent/.test(bg);
      const full = e.dataset.layout ? e.dataset.layout === 'full' : (sr.height > 1800 && opaque);
      return { id: e.id, visual: e.dataset.visual, start: parseFloat(e.dataset.start), full, box };
    });
    const dark = [...document.querySelectorAll('#root *')].filter(e => vis(e) > 0.5).map(e => {
      const cs = getComputedStyle(e), m = cs.backgroundColor.match(/rgba?\(([\d.]+), ([\d.]+), ([\d.]+)(?:, ([\d.]+))?/);
      if (!m || (m[4] !== undefined && parseFloat(m[4]) < 0.6)) return null;
      const q = e.getBoundingClientRect(), lum = (0.2126 * m[1] + 0.7152 * m[2] + 0.0722 * m[3]) / 255;
      return (lum < 0.1 && q.width * q.height > 0.15 * 1080 * 1920) ? (e.id || e.className || e.tagName) : null;
    }).filter(Boolean);
    out.push({ t, texts, scenes, dark });
  }
  return out;
}
"""


def probe(work, dur, safe):
    from playwright.sync_api import sync_playwright
    times = [round(i * 0.25, 2) for i in range(int(dur / 0.25))]
    idx = work / "hf" / "index.html"
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME) if Path(CHROME).exists() else p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("file://" + str(idx))
        pg.wait_for_timeout(1500)
        res = pg.evaluate(PROBE_JS, [times, safe])
        b.close()
    for e in errs:
        FAILS.append(f"page error in index.html: {e[:200]}")
    return res


def check_probe(res, words, safe):
    said = {norm(w["w"]) for w in words}
    said_nums = set()
    for w in words:
        k = norm(w["w"])
        if k.isdigit():
            said_nums.add(k)
        if k in NUMWORDS:
            said_nums.add(str(NUMWORDS[k]))
        said_nums.update(re.findall(r"\d+", w["w"]))
    bottom = 1920 - safe["bottom"]
    seen_safe, seen_num, seen_dash, full_boxes = set(), set(), set(), {}
    for f in res:
        for x in f["texts"]:
            key = x["txt"][:40]
            bad = []
            if x["y"] < safe["top"] - 2:
                bad.append("above the top safe line")
            if x["b"] > bottom + 2:
                bad.append("below the bottom safe line")
            if x["r"] > safe["right_x"] and x["b"] > safe["right_y0"] and x["y"] < safe["right_y1"]:
                bad.append("under the like/comment buttons")
            if x["x"] < 0 or x["r"] > 1080:
                bad.append("off the edge of the frame")
            if bad and key not in seen_safe:
                seen_safe.add(key)
                (FAILS if x["cap"] or "edge" in bad[-1] else WARNS).append(f"{f['t']:.2f}s text '{key}' {', '.join(bad)}")
            if "—" in x["txt"] and key not in seen_dash:
                seen_dash.add(key)
                FAILS.append(f"{f['t']:.2f}s em dash on screen: '{key}'")
            for num in re.findall(r"\d+(?:\.\d+)?", x["txt"]):
                base = num.split(".")[0]
                if base not in said_nums and num not in said_nums and (key, num) not in seen_num:
                    seen_num.add((key, num))
                    WARNS.append(f"{f['t']:.2f}s number '{num}' on screen ('{key}') is never said: check it matches the speech")
        for s in f["scenes"]:
            if s["full"] and s["box"]:
                full_boxes.setdefault(s["id"], []).append((f["t"], s))
        for d in f["dark"]:
            if ("dark", d) not in seen_safe:
                seen_safe.add(("dark", d))
                FAILS.append(f"{f['t']:.2f}s big black background on {d}")
    for sid, seq in full_boxes.items():  # judge each full-screen visual once it has built (85% through its time)
        t, s = seq[min(len(seq) - 1, int(len(seq) * 0.85))]
        bx = s["box"]
        h, cy = bx["b"] - bx["y"], (bx["y"] + bx["b"]) / 2
        if h < 0.40 * (bottom - safe["top"]) or cy < 620 or cy > 1150:
            WARNS.append(f"{t:.2f}s full-screen visual '{s['visual']}' ({sid}) is {h:.0f}px tall, centred at y {cy:.0f}: "
                         "make it bigger and better placed (the visual should own the frame, no big empty space)")
    order = []
    for f in res:
        for s in f["scenes"]:
            if not order or order[-1][0] != s["id"]:
                if s["id"] not in [o[0] for o in order]:
                    order.append((s["id"], s["visual"], s["start"]))
    order.sort(key=lambda o: o[2])
    for a, b in zip(order, order[1:]):
        if a[1] == b[1]:
            FAILS.append(f"same layout twice in a row: '{a[1]}' ({a[0]} then {b[0]}). Design the second one differently.")
    NOTES.append("Visual order: " + " -> ".join(f"{o[1]}@{o[2]:.1f}s" for o in order))


# ------------------------------------------------------------------ 4. captions vs audio
def check_captions(work, words):
    idx = (work / "hf" / "index.html").read_text()
    caps = re.findall(r'<div id="cap\d+" class="cap ([\w ]+?) clip" data-start="([0-9.]+)".*?<span class="t">(.*?)</span></div>', idx)
    if not caps:
        WARNS.append("no captions found in index.html (run captions.py inject)")
        return
    seq = [(norm(w["w"]), w["s"]) for w in words]
    j = 0
    for cls, start, inner in caps:
        text = __import__("html").unescape(re.sub(r"<[^>]+>", "", inner))
        toks = [norm(t) for t in re.split(r"[\s→]+", text) if norm(t)]
        if not toks:
            continue
        k = next((i for i in range(j, len(seq)) if seq[i][0] == toks[0]), None)
        if k is None:
            k = next((i for i in range(len(seq)) if seq[i][0] == toks[0]), None)
        if k is None:
            FAILS.append(f"caption '{text}' at {float(start):.2f}s: '{toks[0]}' is never said")
            continue
        if "→" not in text and abs(seq[k][1] - float(start)) > 0.25:
            WARNS.append(f"caption '{text}' starts at {float(start):.2f}s but the word is said at {seq[k][1]:.2f}s")
        missing = [t for t in toks if t not in {s[0] for s in seq}]
        if missing:
            FAILS.append(f"caption '{text}' has words that are never said: {missing}")
        j = k + 1
    NOTES.append(f"{len(caps)} captions checked against {len(words)} spoken words")


# ------------------------------------------------------------------ 5. taste lint
def taste(work, tok):
    t = tok.get("taste", {})
    code = (work / "hf" / "index.html").read_text()
    css = (work / "hf" / "assets" / "kit.css").read_text() if (work / "hf" / "assets" / "kit.css").exists() else ""
    allc = code + "\n" + css
    if t.get("no_popin", True):
        for m in re.finditer(r"cubic-bezier\(\s*([-.\d]+)\s*,\s*([-.\d]+)\s*,\s*([-.\d]+)\s*,\s*([-.\d]+)\s*\)", allc):
            y1, y2 = float(m.group(2)), float(m.group(4))
            if y1 > 1.001 or y2 > 1.001 or y1 < -0.001 or y2 < -0.001:
                FAILS.append(f"overshoot easing {m.group(0)} (pop-in feel): use a smooth ease that settles without bouncing")
        for m in re.finditer(r"(back|elastic|bounce)\.(out|in|inOut)", code):
            FAILS.append(f"bouncy GSAP ease '{m.group(0)}' (pop-in feel)")
        for m in re.finditer(r"opacity:\s*0[^}\]]{0,80}scale\((0?\.[0-8]\d*)\)", code):
            WARNS.append(f"something scales up from {m.group(1)} while fading in: that reads as a pop-in, use a rise / fade / blur entrance")
    if t.get("no_underline", True) and re.search(r"text-decoration[^;\"]*underline|<u>", code):
        FAILS.append("underlined text (use colour, size or the shine for emphasis, never an underline)")
    if t.get("no_black_bg", True):
        for m in re.finditer(r"background(?:-color)?\s*:\s*(#000\b|#000000|black\b|rgb\(\s*0\s*,\s*0\s*,\s*0\s*\))", code):
            FAILS.append(f"black background in the code ({m.group(0)}): use the background or accent colour")
    body = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", code, flags=re.S)
    if "—" in body:
        FAILS.append("em dash in the page text")


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    work, mp4 = Path(a[0]).resolve(), Path(a[1]).resolve()
    tok = jload(work / "style.json")
    safe = tok["safe"]
    words = jload(work / "words.json")
    dur = ffprobe_duration(mp4)
    sheets = contact_sheet(work, mp4, dur)
    res = probe(work, dur, safe)
    check_probe(res, words, safe)
    check_captions(work, words)
    taste(work, tok)
    # close-up times: the middle of every visual + the first caption moment of every face shot + --at
    times, spans = set(), {}
    for f in res:
        for sc in f["scenes"]:
            spans.setdefault(sc["id"], []).append(f["t"])
    for ts in spans.values():
        times.add(round((min(ts) + max(ts)) / 2 + 0.25, 2))
    for s in jload(work / "segments.json"):
        if s.get("kind") == "face":
            times.add(round(s["start"] + min(0.9, s["dur"] / 2), 2))
    if "--at" in a:
        times.update(float(x) for x in a[a.index("--at") + 1].split(","))
    shots = closeups(work, mp4, sorted(t for t in times if t < dur), safe)
    lufs, tp = loudness(mp4)
    (FAILS if lufs is None or abs(lufs + 16) > 1.0 else NOTES).append(f"loudness {lufs} LUFS (target -16 +/- 1)")
    (FAILS if tp is None or tp > -0.9 else NOTES).append(f"true peak {tp} dBTP (under -1)")
    rep = [f"# Self-review: {mp4.name} ({dur:.1f}s)", "", "## FAIL (fix before showing)"] + [f"- {x}" for x in FAILS or ["none"]] + \
          ["", "## WARN (look at the pictures, then decide)"] + [f"- {x}" for x in WARNS or ["none"]] + \
          ["", "## Notes"] + [f"- {x}" for x in NOTES] + ["", "## Pictures to look at"] + [f"- {p}" for p in sheets + shots]
    (work / "qa").mkdir(exist_ok=True)
    (work / "qa" / "report.md").write_text("\n".join(rep) + "\n")
    print("\n".join(rep))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
