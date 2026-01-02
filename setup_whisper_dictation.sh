#!/bin/bash

echo "=============================================="
echo "Whisper Dictation Setup"
echo "=============================================="
echo ""

# Create log directory
echo "Creating log directory..."
mkdir -p ~/whisper-dictation/logs

# Fix LaunchAgents directory ownership if needed
echo "Checking LaunchAgents directory permissions..."
if [ ! -w "$HOME/Library/LaunchAgents" ]; then
    echo "Fixing LaunchAgents directory ownership (requires password)..."
    sudo chown $USER "$HOME/Library/LaunchAgents"
fi

# Copy plist file
echo "Installing LaunchAgent..."
cp ~/whisper-dictation/com.whisper.dictation.plist ~/Library/LaunchAgents/

# Load the service
echo "Loading the service..."
launchctl unload ~/Library/LaunchAgents/com.whisper.dictation.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.whisper.dictation.plist

echo ""
echo "=============================================="
echo "✓ Setup Complete!"
echo "=============================================="
echo ""
echo "The Whisper Dictation service is now running in the background!"
echo ""
echo "Usage:"
echo "  1. Press Command+Space to start recording"
echo "  2. Speak your text"
echo "  3. Press Command+Space again to stop"
echo "  4. Text will be automatically transcribed and pasted!"
echo ""
echo "Logs are saved to: ~/whisper-dictation/logs/"
echo "You can view them in Finder or Terminal!"
echo ""
echo "Commands:"
echo "  Stop the service:  launchctl unload ~/Library/LaunchAgents/com.whisper.dictation.plist"
echo "  Start the service: launchctl load ~/Library/LaunchAgents/com.whisper.dictation.plist"
echo "  View logs:         tail -f ~/whisper-dictation/logs/dictation.log"
echo "  Open in Finder:    open ~/whisper-dictation/logs"
echo ""
echo "⚠️  Important: Grant Accessibility and Microphone permissions when prompted!"
echo ""
