# service.py
"""
Transcription service — orchestrates the full pipeline.

WHY THIS FILE EXISTS:
    Neither the preprocessor nor the transcriber should know about each other.
    The service layer CONNECTS them in sequence:

        upload -> preprocess -> transcribe -> save -> return result

    This is a common pattern in production systems:
    - preprocessor.py does ONE thing (convert audio format)
    - transcriber.py does ONE thing (run Whisper)
    - service.py orchestrates the flow

    If we later add noise reduction, speaker diarization, or profanity
    filtering, they get added as steps HERE — without touching the
    other modules.
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime

from transcription.preprocessor import preprocess_audio
from transcription.transcriber import transcribe
from transcription.models import TranscriptionResult

logger = logging.getLogger("transcription.service")

# ── Directories ────────────────────────────────────────────────────────────────
# All paths are relative to the MediFlow project root.
BASE_DIR = Path(__file__).parent.parent  # MediFlow/
UPLOAD_DIR = str(BASE_DIR / "uploads")
PROCESSED_DIR = str(BASE_DIR / "uploads" / "processed")
TRANSCRIPT_DIR = str(BASE_DIR / "transcripts")


def process_audio(audio_path: str, original_filename: str) -> TranscriptionResult:
    """
    Run the full transcription pipeline.

    Args:
        audio_path:         Path to the uploaded audio file on disk.
        original_filename:  Original name of the uploaded file (for metadata).

    Returns:
        TranscriptionResult with full text, segments, and metadata.

    Pipeline:
        1. Preprocess audio  -> 16kHz mono WAV
        2. Transcribe         -> segments + full text
        3. Save transcript    -> JSON file in transcripts/
        4. Return result
    """
    logger.info("=== Transcription Pipeline Start ===")
    logger.info("Input: %s", original_filename)

    # ── Step 1: Preprocess ─────────────────────────────────────────────────
    logger.info("Step 1: Preprocessing audio...")
    processed_path = preprocess_audio(audio_path, PROCESSED_DIR)

    # ── Step 2: Transcribe ─────────────────────────────────────────────────
    logger.info("Step 2: Running Whisper transcription...")
    result = transcribe(processed_path)

    # Override audio_file with the original filename (more meaningful)
    result.audio_file = original_filename

    # ── Step 3: Save transcript ────────────────────────────────────────────
    logger.info("Step 3: Saving transcript...")
    _save_transcript(result, original_filename)

    logger.info("=== Transcription Pipeline Complete ===")
    return result


def _save_transcript(result: TranscriptionResult, original_filename: str) -> str:
    """
    Save the transcript as a JSON file for audit trail.

    WHY SAVE TO DISK:
        Medical systems MUST retain raw transcripts.
        Even after we add a database (Module 5), we keep the JSON
        files as a backup / audit trail.

    File naming: transcript_<original_name>_<timestamp>.json
    """
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

    stem = Path(original_filename).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"transcript_{stem}_{timestamp}.json"
    filepath = os.path.join(TRANSCRIPT_DIR, filename)

    # Pydantic's model_dump() converts the object to a dict.
    # mode="json" ensures datetime objects become ISO strings.
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    logger.info("Transcript saved: %s", filepath)
    return filepath
