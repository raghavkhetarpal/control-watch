"""Unit tests for deterministic risk scoring."""
import pytest
from backend.risk_engine.scoring import calculate_risk_score, score_exception, assign_severity


def test_low_risk_score():
    """Test low risk score calculation."""
    score, level = calculate_risk_score(1, 1, 5)
    assert score == 1
    assert level == "LOW"


def test_high_risk_score():
    """Test high risk score calculation."""
    score, level = calculate_risk_score(4, 4, 2)
    assert score == 64
    assert level == "HIGH"


def test_critical_risk_score():
    """Test critical risk score calculation."""
    score, level = calculate_risk_score(5, 5, 1)
    assert score == 125
    assert level == "CRITICAL"


def test_medium_risk_score():
    """Test medium risk score calculation."""
    score, level = calculate_risk_score(3, 3, 3)
    assert score == 27
    assert level == "MEDIUM"


def test_score_boundaries():
    """Test exact boundary values for risk scores."""
    # 24 is highest LOW
    score, level = calculate_risk_score(2, 4, 3)
    assert score == 24
    assert level == "LOW"

    # Score exception breakdown
    score, level, breakdown = score_exception({"name": "test"})
    assert "formula" in breakdown
    assert breakdown["impact"] == 3
    assert level == "MEDIUM"
