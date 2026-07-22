#!/bin/bash
cd "/Users/mdonghia/whisper-dictation"
echo "Whisper Dictation is starting. Keep this window open (you can minimize it)."
echo "Press Command+Space anywhere to dictate."
exec /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 whisper_menubar.py
