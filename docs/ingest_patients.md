# Documentation: `db/ingest_patients.py`

## Purpose
This script automates the **Ingestion Pipeline**. It scans the data folders for patient PDFs, processes them through the loader and chunker, and securely stores the calculated vectors into the Chroma database. This script is intended to be run manually whenever new patient PDFs are added to the system.

## Code Explanation

```python
import sys
from pathlib import Path

# Add project root to path to resolve custom imports
sys.path.append(str(Path(__file__).parent.parent))

from document_loading.pdf_loader import load_and_chunk_pdf
from db.chroma_store import add_documents_to_db

def ingest_all_patients():
    # Target directory definition
    data_dir = Path(__file__).parent.parent / "data" / "sample_patients"
    
    # 1. Gather all PDF files
    pdf_files = list(data_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {data_dir}")
        return

    # 2. Iteration Loop
    for pdf_path in pdf_files:
        patient_id = pdf_path.stem
        
        # 3. Trigger loader & chunker
        chunks = load_and_chunk_pdf(pdf_path)
        
        # 4. Trigger database storage
        add_documents_to_db(chunks, patient_id=patient_id)
        
        print(f"  - Successfully ingested {patient_id}!")

if __name__ == "__main__":
    ingest_all_patients()
```

## How It Works
1. **File Scanning**: We use `pathlib.glob` to search the `data/sample_patients/` folder and find all files ending in `.pdf`.
2. **Looping Logic**: For each file, we extract the filename without the extension (`.stem`) and assign it as our unique `patient_id` (e.g., `"PT-2024-001-Rajesh-Kumar"`).
3. **Execution**: It passes the exact file path to `load_and_chunk_pdf` (which extracts text) and then passes the resulting chunks to `add_documents_to_db` (which generates the vectors and saves them to the disk using the isolated patient ID folder).
