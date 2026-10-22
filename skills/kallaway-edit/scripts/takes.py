#!/usr/bin/env python3
"""List every spoken attempt in a raw clip, so the best take of each line is easy to pick.

Usage:
  PY scripts/takes.py <work_dir> <clip> [<clip> ...] [--fast] [--noise -38] [--gap 0.25]

How it works: ffmpeg finds the silences, the speech between them becomes "chunks"
(pauses shorter than --gap seconds stay inside a chunk), and every chunk is
transcribed ON ITS OWN. That matters: transcribing a whole rambling clip at once
makes Whisper merge retakes and smear word times over pauses; one chunk at a time
gives exactly what was said in that stretch, with silence-accurate edges.

Writes <work_dir>/takes/<clip-stem>.takes.json and .takes.txt:
  c012  [ 24.93 -  28.42]  Anthropic just dropped a prompting guide for Opus 5.5.
Lines that repeat an earlier line are marked "(retake)"; the LAST complete take is
usually the one to use. The edit decision list (edl.json) points at chunk ids.
"""
import json
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np


def silences(clip: Path, noise: float, dur: float = 0.12):
    out = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(clip), "-vn", "-af",
         f"silencedetect=noise={noise}dB:d={dur}", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", out)]
    return starts, ends


def duration(clip: Path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)],
        capture_output=True, text=True, check=True).stdout.strip())


def speech_chunks(clip: Path, noise: float, gap: float):
    starts, ends = silences(clip, noise)
    total = duration(clip)
    # speech = complement of silences
    spans, cur = [], 0.0
    for s, e in zip(starts, ends + [total] * (len(starts) - len(ends))):
        if s > cur:
            spans.append([cur, s])
        cur = e
    if cur < total:
        spans.append([cur, total])
    spans = [x for x in spans if x[1] - x[0] > 0.12]
    merged = []
    for s in spans:
        if merged and s[0] - merged[-1][1] < gap:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return merged


def norm(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", t.lower()).strip()


def main() -> None:
    args = sys.argv[1:]
    opts = {"--noise": -38.0, "--gap": 0.25}
    for k in list(opts):
        if k in args:
            i = args.index(k)
            opts[k] = float(args[i + 1])
            del args[i:i + 2]
    fast = "--fast" in args
    args = [a for a in args if a != "--fast"]
    if len(args) < 2:
        sys.exit(__doc__)
    work = Path(args[0])
    (work / "takes").mkdir(parents=True, exist_ok=True)

    from faster_whisper import WhisperModel
    model = WhisperModel("small.en" if fast else "medium.en", device="cpu", compute_type="int8")

    for clip in map(Path, args[1:]):
        print(f"Finding every attempt in {clip.name} ...", flush=True)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-vn", "-ac", "1",
                              "-ar", "16000", "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        audio = np.frombuffer(raw, dtype=np.float32)
        chunks = []
        for s, e in speech_chunks(clip, opts["--noise"], opts["--gap"]):
            a = audio[int(max(0, s - 0.05) * 16000):int((e + 0.05) * 16000)].copy()
            segs, _ = model.transcribe(a, language="en", vad_filter=False, beam_size=5,
                                       condition_on_previous_text=False,
                                       initial_prompt="Claude, Claude Code, Anthropic, Opus 5.5.")
            text = " ".join(x.text.strip() for x in segs).strip()
            if not text or len(norm(text)) < 2:
                continue
            chunks.append({"id": f"c{len(chunks):03d}", "start": round(s, 3), "end": round(e, 3),
                           "text": text})
        # mark retakes: a chunk whose text closely matches a LATER chunk's opening
        for i, c in enumerate(chunks):
            for later in chunks[i + 1:]:
                a, b = norm(c["text"]), norm(later["text"])
                if a and SequenceMatcher(None, a, b[:len(a) + 8]).ratio() > 0.72:
                    c["retake"] = True
                    break
        stem = clip.stem
        (work / "takes" / f"{stem}.takes.json").write_text(json.dumps(
            {"clip": str(clip.resolve()), "chunks": chunks}, indent=1))
        lines = [f"{c['id']}  [{c['start']:7.2f} - {c['end']:7.2f}]  {c['text']}"
                 + ("   (retake)" if c.get("retake") else "") for c in chunks]
        (work / "takes" / f"{stem}.takes.txt").write_text("\n".join(lines) + "\n")
        print(f"  {len(chunks)} chunks -> {work / 'takes' / (stem + '.takes.txt')}")


if __name__ == "__main__":
    main()
