#!/bin/bash
# Restart the Whisper Dictation menu bar app
# This script kills any running instance and starts a fresh one.

pkill -f whisper_menubar.py 2>/dev/null
sleep 2
cd /Users/mdonghia/whisper-dictation
nohup /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 whisper_menubar.py >/dev/null 2>&1 &
