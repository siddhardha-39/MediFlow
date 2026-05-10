# transcriber.py
"""
faster-whisper transcription wrapper.

WHY THIS FILE EXISTS:
    This is the CORE of Module 1. It wraps the faster-whisper library
    and provides a clean function: give it an audio file path, get back
    a TranscriptionResult.

WHY faster-whisper INSTEAD OF openai-whisper:
    - 4x faster inference (uses CTranslate2 engine)
    - Lower memory usage
    - Same accuracy (same model weights)
    - Runs 100% locally (no API key, no internet needed)

MODEL SIZES:
    Model     | Size   | RAM    | Use case
    --------- | ------ | ------ | --------
    tiny      | 39 MB  | ~1 GB  | Quick tests, low RAM
    base      | 74 MB  | ~1 GB  | Good balance for limited hardware
    small     | 244 MB | ~2 GB  | Better accuracy
    medium    | 769 MB | ~5 GB  | High accuracy
    large-v3  | 1.5 GB | ~10 GB | Best accuracy (needs GPU ideally)

    We use "base" by default to stay within your ~3GB RAM constraint.
    You can upgrade to "small" later if RAM allows.

CONCEPTS:
    - CTranslate2: Optimized inference engine for transformer models
    - beam_size: Number of hypotheses to explore (higher = more accurate but slower)
    - VAD filter: Voice Activity Detection — skips silence for faster processing
"""
import time
import logging
from faster_whisper import WhisperModel

from transcription.models import TranscriptionResult, TranscriptSegment

logger = logging.getLogger("transcription.transcriber")

# ── Model Configuration ───────────────────────────────────────────────────────
# "base" is the sweet spot for low-RAM systems:
#   - 74MB download, ~1GB RAM usage
#   - Good enough accuracy for clear doctor dictation
#   - Can upgrade to "small" later
MODEL_SIZE = "base"

# "cpu" because we don't have a CUDA GPU setup
# If you add a GPU later, change to "cuda"
COMPUTE_TYPE = "int8"  # quantized — uses less RAM than float32

# ── Model Loading ──────────────────────────────────────────────────────────────
# We load the model ONCE at module level (not per request).
# WHY: Model loading takes 2-5 seconds. Loading once and reusing
#      across requests is standard practice for ML serving.
logger.info("Loading Whisper model: %s (compute: %s)...", MODEL_SIZE, COMPUTE_TYPE)
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)
logger.info("Whisper model loaded successfully.")


# ── Public API ─────────────────────────────────────────────────────────────────

def transcribe(audio_path: str) -> TranscriptionResult:
    """
    Transcribe a preprocessed audio file using faster-whisper.

    Args:
        audio_path: Path to a 16kHz mono WAV file (output of preprocessor.py).

    Returns:
        TranscriptionResult with full text, segments, and metadata.

    Flow:
        audio file
            -> faster-whisper model.transcribe()
            -> iterate over segments (generator)
            -> build TranscriptSegment list
            -> combine into full_text
            -> wrap in TranscriptionResult
    """
    logger.info("Starting transcription: %s", audio_path)
    start_time = time.time()

    # model.transcribe() returns a generator of segments + metadata
    # beam_size=5: explores 5 hypotheses per step (default, good balance)
    # vad_filter=True: skips silence — faster processing, cleaner output
    segments_gen, info = model.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=True,
        language="en",  # force English — avoids language detection overhead
    )

    # Collect segments from the generator
    # WHY A LOOP: faster-whisper yields segments lazily (one at a time).
    #             This is memory-efficient for long audio files.
    segments = []
    for seg in segments_gen:
        segments.append(
            TranscriptSegment(
                start=round(seg.start, 2),
                end=round(seg.end, 2),
                text=seg.text.strip(),
            )
        )

    # Combine all segment texts into one full transcript
    full_text = " ".join(s.text for s in segments)

    elapsed_ms = round((time.time() - start_time) * 1000, 1)
    logger.info(
        "Transcription complete: %d segments, %.1f seconds audio, %dms processing",
        len(segments), info.duration, elapsed_ms,
    )

    return TranscriptionResult(
        full_text=full_text,
        segments=segments,
        audio_file=audio_path,
        duration_secs=round(info.duration, 2),
        language=info.language or "en",
        model_used=MODEL_SIZE,
        processing_ms=elapsed_ms,
    )
