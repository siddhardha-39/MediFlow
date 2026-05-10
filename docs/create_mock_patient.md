# Documentation: `data/create_mock_patient.py`

## Purpose
This script dynamically generates realistic mock patient medical records in PDF format using the `fpdf2` library. It allows developers to quickly generate test data without needing access to real patient information.

## Code Explanation

```python
from fpdf import FPDF

def create_mock_patient_pdf(output_path: str):
    # Initialize the PDF document
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    # Multi-line string containing the comprehensive patient record
    content = \"\"\"
    PATIENT MEDICAL RECORD
    ======================
    ...
    \"\"\"

    # Iterates line-by-line and writes it to the PDF canvas
    for line in content.strip().split("\n"):
        pdf.cell(0, 8, line, new_x="LMARGIN", new_y="NEXT")

    # Saves the generated PDF to disk
    pdf.output(output_path)
    print(f"Mock patient PDF created at: {output_path}")

if __name__ == "__main__":
    create_mock_patient_pdf("data/sample_patients/PT-2024-001-Rajesh-Kumar.pdf")
```

## How It Works
1. **PDF Initialization**: We inherit or instantiate `FPDF`, creating a blank document with Helvetica font.
2. **Text Generation**: A hardcoded block of text containing patient demographics, chronic conditions, medications, and allergies is defined.
3. **Writing to PDF**: We iterate over every line in our block, using `pdf.cell` to plot the text onto the document and advance to the next line (`new_y="NEXT"`).
4. **Saving**: We call `pdf.output()` to generate the physical `.pdf` file in our `sample_patients` folder.
