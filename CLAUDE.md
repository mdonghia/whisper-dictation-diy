# Whisper Dictation Service - Project Instructions

## Service Management

- **Auto-restart after changes:** Automatically restart the whisper-dictation LaunchAgent service after making any changes to `whisper_dictation.py`.
- **How to restart:** `launchctl unload/load ~/Library/LaunchAgents/com.whisper.dictation.plist` (a `restart_whisper.sh` helper also exists in this folder).
