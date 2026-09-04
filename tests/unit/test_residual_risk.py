"""Unit tests for residual risk calculation."""
import pytest
from backend.risk_engine.residual_risk import calculate_residual_risk


def test_high_inherent_strong_control():
    """High inherent risk (20.0) with strong control effectiveness (0.8) -> reduced to LOW residual."""
    residual, level = calculate_residual_risk(20.0, 0.8)
    # residual = 20.0 * (1 - 0.8) = 4.0 <= 6 -> LOW
    assert residual == 4.0
    assert level == "LOW"


def test_high_inherent_weak_control():
    """High inherent risk (20.0) with weak control effectiveness (0.1) -> remains HIGH/CRITICAL."""
    residual, level = calculate_residual_risk(20.0, 0.1)
    # residual = 20.0 * (1 - 0.1) = 18.0 -> HIGH
    assert residual == 18.0
    assert level == "HIGH"


def test_residual_calculation_formula():
    """Verify exact formula for residual risk."""
    residual, level = calculate_residual_risk(16.0, 0.5)
    # residual = 16.0 * 0.5 = 8.0 -> MEDIUM (7-12)
    assert residual == 8.0
    assert level == "MEDIUM"

    # Extreme critical
    residual_crit, level_crit = calculate_residual_risk(25.0, 0.0)
    assert residual_crit == 25.0
    assert level_crit == "CRITICAL"
