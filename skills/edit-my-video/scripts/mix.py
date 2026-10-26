#!/usr/bin/env python3
"""Mix the voice with the style's sound effects (at the levels in sfx.json) and optional music, at ~-16 LUFS.

Usage:
  python3 mix.py <WORK>

Reads WORK/cues.json:
  {"cues": [{"t": 3.27, "sfx": "cut"}, {"t": 0.9, "sfx": "hero", "db": -2, "why": "FREE lands"}, ...],
   "music": {"file": "/path/the user named.mp3", "db": -20}}        <- only if the user named a track
  sfx = a role from the file name ("cut", "blur", "shine", "tick", "panel", "icon", "line", "hero"...), a file name,
  or a need number. "db" nudges that one cue relative to its locked level (keep it at 0 unless it pokes out).
  t = the moment the sound should HIT (the file's own hit point is lined up to it).

Writes WORK/hf/assets/mix.wav (what the video plays), WORK/audio/sfx-only.wav, and prints the loudness report.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ffprobe_duration, jload, loudness  # noqa: E402


def find(sfx, key):
    key = str(key)
    for s in sfx:
        if key in (s["role"], s["file"], str(s.get("need")), Path(s["file"]).stem):
            return s
    for s in sfx:
        if key.lower() in (s["name"] + " " + s["file"]).lower():
            return s
    sys.exit(f"No picked sound effect matches '{key}'. Picked: " + ", ".join(f"{s['role']} ({s['file']})" for s in sfx))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    work = Path(sys.argv[1]).resolve()
    tok = jload(work / "style.json")
    sfx = tok["sfx"]
    spec = jload(work / "cues.json") if (work / "cues.json").exists() else {"cues": []}
    cues = spec["cues"] if isinstance(spec, dict) else spec
    music = spec.get("music") if isinstance(spec, dict) else None
    voice = work / "audio" / "voice.wav"
    dur = ffprobe_duration(voice)
    inputs, fx, labels = ["-i", str(voice)], [], []
    for i, c in enumerate(sorted(cues, key=lambda c: c["t"])):
        s = find(sfx, c["sfx"])
        start = max(0.0, float(c["t"]) - float(s.get("hit_s") or 0))
        inputs += ["-i", s["path"]]
        fx.append(f"[{i + 1}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={s['mix_db'] + c.get('db', 0)}dB,"
                  f"adelay={int(start * 1000)}:all=1[s{i}]")
        labels.append(f"[s{i}]")
        print(f"  {c['t']:6.2f}s  {s['role']:6} {s['file']:32} {s['mix_db'] + c.get('db', 0):+.0f} dB  {c.get('why', '')}")
    n = len(labels)
    if n:
        fx.append(("".join(labels) + f"amix=inputs={n}:normalize=0:duration=longest," if n > 1 else labels[0])
                  + f"apad=whole_dur={dur:.4f},atrim=0:{dur:.4f}[fx]")
    fl = ["[0:a]aformat=sample_rates=48000:channel_layouts=stereo[v0]"] + fx
    parts = ["[v0]"] + (["[fx]"] if n else [])
    if music and music.get("file"):
        k = n + 1
        inputs += ["-stream_loop", "-1", "-i", music["file"]]
        fl[0] = "[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[v0][vk]"
        fl.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{dur:.4f},volume={music.get('db', -20)}dB,"
                  f"afade=t=out:st={max(0, dur - 1.2):.3f}:d=1.2[mu]")
        fl.append("[mu][vk]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[bed]")
        parts.append("[bed]")
    fl.append("".join(parts) + f"amix=inputs={len(parts)}:normalize=0:duration=first,alimiter=limit=0.84:level=false[m]"
              if len(parts) > 1 else "[v0]anull[m]")
    out = work / "hf" / "assets" / "mix.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fl), "-map", "[m]", "-ar", "48000",
                    "-c:a", "pcm_s16le", str(out)], check=True)
    if n:
        fo = work / "audio" / "sfx-only.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs[:2 * (n + 1)], "-filter_complex", ";".join(fx), "-map", "[fx]",
                        "-ar", "48000", str(fo)], check=True)
        fx_lufs, fx_tp = loudness(fo)
    lufs, tp = loudness(out)
    if lufs is not None and abs(lufs + 16) > 0.3:  # land the whole mix on -16 LUFS, peaks held under -1.5 dBTP
        tmp = out.with_suffix(".pre.wav")
        out.rename(tmp)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af", f"volume={-16 - lufs:.2f}dB,alimiter=limit=0.84:level=false",
                        "-ar", "48000", "-c:a", "pcm_s16le", str(out)], check=True)
        tmp.unlink()
        lufs, tp = loudness(out)
    v_lufs, _ = loudness(voice)
    print(f"\nMix: {lufs} LUFS (target -16), true peak {tp} dBTP -> {out}")
    if n:
        print(f"Sound effects alone: {fx_lufs} LUFS, {round(v_lufs - fx_lufs, 1) if fx_lufs is not None else '?'} LU under the voice "
              f"(set from the feel they picked in StyleLab; if they say louder or quieter, change its db)")
    if lufs is not None and abs(lufs + 16) > 1.0:
        print("WARNING: mix is more than 1 LU off -16 LUFS; check the voice (cut.py normalises it).")


if __name__ == "__main__":
    main()
