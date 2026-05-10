import sys
from pathlib import Path

# Add project root to sys.path so we can import from document_loading and db
sys.path.append(str(Path(__file__).parent.parent))

from document_loading.pdf_loader import load_and_chunk_pdf
from db.chroma_store import add_documents_to_db

def ingest_all_patients():
    """
    Loops through all PDFs in data/sample_patients, extracts text, chunks it,
    and stores the embeddings in separate ChromaDB folders per patient.
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
        
        # 1. Loader & Chunker
        chunks = load_and_chunk_pdf(pdf_path)
        print(f"  - Generated {len(chunks)} chunks.")
        
        # 2. Embeddings & ChromaDB (Stored separately per patient ID)
        print(f"  - Storing embeddings in ChromaDB...")
        add_documents_to_db(chunks, patient_id=patient_id)
        
        print(f"  - Successfully ingested {patient_id}!")

if __name__ == "__main__":
    ingest_all_patients()
