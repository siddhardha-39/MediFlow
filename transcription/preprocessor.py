# preprocessor.py
"""
Audio preprocessing layer.

WHY THIS FILE EXISTS:
    faster-whisper works best with:
    - 16kHz sample rate (Whisper was trained on 16kHz audio)
    - Mono channel (stereo adds no value for speech-to-text)
    - WAV format (uncompressed, no codec issues)

    Doctors may upload MP3, M4A, or WAV at any sample rate.
    This module normalises ANY audio file into the format Whisper expects.

DEPENDENCIES:
    - pydub: high-level audio manipulation (wraps ffmpeg)
    - ffmpeg: system binary that pydub calls under the hood
"""
import os
import logging
from pathlib import Path
from pydub import AudioSegment

logger = logging.getLogger("transcription.preprocessor")

# Whisper expects 16kHz mono WAV
TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1  # mono


def preprocess_audio(input_path: str, output_dir: str) -> str:
    """
    Convert any audio file to 16kHz mono WAV for Whisper.

    Args:
        input_path:  Path to the uploaded audio file (.wav, .mp3, .m4a, etc.)
        output_dir:  Directory to save the preprocessed WAV file.

    Returns:
        Path to the preprocessed WAV file.

    Flow:
        input.mp3  ->  pydub loads it  ->  set to 16kHz mono  ->  export as WAV
    """
    input_path = Path(input_path)
    os.makedirs(output_dir, exist_ok=True)

    # Determine file format from extension
    ext = input_path.suffix.lower().lstrip(".")
    logger.info("Loading audio: %s (format: %s)", input_path.name, ext)

    # pydub auto-detects format from extension
    # For .wav it reads directly, for .mp3/.m4a it uses ffmpeg
    audio = AudioSegment.from_file(str(input_path), format=ext if ext != "wav" else None)

    # Log original properties
    logger.info(
        "Original: %d Hz, %d channels, %.1f seconds",
        audio.frame_rate, audio.channels, len(audio) / 1000.0,
    )

    # Convert to 16kHz mono
    audio = audio.set_frame_rate(TARGET_SAMPLE_RATE)
    audio = audio.set_channels(TARGET_CHANNELS)

    # Export as WAV
    output_filename = input_path.stem + "_processed.wav"
    output_path = os.path.join(output_dir, output_filename)
    audio.export(output_path, format="wav")

    logger.info("Preprocessed audio saved to: %s", output_path)
    return output_path


def get_audio_duration(file_path: str) -> float:
    """
    Get the duration of an audio file in seconds.

    WHY A SEPARATE FUNCTION:
        We need duration for the TranscriptionResult metadata,
        and sometimes we want to check duration BEFORE running
        Whisper (e.g., to reject files that are too long).
    """
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0  # pydub gives milliseconds
