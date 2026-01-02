#!/bin/bash
# This script will launch Python.app visibly to trigger microphone permission

osascript -e 'tell application "Terminal" to do script "/Library/Frameworks/Python.framework/Versions/3.13/Resources/Python.app/Contents/MacOS/Python -c \"import sounddevice as sd; print(sd.query_devices()); import time; time.sleep(3)\""'
