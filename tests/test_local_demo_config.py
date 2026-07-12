import os
import sys
import unittest

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MEDIFLOW_API_URL, MEDIFLOW_EMBEDDING_MODEL, MEDIFLOW_LLM_MODEL, RAG_EMBEDDING_PROVIDER
from agents import router as agents_router


@pytest.mark.unit
class TestLocalDemoConfig(unittest.IsolatedAsyncioTestCase):
    def test_default_local_demo_settings(self):
        self.assertEqual(MEDIFLOW_LLM_MODEL, os.getenv("MEDIFLOW_LLM_MODEL", "gemma-4-31b-it"))
        self.assertEqual(MEDIFLOW_EMBEDDING_MODEL, os.getenv("MEDIFLOW_EMBEDDING_MODEL", "BAAI/bge-small-en"))
        self.assertEqual(RAG_EMBEDDING_PROVIDER, os.getenv("RAG_EMBEDDING_PROVIDER", "huggingface").lower())
        self.assertEqual(MEDIFLOW_API_URL, os.getenv("MEDIFLOW_API_URL", "http://localhost:8000"))

    async def test_dashboard_qa_uses_mock_llm(self):
        response = await agents_router.ask_dashboard(
            agents_router.AskRequest(query="How many patients are in the database?")
        )

        self.assertIn("answer", response)
        self.assertIn("mock LLM responded", response["answer"])


if __name__ == "__main__":
    unittest.main()
