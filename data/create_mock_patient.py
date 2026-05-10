from fpdf import FPDF

def create_mock_patient_pdf(output_path: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    content = """
PATIENT MEDICAL RECORD
======================
Patient ID: PT-2024-001
Name: Rajesh Kumar
Date of Birth: 14 March 1968 (Age: 56)
Gender: Male
Blood Group: B+

CHRONIC CONDITIONS
------------------
- Type 2 Diabetes Mellitus (diagnosed 2015)
- Hypertension (diagnosed 2018)
- Mild Chronic Kidney Disease - Stage 2 (diagnosed 2022)

CURRENT MEDICATIONS
-------------------
- Metformin 500mg - twice daily (for diabetes)
- Amlodipine 5mg - once daily (for hypertension)
- Losartan 50mg - once daily (for hypertension + kidney protection)
- Aspirin 75mg - once daily (preventive)

KNOWN ALLERGIES
---------------
- Penicillin (causes severe rash and swelling)
- Sulfonamides (causes breathing difficulty)

RECENT INVESTIGATIONS (Last 6 months)
--------------------------------------
- HbA1c: 7.8% (slightly above target, diabetes not fully controlled)
- Fasting Blood Sugar: 148 mg/dL (elevated)
- Serum Creatinine: 1.4 mg/dL (mildly elevated, monitor kidney)
- eGFR: 58 mL/min (Stage 2 CKD confirmed)
- Blood Pressure reading: 142/88 mmHg (above target)
- Lipid Profile: LDL 112 mg/dL (borderline high)

RECENT VISITS
-------------
- 10 Jan 2024: Routine diabetes follow-up. Increased Metformin dose.
- 05 Mar 2024: Complained of occasional dizziness. BP reviewed.
- 22 Apr 2024: Kidney function review. Referred to nephrologist.

SURGICAL HISTORY
----------------
- Appendectomy (2001) - no complications

FAMILY HISTORY
--------------
- Father: Died of heart attack at age 62
- Mother: Type 2 Diabetes, alive age 78

LIFESTYLE
---------
- Non-smoker
- Occasional alcohol (1-2 units per week)
- Sedentary job (desk work)
- Diet: Partially following diabetic diet plan

NOTES FROM LAST DOCTOR
-----------------------
Patient needs strict BP and sugar control. 
Kidney function must be monitored every 3 months.
Consider cardiology referral given family history.
Patient counselled on lifestyle changes and diet.
"""

    for line in content.strip().split("\n"):
        pdf.cell(0, 8, line, new_x="LMARGIN", new_y="NEXT")

    pdf.output(output_path)
    print(f"Mock patient PDF created at: {output_path}")

if __name__ == "__main__":
    create_mock_patient_pdf("data/sample_patients/PT-2024-001-Rajesh-Kumar.pdf")