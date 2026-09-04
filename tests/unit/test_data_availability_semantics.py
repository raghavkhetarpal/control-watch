"""Unit tests for Phase 3: Data availability semantics, REC-002 integrity, and AI missing-evidence handling."""
import pytest
from unittest.mock import MagicMock
from datetime import date

from backend.controls.base import ControlResult
from backend.controls.reconciliation import PortfolioCompletenessControl
from backend.risk_engine.scoring import calculate_risk_score, score_exception, assign_severity
from backend.ai.copilot import AIAssistant, AIResponse


def test_rec002_separates_data_unavailable_from_analytical():
    """REC-002 must classify funds with 0 holdings as DATA_AVAILABILITY and funds with diff > 10% as ANALYTICAL_EXCEPTION."""
    ctrl = PortfolioCompletenessControl()
    assert ctrl.control_id == "REC-002"
    assert ctrl.TOLERANCE_PCT == 10.0
    assert "funds.total_assets" in ctrl.data_requirements

    # Mock database session returning two funds:
    # Fund 1: reports 10,000,000 total assets, but 0 holdings (schedule missing)
    # Fund 2: reports 10,000,000 total assets, holdings total 8,000,000 (20% diff, analytical exception)
    # Fund 3: reports 10,000,000 total assets, holdings total 9,500,000 (5% diff, passes within 10% tolerance)
    mock_session = MagicMock()
    mock_session.execute.return_value.mappings.return_value.all.return_value = [
        {"fund_id": 1, "fund_name": "Fund No Schedule", "total_assets": 10000000.0, "holdings_total": 0.0, "holding_count": 0},
        {"fund_id": 2, "fund_name": "Fund Inconsistent", "total_assets": 10000000.0, "holdings_total": 8000000.0, "holding_count": 50},
        {"fund_id": 3, "fund_name": "Fund Clean", "total_assets": 10000000.0, "holdings_total": 9500000.0, "holding_count": 100},
    ]

    res = ctrl.execute(mock_session, date(2025, 6, 30))
    assert res.records_scanned == 3
    assert res.testable_records == 2
    assert res.not_testable_records == 1
    assert res.coverage_ratio == round(2 / 3, 4)
    assert len(res.exceptions) == 2

    # Verify exception types
    data_avail_exc = next(e for e in res.exceptions if e["fund_id"] == 1)
    assert data_avail_exc["exception_type"] == "DATA_AVAILABILITY"
    assert data_avail_exc["severity"] == "LOW"
    assert "Holdings data unavailable" in data_avail_exc["description"]

    analytical_exc = next(e for e in res.exceptions if e["fund_id"] == 2)
    assert analytical_exc["exception_type"] == "ANALYTICAL_EXCEPTION"
    assert analytical_exc["severity"] == "MEDIUM"  # 20% diff is <= 25%
    assert analytical_exc["evidence"]["difference_pct"] == 20.0

    # Fund 3 should not be in exceptions (passed within 10% tolerance)
    assert not any(e["fund_id"] == 3 for e in res.exceptions)

    # Pass rate calculated over testable records (1 passed / 2 testable = 50.0%)
    assert res.pass_rate == 50.0


def test_risk_scoring_insufficient_evidence():
    """When exception is DATA_AVAILABILITY or missing evidence, score must be 0 and risk_level INSUFFICIENT_EVIDENCE."""
    score, level, breakdown = score_exception({"exception_type": "DATA_AVAILABILITY", "severity": "LOW"})
    assert score == 0
    assert level == "INSUFFICIENT_EVIDENCE"
    assert breakdown["risk_status"] == "INSUFFICIENT_EVIDENCE"

    score2, level2, breakdown2 = score_exception({"is_data_unavailable": True})
    assert score2 == 0
    assert level2 == "INSUFFICIENT_EVIDENCE"

    # Severity assignment for DATA_AVAILABILITY is always LOW
    sev = assign_severity("REC-002", {"exception_type": "DATA_AVAILABILITY", "severity": "HIGH"})
    assert sev == "LOW"


def test_ai_copilot_missing_evidence_refusal(monkeypatch):
    """AI copilot must explicitly state insufficient evidence when data is missing or DATA_AVAILABILITY."""
    monkeypatch.setenv("AI_PROVIDER", "none")
    assistant = AIAssistant()

    # Empty evidence
    res1 = assistant.analyze(
        query="Did this fund breach limits?",
        context_type="exception",
        evidence={},
    )
    assert res1.response == "There is insufficient evidence in the reported filings to determine whether this represents a genuine control breach."
    assert res1.tokens_used == 0

    # Explicit DATA_AVAILABILITY exception
    res2 = assistant.analyze(
        query="Explain this failure",
        context_type="exception",
        evidence={"exception_type": "DATA_AVAILABILITY", "fund_name": "Incomplete Fund"},
    )
    assert res2.response == "There is insufficient evidence in the reported filings to determine whether this represents a genuine control breach."


def test_control_result_evaluation_status():
    """ControlResult supports NOT_TESTABLE, PARTIAL, and COMPLETED evaluation statuses."""
    res_not_testable = ControlResult(
        control_id="REC-001",
        name="Period-over-Period Reconciliation",
        status="COMPLETED",
        records_scanned=100,
        exceptions_found=0,
        pass_rate=100.0,
        duration_ms=10,
        testable_records=0,
        not_testable_records=100,
        evaluation_status="NOT_TESTABLE",
        coverage_ratio=0.0,
    )
    assert res_not_testable.evaluation_status == "NOT_TESTABLE"
    assert res_not_testable.coverage_ratio == 0.0
