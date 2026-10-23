#!/usr/bin/env python3
"""Cut the picked takes into reel segments, build the voice track at ~-16 LUFS, and get word timings for captions.

Usage:
  python3 cut.py <WORK> [--from-storyboard] [--no-tighten] [--prompt "Names, Claude, GitHub"] [--model small.en]

Reads WORK/edl.json:
  {"source_dir": "/path/to/raw clips",
   "segments": [{"id": "s01", "beat": "b1", "clip": "01 - hooks (IMG_4712).MOV", "in": 98.56, "out": 101.83,
                 "kind": "face|split|full|footage"}, ...]}
--from-storyboard writes edl.json from WORK/storyboard.json first (one segment per beat, its source in/out).

Writes (originals are only ever read):
  WORK/hf/assets/v/<id>.mp4     1080x1920 30 fps, muted, frame-exact
  WORK/audio/voice.wav           all segments joined, loudness-normalised to -16 LUFS (true peak -1.5)
  WORK/segments.json             id, beat, kind, clip, in, out, start (reel time), dur
  WORK/words.json / words.txt    every word with reel times (from the joined voice, so they match the render)
  WORK/progress/NN-cut.jpg       one frame from the middle of every segment, in order
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FPS, H, W, jdump, jload, loudness, whisper_model  # noqa: E402
from progress import progress_path  # noqa: E402


def edges(src, a, b, noise=-38):
    """Silence at the start/end of [a, b] in the source (seconds of leading and trailing silence)."""
    err = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(src), "-vn", "-af",
                          f"silencedetect=noise={noise}dB:d=0.08", "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[0-9.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    dur = b - a
    lead = ends[0] if starts and starts[0] <= 0.02 and ends else 0.0
    trail = dur - starts[-1] if starts and (len(ends) < len(starts) or ends[-1] >= dur - 0.02) else 0.0
    return max(0.0, lead), max(0.0, trail)


def from_storyboard(work):
    sb = jload(work / "storyboard.json")
    segs = []
    for i, b in enumerate(sb["beats"], 1):
        plan = b
        if b.get("alternatives"):
            pick = b.get("approved_pick") or b.get("recommended") or "A"
            plan = next((x for x in b["alternatives"] if x.get("pick") == pick), b["alternatives"][0])
        lay = (plan.get("layout") or "face").lower()
        kind = "full" if "full" in lay else ("split" if "split" in lay else "face")
        segs.append({"id": f"s{i:02d}", "beat": b["id"], "clip": b["source"]["clip"], "in": b["source"]["in"],
                     "out": b["source"]["out"], "kind": kind})
    edl = {"source_dir": sb["folder"], "segments": segs}
    jdump(edl, work / "edl.json")
    return edl


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    work = Path(a[0]).resolve()
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d  # noqa: E731
    edl = from_storyboard(work) if "--from-storyboard" in a else jload(work / "edl.json")
    tighten = "--no-tighten" not in a
    src_dir = Path(edl.get("source_dir", "."))
    vdir = work / "hf" / "assets" / "v"
    adir = work / "audio" / "seg"
    vdir.mkdir(parents=True, exist_ok=True)
    adir.mkdir(parents=True, exist_ok=True)
    out, t = [], 0.0
    for s in edl["segments"]:
        src = Path(s["clip"]) if Path(s["clip"]).is_absolute() else src_dir / s["clip"]
        if not src.exists():
            sys.exit(f"Can't find the clip {src}")
        a0, b0 = float(s["in"]), float(s["out"])
        if tighten and not s.get("keep_edges"):
            lead, trail = edges(src, a0, b0)
            a0 += max(0.0, lead - 0.06)
            b0 -= max(0.0, trail - 0.10)
        n = max(1, round((b0 - a0) * FPS))
        d = n / FPS
        vf = f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a0:.3f}", "-i", str(src), "-t", f"{d + 0.2:.4f}", "-vf", vf,
                        "-frames:v", str(n), "-an", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-g", "15",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(vdir / f"{s['id']}.mp4")], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a0:.3f}", "-i", str(src), "-t", f"{d:.4f}", "-vn", "-ac", "1",
                        "-ar", "48000", "-af", f"apad=whole_dur={d:.4f},afade=t=in:d=0.012,afade=t=out:st={max(0, d - 0.02):.4f}:d=0.02",
                        str(adir / f"{s['id']}.wav")], check=True)
        out.append({**s, "in": round(a0, 3), "out": round(a0 + d, 3), "start": round(t, 4), "dur": round(d, 4)})
        print(f"  {s['id']} {s.get('beat', ''):>5} {s.get('kind', ''):6} reel {t:6.2f}-{t + d:6.2f}  ({src.name} {a0:.2f}-{a0 + d:.2f})")
        t += d
    jdump(out, work / "segments.json")

    # join + loudness (two-pass loudnorm to -16 LUFS integrated, -1.5 dBTP)
    lst = work / "audio" / "concat.txt"
    lst.write_text("".join(f"file '{adir / (s['id'] + '.wav')}'\n" for s in out))
    raw = work / "audio" / "voice-raw.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "pcm_s16le", str(raw)], check=True)
    err = subprocess.run(["ffmpeg", "-v", "info", "-i", str(raw), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    m = {k: re.search(rf'"{k}"\s*:\s*"(-?[0-9.]+|-inf)"', err).group(1) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}
    voice = work / "audio" / "voice.wav"
    af = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", af, "-ar", "48000", "-ac", "1", str(voice)], check=True)
    lufs, tp = loudness(voice)
    print(f"Voice: {t:.2f}s, {lufs} LUFS, peak {tp} dBTP -> {voice}")

    # word timings on the joined voice (these are reel times)
    prompt = opt("--prompt")
    if not prompt and (work / "storyboard.json").exists():
        prompt = " ".join(b["words"] for b in jload(work / "storyboard.json")["beats"])[:800]
    model = whisper_model(opt("--model", "small.en"))
    segs, _ = model.transcribe(str(voice), word_timestamps=True, language="en", vad_filter=False,
                               initial_prompt=prompt or None, condition_on_previous_text=False)
    words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for sg in segs for w in (sg.words or []) if w.word.strip()]
    for w in words:  # which segment each word sits in
        mid = (w["s"] + w["e"]) / 2
        w["seg"] = next((s["id"] for s in out if s["start"] <= mid < s["start"] + s["dur"]), out[-1]["id"])
    jdump(words, work / "words.json")
    (work / "words.txt").write_text("\n".join(f"{i:3d} {w['s']:6.2f}-{w['e']:6.2f} {w['seg']} {w['w']}" for i, w in enumerate(words)) + "\n")
    print(f"{len(words)} words -> words.json / words.txt")
    print("  " + " ".join(w["w"] for w in words))

    # progress picture: the middle frame of every segment, in reel order
    tiles = []
    for s in out:
        p = work / "audio" / f"mid-{s['id']}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s['dur'] / 2:.3f}", "-i", str(vdir / f"{s['id']}.mp4"),
                        "-frames:v", "1", "-vf", "scale=270:480", str(p)], check=True)
        tiles.append(p)
    inputs = sum((["-i", str(p)] for p in tiles), [])
    sheet = progress_path(work, "cut-takes-in-order.jpg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex",
                    ("".join(f"[{i}:v]" for i in range(len(tiles))) + f"hstack=inputs={len(tiles)}") if len(tiles) > 1 else "[0:v]null",
                    str(sheet)], check=True)
    print("progress:", sheet)


if __name__ == "__main__":
    main()
