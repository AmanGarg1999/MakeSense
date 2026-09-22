#!/usr/bin/env python3
"""
Local Voice Agent with STT (faster-whisper) and TTS (Edge TTS)
Can make web calls and run locally on your setup.
"""

import asyncio
import json
import os
import sys
import threading
import time
import wave
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

import edge_tts
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

# ============================================================================
# Configuration
# ============================================================================

CONFIG = {
    "stt": {
        "model_size": "base",  # tiny, base, small, medium, large-v3
        "device": "cpu",  # "cuda" or "cpu" - GTX 960M doesn't support efficient float16/int8
        "compute_type": "int8",  # "float16", "int8", "int8_float16" - int8 works on CPU
        "language": "en",
        "vad_filter": True,
        "vad_parameters": {
            "threshold": 0.5,
            "min_speech_duration_ms": 250,
            "max_speech_duration_s": float("inf"),
            "min_silence_duration_ms": 1000,
            "speech_pad_ms": 400,
        },
    },
    "tts": {
        "provider": "edge",  # "edge" for now
        "edge_voice": "en-US-AriaNeural",
        "edge_rate": "+0%",
        "edge_volume": "+0%",
    },
    "audio": {
        "sample_rate": 16000,
        "channels": 1,
        "dtype": "int16",
        "block_duration_ms": 100,  # for VAD processing
    },
    "recording": {
        "max_duration_s": 60,
        "silence_timeout_s": 3.0,
        "energy_threshold": 300,
    },
}

# ============================================================================
# Speech-to-Text (faster-whisper)
# ============================================================================

class STTEngine:
    def __init__(self, config: dict):
        self.config = config
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the Whisper model."""
        print(f"Loading Whisper model: {self.config['model_size']} on {self.config['device']}...")
        self.model = WhisperModel(
            self.config["model_size"],
            device=self.config["device"],
            compute_type=self.config["compute_type"],
        )
        print("Whisper model loaded!")

    def transcribe_file(self, audio_path: str) -> str:
        """Transcribe an audio file."""
        segments, info = self.model.transcribe(
            audio_path,
            language=self.config.get("language"),
            vad_filter=self.config.get("vad_filter", True),
            vad_parameters=self.config.get("vad_parameters"),
        )
        text = " ".join([seg.text for seg in segments])
        return text.strip()

    def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int) -> str:
        """Transcribe audio data from numpy array."""
        # Save to temporary WAV file on external drive (more space)
        import tempfile
        tmp_dir = "/run/media/huntingvision/1c514555-9d09-44e0-8fcc-e90fcada2549/tmp_voice"
        os.makedirs(tmp_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=tmp_dir) as tmp:
            tmp_path = tmp.name
            self._save_wav(tmp_path, audio_data, sample_rate)

        try:
            return self.transcribe_file(tmp_path)
        finally:
            os.unlink(tmp_path)

    def _save_wav(self, path: str, audio_data: np.ndarray, sample_rate: int):
        """Save numpy array as WAV file."""
        # Ensure int16
        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())


# ============================================================================
# Text-to-Speech (Edge TTS)
# ============================================================================

class TTSEngine:
    def __init__(self, config: dict):
        self.config = config
        self.voice = config.get("edge_voice", "en-US-AriaNeural")
        self.rate = config.get("edge_rate", "+0%")
        self.volume = config.get("edge_volume", "+0%")

    async def synthesize(self, text: str, output_path: str) -> str:
        """Synthesize speech and save to file."""
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
        )
        await communicate.save(output_path)
        return output_path

    async def synthesize_and_play(self, text: str):
        """Synthesize and play immediately."""
        import tempfile
        tmp_dir = "/run/media/huntingvision/1c514555-9d09-44e0-8fcc-e90fcada2549/tmp_voice"
        os.makedirs(tmp_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=tmp_dir) as tmp:
            tmp_path = tmp.name

        try:
            await self.synthesize(text, tmp_path)
            # Play using sounddevice (more reliable than ffplay)
            import sounddevice as sd
            import soundfile as sf
            data, fs = sf.read(tmp_path)
            sd.play(data, fs)
            sd.wait()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def get_available_voices(self) -> list:
        """Get list of available Edge TTS voices."""
        # This would require async call, returning known good voices
        return [
            "en-US-AriaNeural",
            "en-US-JennyNeural",
            "en-US-GuyNeural",
            "en-GB-SoniaNeural",
            "en-AU-NatashaNeural",
            "en-CA-ClaraNeural",
        ]


# ============================================================================
# Audio Recorder with VAD
# ============================================================================

class AudioRecorder:
    def __init__(self, config: dict):
        self.config = config
        self.sample_rate = config["audio"]["sample_rate"]
        self.channels = config["audio"]["channels"]
        self.dtype = config["audio"]["dtype"]
        self.max_duration = config["recording"]["max_duration_s"]
        self.silence_timeout = config["recording"]["silence_timeout_s"]
        self.energy_threshold = config["recording"]["energy_threshold"]

        self._recording = False
        self._audio_buffer = []
        self._stream = None
        self._start_time = None
        self._last_speech_time = None

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream."""
        if status:
            print(f"Audio status: {status}")

        if self._recording:
            self._audio_buffer.append(indata.copy())

            # Simple energy-based VAD
            try:
                energy = np.sqrt(np.mean(indata.astype(np.float32)**2))
            except (ValueError, RuntimeWarning):
                energy = 0.0
            current_time = time.time()

            if energy > self.energy_threshold:
                self._last_speech_time = current_time

            # Check for silence timeout
            if self._last_speech_time and (current_time - self._last_speech_time) > self.silence_timeout:
                self.stop()

            # Check max duration
            if current_time - self._start_time > self.max_duration:
                self.stop()

    def start(self):
        """Start recording."""
        self._recording = True
        self._audio_buffer = []
        self._start_time = time.time()
        self._last_speech_time = None

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            callback=self._audio_callback,
            blocksize=int(self.sample_rate * self.config["audio"]["block_duration_ms"] / 1000),
        )
        self._stream.start()
        print("🎙️  Recording started... (speak now)")

    def stop(self) -> Optional[np.ndarray]:
        """Stop recording and return audio data."""
        if not self._recording:
            return None

        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._audio_buffer:
            print("No audio recorded")
            return None

        audio_data = np.concatenate(self._audio_buffer, axis=0)
        duration = len(audio_data) / self.sample_rate
        print(f"🛑 Recording stopped. Duration: {duration:.1f}s")
        return audio_data.flatten()

    def is_recording(self) -> bool:
        return self._recording


# ============================================================================
# Web Call Handler
# ============================================================================

class WebCaller:
    """Handle web API calls from voice commands."""

    def __init__(self):
        self.session = None

    async def init_session(self):
        import aiohttp
        self.session = aiohttp.ClientSession()

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def call_api(self, url: str, method: str = "GET", **kwargs) -> dict:
        """Make an HTTP request."""
        if not self.session:
            await self.init_session()

        async with self.session.request(method, url, **kwargs) as resp:
            return {
                "status": resp.status,
                "data": await resp.json() if resp.content_type == "application/json" else await resp.text(),
            }

    async def search_web(self, query: str) -> str:
        """Search the web using a simple API."""
        # Using duckduckgo html scrape or a search API
        import aiohttp
        if not self.session:
            await self.init_session()

        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        headers = {"User-Agent": "Mozilla/5.0"}

        async with self.session.post(url, data=params, headers=headers) as resp:
            html = await resp.text()
            # Simple extraction
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            results = soup.find_all("a", class_="result__url")
            snippets = soup.find_all("a", class_="result__snippet")
            output = []
            for r, s in zip(results[:3], snippets[:3]):
                output.append(f"{r.get_text(strip=True)}: {s.get_text(strip=True)}")
            return "\n".join(output) if output else "No results found"


# ============================================================================
# Voice Agent Main Class
# ============================================================================

class VoiceAgent:
    def __init__(self, config: dict = None):
        self.config = config or CONFIG
        self.stt = STTEngine(self.config["stt"])
        self.tts = TTSEngine(self.config["tts"])
        self.recorder = AudioRecorder(self.config)
        self.web = WebCaller()
        self.running = False
        self.wake_word = "hey hermes"  # Simple wake word

    async def initialize(self):
        """Initialize all components."""
        print("Initializing Voice Agent...")
        await self.web.init_session()
        print("Voice Agent ready!")

    async def shutdown(self):
        """Clean shutdown."""
        await self.web.close_session()
        print("Voice Agent shut down.")

    def record_and_transcribe(self) -> Optional[str]:
        """Record audio and transcribe."""
        print("\n" + "=" * 50)
        print("Press Enter to start recording, then speak...")
        print("Recording will auto-stop after 3 seconds of silence")
        print("=" * 50)
        input()

        self.recorder.start()
        audio_data = self.recorder.stop()

        if audio_data is None or len(audio_data) == 0:
            return None

        print("Transcribing...")
        text = self.stt.transcribe_audio(audio_data, self.config["audio"]["sample_rate"])
        print(f"You said: {text}")
        return text

    async def process_command(self, text: str) -> str:
        """Process a voice command and return response."""
        text_lower = text.lower().strip()

        # Wake word check (optional)
        if self.wake_word and not text_lower.startswith(self.wake_word):
            # Still process but note it wasn't wake-word triggered
            pass

        # Remove wake word if present
        if text_lower.startswith(self.wake_word):
            text = text[len(self.wake_word):].strip()
            text_lower = text.lower()

        # Built-in commands
        if text_lower in ["exit", "quit", "stop", "goodbye"]:
            return "GOODBYE"

        if text_lower in ["help", "what can you do"]:
            return (
                "I can help you with: web searches, answering questions, "
                "telling you the time, weather, or just chatting. "
                "Try saying 'search for python tutorials' or 'what time is it'."
            )

        if text_lower.startswith("search for ") or text_lower.startswith("search "):
            query = text_lower.replace("search for ", "").replace("search ", "")
            print(f"Searching web for: {query}")
            result = await self.web.search_web(query)
            return f"Search results for '{query}':\n{result}"

        if "time" in text_lower:
            now = datetime.now().strftime("%I:%M %p on %A, %B %d")
            return f"It's {now}"

        if "date" in text_lower:
            today = datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {today}"

        # Default: echo back or use LLM (would need integration)
        return f"I heard: {text}. This is a local voice agent - for LLM integration, connect to your Hermes instance."

    async def speak(self, text: str):
        """Speak the response."""
        print(f"Agent: {text}")
        await self.tts.synthesize_and_play(text)

    async def run_interactive(self):
        """Run interactive voice session."""
        await self.initialize()

        print("\n" + "=" * 60)
        print("🎤 LOCAL VOICE AGENT STARTED")
        print("=" * 60)
        print("Commands:")
        print("  - Press Enter to start recording")
        print("  - Say 'exit', 'quit', or 'goodbye' to stop")
        print("  - Say 'search for <query>' to search the web")
        print("  - Say 'what time is it' for current time")
        print("=" * 60)

        self.running = True
        while self.running:
            try:
                # Record and transcribe
                text = self.record_and_transcribe()

                if not text:
                    continue

                # Process command
                response = await self.process_command(text)

                if response == "GOODBYE":
                    await self.speak("Goodbye!")
                    break

                # Speak response
                await self.speak(response)

            except KeyboardInterrupt:
                print("\nInterrupted by user")
                break
            except Exception as e:
                print(f"Error: {e}")
                await self.speak("Sorry, I encountered an error.")

        await self.shutdown()


# ============================================================================
# Simple test mode
# ============================================================================

async def test_components():
    """Test STT and TTS components."""
    print("Testing STT...")
    stt = STTEngine(CONFIG["stt"])

    print("Testing TTS...")
    tts = TTSEngine(CONFIG["tts"])

    # Test TTS
    test_text = "Hello! This is a test of the local voice agent using Edge TTS."
    output_path = "/run/media/huntingvision/1c514555-9d09-44e0-8fcc-e90fcada2549/test_tts.mp3"
    await tts.synthesize(test_text, output_path)
    print(f"TTS saved to {output_path}")

    # Test recording (5 seconds)
    print("\nTest recording for 5 seconds...")
    recorder = AudioRecorder(CONFIG)
    recorder.start()
    await asyncio.sleep(5)
    audio = recorder.stop()

    if audio is not None:
        print("Transcribing test recording...")
        text = stt.transcribe_audio(audio, CONFIG["audio"]["sample_rate"])
        print(f"Transcribed: {text}")

    print("Component test complete!")


# ============================================================================
# Main entry point
# ============================================================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Local Voice Agent")
    parser.add_argument("--test", action="store_true", help="Run component tests")
    parser.add_argument("--interactive", action="store_true", help="Run interactive mode (default)")
    parser.add_argument("--model", default="base", help="Whisper model size (tiny, base, small, medium, large-v3)")
    parser.add_argument("--device", default="cpu", help="Device for Whisper (cuda, cpu)")
    args = parser.parse_args()

    # Update config from args
    CONFIG["stt"]["model_size"] = args.model
    CONFIG["stt"]["device"] = args.device
    # Use float32 for broadest compatibility (works on CPU and older GPUs)
    CONFIG["stt"]["compute_type"] = "float32" if args.device == "cuda" else "int8"

    agent = VoiceAgent(CONFIG)

    if args.test:
        await test_components()
    else:
        await agent.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())