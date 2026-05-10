# test_transcription.py
"""
Test script for Module 1 — Whisper Audio Transcription Pipeline.

HOW TO USE:
    1. Start the FastAPI server:
       python app.py

    2. In ANOTHER terminal, run this test:
       python test_transcription.py

    This script:
    - Creates a small synthetic test audio file (no microphone needed)
    - Uploads it to the /api/transcribe endpoint
    - Prints the structured result

WHY SYNTHETIC AUDIO:
    We don't want to rely on having a real doctor recording for testing.
    We generate a short WAV file with a sine tone so we can verify:
    - File upload works
    - Preprocessing works
    - Whisper runs without crashing
    - Response schema is correct

    The transcription of a sine tone will be empty or garbage — that's fine.
    The point is to test the PIPELINE, not the accuracy.

    For a real test, replace TEST_WITH_SYNTHETIC with a real .wav file path.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import wave
import struct
import math
import requests

API_URL = "http://localhost:8000"
TEST_AUDIO_PATH = os.path.join(os.path.dirname(__file__), "uploads", "test_audio.wav")


def create_test_audio(filepath: str, duration_secs: float = 3.0, freq: float = 440.0):
    """
    Generate a simple sine wave WAV file for testing.

    This creates a valid audio file without needing a microphone.
    Whisper will try to transcribe it (and produce empty/garbage text).
    That's expected — we're testing the pipeline, not accuracy.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    sample_rate = 16000
    n_samples = int(sample_rate * duration_secs)

    with wave.open(filepath, "w") as wav_file:
        wav_file.setnchannels(1)        # mono
        wav_file.setsampwidth(2)        # 16-bit
        wav_file.setframerate(sample_rate)

        for i in range(n_samples):
            # Generate sine wave sample
            value = int(32767 * 0.5 * math.sin(2 * math.pi * freq * i / sample_rate))
            wav_file.writeframes(struct.pack("<h", value))

    print(f"[OK] Test audio created: {filepath} ({duration_secs}s)")


def test_health():
    """Test that the server is running."""
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5)
        print(f"[OK] Health check: {resp.json()}")
        return True
    except requests.ConnectionError:
        print("[FAIL] Server not running. Start it with: python app.py")
        return False


def test_transcription(audio_path: str):
    """Upload an audio file and print the transcription result."""
    print(f"\n--- Uploading: {os.path.basename(audio_path)} ---")

    with open(audio_path, "rb") as f:
        resp = requests.post(
            f"{API_URL}/api/transcribe",
            files={"file": (os.path.basename(audio_path), f, "audio/wav")},
            timeout=120,  # Whisper can take a while on CPU
        )

    if resp.status_code == 200:
        result = resp.json()
        print(f"[OK] Transcription succeeded!")
        print(f"  Full text:     {result['full_text'][:100]}...")
        print(f"  Segments:      {len(result['segments'])}")
        print(f"  Duration:      {result['duration_secs']}s")
        print(f"  Model:         {result['model_used']}")
        print(f"  Processing:    {result['processing_ms']}ms")
        print(f"\n  Full response:")
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"[FAIL] Status {resp.status_code}: {resp.text}")


def main():
    print("=" * 60)
    print("  MediFlow - Transcription Pipeline Test")
    print("=" * 60)

    # Step 1: Health check
    if not test_health():
        return

    # Step 2: Create test audio (if no real audio file provided)
    audio_path = TEST_AUDIO_PATH
    if len(sys.argv) > 1:
        # User provided a real audio file path as argument
        audio_path = sys.argv[1]
        print(f"Using provided audio: {audio_path}")
    else:
        # Generate synthetic test audio
        create_test_audio(audio_path)

    # Step 3: Test transcription
    test_transcription(audio_path)

    print("\n" + "=" * 60)
    print("  Test complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
