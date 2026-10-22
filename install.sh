#!/bin/bash
# Installs (or updates) the two video editing skills into Claude Code's global skills folder.
# Safe to run again: an older copy is moved to a backup folder, never deleted, and your settings,
# tools and sound effects live in ~/.claude-video-editor, which this never touches.
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
SKILLS="$HOME/.claude/skills"
STAMP="$(date +%Y-%m-%d-%H%M%S)"

mkdir -p "$SKILLS"
for skill in kallaway-edit new-edit-style; do
  if [ -e "$SKILLS/$skill" ]; then
    mkdir -p "$HOME/.claude/skills-backup/$STAMP"
    mv "$SKILLS/$skill" "$HOME/.claude/skills-backup/$STAMP/$skill"
    echo "  moved your old $skill to ~/.claude/skills-backup/$STAMP/"
  fi
  cp -R "$HERE/skills/$skill" "$SKILLS/$skill"
  find "$SKILLS/$skill" -name "__pycache__" -type d -prune -exec rm -rf {} +
  echo "  installed $skill"
done

echo ""
echo "Done. Start a new Claude Code session, then type /kallaway-edit"
echo "(the first run walks you through a short setup)."
