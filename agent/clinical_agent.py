# agent/clinical_agent.py
"""
Simple clinical documentation agent using LangChain.

WHAT IS A REACT AGENT:
    ReAct = Reasoning + Acting.
    The agent follows this loop:
        1. THINK:  "What do I need to do?"
        2. ACT:    Call a tool
        3. OBSERVE: Read the tool's output
        4. REPEAT:  Until the task is done
        5. RESPOND: Give the final answer

    Example reasoning:
        Thought: The doctor uploaded audio. I need to transcribe it first.
        Action:  transcribe_audio("recording.wav")
        Observation: "Patient reports chest pain and shortness of breath..."
        Thought: Now I should generate a SOAP note from this transcript.
        Action:  generate_soap("Patient reports chest pain...")
        Observation: "S: Patient reports... O: ... A: ... P: ..."
        Thought: I should save this to the database.
        Action:  save_patient_record(...)
        Final Answer: "I've transcribed the audio, generated a SOAP note..."

WHY NOT AUTONOMOUS AGENTS:
    We're using a simple tool-calling agent, NOT an autonomous system.
    The agent handles ONE task at a time. It doesn't make decisions
    about what to do next without the doctor's input.
"""
import logging
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from tools.clinical_tools import ALL_TOOLS
from agent.prompts import SYSTEM_PROMPT
from memory.session_memory import SessionContext

logger = logging.getLogger("agent.clinical_agent")


class ClinicalAgent:
    """
    Simple clinical documentation agent.

    Uses ChatOllama with tool binding for structured tool calls.
    Maintains session memory across interactions.
    """

    def __init__(self, model: str = "llama3.2:1b"):
        # Bind tools to the LLM so it knows what's available
        self.llm = ChatOllama(model=model, temperature=0.0)
        self.llm_with_tools = self.llm.bind_tools(ALL_TOOLS)
        self.tools_by_name = {t.name: t for t in ALL_TOOLS}
        self.session = SessionContext()
        logger.info("Clinical agent initialized with model: %s", model)

    def _build_system_prompt(self) -> str:
        """Build system prompt with current session context."""
        context = self.session.get_full_context()
        return SYSTEM_PROMPT.format(context=context)

    def run(self, user_input: str, patient_name: str = None) -> str:
        """
        Process a user request through the agent.

        This is a simplified ReAct loop:
        1. Send the user message with tools to the LLM
        2. If the LLM calls a tool, execute it and feed the result back
        3. Repeat until the LLM gives a final text response

        Args:
            user_input: The doctor's request.
            patient_name: Optional patient name for context.

        Returns:
            The agent's final response.
        """
        # Set patient context if provided
        if patient_name:
            self.session.set_patient(patient_name)

        # Build messages
        system_msg = SystemMessage(content=self._build_system_prompt())
        human_msg = HumanMessage(content=user_input)
        messages = [system_msg, human_msg]

        # Log the interaction
        self.session.conversation.add("user", user_input)
        logger.info("Agent processing: %s", user_input[:100])

        # Agent loop (max 10 iterations to prevent infinite loops)
        for step in range(10):
            response = self.llm_with_tools.invoke(messages)
            messages.append(response)

            # Check if the LLM called any tools
            if not response.tool_calls:
                # No tool calls = final answer
                final_answer = response.content
                self.session.conversation.add("agent", final_answer)
                logger.info("Agent finished after %d steps", step + 1)
                return final_answer

            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                logger.info("Agent calling tool: %s(%s)", tool_name, tool_args)

                if tool_name in self.tools_by_name:
                    try:
                        result = self.tools_by_name[tool_name].invoke(tool_args)
                    except Exception as e:
                        result = f"Tool error: {str(e)}"
                        logger.error("Tool %s failed: %s", tool_name, e)
                else:
                    result = f"Unknown tool: {tool_name}"

                # Feed tool result back to the LLM
                from langchain_core.messages import ToolMessage
                messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

        # Safety: if we hit max iterations
        logger.warning("Agent hit max iterations")
        return "I wasn't able to complete the task. Please try again with a simpler request."

    def process_transcript(self, transcript: str, patient_name: str) -> str:
        """
        Convenience method: process a transcript end-to-end.

        Shortcut that bypasses the agent loop for direct pipeline execution.
        Useful when you don't need the agent's reasoning — just want results.
        """
        self.session.set_patient(patient_name)
        self.session.set_transcript(transcript)

        return self.run(
            f"Process this clinical transcript for patient {patient_name}. "
            f"Generate a SOAP note, validate it, and save the record. "
            f"Transcript: {transcript}",
            patient_name=patient_name,
        )

    def reset(self):
        """Reset the agent session."""
        self.session.reset()
        logger.info("Agent session reset")
