"""progress/ pictures: every step drops a numbered image into WORK/progress/ so the user can follow along."""
import re
from pathlib import Path


def progress_path(work, name):
    d = Path(work) / "progress"
    d.mkdir(parents=True, exist_ok=True)
    nums = [int(m.group(1)) for p in d.iterdir() if (m := re.match(r"(\d+)-", p.name))]
    return d / f"{(max(nums) + 1) if nums else 1:02d}-{name}"
