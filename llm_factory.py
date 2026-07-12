import os
import logging

from config import MEDIFLOW_LLM_MODEL

logger = logging.getLogger("llm_factory")

def get_llm_provider() -> str:
    """Determine the configured LLM provider."""
    # Check explicitly defined provider first
    provider = os.getenv("MEDIFLOW_LLM_PROVIDER", "").strip().lower()
    if provider:
        return provider

    # Fallback heuristic: check if API keys are set
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini"
    
    return "ollama"

# Subclass ChatGoogleGenerativeAI to extract only the text content block (handling thinking blocks in Gemma 4)
def get_clean_chat_google_generative_ai_class():
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    class CleanChatGoogleGenerativeAI(ChatGoogleGenerativeAI):
        def invoke(self, *args, **kwargs):
            response = super().invoke(*args, **kwargs)
            if hasattr(response, "content") and isinstance(response.content, list):
                text_parts = []
                for part in response.content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        text_parts.append(part)
                response.content = "".join(text_parts)
            return response
            
    return CleanChatGoogleGenerativeAI

def get_chat_llm(model_name: str = None, temperature: float = 0.0):
    """
    Get a chat model instance (CleanChatGoogleGenerativeAI or ChatOllama)
    based on the configured provider.
    """
    model = model_name or MEDIFLOW_LLM_MODEL
    provider = get_llm_provider()
    
    logger.info("Initializing chat LLM: provider=%s, model=%s, temp=%.1f", provider, model, temperature)
    
    if provider == "gemini":
        CleanChatGoogleGenerativeAI = get_clean_chat_google_generative_ai_class()
        
        # Verify API key
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("Gemini API key is not set, ChatGoogleGenerativeAI might fail.")
            
        return CleanChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key
        )
    else:
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model, temperature=temperature)

def get_llm(model_name: str = None, temperature: float = 0.0):
    """
    Get a legacy text completion model instance (GoogleGenerativeAI or OllamaLLM)
    based on the configured provider.
    """
    model = model_name or MEDIFLOW_LLM_MODEL
    provider = get_llm_provider()
    
    logger.info("Initializing LLM: provider=%s, model=%s, temp=%.1f", provider, model, temperature)
    
    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAI
        
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("Gemini API key is not set, GoogleGenerativeAI might fail.")
            
        return GoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key
        )
    else:
        from langchain_ollama import OllamaLLM
        return OllamaLLM(model=model, temperature=temperature)
