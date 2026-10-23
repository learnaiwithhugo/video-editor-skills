#!/usr/bin/env python3
"""Find every spoken attempt in the raw clips, with word timings, so the LAST clean take of each line is easy to pick.

Usage:
  python3 takes.py <WORK> <clip> [<clip> ...] [--model small.en|medium.en] [--prompt "names, Claude, GitHub"]
                                              [--noise -38] [--gap 0.35]

How: ffmpeg finds the silences; the speech between them becomes chunks (pauses shorter than --gap stay inside a
chunk); every chunk is transcribed on its own (so retakes don't get merged and word times don't smear over pauses).
Writes WORK/takes/<clip>.json (chunks with words) and WORK/takes/<clip>.txt:
    c012  [ 24.93 -  28.42]  Anthropic just dropped a prompting guide.   (retake of c010)
Lines that repeat an earlier line are marked; the LAST complete take is usually the one to use.
"""
import re
import subprocess
import sys
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ffprobe_duration, jdump, whisper_model  # noqa: E402


def speech_chunks(clip, noise, gap):
    err = subprocess.run(["ffmpeg", "-v", "info", "-i", str(clip), "-vn", "-af", f"silencedetect=noise={noise}dB:d=0.12",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[0-9.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    total = ffprobe_duration(clip)
    spans, cur = [], 0.0
    for i, s in enumerate(starts):
        if s > cur:
            spans.append([cur, s])
        cur = ends[i] if i < len(ends) else total
    if cur < total:
        spans.append([cur, total])
    merged = []
    for s in (x for x in spans if x[1] - x[0] > 0.15):
        if merged and s[0] - merged[-1][1] < gap:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return merged


def norm(t):
    return re.sub(r"[^a-z0-9 ]", "", t.lower()).strip()


def main():
    a = sys.argv[1:]
    opt = {"--model": "small.en", "--prompt": "", "--noise": "-38", "--gap": "0.35"}
    for k in list(opt):
        if k in a:
            i = a.index(k)
            opt[k] = a[i + 1]
            del a[i:i + 2]
    if len(a) < 2:
        sys.exit(__doc__)
    work, clips = Path(a[0]), [Path(x) for x in a[1:]]
    (work / "takes").mkdir(parents=True, exist_ok=True)
    model = whisper_model(opt["--model"])
    tmp = Path(tempfile.mkdtemp())
    for clip in clips:
        print(f"Listening to {clip.name} ...", flush=True)
        wav = tmp / "a.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
        chunks = []
        for n, (s, e) in enumerate(speech_chunks(clip, float(opt["--noise"]), float(opt["--gap"]))):
            seg = tmp / "c.wav"
            pad_s = max(0, s - 0.08)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{pad_s:.3f}", "-to", f"{e + 0.08:.3f}", "-i", str(wav), str(seg)], check=True)
            segs, _ = model.transcribe(str(seg), word_timestamps=True, language="en", vad_filter=False,
                                       initial_prompt=opt["--prompt"] or None, condition_on_previous_text=False)
            ws = [{"w": w.word.strip(), "s": round(w.start + pad_s, 3), "e": round(w.end + pad_s, 3)}
                  for sg in segs for w in (sg.words or []) if w.word.strip()]
            if not ws:
                continue
            chunks.append({"id": f"c{n:03d}", "start": round(s, 3), "end": round(e, 3),
                           "text": " ".join(w["w"] for w in ws), "words": ws})
        for i, c in enumerate(chunks):  # mark retakes: an earlier chunk that reads like this one
            for p in chunks[:i]:
                if SequenceMatcher(None, norm(p["text"]), norm(c["text"])).ratio() > 0.6:
                    c["retake_of"] = p["id"]
        jdump({"clip": str(clip), "chunks": chunks}, work / "takes" / f"{clip.stem}.json")
        lines = [f"{c['id']}  [{c['start']:7.2f} - {c['end']:7.2f}]  {c['text']}" + (f"   (retake of {c['retake_of']})" if c.get("retake_of") else "")
                 for c in chunks]
        (work / "takes" / f"{clip.stem}.txt").write_text("\n".join(lines) + "\n")
        print(f"  {len(chunks)} chunks -> {work / 'takes' / (clip.stem + '.txt')}")


if __name__ == "__main__":
    main()
