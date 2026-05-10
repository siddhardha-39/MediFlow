# memory/session_memory.py
"""
Patient session memory.

WHAT IS MEMORY IN AN AI SYSTEM:
    Memory = giving the LLM context about what happened before.
    Without memory, every request is isolated — the agent forgets everything.

    In a clinical system, memory means:
    - Remembering what was discussed in THIS session (conversation memory)
    - Remembering PAST visits for this patient (patient history)
    - Providing relevant context to improve SOAP note quality

THREE TYPES OF MEMORY HERE:
    1. ConversationMemory - tracks the current agent conversation
    2. PatientContext     - retrieves past visit history from the database
    3. SessionContext     - combines both for the agent prompt

WHY NOT USE LANGCHAIN'S BUILT-IN MEMORY:
    LangChain's memory modules are designed for chatbot conversations.
    Our use case is different — we need clinical session context.
    A simple Python class is clearer and more maintainable.
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime

from database.db import get_patient_by_name, get_patient_history

logger = logging.getLogger("memory.session_memory")


class ConversationMemory:
    """
    Simple conversation memory for the current agent session.

    Stores a list of (role, message) tuples.
    The agent can look back at what was said earlier in the conversation.
    """

    def __init__(self, max_turns: int = 20):
        self.messages: List[Dict[str, str]] = []
        self.max_turns = max_turns

    def add(self, role: str, content: str):
        """Add a message to the conversation history."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        # Keep only the most recent messages to avoid context overflow
        if len(self.messages) > self.max_turns:
            self.messages = self.messages[-self.max_turns:]

    def get_history(self) -> str:
        """Get formatted conversation history for the agent prompt."""
        if not self.messages:
            return "No conversation history."

        lines = []
        for msg in self.messages:
            lines.append(f"[{msg['role']}]: {msg['content']}")
        return "\n".join(lines)

    def clear(self):
        """Clear the conversation history."""
        self.messages = []
        logger.info("Conversation memory cleared")


class PatientContext:
    """
    Retrieves and caches patient history from the database.

    WHY CACHE:
        Database queries are fast for SQLite, but if we later move to
        PostgreSQL or add a vector DB lookup, caching prevents redundant
        calls during a single agent session.
    """

    def __init__(self):
        self._cache: Dict[str, str] = {}

    def get_context(self, patient_name: str) -> str:
        """
        Get patient history context for the agent.

        Returns formatted text the agent can use to understand
        the patient's background.
        """
        if patient_name in self._cache:
            return self._cache[patient_name]

        patient = get_patient_by_name(patient_name)
        if not patient:
            context = f"No previous records found for patient '{patient_name}'. This appears to be a new patient."
        else:
            context = get_patient_history(patient["id"])

        self._cache[patient_name] = context
        logger.info("Patient context loaded for: %s", patient_name)
        return context

    def invalidate(self, patient_name: str = None):
        """Clear cache for a patient (or all patients)."""
        if patient_name:
            self._cache.pop(patient_name, None)
        else:
            self._cache.clear()


class SessionContext:
    """
    Combines conversation memory and patient context into a single
    context block for the agent.

    This is what gets injected into the agent's system prompt.
    """

    def __init__(self):
        self.conversation = ConversationMemory()
        self.patient = PatientContext()
        self.current_patient: Optional[str] = None
        self.current_transcript: Optional[str] = None

    def set_patient(self, name: str):
        """Set the current patient for this session."""
        self.current_patient = name
        logger.info("Session patient set: %s", name)

    def set_transcript(self, text: str):
        """Store the current transcript in the session."""
        self.current_transcript = text

    def get_full_context(self) -> str:
        """
        Build the complete context string for the agent.

        Includes:
        - Patient history (if patient is set)
        - Current transcript (if available)
        - Conversation history
        """
        parts = []

        if self.current_patient:
            parts.append("=== Patient History ===")
            parts.append(self.patient.get_context(self.current_patient))
            parts.append("")

        if self.current_transcript:
            parts.append("=== Current Transcript ===")
            parts.append(self.current_transcript[:2000])  # Truncate for context window
            parts.append("")

        history = self.conversation.get_history()
        if history != "No conversation history.":
            parts.append("=== Conversation History ===")
            parts.append(history)

        return "\n".join(parts) if parts else "No context available."

    def reset(self):
        """Reset the entire session."""
        self.conversation.clear()
        self.patient.invalidate()
        self.current_patient = None
        self.current_transcript = None
        logger.info("Session context reset")
