# router.py
"""
FastAPI endpoint for audio upload and transcription.

WHY THIS FILE EXISTS:
    This is the HTTP interface to the transcription pipeline.
    Doctors or frontend apps upload audio files here via POST request.

    Separation of concerns:
    - router.py handles HTTP (request/response, file upload, validation)
    - service.py handles business logic (preprocess, transcribe, save)

    This means we can also call service.process_audio() directly from
    Python code (e.g., from a LangChain tool in Module 3) without
    needing to go through HTTP.

ENDPOINT:
    POST /api/transcribe
    - Accepts: audio file (multipart form upload)
    - Returns: TranscriptionResult as JSON

HOW FILE UPLOAD WORKS IN FASTAPI:
    1. Client sends POST with Content-Type: multipart/form-data
    2. FastAPI receives it as an UploadFile object
    3. We save it to disk (uploads/ directory)
    4. Pass the file path to our service
    5. Return the structured result
"""
import os
import shutil
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from transcription.service import process_audio
from transcription.models import TranscriptionResult

logger = logging.getLogger("transcription.router")

# APIRouter lets us define endpoints in a separate file
# and mount them onto the main FastAPI app later.
router = APIRouter(prefix="/api", tags=["transcription"])

# Allowed audio formats
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}

# Max file size: 25MB (about 10 minutes of audio)
MAX_FILE_SIZE_MB = 25

# Upload directory
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"


@router.post("/transcribe", response_model=TranscriptionResult)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Upload an audio file and receive a structured transcription.

    HOW THIS ENDPOINT WORKS:
        1. Validate file extension and size
        2. Save uploaded file to uploads/
        3. Call service.process_audio() — runs the full pipeline
        4. Return TranscriptionResult as JSON

    Usage (curl):
        curl -X POST http://localhost:8000/api/transcribe \
             -F "file=@doctor_recording.wav"

    Usage (Python requests):
        import requests
        with open("recording.wav", "rb") as f:
            resp = requests.post(
                "http://localhost:8000/api/transcribe",
                files={"file": f}
            )
        print(resp.json())
    """
    # ── Validate file extension ────────────────────────────────────────────
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # ── Save uploaded file to disk ─────────────────────────────────────────
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    upload_path = str(UPLOAD_DIR / file.filename)

    logger.info("Receiving upload: %s", file.filename)

    # Read and check file size
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {size_mb:.1f}MB. Max: {MAX_FILE_SIZE_MB}MB.",
        )

    # Write to disk
    with open(upload_path, "wb") as f:
        f.write(contents)

    logger.info("File saved: %s (%.1f MB)", upload_path, size_mb)

    # ── Run transcription pipeline ─────────────────────────────────────────
    try:
        result = process_audio(upload_path, file.filename)
        return result
    except Exception as e:
        logger.error("Transcription failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
