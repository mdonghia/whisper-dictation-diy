# Whisper Dictation

Real-time speech-to-text dictation for macOS using OpenAI Whisper.

## How It Works

Press **Command+Space** to start recording, speak, press **Command+Space** again to stop. Text is automatically transcribed and pasted at your cursor.

Works anywhere: Gmail, Slack, Notes, VS Code, etc.

## Important: How the Service Runs

**This service must run in a Terminal window** (not as a background LaunchAgent). This is required because:
- macOS microphone permissions only work properly in a Terminal context
- LaunchAgents run without a GUI session and can't access the microphone reliably

The service starts via **Login Items** using `start_whisper.command`. A Terminal window will open at login - you can minimize it but don't close it.

## Files

```
whisper-dictation/
├── whisper_dictation.py      # Main script
├── start_whisper.command     # Startup script (runs at login via Login Items)
├── logs/                     # Log files
│   └── dictation.log         # Activity log
└── README.md                 # This file
```

## Setup

The service should already be configured to run at login. If not:

1. Open **System Settings > General > Login Items**
2. Click **+** and add `start_whisper.command` from this folder

To start manually:
```bash
open ~/Documents/all_tools/whisper-dictation/start_whisper.command
```

## Permissions Required

Both of these must be enabled in **System Settings > Privacy & Security**:

- **Microphone** - Terminal needs microphone access
- **Accessibility** - Python needs accessibility access (for the hotkey and auto-paste)

If dictation stops working after a system update, check these permissions.

## Logs

```bash
# Watch live activity
tail -f ~/Documents/all_tools/whisper-dictation/logs/dictation.log

# Open logs folder
open ~/Documents/all_tools/whisper-dictation/logs
```

## Troubleshooting

**Hotkey not responding:**
- Check that Python has Accessibility permission
- Make sure the Terminal window is still running

**"No speech detected" every time:**
- Check that Terminal has Microphone permission
- Toggle the permission off and on, then restart the script

**Service not starting at login:**
- Verify `start_whisper.command` is in Login Items

## Model Options

Edit `whisper_dictation.py` to change the Whisper model (line 157):

- `tiny` - Fastest, least accurate
- `small` - Good balance (current default)
- `medium` - Better accuracy, slower
- `large` - Best accuracy, very slow

## Stopping the Service

Close the Terminal window running the script, or press Ctrl+C in that window.
