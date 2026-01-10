#!/usr/bin/env python3
"""
Whisper Dictation - Menu Bar App
Runs in the background with a menu bar icon. No Terminal window needed.

Status icons:
- 🎙 Ready (idle)
- 🔴 Recording
- ⏳ Transcribing
"""

import AppKit
info = AppKit.NSBundle.mainBundle().infoDictionary()
info["LSBackgroundOnly"] = "1"

import rumps
import sounddevice as sd
import soundfile as sf
import numpy as np
import pyperclip
from pynput import keyboard
import tempfile
import os
import threading
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from script directory
load_dotenv(Path(__file__).parent / ".env")

# ============================================================================
# CONFIGURATION
# ============================================================================
MODE = "api"  # "api" for OpenAI API (faster), "local" for offline (slower)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LOCAL_MODEL_SIZE = "small"  # For local mode: tiny, base, small, medium, large
# ============================================================================

# Set up logging
log_dir = Path.home() / "Documents" / "all_tools" / "whisper-dictation" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "dictation.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)


class WhisperMenuBar(rumps.App):
    def __init__(self):
        super(WhisperMenuBar, self).__init__("🎙", quit_button=None)

        self.mode = MODE
        self.model = None
        self.client = None

        # Initialize API or local model
        if self.mode == "api":
            self._init_api()
        else:
            self._init_local()

        self.is_recording = False
        self.audio_data = []
        self.sample_rate = 16000
        self.recording_thread = None

        # Menu items
        self.menu = [
            rumps.MenuItem(f"Mode: {'OpenAI API' if self.mode == 'api' else 'Local'}", callback=None),
            rumps.MenuItem("Hotkeys: Cmd+Space (toggle) or Hold Right Option", callback=None),
            None,  # Separator
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]

        # Start combined keyboard listener in background thread
        self.keyboard_thread = threading.Thread(target=self._run_keyboard_listener, daemon=True)
        self.keyboard_thread.start()

        logging.info("Whisper Dictation menu bar app started")
        logging.info(f"Mode: {'OpenAI API' if self.mode == 'api' else 'Local'}")
        logging.info("Press Cmd+Space to toggle, or hold Right Option to record")

    def _init_api(self):
        """Initialize OpenAI API client"""
        from openai import OpenAI

        if not OPENAI_API_KEY:
            logging.error("No OpenAI API key found! Falling back to local mode.")
            self.mode = "local"
            self._init_local()
            return

        self.client = OpenAI(api_key=OPENAI_API_KEY)
        logging.info("OpenAI API client ready")

    def _init_local(self):
        """Initialize local faster-whisper model"""
        from faster_whisper import WhisperModel

        logging.info(f"Loading local Whisper {LOCAL_MODEL_SIZE} model...")
        self.model = WhisperModel(LOCAL_MODEL_SIZE, device="cpu", compute_type="int8")
        logging.info("Local model loaded")

    def _run_keyboard_listener(self):
        """Run combined keyboard listener for both hotkey and hold-to-record"""
        self.right_option_held = False
        self.cmd_held = False

        def on_press(key):
            # Track modifier states
            if key == keyboard.Key.cmd:
                self.cmd_held = True

            # Right Option hold-to-record
            if key == keyboard.Key.alt_r and not self.right_option_held and not self.is_recording:
                self.right_option_held = True
                self.start_recording()

            # Cmd+Space toggle
            if key == keyboard.Key.space and self.cmd_held:
                self.toggle_recording()

        def on_release(key):
            # Track modifier states
            if key == keyboard.Key.cmd:
                self.cmd_held = False

            # Right Option release
            if key == keyboard.Key.alt_r and self.right_option_held:
                self.right_option_held = False
                if self.is_recording:
                    self.stop_recording()

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

    def start_recording(self):
        """Start recording"""
        if self.is_recording:
            return
        self.audio_data = []
        self.is_recording = True
        self.title = "🔴"
        self.recording_thread = threading.Thread(target=self._record_audio)
        self.recording_thread.start()
        logging.info("Recording started")

    def stop_recording(self):
        """Stop recording and transcribe"""
        if not self.is_recording:
            return
        self.is_recording = False
        self.title = "⏳"
        if self.recording_thread:
            self.recording_thread.join()
        threading.Thread(target=self._transcribe).start()

    def toggle_recording(self):
        """Start or stop recording"""
        if not self.is_recording:
            self.audio_data = []
            self.is_recording = True
            self.title = "🔴"
            self.recording_thread = threading.Thread(target=self._record_audio)
            self.recording_thread.start()
            logging.info("Recording started")
        else:
            self.is_recording = False
            self.title = "⏳"
            if self.recording_thread:
                self.recording_thread.join()
            threading.Thread(target=self._transcribe).start()

    def _record_audio(self):
        """Record audio from microphone"""
        def callback(indata, frames, time_info, status):
            if status:
                logging.warning(status)
            self.audio_data.append(indata.copy())

        with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=callback):
            while self.is_recording:
                sd.sleep(100)

    def _transcribe(self):
        """Transcribe recorded audio"""
        if not self.audio_data:
            logging.warning("No audio recorded")
            self.title = "🎙"
            return

        logging.info("Transcribing...")
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
                pyperclip.copy(text)
                logging.info(f"Transcribed in {elapsed:.1f}s: {text}")

                # Auto-paste
                controller = keyboard.Controller()
                time.sleep(0.1)
                with controller.pressed(keyboard.Key.cmd):
                    controller.press('v')
                    controller.release('v')
            else:
                logging.warning("No speech detected")

        finally:
            os.unlink(tmp_filename)
            self.title = "🎙"

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
            condition_on_previous_text=False,
            word_timestamps=False,
        )
        return " ".join([segment.text.strip() for segment in segments])

    def quit_app(self, _):
        """Quit the application"""
        logging.info("Whisper Dictation stopped")
        rumps.quit_application()


if __name__ == "__main__":
    WhisperMenuBar().run()
