# Documentation: `document_loading/pdf_loader.py`

## Purpose
This script represents the **Loader** and **Chunker** phases of the RAG pipeline. It takes raw PDF files, extracts the embedded text, and intelligently breaks the text down into optimized, overlapping chunks that can be efficiently processed by a vector embedding model.

## Code Explanation

```python
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def load_and_chunk_pdf(pdf_path: str | Path, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[Document]:
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"Patient PDF not found: {path}")

    # 1. Loader: Extract raw text from the PDF pages
    loader = PyPDFLoader(str(path))
    documents = loader.load()

    # 2. Chunker: Split text into overlapping segments
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = text_splitter.split_documents(documents)
    return chunks
```

## How It Works
1. **Validation**: Checks if the provided PDF path actually exists on the disk.
2. **PyPDFLoader**: This LangChain integration opens the PDF file and pulls out the text layer page-by-page.
3. **RecursiveCharacterTextSplitter**: 
   - `chunk_size=1000`: We enforce a hard limit of 1000 characters per chunk to ensure the text isn't too large for the embedding model to represent accurately.
   - `chunk_overlap=200`: A 200-character overlap between consecutive chunks ensures we don't accidentally cut off important context (like a sentence splitting mid-way).
   - `separators`: It tries to split nicely on paragraphs (`\n\n`) first, then single lines (`\n`), and only defaults to hard splits if a single paragraph is too massive.
4. **Output**: Returns an array of `Document` objects, each containing a chunk of text and its metadata.
