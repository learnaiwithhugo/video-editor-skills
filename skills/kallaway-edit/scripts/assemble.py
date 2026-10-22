#!/usr/bin/env python3
"""Cut the chosen takes into one tight, constant-frame-rate clip, then time every word.

Usage:
  PY scripts/assemble.py <work_dir> [--max-pause 0.2] [--fast]

Reads  <work_dir>/edl.json:
  {"clips": {"A": "/abs/path/hook.MOV", "B": "/abs/path/tips.MOV"},
   "segments": [ {"clip": "A", "chunk": "c009"},                 # a chunk from takes/<clip>.takes.json
                 {"clip": "B", "start": 91.70, "end": 95.96} ]}  # or an explicit range (raw seconds)
Writes:
  cut.mp4         1080 wide, 30 fps CFR, keyframe every second, voice compressed + levelled
  segments.json   every piece: source range and its frame range in cut.mp4 ("line" = EDL segment index)
  words.json      every word on the cut.mp4 timeline (re-transcribed from the cut itself)
  words.txt       the same, readable, one line per EDL segment, for checking

Why it works this way:
- Every piece is trimmed to a whole number of frames, so video and audio can never drift
  and every cut sits exactly on a frame boundary (the cut-out layer depends on that).
- Pauses inside a take longer than --max-pause are cut down to ~0.12 s (Kallaway pace).
- Each piece gets a 6 ms audio fade at both ends, so joins never click.
- Words are re-timed from the finished cut, not mapped from the raw clip, so caption times
  are as exact as the transcriber can make them.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

FPS = 30
PRE, POST = 0.05, 0.09        # breathing room kept before the first and after the last syllable
KEEP_IN_PAUSE = 0.06          # each side of a shortened inner pause


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def silences(clip, noise=-38, d=0.06):
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", str(clip), "-vn", "-af",
                          f"silencedetect=noise={noise}dB:d={d}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    s = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", out)]
    e = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", out)]
    return list(zip(s, e))


def frames(t):
    return int(round(t * FPS))


def main():
    args = sys.argv[1:]
    max_pause = 0.2
    if "--max-pause" in args:
        i = args.index("--max-pause"); max_pause = float(args[i + 1]); del args[i:i + 2]
    fast = "--fast" in args
    args = [a for a in args if a != "--fast"]
    work = Path(args[0]).resolve()
    edl = json.loads((work / "edl.json").read_text())
    if (work / "words.json").exists():  # keep the last word list so reindex.py can follow changes
        (work / ".prev").mkdir(exist_ok=True)
        (work / ".prev" / "words.json").write_text((work / "words.json").read_text())
    clips = edl["clips"]

    takes, sil, levels = {}, {}, {}
    for key, path in clips.items():
        pcm = run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "8000", "-f", "f32le", "-"],
                  capture_output=True).stdout
        a = np.frombuffer(pcm, dtype=np.float32); n = len(a) // 80
        levels[key] = 20 * np.log10(np.sqrt((a[:n * 80].reshape(n, 80) ** 2).mean(1)) + 1e-9)
        tj = work / "takes" / (Path(path).stem + ".takes.json")
        takes[key] = {c["id"]: c for c in json.loads(tj.read_text())["chunks"]} if tj.exists() else {}
        sil[key] = silences(path)

    pieces = []  # (clip, src_start, src_end, line)
    for line, seg in enumerate(edl["segments"]):
        k = seg["clip"]
        if "chunk" in seg:
            c = takes[k][seg["chunk"]]
            s, e = c["start"], c["end"]
        else:
            s, e = seg["start"], seg["end"]
        s, e = s + seg.get("trim_start", 0.0), e - seg.get("trim_end", 0.0)
        # Tighten to the voice itself: silencedetect edges can include a breath or room noise,
        # which leaves 100-200 ms of silent mouth after a cut. First 10 ms louder than -32 dB is
        # the onset; last one louder than -40 dB is the tail.
        db = levels[k]
        i0, i1 = int(max(0, s - 0.1) * 100), int((s + 0.5) * 100)
        on = next((j for j in range(i0, min(i1, len(db))) if db[j] > -32), None)
        if on is not None and on / 100 < e:
            s = on / 100
        j0, j1 = int(max(s, e - 0.5) * 100), int(min(len(db) / 100, e + 0.15) * 100)
        off = next((j for j in range(j1 - 1, j0, -1) if db[j] > -40), None)
        if off is not None:
            e = (off + 1) / 100
        s, e = max(0.0, s - PRE), e + POST
        # shorten long pauses inside the take
        cur = s
        for a, b in sil[k]:
            if a > cur + 0.15 and b < e - 0.15 and (b - a) > max_pause:
                pieces.append((k, cur, a + KEEP_IN_PAUSE, line))
                cur = b - KEEP_IN_PAUSE
        pieces.append((k, cur, e, line))

    # snap every piece to whole frames
    out_pieces, t_frames = [], 0
    for k, s, e, line in pieces:
        n = max(1, frames(e - s))
        out_pieces.append({"clip": k, "src_start": round(s, 4), "src_end": round(s + n / FPS, 4),
                           "line": line, "frame_start": t_frames, "frames": n,
                           "start": round(t_frames / FPS, 4)})
        t_frames += n

    # one ffmpeg pass: trim each piece from its source, join, force CFR, clean the voice
    inputs, keys = [], list(clips)
    for k in keys:
        inputs += ["-i", clips[k]]
    fc = []
    for i, p in enumerate(out_pieces):
        src = keys.index(p["clip"])
        d = p["frames"] / FPS
        fc.append(f"[{src}:v]trim=start={p['src_start']}:duration={d},setpts=PTS-STARTPTS,"
                  f"fps={FPS},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                  f"setsar=1,trim=end_frame={p['frames']}[v{i}]")
        fc.append(f"[{src}:a]atrim=start={p['src_start']}:duration={d},asetpts=PTS-STARTPTS,"
                  f"aformat=sample_rates=48000:channel_layouts=stereo,"
                  f"afade=t=in:d=0.006,afade=t=out:st={max(0, d - 0.006):.4f}:d=0.006,"
                  f"apad=whole_dur={d:.4f},atrim=duration={d:.4f}[a{i}]")
    n = len(out_pieces)
    fc.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]")
    fc.append(f"[vc]setpts=N/{FPS}/TB[vout]")
    # voice chain: rumble cut, firm compression (Kallaway's voice is loud and dense), level to -14 LUFS
    fc.append("[ac]highpass=f=80,acompressor=threshold=-22dB:ratio=4:attack=4:release=90:makeup=4,"
              "loudnorm=I=-14:TP=-1.5:LRA=7,aresample=48000[aout]")
    cut = work / "cut.mp4"
    print(f"Cutting {n} pieces from {len(edl['segments'])} lines ...", flush=True)
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc),
         "-map", "[vout]", "-map", "[aout]", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
         "-crf", "15", "-pix_fmt", "yuv420p", "-g", str(FPS), "-keyint_min", str(FPS),
         "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", str(cut)])

    nb = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                             "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(cut)],
                            capture_output=True, text=True).stdout.strip())
    if nb != t_frames:
        print(f"  ! frame count {nb} != planned {t_frames}", flush=True)
    (work / "segments.json").write_text(json.dumps(
        {"fps": FPS, "frames": nb, "duration": round(nb / FPS, 4), "pieces": out_pieces}, indent=1))
    print(f"  cut.mp4: {nb} frames = {nb / FPS:.2f} s", flush=True)

    # time every word on the finished cut
    raw = run(["ffmpeg", "-v", "error", "-i", str(cut), "-vn", "-ac", "1", "-ar", "16000",
               "-f", "f32le", "-"], capture_output=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32).copy()
    from faster_whisper import WhisperModel
    model = WhisperModel("small.en" if fast else "medium.en", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(audio, language="en", word_timestamps=True, vad_filter=False,
                               condition_on_previous_text=False, beam_size=5,
                               initial_prompt="Claude, Claude Code, Anthropic, Opus 5.5, Sonnet.")
    words = []
    for s in segs:
        for w in s.words or []:
            t = w.word.strip()
            if not t:
                continue
            # Whisper splits "5.5" into "5" + ".5": glue a token that starts with "." onto the last
            if words and re.match(r"^\.\d", t):
                words[-1]["w"] += t
                words[-1]["end"] = round(w.end, 3)
                continue
            words.append({"w": t, "start": round(w.start, 3), "end": round(w.end, 3)})
    # tag each word with its EDL line (by the piece its midpoint falls in)
    bounds = [(p["start"], p["start"] + p["frames"] / FPS, p["line"]) for p in out_pieces]
    for w in words:
        mid = (w["start"] + w["end"]) / 2
        w["line"] = next((l for a, b, l in bounds if a <= mid < b), bounds[-1][2])
    for i, w in enumerate(words):
        w["i"] = i
    (work / "words.json").write_text(json.dumps(words, indent=1))
    lines = {}
    for w in words:
        lines.setdefault(w["line"], []).append(f"{w['w']}")
    txt = [f"line {l:2d} [{bounds[[b[2] for b in bounds].index(l)][0]:6.2f}s]: " + " ".join(ws)
           for l, ws in sorted(lines.items())]
    (work / "words.txt").write_text("\n".join(txt) + "\n")
    print("\n".join(txt))


if __name__ == "__main__":
    main()
