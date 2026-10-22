"""Where the editor keeps the user's things: their settings, its own Python packages, the sound
effects and caches.

Never inside the skill folder. When the editor is installed as a Claude Code plugin, every update
replaces the plugin folder with the new version, so anything written there would be wiped. The data
folder is, first match wins:

  1. $VIDEO_EDITOR_DATA            the skill passes Claude Code's ${CLAUDE_PLUGIN_DATA} here
  2. <skill>/data-dir.txt          style skills made by /new-edit-style point at the shared folder
  3. an installed plugin's own data folder, <config>/plugins/data/<plugin>-<marketplace>/
                                   (the same folder ${CLAUDE_PLUGIN_DATA} names)
  4. ~/.claude-video-editor/       anything else (a copy of the skill run on its own)

Inside it:
  config.json   the user's folders and choices (no secrets, ever)
  venv/         the editor's own Python: faster-whisper, numpy, pillow
  sfx/          the recorded sound effects (fetched at setup, never shipped)
  fonts/        free Google Fonts downloaded by the font matcher
"""
import json
import os
import re
from pathlib import Path

PIN = "0.8.185"  # the HyperFrames version this editor is built and tested against
SK = Path(__file__).resolve().parent.parent  # this skill's folder (read-only: updates replace it)
HF_ENV = dict(os.environ, HYPERFRAMES_SKIP_SKILLS="1", HYPERFRAMES_NO_TELEMETRY="1")


def _plugin_data_dir():
    """<config>/plugins/cache/<marketplace>/<plugin>/<version>/... -> <config>/plugins/data/<id>/"""
    parts = SK.parts
    for i in range(len(parts) - 3, 0, -1):
        if parts[i] == "cache" and parts[i - 1] == "plugins":
            plugin_id = re.sub(r"[^A-Za-z0-9_-]", "-", f"{parts[i + 2]}@{parts[i + 1]}")
            return Path(*parts[:i]) / "data" / plugin_id
    return None


def data_dir() -> Path:
    env = os.environ.get("VIDEO_EDITOR_DATA", "").strip()
    pointer = SK / "data-dir.txt"
    if env and "${" not in env:  # an unsubstituted ${CLAUDE_PLUGIN_DATA} means "not set"
        d = Path(env).expanduser()
    elif pointer.exists() and pointer.read_text().strip():
        d = Path(pointer.read_text().strip()).expanduser()
    else:
        d = _plugin_data_dir() or Path.home() / ".claude-video-editor"
    d.mkdir(parents=True, exist_ok=True)
    return d


DATA = data_dir()
CONFIG = DATA / "config.json"
VENV = DATA / "venv"
PY = VENV / "bin" / "python"
SFX = DATA / "sfx"
FONTS = DATA / "fonts"


def load_config() -> dict:
    try:
        return json.loads(CONFIG.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def save_config(**changes) -> dict:
    cfg = load_config()
    cfg.update({k: v for k, v in changes.items() if v is not None})
    CONFIG.write_text(json.dumps(cfg, indent=1))
    return cfg
