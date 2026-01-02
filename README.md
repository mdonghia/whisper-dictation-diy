# Whisper Dictation

Real-time speech-to-text dictation for macOS using OpenAI Whisper.

## Installation

Run the setup script:
```bash
~/whisper-dictation/setup_whisper_dictation.sh
```

This will:
- Configure the service to run automatically in the background
- Start the service immediately
- Set it to launch on login

## Usage

1. Press **Command+Space** to start recording
2. Speak your text
3. Press **Command+Space** again to stop
4. Text will be automatically transcribed and pasted where your cursor is!

Works anywhere: Gmail, Slack, Notes, etc.

## Files

```
~/whisper-dictation/
├── whisper_dictation.py           # Main script
├── setup_whisper_dictation.sh     # Setup/installation script
├── com.whisper.dictation.plist    # LaunchAgent configuration
├── logs/                          # Log files (visible in Finder!)
│   ├── dictation.log             # Main activity log
│   ├── stdout.log                # Standard output
│   └── stderr.log                # Error messages
└── README.md                      # This file
```

## Logs

### View in Finder
```bash
open ~/whisper-dictation/logs
```

### View in Terminal
```bash
# Watch live activity
tail -f ~/whisper-dictation/logs/dictation.log

# View all logs
cat ~/whisper-dictation/logs/dictation.log
```

## Service Management

```bash
# Stop the service
launchctl unload ~/Library/LaunchAgents/com.whisper.dictation.plist

# Start the service
launchctl load ~/Library/LaunchAgents/com.whisper.dictation.plist

# Check if running
launchctl list | grep whisper
```

## Permissions

On first run, macOS will ask for:
- **Microphone access** - Required to record your voice
- **Accessibility access** - Required to auto-paste text

Grant these in: **System Settings > Privacy & Security**

## Troubleshooting

If dictation isn't working:

1. Check if the service is running:
   ```bash
   launchctl list | grep whisper
   ```

2. View the logs:
   ```bash
   tail -f ~/whisper-dictation/logs/dictation.log
   ```

3. Restart the service:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.whisper.dictation.plist
   launchctl load ~/Library/LaunchAgents/com.whisper.dictation.plist
   ```

## Model Options

The script uses the "base" Whisper model by default. You can change this in [whisper_dictation.py:106](whisper_dictation.py#L106):

- `tiny` - Fastest, least accurate
- `base` - Good balance (default)
- `small` - Better accuracy, slower
- `medium` - Great accuracy, much slower
- `large` - Best accuracy, very slow

## Uninstall

```bash
# Stop and remove the service
launchctl unload ~/Library/LaunchAgents/com.whisper.dictation.plist
rm ~/Library/LaunchAgents/com.whisper.dictation.plist

# Remove all files
rm -rf ~/whisper-dictation
```
