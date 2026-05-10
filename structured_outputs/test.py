# test.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from structured_outputs.extractor import extract_medical_info

patient_text = """
Patient has diabetes.
Taking metformin.
Allergic to penicillin.
Complains of fatigue and chest pain.
"""

response = extract_medical_info(patient_text)

print(response)