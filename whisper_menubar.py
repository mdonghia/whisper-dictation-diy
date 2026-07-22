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
MODE = "local"  # "local" runs on this Mac's GPU (fast, offline); "api" uses OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")  # kept as automatic fallback
LOCAL_MODEL_REPO = "mlx-community/whisper-large-v3-turbo"
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


def request_permissions():
    """Ask macOS for the permissions this app needs, so the standard
    system popups appear (instead of silently recording nothing).
    Safe to run every launch — only prompts when not yet granted."""
    import ctypes

    # Input Monitoring — needed to hear the Cmd+Space hotkey
    try:
        iokit = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
        kIOHIDRequestTypeListenEvent = 1
        if iokit.IOHIDCheckAccess(kIOHIDRequestTypeListenEvent) != 0:
            logging.warning("Input Monitoring not granted yet — requesting")
            iokit.IOHIDRequestAccess(kIOHIDRequestTypeListenEvent)
    except Exception as e:
        logging.warning(f"Input Monitoring check failed: {e}")

    # Accessibility — needed to auto-paste the text with Cmd+V
    try:
        from HIServices import (
            AXIsProcessTrusted,
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )
        if not AXIsProcessTrusted():
            logging.warning("Accessibility not granted yet — requesting")
            AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
    except Exception as e:
        logging.warning(f"Accessibility check failed: {e}")

    # Microphone — a short throwaway recording triggers the popup if needed
    try:
        test = sd.rec(int(0.3 * 16000), samplerate=16000, channels=1, dtype="float32")
        sd.wait()
        peak = float(np.abs(test).max())
        if peak > 0.0:
            logging.info(f"Mic check OK (peak={peak:.6f})")
        else:
            logging.warning("Mic check SILENT — Microphone access not granted")
    except Exception as e:
        logging.warning(f"Mic check failed: {e}")


class WhisperMenuBar(rumps.App):
    def __init__(self):
        super(WhisperMenuBar, self).__init__("🎙", quit_button=None)

        request_permissions()

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

        # Exercise the model every 5 minutes so macOS never pages it out of
        # memory — otherwise the first dictation after a long idle takes ~9s
        # instead of ~0.4s while it reloads
        self._warm_timer = rumps.Timer(self._keep_warm, 300)
        self._warm_timer.start()

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
        """Initialize local mlx-whisper model (runs on Apple GPU)"""
        import mlx_whisper
        self._mlx = mlx_whisper

        logging.info(f"Warming up local Whisper model ({LOCAL_MODEL_REPO})...")
        # Transcribe one second of silence so the model is loaded into memory
        # and the first real dictation is instant
        self._mlx.transcribe(
            np.zeros(16000, dtype=np.float32),
            path_or_hf_repo=LOCAL_MODEL_REPO,
            language="en",
        )
        logging.info("Local model ready")

    def _run_keyboard_listener(self):
        """Run combined keyboard listener for both hotkey and hold-to-record"""
        self.right_option_held = False
        self.cmd_held = False
        self.space_held = False
        self.last_toggle_time = 0

        def on_press(key):
            # Track modifier states
            if key == keyboard.Key.cmd:
                self.cmd_held = True

            # Right Option hold-to-record
            if key == keyboard.Key.alt_r and not self.right_option_held and not self.is_recording:
                self.right_option_held = True
                self.start_recording()

            # Cmd+Space toggle (ignore key repeat via space_held flag)
            if key == keyboard.Key.space and self.cmd_held and not self.space_held:
                self.space_held = True
                now = time.time()
                if now - self.last_toggle_time > 1.0:
                    self.last_toggle_time = now
                    self.toggle_recording()

        def on_release(key):
            # Track modifier states
            if key == keyboard.Key.cmd:
                self.cmd_held = False
            if key == keyboard.Key.space:
                self.space_held = False

            # Right Option release
            if key == keyboard.Key.alt_r and self.right_option_held:
                self.right_option_held = False
                if self.is_recording:
                    self.stop_recording()

        # If the listener ever dies (macOS hiccup, exception), restart it
        # instead of leaving the app running but deaf to the hotkey
        while True:
            try:
                with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                    listener.join()
                logging.warning("Keyboard listener stopped — restarting it")
            except Exception as e:
                logging.error(f"Keyboard listener crashed: {e} — restarting it")
            self.cmd_held = False
            self.space_held = False
            self.right_option_held = False
            time.sleep(2)

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
                text = self._transcribe_local(audio)
                if text is None and OPENAI_API_KEY:
                    logging.warning("Local transcription failed — falling back to OpenAI API")
                    text = self._transcribe_api(tmp_filename)

            elapsed = time.time() - start_time

            if text:
                pyperclip.copy(text)
                logging.info(f"Transcribed in {elapsed:.1f}s: {text}")
                time.sleep(0.1)
                self._paste_cmd_v()
                logging.info("Text pasted")
                os.unlink(tmp_filename)
            elif text is not None:
                # Transcription worked but heard nothing — not a failure
                logging.info("No speech detected")
                os.unlink(tmp_filename)
            else:
                self._save_failed_recording(tmp_filename)

        except Exception as e:
            logging.error(f"Transcription crashed: {e}")
            self._save_failed_recording(tmp_filename)

        finally:
            self.title = "🎙"

    def _save_failed_recording(self, tmp_filename):
        """Keep the audio when transcription fails so it can be retried later"""
        failed_dir = log_dir.parent / "failed_recordings"
        failed_dir.mkdir(parents=True, exist_ok=True)
        saved_path = failed_dir / f"recording_{time.strftime('%Y-%m-%d_%H-%M-%S')}.wav"
        try:
            os.rename(tmp_filename, saved_path)
        except OSError:
            import shutil
            shutil.move(tmp_filename, saved_path)
        logging.warning(f"Transcription failed — audio saved to {saved_path}")
        rumps.notification(
            "Whisper Dictation",
            "Transcription failed — recording saved",
            f"Audio kept at {saved_path.name}. Ask Claude to transcribe it.",
        )

    def _keep_warm(self, _timer):
        if self.mode != "local" or self.is_recording or self.title != "🎙":
            return
        try:
            self._mlx.transcribe(
                np.zeros(4800, dtype=np.float32),
                path_or_hf_repo=LOCAL_MODEL_REPO,
                language="en",
            )
        except Exception as e:
            logging.warning(f"Keep-warm failed: {e}")

    def _paste_cmd_v(self):
        """Send Cmd+V using raw key codes. pynput's Controller looks up the
        keyboard layout in a way macOS forbids off the main thread in a real
        app bundle, which crashed the whole app right after transcribing."""
        import Quartz
        V_KEY = 9  # 'v' on a standard keyboard
        for is_down in (True, False):
            event = Quartz.CGEventCreateKeyboardEvent(None, V_KEY, is_down)
            Quartz.CGEventSetFlags(event, Quartz.kCGEventFlagMaskCommand)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

    def _transcribe_api(self, audio_file):
        """Transcribe using OpenAI Whisper API"""
        try:
            if self.client is None:
                from openai import OpenAI
                self.client = OpenAI(api_key=OPENAI_API_KEY)
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

    def _transcribe_local(self, audio):
        """Transcribe on this Mac's GPU using mlx-whisper"""
        try:
            result = self._mlx.transcribe(
                audio.flatten().astype(np.float32),
                path_or_hf_repo=LOCAL_MODEL_REPO,
                language="en",
                condition_on_previous_text=False,
            )
            return result["text"].strip()
        except Exception as e:
            logging.error(f"Local transcription error: {e}")
            return None

    def quit_app(self, _):
        """Quit the application"""
        logging.info("Whisper Dictation stopped")
        rumps.quit_application()


if __name__ == "__main__":
    WhisperMenuBar().run()
