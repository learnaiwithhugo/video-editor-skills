#!/usr/bin/env python3
"""Transcribe raw clips with word timestamps (free, local, faster-whisper).

Usage:
  PY scripts/transcribe.py <work_dir> <clip> [<clip> ...] [--model small.en]

Writes, per clip, into <work_dir>/transcripts/:
  <clip-stem>.words.json   every word: {"w", "start", "end", "p"}   (seconds in the RAW clip)
  <clip-stem>.txt          one line per spoken phrase with its time range, for picking takes

Options: --model medium.en (slower, more accurate), --range 20-40 (only that
stretch, to double-check a take; times stay in raw-clip seconds), --no-vad
(keeps every false start, handy when a take is missing from the transcript).

Audio is decoded with ffmpeg (not PyAV), so the PyAV-version problem some
faster-whisper installs hit never comes up.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


def decode(path: Path) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
           "-f", "f32le", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def main() -> None:
    args = sys.argv[1:]
    model_name = "small.en"
    rng = None
    if "--range" in args:  # re-check one stretch: --range 20-40 (seconds)
        i = args.index("--range")
        rng = tuple(float(x) for x in args[i + 1].split("-"))
        del args[i:i + 2]
    use_vad = "--no-vad" not in args
    args = [a for a in args if a != "--no-vad"]
    if "--model" in args:
        i = args.index("--model")
        model_name = args[i + 1]
        del args[i:i + 2]
    if len(args) < 2:
        sys.exit(__doc__)
    work = Path(args[0])
    out = work / "transcripts"
    out.mkdir(parents=True, exist_ok=True)

    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    for clip in map(Path, args[1:]):
        print(f"Listening to {clip.name} ...", flush=True)
        audio = decode(clip)
        offset = 0.0
        if rng:
            offset = rng[0]
            audio = audio[int(rng[0] * 16000):int(rng[1] * 16000)]
        segs, _info = model.transcribe(
            audio, language="en", word_timestamps=True, vad_filter=use_vad,
            vad_parameters={"min_silence_duration_ms": 300},
            condition_on_previous_text=False, beam_size=5,
            # Helps Whisper spell the words creators actually say.
            initial_prompt="Claude, Claude Code, Anthropic, Opus, Sonnet, ChatGPT, prompt.",
        )
        words, lines = [], []
        for s in segs:
            seg_words = []
            for w in s.words or []:
                t = w.word.strip()
                if not t:
                    continue
                rec = {"w": t, "start": round(w.start + offset, 3), "end": round(w.end + offset, 3),
                       "p": round(w.probability, 3)}
                words.append(rec)
                seg_words.append(rec)
            if seg_words:
                first = len(words) - len(seg_words)
                lines.append(f"[{seg_words[0]['start']:7.2f} - {seg_words[-1]['end']:7.2f}] "
                             f"(w{first}-w{len(words) - 1}) "
                             + " ".join(x["w"] for x in seg_words))
        stem = clip.stem + (f".{rng[0]:g}-{rng[1]:g}" if rng else "")
        (out / f"{stem}.words.json").write_text(json.dumps(words, indent=1))
        (out / f"{stem}.txt").write_text("\n".join(lines) + "\n")
        print(f"  {len(words)} words -> {out / (stem + '.txt')}")


if __name__ == "__main__":
    main()
