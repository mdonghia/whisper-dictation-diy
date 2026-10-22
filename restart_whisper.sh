#!/bin/bash
# Restart the Whisper Dictation menu bar app (single instance via LaunchAgent).
set -euo pipefail
UID_NUM=$(id -u)
LABEL=gui/${UID_NUM}/com.whisper.dictation
PLIST="$HOME/Library/LaunchAgents/com.whisper.dictation.plist"

launchctl bootout "$LABEL" 2>/dev/null || true
pkill -9 -f 'whisper_menubar.py' 2>/dev/null || true
pkill -9 -f 'Whisper Dictation' 2>/dev/null || true
sleep 1
launchctl bootstrap "gui/${UID_NUM}" "$PLIST"
echo "Whisper Dictation restarted (one menu-bar instance)."
