#!/usr/bin/env python3
"""
Whisper Dictation - Real-time speech-to-text with hotkey activation
Press Command+Space to start/stop recording and transcribe speech

Supports two modes:
- "api" (default): Uses OpenAI Whisper API - faster, more accurate, requires internet
- "local": Uses local faster-whisper model - free, offline, slower
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
import pyperclip
from pynput import keyboard
import tempfile
import os
import threading
import time
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from script directory
load_dotenv(Path(__file__).parent / ".env")

# ============================================================================
# CONFIGURATION - Change these settings as needed
# ============================================================================
MODE = "api"  # "api" for OpenAI API (faster), "local" for offline (slower)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LOCAL_MODEL_SIZE = "small"  # For local mode: tiny, base, small, medium, large
# ============================================================================


class WhisperDictation:
    def __init__(self, mode="api"):
        # Set up logging
        log_dir = Path.home() / "Documents" / "all_tools" / "whisper-dictation" / "logs"
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

        self.mode = mode
        self.model = None
        self.client = None

        if mode == "api":
            self._init_api()
        else:
            self._init_local()

        self.is_recording = False
        self.audio_data = []
        self.sample_rate = 16000
        self.recording_thread = None

    def _init_api(self):
        """Initialize OpenAI API client"""
        from openai import OpenAI

        api_key = OPENAI_API_KEY
        if not api_key:
            logging.error("No OpenAI API key found! Set OPENAI_API_KEY environment variable or edit the script.")
            logging.info("Falling back to local mode...")
            self.mode = "local"
            self._init_local()
            return

        logging.info("Using OpenAI Whisper API (fast mode)")
        self.client = OpenAI(api_key=api_key)
        logging.info("✓ OpenAI client ready!")

    def _init_local(self):
        """Initialize local faster-whisper model"""
        from faster_whisper import WhisperModel

        logging.info(f"Loading local Whisper {LOCAL_MODEL_SIZE} model... (this may take a moment)")
        self.model = WhisperModel(LOCAL_MODEL_SIZE, device="cpu", compute_type="int8")
        logging.info(f"✓ Local Whisper {LOCAL_MODEL_SIZE} model loaded!")

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
        start_time = time.time()

        # Combine audio chunks
        audio = np.concatenate(self.audio_data, axis=0)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_filename = tmp_file.name
            sf.write(tmp_filename, audio, self.sample_rate)

        try:
            if self.mode == "api":
                text = self._transcribe_api(tmp_filename)
            else:
                text = self._transcribe_local(tmp_filename)

            elapsed = time.time() - start_time

            if text:
                # Copy to clipboard
                pyperclip.copy(text)
                logging.info(f"✓ Transcribed in {elapsed:.1f}s: {text}")

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

    def _transcribe_api(self, audio_file):
        """Transcribe using OpenAI Whisper API"""
        try:
            with open(audio_file, "rb") as f:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="en"
                )
            return response.text.strip()
        except Exception as e:
            logging.error(f"API error: {e}")
            return None

    def _transcribe_local(self, audio_file):
        """Transcribe using local faster-whisper model"""
        segments, info = self.model.transcribe(
            audio_file,
            language="en",
            beam_size=5,
            temperature=0.0,
            vad_filter=True,
            vad_parameters=dict(
                threshold=0.5,
                min_speech_duration_ms=250,
                min_silence_duration_ms=2000,
                speech_pad_ms=400
            ),
            condition_on_previous_text=False,
            word_timestamps=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0
        )
        return " ".join([segment.text.strip() for segment in segments])

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

    dictation = WhisperDictation(mode=MODE)

    logging.info("\n" + "=" * 60)
    logging.info(f"Mode: {'OpenAI API (fast)' if dictation.mode == 'api' else 'Local (offline)'}")
    logging.info("Ready! Press Command+Space to start/stop dictation")
    logging.info(f"Logs: {dictation.log_file}")
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
