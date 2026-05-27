from pathlib import Path

from rag.service import ingest_patient_documents


def ingest_all_patients(force_rebuild: bool = False):
    """
    Loops through all PDFs in data/sample_patients, extracts text, chunks it,
    and stores the embeddings in the upgraded patient-specific RAG folders.
    """
    data_dir = Path(__file__).parent.parent / "data" / "sample_patients"
    
    if not data_dir.exists():
        print(f"Directory not found: {data_dir}")
        return

    pdf_files = list(data_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {data_dir}")
        return

    print(f"Found {len(pdf_files)} patient record(s) to process.")

    for pdf_path in pdf_files:
        patient_id = pdf_path.stem
        print(f"\nProcessing {patient_id}...")
        ingest_patient_documents(
            patient_id=patient_id,
            docs_dir=data_dir,
            force_rebuild=force_rebuild,
        )
        print(f"  - Successfully ingested {patient_id}!")

if __name__ == "__main__":
    ingest_all_patients()
