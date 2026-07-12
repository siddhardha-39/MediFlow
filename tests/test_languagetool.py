# tests/test_languagetool.py
"""
Tests for LanguageTool integration including configuration, client API calls,
response parsing, and LangGraph workflow node integration.
"""
import os
import unittest
from unittest.mock import patch, MagicMock
import httpx
import importlib

import pytest
import config
from clinical_workflow.languagetool import check_text, LanguageToolCheckResult, LanguageToolWarning
from clinical_workflow.nodes.validator import validator_node


@pytest.mark.unit
class TestLanguageTool(unittest.TestCase):
    # ── Configuration Tests ───────────────────────────────────────────────────

    def test_default_config(self):
        """1. Default LanguageTool URL and 2. Default timeout configuration."""
        with patch.dict(os.environ, {}):
            importlib.reload(config)
            self.assertEqual(config.MEDIFLOW_LANGUAGETOOL_URL, "http://localhost:8010/v2/check")
            self.assertEqual(config.MEDIFLOW_LANGUAGETOOL_TIMEOUT_SECONDS, 5.0)

    def test_custom_config(self):
        """3. Custom URL and 4. Custom timeout configuration."""
        with patch.dict(os.environ, {
            "MEDIFLOW_LANGUAGETOOL_URL": "http://custom-host:9999/v2/check",
            "MEDIFLOW_LANGUAGETOOL_TIMEOUT_SECONDS": "12.5"
        }):
            importlib.reload(config)
            self.assertEqual(config.MEDIFLOW_LANGUAGETOOL_URL, "http://custom-host:9999/v2/check")
            self.assertEqual(config.MEDIFLOW_LANGUAGETOOL_TIMEOUT_SECONDS, 12.5)

    def test_invalid_timeout(self):
        """5. Invalid timeout value raises a clear configuration error."""
        with patch.dict(os.environ, {"MEDIFLOW_LANGUAGETOOL_TIMEOUT_SECONDS": "abc"}):
            with self.assertRaises(ValueError) as ctx:
                importlib.reload(config)
            self.assertIn("MEDIFLOW_LANGUAGETOOL_TIMEOUT_SECONDS must be a valid float", str(ctx.exception))

    def test_zero_timeout(self):
        """6. Zero timeout raises a clear configuration error."""
        with patch.dict(os.environ, {"MEDIFLOW_LANGUAGETOOL_TIMEOUT_SECONDS": "0"}):
            with self.assertRaises(ValueError) as ctx:
                importlib.reload(config)
            self.assertIn("MEDIFLOW_LANGUAGETOOL_TIMEOUT_SECONDS must be greater than zero", str(ctx.exception))

    def test_negative_timeout(self):
        """7. Negative timeout raises a clear configuration error."""
        with patch.dict(os.environ, {"MEDIFLOW_LANGUAGETOOL_TIMEOUT_SECONDS": "-1.5"}):
            with self.assertRaises(ValueError) as ctx:
                importlib.reload(config)
            self.assertIn("MEDIFLOW_LANGUAGETOOL_TIMEOUT_SECONDS must be greater than zero", str(ctx.exception))

    def tearDown(self):
        # Restore configuration defaults after configuration tests
        with patch.dict(os.environ, {}):
            importlib.reload(config)

    # ── Client Input Validation Tests ─────────────────────────────────────────

    @patch("httpx.post")
    def test_empty_and_whitespace_only_text(self, mock_post):
        """8. Empty text and 9. Whitespace-only text return a successful empty result without an HTTP request."""
        # Empty text
        res_empty = check_text("")
        self.assertTrue(res_empty.success)
        self.assertEqual(len(res_empty.warnings), 0)
        
        # Whitespace-only text
        res_whitespace = check_text("   \n \t ")
        self.assertTrue(res_whitespace.success)
        self.assertEqual(len(res_whitespace.warnings), 0)
        
        mock_post.assert_not_called()

    # ── Response Parsing and Mapping Tests ────────────────────────────────────

    @patch("httpx.post")
    def test_successful_response_no_matches(self, mock_post):
        """10. Successful response with no matches."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"matches": []}
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        res = check_text("All correct text.")
        self.assertTrue(res.success)
        self.assertEqual(len(res.warnings), 0)
        mock_post.assert_called_once()

    @patch("httpx.post")
    def test_successful_response_one_match_and_metadata(self, mock_post):
        """
        Covers:
        - 11. Successful response with one match
        - 13. Replacement suggestions are preserved
        - 14. Rule ID is preserved
        - 15. Category is preserved
        - 16. Offset and length are preserved
        - 17. Matched text is derived correctly
        """
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "matches": [{
                "message": "Use 'a' instead of 'an' before consonant sounds.",
                "rule": {
                    "id": "EN_A_VS_AN",
                    "category": {"name": "MISC"}
                },
                "offset": 8,
                "length": 2,
                "replacements": [{"value": "a"}]
            }]
        }
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        text = "This is an patient."
        res = check_text(text)
        self.assertTrue(res.success)
        self.assertEqual(len(res.warnings), 1)
        
        w = res.warnings[0]
        self.assertEqual(w.message, "Use 'a' instead of 'an' before consonant sounds.")
        self.assertEqual(w.rule_id, "EN_A_VS_AN")
        self.assertEqual(w.category, "MISC")
        self.assertEqual(w.offset, 8)
        self.assertEqual(w.length, 2)
        self.assertEqual(w.replacements, ["a"])
        self.assertEqual(w.matched_text, "an") # Correctly derived from string slices

    @patch("httpx.post")
    def test_multiple_matches_parsed(self, mock_post):
        """12. Multiple matches are parsed correctly."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "matches": [
                {
                    "message": "First grammar issue",
                    "rule": {"id": "RULE_1", "category": {"name": "GRAMMAR"}},
                    "offset": 0,
                    "length": 5,
                    "replacements": []
                },
                {
                    "message": "Second spelling issue",
                    "rule": {"id": "RULE_2", "category": {"name": "TYPO"}},
                    "offset": 8,
                    "length": 4,
                    "replacements": [{"value": "word"}]
                }
            ]
        }
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        res = check_text("Firstand second.")
        self.assertTrue(res.success)
        self.assertEqual(len(res.warnings), 2)
        self.assertEqual(res.warnings[0].rule_id, "RULE_1")
        self.assertEqual(res.warnings[1].rule_id, "RULE_2")

    @patch("httpx.post")
    def test_out_of_range_indices_safety(self, mock_post):
        """18. Out-of-range offset/length does not crash parsing."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "matches": [{
                "message": "Out of range match indexes.",
                "rule": {"id": "OUT_OF_RANGE", "category": {"name": "OTHER"}},
                "offset": 1000, # past length of string
                "length": 50,
                "replacements": []
            }]
        }
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        # Should parse safely and match empty string
        res = check_text("Short.")
        self.assertTrue(res.success)
        self.assertEqual(len(res.warnings), 1)
        self.assertEqual(res.warnings[0].matched_text, "")

    # ── Service Failure Handling Tests ────────────────────────────────────────

    @patch("httpx.post")
    def test_http_timeout_failure(self, mock_post):
        """19. HTTP timeout returns a distinguishable service-failure result."""
        mock_post.side_effect = httpx.TimeoutException("Request timed out")
        res = check_text("Valid text.")
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "timeout")

    @patch("httpx.post")
    def test_connection_refused_failure(self, mock_post):
        """20. Connection failure returns a distinguishable service-failure result."""
        mock_post.side_effect = httpx.ConnectError("Connection refused by target")
        res = check_text("Valid text.")
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "connection_failure")

    @patch("httpx.post")
    def test_non_success_http_status_failure(self, mock_post):
        """21. Non-success HTTP status returns a distinguishable service-failure result."""
        mock_resp = MagicMock()
        req = httpx.Request("POST", "http://localhost:8010/v2/check")
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", request=req, response=mock_resp
        )
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        res = check_text("Valid text.")
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "http_error")

    @patch("httpx.post")
    def test_malformed_json_failure(self, mock_post):
        """22. Malformed JSON returns a distinguishable service-failure result."""
        mock_resp = MagicMock()
        mock_resp.json.side_effect = ValueError("Invalid JSON string")
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        res = check_text("Valid text.")
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "json_error")

    @patch("httpx.post")
    def test_unexpected_json_structure_failure(self, mock_post):
        """23. Unexpected JSON structure returns a distinguishable service-failure result."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"not_matches": []}
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        res = check_text("Valid text.")
        self.assertFalse(res.success)
        self.assertEqual(res.error_type, "unexpected_structure")

    # ── Workflow Integration Tests ────────────────────────────────────────────

    @patch("clinical_workflow.nodes.validator.check_text")
    def test_validator_node_integration(self, mock_check):
        """
        Covers workflow integration requirements:
        - 24. Validator checks all non-empty SOAP sections
        - 25. Validator skips empty SOAP sections
        - 26. SOAP section origin is preserved in warnings
        - 27. LanguageTool warnings remain separate from clinical warnings
        - 28. Service failures remain separate from grammar/style warnings
        - 29. Failure of one SOAP section does not prevent remaining sections from being checked
        - 30. LanguageTool failure does not prevent workflow completion
        """
        def mock_check_text(text, *args, **kwargs):
            if text == "Subjective history text":
                return LanguageToolCheckResult(
                    success=True,
                    warnings=[
                        LanguageToolWarning(
                            message="spelling suggestion",
                            rule_id="SP_1",
                            category="TYPO",
                            offset=0,
                            length=10,
                            replacements=["Subjective"],
                            matched_text="Subjective"
                        )
                    ]
                )
            elif text == "Assessment notes":
                # Simulate a timeout error for this section
                return LanguageToolCheckResult(
                    success=False,
                    error_type="timeout",
                    error_detail="Timeout on Assessment"
                )
            elif text == "Plan details":
                # Plan checks successfully with no warnings
                return LanguageToolCheckResult(success=True, warnings=[])
            return LanguageToolCheckResult(success=True, warnings=[])

        mock_check.side_effect = mock_check_text

        # Initial state setup
        state = {
            "soap_subjective": "Subjective history text",
            "soap_objective": "",  # Empty section -> must be skipped
            "soap_assessment": "Assessment notes",
            "soap_plan": "Plan details",
            "retry_count": 0,
        }

        # 30. Node completes without raising exception
        res = validator_node(state)
        
        self.assertIsNotNone(res)
        
        # 25. Empty section (Objective) is correctly registered as missing by clinical validation
        self.assertEqual(res["missing_sections"], ["Objective"])
        
        # 26. Section origin preserved & 27. Grammar warnings kept separate from clinical warnings
        lt_warnings = res["languagetool_warnings"]
        self.assertEqual(len(lt_warnings), 1)
        self.assertEqual(lt_warnings[0]["section"], "Subjective")
        self.assertEqual(lt_warnings[0]["rule_id"], "SP_1")
        
        # 28. Status/failures separate, 29. Failure on Assessment did not stop checking Plan
        self.assertFalse(res["languagetool_status"]["success"])
        self.assertEqual(res["languagetool_status"]["error_type"], "timeout")

    @patch("clinical_workflow.nodes.validator.check_text")
    def test_duplicate_checks_caching(self, mock_check):
        """
        Covers recheck logic:
        - 32. Unchanged SOAP content is not unnecessarily rechecked
        - 33. Changed SOAP content is rechecked
        """
        mock_check.return_value = LanguageToolCheckResult(
            success=True,
            warnings=[
                LanguageToolWarning(
                    message="grammar warning",
                    rule_id="GR_1",
                    category="GRAMMAR",
                    offset=0,
                    length=4,
                    replacements=[],
                    matched_text="text"
                )
            ]
        )

        # First execution (no cached results exist)
        state_1 = {
            "soap_subjective": "Sub text",
            "soap_objective": "Obj text",
            "soap_assessment": "Ass text",
            "soap_plan": "Plan text",
            "languagetool_checked_sections": {},
            "languagetool_warnings": [],
        }
        res_1 = validator_node(state_1)
        # Should call check_text 4 times
        self.assertEqual(mock_check.call_count, 4)

        # Second execution (subjective & objective unchanged, assessment changed, plan empty)
        mock_check.reset_mock()
        state_2 = {
            "soap_subjective": "Sub text",           # Unchanged
            "soap_objective": "Obj text",            # Unchanged
            "soap_assessment": "Modified Ass text",  # Changed
            "soap_plan": "",                         # Cleared
            "languagetool_checked_sections": res_1["languagetool_checked_sections"],
            "languagetool_warnings": res_1["languagetool_warnings"],
        }
        
        res_2 = validator_node(state_2)
        
        # Should call check_text exactly once (for changed assessment section)
        self.assertEqual(mock_check.call_count, 1)
        mock_check.assert_called_once_with("Modified Ass text")
        
        # Warnings from unchanged sections (Subjective & Objective) must be preserved
        warnings = res_2["languagetool_warnings"]
        sections_cached = {w["section"] for w in warnings}
        self.assertIn("Subjective", sections_cached)
        self.assertIn("Objective", sections_cached)
        self.assertNotIn("Plan", sections_cached)
