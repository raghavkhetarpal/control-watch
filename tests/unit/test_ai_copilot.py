"""Unit tests for AI Copilot provider abstraction and helper methods."""
import os
import pytest

from backend.ai.copilot import AIAssistant, AIResponse


def test_ai_copilot_fallback_when_none(monkeypatch):
    """When AI_PROVIDER='none', returns template-based fallback with 0 tokens."""
    monkeypatch.setenv("AI_PROVIDER", "none")
    assistant = AIAssistant()
    res = assistant.analyze(
        query="Summarize risk status",
        context_type="general",
        evidence={"fund_name": "Test Fund", "open_exceptions": 2},
    )
    assert isinstance(res, AIResponse)
    assert "Template-based response" in res.response
    assert res.tokens_used == 0
    assert res.validation_status == "VALIDATED"
    assert len(res.evidence_hash) == 64


def test_ai_copilot_mock_openai(monkeypatch):
    """When AI_PROVIDER='openai' and key present, calls provider."""
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-mock-key")
    assistant = AIAssistant()
    res = assistant.analyze(
        query="What is the top exception?",
        context_type="exception",
        evidence={"control_id": "DQ-001"},
    )
    assert "[OpenAI Response]" in res.response
    assert res.tokens_used > 0


def test_ai_copilot_mock_groq(monkeypatch):
    """When AI_PROVIDER='groq' and key present, calls provider."""
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_mock_key")
    assistant = AIAssistant()
    res = assistant.analyze(
        query="Explain KRI trend",
        context_type="kri",
        evidence={"kri_id": "KRI-001", "value": 35.0},
    )
    assert "[Groq Response]" in res.response
    assert res.tokens_used > 0


def test_ai_copilot_summarize_fund(monkeypatch):
    """Test summarize_fund helper."""
    monkeypatch.setenv("AI_PROVIDER", "none")
    assistant = AIAssistant()
    summary = assistant.summarize_fund(
        fund_data={"fund_name": "Core Equity"},
        exceptions=[{"severity": "HIGH"}],
        kris=[{"kri_id": "KRI-001", "status": "GREEN"}],
    )
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_ai_copilot_explain_exception(monkeypatch):
    """Test explain_exception helper."""
    monkeypatch.setenv("AI_PROVIDER", "none")
    assistant = AIAssistant()
    exp = assistant.explain_exception({"id": 1, "description": "Duplicate holding"})
    assert isinstance(exp, str)


def test_ai_copilot_suggest_root_cause(monkeypatch):
    """Test suggest_root_cause helper."""
    monkeypatch.setenv("AI_PROVIDER", "none")
    assistant = AIAssistant()
    rc = assistant.suggest_root_cause({"control_id": "DQ-001"})
    assert isinstance(rc, str)


def test_ai_copilot_explain_kri(monkeypatch):
    """Test explain_kri helper."""
    monkeypatch.setenv("AI_PROVIDER", "none")
    assistant = AIAssistant()
    kri_exp = assistant.explain_kri({"kri_id": "KRI-001", "value": 42.0}, history=[35.0, 38.0])
    assert isinstance(kri_exp, str)


def test_ai_copilot_summarize_remediation(monkeypatch):
    """Test summarize_remediation helper."""
    monkeypatch.setenv("AI_PROVIDER", "none")
    assistant = AIAssistant()
    rem = assistant.summarize_remediation({"owner": "sarah.chen", "action": "Verify CUSIP"})
    assert isinstance(rem, str)
