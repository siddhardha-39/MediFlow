# prompts.py

EXTRACTION_PROMPT = """You are a clinical information extraction engine.

Your ONLY task is to extract medical entities from the patient history below.

Return ONLY a valid JSON object. No explanation. No markdown. No code fences.
Do NOT add any text before or after the JSON.

Required JSON format:
{{
  "conditions":  ["list of diagnosed conditions"],
  "allergies":   ["list of known allergies"],
  "medications": ["list of current medications"],
  "symptoms":    ["list of reported symptoms"]
}}

Rules:
- Use empty lists [] for fields with no information found.
- Normalise abbreviations: "DM" → "Diabetes", "NKDA" → "No known drug allergies", "Hx" → "History of", "Rx" → "Prescription".
- Each item must be a plain string.
- Return ONLY the JSON object. Nothing else.

Patient History:
{patient_text}"""


RETRY_PROMPT = """Your previous response was not valid JSON.

Original patient text:
{patient_text}

Your previous response:
{previous_response}

Error:
{error}

Return ONLY the corrected JSON object. No explanation. No markdown. No code fences.

Required format:
{{
  "conditions":  [],
  "allergies":   [],
  "medications": [],
  "symptoms":    []
}}"""