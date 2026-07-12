import os
import sys
import unittest

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MEDIFLOW_API_URL, MEDIFLOW_EMBEDDING_MODEL, MEDIFLOW_LLM_MODEL, RAG_EMBEDDING_PROVIDER
from agents import router as agents_router


class FailingLLM:
    def __init__(self, *args, **kwargs):
        pass

    def invoke(self, *args, **kwargs):
        raise ConnectionError("Ollama offline")


@pytest.mark.unit
class TestLocalDemoConfig(unittest.IsolatedAsyncioTestCase):
    def test_default_local_demo_settings(self):
        self.assertEqual(MEDIFLOW_LLM_MODEL, os.getenv("MEDIFLOW_LLM_MODEL", "llama3.2:1b"))
        self.assertEqual(MEDIFLOW_EMBEDDING_MODEL, os.getenv("MEDIFLOW_EMBEDDING_MODEL", "nomic-embed-text"))
        self.assertEqual(RAG_EMBEDDING_PROVIDER, os.getenv("RAG_EMBEDDING_PROVIDER", "ollama").lower())
        self.assertEqual(MEDIFLOW_API_URL, os.getenv("MEDIFLOW_API_URL", "http://localhost:8000"))

    async def test_dashboard_qa_falls_back_when_llm_offline(self):
        original_llm = agents_router.get_chat_llm
        agents_router.get_chat_llm = FailingLLM
        try:
            response = await agents_router.ask_dashboard(
                agents_router.AskRequest(query="How many patients are in the database?")
            )
        finally:
            agents_router.get_chat_llm = original_llm

        self.assertIn("answer", response)
        self.assertIn("Local LLM service is offline", response["answer"])


if __name__ == "__main__":
    unittest.main()
