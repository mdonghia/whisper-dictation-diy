#!/usr/bin/env python3
"""
Whisper Dictation - Real-time speech-to-text with hotkey activation
Press Command+Space to start/stop recording and transcribe speech
Runs as a background service without terminal window
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
from faster_whisper import WhisperModel
import pyperclip
from pynput import keyboard
import tempfile
import os
import threading
import time
import sys
import logging
from pathlib import Path

class WhisperDictation:
    def __init__(self, model_size="base"):
        # Set up logging - logs are in ~/whisper-dictation/logs (visible in Finder!)
        log_dir = Path.home() / "whisper-dictation" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = log_dir / "dictation.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )

        logging.info("Loading Whisper model... (this may take a moment)")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logging.info(f"✓ Whisper {model_size} model loaded!")

        self.is_recording = False
        self.audio_data = []
        self.sample_rate = 16000
        self.recording_thread = None

    def record_audio(self):
        """Record audio from microphone"""
        logging.info("🎤 Recording... (Press Command+Space again to stop)")

        def callback(indata, frames, time, status):
            if status:
                logging.warning(status)
            self.audio_data.append(indata.copy())

        with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=callback):
            while self.is_recording:
                sd.sleep(100)

    def transcribe(self):
        """Transcribe recorded audio"""
        if not self.audio_data:
            logging.warning("⚠️  No audio recorded")
            return

        logging.info("✍️  Transcribing...")

        # Combine audio chunks
        audio = np.concatenate(self.audio_data, axis=0)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_filename = tmp_file.name
            sf.write(tmp_filename, audio, self.sample_rate)

        try:
            # Transcribe
            segments, info = self.model.transcribe(tmp_filename, beam_size=5)

            # Collect all text
            text = " ".join([segment.text.strip() for segment in segments])

            if text:
                # Copy to clipboard
                pyperclip.copy(text)
                logging.info(f"✓ Transcribed: {text}")
                logging.info("📋 Text copied to clipboard! Paste with Command+V")

                # Auto-paste using keyboard controller
                controller = keyboard.Controller()
                time.sleep(0.1)  # Brief delay
                with controller.pressed(keyboard.Key.cmd):
                    controller.press('v')
                    controller.release('v')
                logging.info("✓ Text pasted!")
            else:
                logging.warning("⚠️  No speech detected")

        finally:
            # Clean up temp file
            os.unlink(tmp_filename)

    def toggle_recording(self):
        """Start or stop recording"""
        if not self.is_recording:
            # Start recording
            self.audio_data = []
            self.is_recording = True
            self.recording_thread = threading.Thread(target=self.record_audio)
            self.recording_thread.start()
        else:
            # Stop recording
            self.is_recording = False
            if self.recording_thread:
                self.recording_thread.join()
            self.transcribe()

def main():
    logging.info("=" * 60)
    logging.info("Whisper Dictation - Real-time Speech-to-Text")
    logging.info("=" * 60)
    logging.info("\nInitializing...")

    dictation = WhisperDictation(model_size="base")

    logging.info("\n" + "=" * 60)
    logging.info("Ready! Press Command+Space to start/stop dictation")
    logging.info(f"Logs are being written to: {dictation.log_file}")
    logging.info("=" * 60 + "\n")

    # Set up hotkey listener
    def on_activate():
        dictation.toggle_recording()

    # Command+Space hotkey
    with keyboard.GlobalHotKeys({
        '<cmd>+<space>': on_activate
    }) as h:
        h.join()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("\n\n👋 Goodbye!")
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
