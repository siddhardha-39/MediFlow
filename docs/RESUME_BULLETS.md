# MediFlow Resume Highlights

### Project Title
**MediFlow: AI-Powered Clinical Intelligence & Documentation System**

### Project Description
An offline-first clinical assistant that automates clinical note-taking (SOAP notes) and summarizes medical history using stateful LangGraph workflows, local LLMs, and RAG.

### Resume Bullets

* **Engineered a Stateful Clinical Documentation Pipeline**: Designed a multi-node cyclical graph using **LangGraph** to process clinical consultation transcripts. Structured raw inputs into validated SOAP notes with built-in doctor correction loops and human-in-the-loop approval interrupts.
* **Architected Privacy-First AI & RAG Integration**: Built a local-first retrieval-augmented generation (**RAG**) engine using **ChromaDB** and local **Ollama** embeddings to index clinical PDFs. Applied strict metadata filtering to extract patient allergies, conditions, and medications, ensuring all clinical data is processed entirely on-premise without reliance on external cloud APIs.
* **Developed Resilient Database Persistence & Fallbacks**: Integrated **PostgreSQL** with an automatic **SQLite fallback** module in **FastAPI**, resolving SQL parameterization syntax differences dynamically. Implemented graceful degradation for secondary style-checking APIs (LanguageTool) to prevent workflow failures when services are offline.

### Technology Stack
Python, FastAPI, Streamlit, LangGraph, LangChain, ChromaDB, Ollama, PostgreSQL, SQLite, LanguageTool, Docker Compose, Pytest.
