from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def load_and_chunk_pdf(pdf_path: str | Path, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[Document]:
    """
    Loads a PDF and splits it into smaller chunks.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"Patient PDF not found: {path}")

    # 1. Loader
    loader = PyPDFLoader(str(path))
    documents = loader.load()

    # 2. Chunker
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = text_splitter.split_documents(documents)
    return chunks

if __name__ == "__main__":
    # Small test
    test_pdf = Path(__file__).parent.parent / "data" / "sample_patients" / "PT-2024-001-Rajesh-Kumar.pdf"
    if test_pdf.exists():
        chunks = load_and_chunk_pdf(test_pdf)
        print(f"Loaded and split into {len(chunks)} chunks.")