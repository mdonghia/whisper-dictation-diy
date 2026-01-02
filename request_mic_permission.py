#!/usr/bin/env python3
"""
Quick script to trigger microphone permission request for Python.app
"""
import sounddevice as sd
import time

print("Requesting microphone access...")
print("Please click 'Allow' when the permission popup appears!")
time.sleep(1)

try:
    # This will trigger the microphone permission request
    devices = sd.query_devices()
    print("\nMicrophone access granted!")
    print("You can now close this window.")
    time.sleep(2)
except Exception as e:
    print(f"Error: {e}")
    time.sleep(5)
