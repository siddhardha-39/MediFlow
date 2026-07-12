# clinical_workflow/languagetool.py
"""
LanguageTool client and warning models.

Handles checking text quality using LanguageTool's REST API.
"""
import logging
from typing import Optional, List
import httpx
from pydantic import BaseModel

from config import MEDIFLOW_LANGUAGETOOL_URL, MEDIFLOW_LANGUAGETOOL_TIMEOUT_SECONDS

logger = logging.getLogger("workflow.languagetool")


class LanguageToolWarning(BaseModel):
    """Structured representation of a single grammar/style warning."""
    message: str
    rule_id: str
    category: str
    offset: int
    length: int
    replacements: List[str]
    matched_text: str


class LanguageToolCheckResult(BaseModel):
    """Result of checking a text snippet, including success status or errors."""
    success: bool
    warnings: List[LanguageToolWarning] = []
    error_type: Optional[str] = None  # "timeout", "connection_failure", "http_error", "json_error", "unexpected_structure"
    error_detail: Optional[str] = None


def check_text(
    text: str,
    language: str = "en-US",
    url: str = MEDIFLOW_LANGUAGETOOL_URL,
    timeout: float = MEDIFLOW_LANGUAGETOOL_TIMEOUT_SECONDS,
) -> LanguageToolCheckResult:
    """
    Check the spelling, grammar, and style of the text using LanguageTool.

    Does not send an HTTP request if the text is empty or whitespace-only.
    """
    # 1. Skip check if empty or whitespace-only
    if not text or not text.strip():
        return LanguageToolCheckResult(success=True, warnings=[])

    try:
        # 2. Make the HTTP request
        resp = httpx.post(
            url,
            data={"text": text, "language": language},
            timeout=timeout,
        )
        # Raise exception for non-2xx status codes
        resp.raise_for_status()

    except httpx.TimeoutException as e:
        logger.warning("LanguageTool request timed out (timeout=%s): %s", timeout, e)
        return LanguageToolCheckResult(
            success=False,
            error_type="timeout",
            error_detail=str(e),
        )
    except httpx.ConnectError as e:
        logger.warning("LanguageTool connection failed (url=%s): %s", url, e)
        return LanguageToolCheckResult(
            success=False,
            error_type="connection_failure",
            error_detail=str(e),
        )
    except httpx.HTTPStatusError as e:
        logger.warning("LanguageTool returned HTTP error status %s: %s", resp.status_code, e)
        return LanguageToolCheckResult(
            success=False,
            error_type="http_error",
            error_detail=f"Status {resp.status_code}: {e}",
        )
    except Exception as e:
        # Re-raise unexpected/programming errors, swallow only standard HTTP ones
        if isinstance(e, (httpx.RequestError, httpx.HTTPError)):
            logger.warning("LanguageTool HTTP request error: %s", e)
            return LanguageToolCheckResult(
                success=False,
                error_type="connection_failure",
                error_detail=str(e),
            )
        raise e

    # 3. Parse JSON response
    try:
        data = resp.json()
    except Exception as e:
        logger.warning("LanguageTool returned malformed JSON: %s", e)
        return LanguageToolCheckResult(
            success=False,
            error_type="json_error",
            error_detail=str(e),
        )

    # 4. Map JSON to structured Warning objects
    if not isinstance(data, dict) or "matches" not in data:
        logger.warning("LanguageTool response missing 'matches' key or not a dictionary")
        return LanguageToolCheckResult(
            success=False,
            error_type="unexpected_structure",
            error_detail="Missing 'matches' key in JSON response",
        )

    warnings: List[LanguageToolWarning] = []
    for match in data["matches"]:
        try:
            msg = match.get("message", "")
            rule = match.get("rule", {})
            rule_id = rule.get("id", "") if isinstance(rule, dict) else ""
            category = rule.get("category", {}).get("name", "") if isinstance(rule, dict) and isinstance(rule.get("category"), dict) else ""
            offset = int(match.get("offset", 0))
            length = int(match.get("length", 0))
            
            reps = [r.get("value", "") for r in match.get("replacements", []) if isinstance(r, dict)]
            
            # Derive matched text safely using offset and length
            matched_text = ""
            if 0 <= offset < len(text) and length > 0:
                matched_text = text[offset : offset + length]

            warnings.append(
                LanguageToolWarning(
                    message=msg,
                    rule_id=rule_id,
                    category=category,
                    offset=offset,
                    length=length,
                    replacements=reps,
                    matched_text=matched_text,
                )
            )
        except Exception as e:
            # Prevent single malformed match from crashing entire response parsing
            logger.warning("Failed to parse LanguageTool match %s: %s", match, e)

    return LanguageToolCheckResult(success=True, warnings=warnings)
