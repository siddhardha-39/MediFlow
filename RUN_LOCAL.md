# MediFlow Local Demo Guide

This setup is tuned for an 8 GB RAM laptop.

## 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## 2. Configure Local Defaults

Create or update `.env` in the `MediFlow` folder:

```env
MEDIFLOW_LLM_MODEL=llama3.2:1b
MEDIFLOW_EMBEDDING_MODEL=nomic-embed-text
RAG_EMBEDDING_PROVIDER=ollama
MEDIFLOW_API_URL=http://localhost:8000
```

## 3. Start Ollama

```bash
ollama serve
```

In another terminal, pull the lightweight local models:

```bash
ollama pull llama3.2:1b
ollama pull nomic-embed-text
```

## 4. Start Backend

```bash
python app.py
```

Open API docs at:

```text
http://localhost:8000/docs
```

## 5. Start UI

```bash
streamlit run ui/app.py
```

## 8 GB RAM Tips

- Keep browser tabs, notebooks, and heavy apps closed during demos.
- Use `llama3.2:1b`; avoid 4B, 7B, or 8B models for now.
- Ingest only a few PDFs while testing RAG.
- If Ollama is offline, dashboard stats and saved patient history still work, but SOAP/RAG generation will show fallback messages.
