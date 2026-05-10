# Documentation: `agents/Patient_history_summeriser.py`

## Purpose
This script represents the final **LLM & Doctor Summary** layer of the pipeline. It acts as the intelligent agent that pulls retrieved vector data and forces the language model to generate a strict, time-saving clinical briefing for the doctor.

## Code Explanation

```python
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from db.chroma_store import get_retriever

# 1. System Prompt Definition
MEDICAL_SUMMARY_PROMPT = \"\"\"You are a clinical assistant... [Prompt omitted for brevity]\"\"\"

def generate_patient_briefing(patient_record_context: str, *, model_name: str = "llama3.2:1b", temperature: float = 0.0) -> str:
    # 2. LLM Engine Initialization
    llm = ChatOllama(model=model_name, temperature=temperature)
    
    # 3. Prompt Wrapping
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a clinical assistant. Always follow the exact format given. Never add extra commentary."),
        ("human", MEDICAL_SUMMARY_PROMPT),
    ])
    
    # 4. LangChain LCEL (Execution Chain)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"patient_record": patient_record_context})

def summarize_patient(patient_id: str, *, model_name: str = "llama3.2:1b") -> str:
    # 5. Database Retrieval
    retriever = get_retriever(patient_id=patient_id, k=5)
    
    # 6. Context Extraction Query
    docs = retriever.invoke("What is the patient's name, age, medical history, medications, allergies, and recent visits?")
    context = "\n\n".join(doc.page_content for doc in docs)
    
    # 7. Summary Generation
    briefing = generate_patient_briefing(context, model_name=model_name)
    return briefing

if __name__ == "__main__":
    patient_id = "PT-2024-001-Rajesh-Kumar"
    briefing = summarize_patient(patient_id)
    print(briefing)
```

## How It Works
1. **System Prompt**: Enforces the exact markdown format using headers like `[CRITICAL ALERTS]`. We avoided emojis here because they caused `UnicodeEncodeError` in Windows CMD environments.
2. **LLM Engine**: It instantiates the lightweight `llama3.2:1b` model running locally via Ollama with a temperature of `0.0` to prevent hallucinations and keep the AI strictly factual.
3. **Retrieval Search**: The agent queries the database using a natural language question. The embedding engine calculates the vector distance of this question and returns the 5 most mathematically similar text chunks from the patient's database folder.
4. **Context Injection**: The chunks are joined into a single massive string and fed directly into the `{patient_record}` variable of the prompt.
5. **Execution**: The prompt is processed by the LLM and the final string is returned to the terminal.
