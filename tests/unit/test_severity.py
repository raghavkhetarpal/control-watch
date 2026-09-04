"""Unit tests for severity assignment."""
import pytest
from backend.exceptions.severity import assign_severity, auto_assign_severity


def test_low_severity():
    """Test low severity assignment with low impact and high control effectiveness."""
    # risk_score = 1 * 1 * (1.5 - 1.0) * 5 = 2.5 (< 25 -> LOW)
    sev = assign_severity(1.0, 1.0, 1.0)
    assert sev == "LOW"


def test_high_severity():
    """Test high severity assignment."""
    # risk_score = 4 * 4 * (1.5 - 0.5) * 5 = 80 (> 75 -> CRITICAL or 50-74 -> HIGH)
    sev = assign_severity(3.0, 4.0, 0.5)
    assert sev in ["HIGH", "CRITICAL"]


def test_critical_severity():
    """Test critical severity assignment."""
    sev = assign_severity(5.0, 5.0, 0.1)
    assert sev == "CRITICAL"


def test_auto_assign_severity():
    """Test automatic severity assignment based on control type."""
    sev, imp, lik, ce = auto_assign_severity("REC-001", {"control_type": "RECONCILIATION"})
    assert imp == 4.0
    assert lik == 4.0
    assert sev in ["HIGH", "CRITICAL"]
