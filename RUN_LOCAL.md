# MediFlow Local Demo Guide

Tested on Python 3.13 in the repository virtual environment.

## 1. Create and activate the virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 2. Install dependencies

```powershell
pip install -r requirements.txt
```

## 3. Start the FastAPI backend

```powershell
.\.venv\Scripts\python app.py
```

Open the API docs at:

```text
http://localhost:8000/docs
```

## 4. Start the Streamlit UI

```powershell
.\.venv\Scripts\python -m streamlit run ui/app.py
```

## 5. Run the demo

1. Open the Streamlit app.
2. Enter your Gemini API key in the runtime key box.
3. Open Patient History and select the synthetic patient.
4. Generate the patient briefing.
5. Open Clinical Documentation, paste a transcript, and generate a SOAP draft.
6. Reject once with feedback, then approve the corrected draft.
7. Open the dashboard and confirm the persisted totals changed.

## 6. Reset demo data

```powershell
.\.venv\Scripts\python scripts/reset_demo_data.py
```

## 7. Run tests

```powershell
python -m pytest -v -m "not integration"
```

The first HuggingFace embedding download may take a little time on the first run.
