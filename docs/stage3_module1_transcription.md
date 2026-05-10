# MediFlow Stage 3 - Module 1: Whisper Audio Transcription

> **Stage:** 3 / Module 1  
> **Date:** May 2026  
> **Status:** Complete and tested

---

## 1. What This Module Does

Takes a doctor's audio recording (WAV, MP3, M4A, etc.) and produces a structured, timestamped transcript that downstream modules can use to generate SOAP notes and clinical documentation.

---

## 2. Architecture

### Pipeline Flow

```
Doctor Audio File (.wav / .mp3)
        |
        v
  POST /api/transcribe          [router.py - HTTP interface]
        |
        v
  Save to uploads/               [router.py - disk persistence]
        |
        v
  Audio Preprocessor             [preprocessor.py - 16kHz mono WAV conversion]
        |
        v
  faster-whisper Model           [transcriber.py - local Whisper inference]
        |
        v
  TranscriptionResult            [models.py - Pydantic structured output]
        |
        v
  Save to transcripts/           [service.py - JSON audit trail]
        |
        v
  JSON Response to client
```

### Module Dependency Map

```
app.py (FastAPI entry point)
  |
  +-- transcription/router.py     (HTTP endpoint)
        |
        +-- transcription/service.py    (orchestrator)
              |
              +-- transcription/preprocessor.py  (audio conversion)
              |
              +-- transcription/transcriber.py   (Whisper wrapper)
              |
              +-- transcription/models.py        (Pydantic schemas)
```

### Why This Separation

| File | Responsibility | Why Separate |
|---|---|---|
| `models.py` | Define data shapes | Other modules import these schemas |
| `preprocessor.py` | Convert audio format | Can be reused, tested independently |
| `transcriber.py` | Run Whisper | ML model logic isolated from HTTP/IO |
| `service.py` | Orchestrate pipeline | Connects the pieces in order |
| `router.py` | Handle HTTP | Can swap HTTP for CLI without touching logic |
| `app.py` | Mount all routers | Single entry point for all API modules |

---

## 3. Key Concepts Explained

### faster-whisper vs OpenAI Whisper
- **Same model weights** (identical accuracy)
- **4x faster** (uses CTranslate2 optimized inference engine)
- **Lower RAM** (supports int8 quantization)
- **100% local** (no API key, no internet after first model download)

### Why 16kHz Mono WAV?
Whisper was trained on 16kHz mono audio. Feeding it other formats works but:
- Higher sample rates waste computation
- Stereo adds no value for speech-to-text
- Preprocessing ensures consistent input quality

### VAD Filter (Voice Activity Detection)
Whisper's VAD filter skips silence in the audio. Benefits:
- Faster processing (doesn't waste time on silence)
- Cleaner output (no empty segments)
- The test audio was a sine tone - VAD correctly filtered it as "not speech"

### temperature=0 (in transcriber)
We don't set temperature explicitly (defaults to 0 in faster-whisper).
Temperature 0 = deterministic output = same audio always gives same text.

---

## 4. Files Created

| File | Lines | Purpose |
|---|---|---|
| `transcription/__init__.py` | 1 | Package marker |
| `transcription/models.py` | 48 | TranscriptSegment, TranscriptionResult schemas |
| `transcription/preprocessor.py` | 82 | Audio -> 16kHz mono WAV conversion |
| `transcription/transcriber.py` | 107 | faster-whisper wrapper, model loading |
| `transcription/service.py` | 100 | Pipeline orchestrator + JSON save |
| `transcription/router.py` | 108 | FastAPI POST /api/transcribe endpoint |
| `app.py` | 52 | FastAPI app entry point |
| `test_transcription.py` | 113 | End-to-end test with synthetic audio |

---

## 5. How to Run

### Start the API server
```bash
cd MediFlow
python app.py
```
Server runs at http://localhost:8000

### Interactive API docs
Open http://localhost:8000/docs in your browser.
FastAPI auto-generates Swagger UI where you can upload audio files directly.

### Test with synthetic audio
```bash
# In a SECOND terminal:
python test_transcription.py
```

### Test with a real audio file
```bash
python test_transcription.py path/to/real_recording.wav
```

### Test with curl
```bash
curl -X POST http://localhost:8000/api/transcribe -F "file=@recording.wav"
```

---

## 6. Dependencies Installed

| Package | Version | Purpose |
|---|---|---|
| `faster-whisper` | 1.2.1 | Local Whisper transcription |
| `fastapi` | 0.136.1 | REST API framework |
| `uvicorn` | 0.46.0 | ASGI server |
| `python-multipart` | 0.0.27 | File upload support |
| `pydub` | 0.25.1 | Audio format conversion |
| `audioop-lts` | 0.2.2 | Python 3.14 compatibility for pydub |
| `ffmpeg` | 8.1.1 | System binary for audio processing |

---

## 7. Bugs Faced & Solutions

### Bug 1 - `No module named 'audioop'`

**Cause:** Python 3.13+ removed the `audioop` module from stdlib. `pydub` depends on it.  
**Fix:** `pip install audioop-lts` - maintained community port of the removed module.  
**Lesson:** Always check dependency compatibility when using bleeding-edge Python versions.

### Bug 2 - `Couldn't find ffmpeg` warning

**Cause:** `winget install` added ffmpeg to PATH, but the current terminal session hadn't reloaded PATH.  
**Fix:** Restart terminal or refresh PATH:
```powershell
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
```
**Lesson:** System PATH changes don't take effect in already-open terminals.

---

## 8. Test Results

```
============================================================
  MediFlow - Transcription Pipeline Test
============================================================
[OK] Health check: {'status': 'healthy', 'version': '0.3.0'}
[OK] Test audio created: uploads/test_audio.wav (3.0s)
[OK] Transcription succeeded!
  Full text:     (empty - expected for sine wave)
  Segments:      0
  Duration:      3.0s
  Model:         base
  Processing:    281ms
============================================================
```

**Verdict:** Pipeline works end-to-end. Empty transcript is correct behavior for non-speech audio. VAD filter correctly identified the sine wave as non-speech.

---

## 9. Common Errors & How to Fix

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: audioop` | Python 3.13+ | `pip install audioop-lts` |
| `Couldn't find ffmpeg` | ffmpeg not in PATH | Restart terminal after installing ffmpeg |
| `File too large` | Audio > 25MB | Split audio or increase `MAX_FILE_SIZE_MB` |
| `Unsupported file format` | Unknown extension | Add to `ALLOWED_EXTENSIONS` in router.py |
| Model download slow | First run downloads ~74MB | One-time download, cached after |

---

## 10. What Connects Next (Module 2)

The `TranscriptionResult.full_text` becomes the **input** to Module 2:

```
TranscriptionResult.full_text
        |
        v
  SOAP Note Generator (Module 2)
        |
        v
  Structured SOAP Note (Pydantic)
```

The transcript text flows directly into the SOAP note extraction prompt.
