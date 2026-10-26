#!/bin/bash
# Installs (or updates) the four video editing skills into Claude Code's global skills folder.
# Safe to run again: an older copy is moved to a backup folder, never deleted. Where you saved your
# style and your edits (each skill's config.json) is carried over to the new copy. Your style folder,
# your videos, and ~/.claude-video-editor (the older skills' settings and sounds) are never touched.
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
SKILLS="$HOME/.claude/skills"
STAMP="$(date +%Y-%m-%d-%H%M%S)"
BACKUP="$HOME/.claude/skills-backup/$STAMP"

mkdir -p "$SKILLS"
# stylelab used to be called build-my-style. Retire the old copy (to the backup, never deleted) and
# keep where its style folder lives.
if [ -e "$SKILLS/build-my-style" ]; then
  mkdir -p "$BACKUP"
  mv "$SKILLS/build-my-style" "$BACKUP/build-my-style"
  echo "  build-my-style is now called stylelab: moved the old copy to ~/.claude/skills-backup/$STAMP/"
  if [ -f "$BACKUP/build-my-style/config.json" ] && [ ! -e "$SKILLS/stylelab" ]; then
    mkdir -p "$BACKUP/stylelab"
    cp "$BACKUP/build-my-style/config.json" "$BACKUP/stylelab/config.json"
  fi
fi
for skill in stylelab edit-my-video kallaway-edit new-edit-style; do
  if [ -e "$SKILLS/$skill" ]; then
    mkdir -p "$BACKUP"
    mv "$SKILLS/$skill" "$BACKUP/$skill"
    echo "  moved your old $skill to ~/.claude/skills-backup/$STAMP/"
  fi
  cp -R "$HERE/skills/$skill" "$SKILLS/$skill"
  find "$SKILLS/$skill" \( -name "__pycache__" -o -name ".DS_Store" \) -prune -exec rm -rf {} +
  if [ -f "$BACKUP/$skill/config.json" ]; then
    cp "$BACKUP/$skill/config.json" "$SKILLS/$skill/config.json"
    echo "  kept your saved folders for $skill"
  fi
  echo "  installed $skill"
done

echo ""
echo "Done. Start a new Claude Code session, then type /stylelab"
echo "to make your own editing style. When it's done, type /edit-my-video to edit your clips in it."
echo "(Each one checks your Mac on first run and tells you if anything is missing.)"
