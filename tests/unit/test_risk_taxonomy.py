"""Unit tests for Risk Taxonomy and control mappings."""
import pytest
from backend.risk_engine.risk_taxonomy import (
    RiskCategory,
    CONTROL_RISK_MAPPING,
    CATEGORY_DEFAULTS,
)


def test_risk_categories_exist():
    """Verify all standard risk categories exist."""
    assert RiskCategory.DATA_QUALITY.value == "DATA_QUALITY"
    assert RiskCategory.RECONCILIATION.value == "RECONCILIATION"
    assert RiskCategory.VALUATION.value == "VALUATION"
    assert RiskCategory.CONCENTRATION.value == "CONCENTRATION"
    assert RiskCategory.REPORTING.value == "REPORTING"
    assert RiskCategory.PROCESS.value == "PROCESS"
    assert RiskCategory.CONTROL_EFFECTIVENESS.value == "CONTROL_EFFECTIVENESS"
    assert RiskCategory.TECHNOLOGY.value == "TECHNOLOGY"


def test_control_risk_mapping():
    """Verify each control is mapped to an appropriate risk category."""
    assert CONTROL_RISK_MAPPING["DQ-001"] == RiskCategory.DATA_QUALITY
    assert CONTROL_RISK_MAPPING["DQ-002"] == RiskCategory.DATA_QUALITY
    assert CONTROL_RISK_MAPPING["DQ-003"] == RiskCategory.DATA_QUALITY
    assert CONTROL_RISK_MAPPING["DQ-004"] == RiskCategory.DATA_QUALITY
    assert CONTROL_RISK_MAPPING["REC-001"] == RiskCategory.RECONCILIATION
    assert CONTROL_RISK_MAPPING["VAL-001"] == RiskCategory.VALUATION
    assert CONTROL_RISK_MAPPING["CONC-001"] == RiskCategory.CONCENTRATION
    assert CONTROL_RISK_MAPPING["RPT-001"] == RiskCategory.REPORTING


def test_category_defaults():
    """Verify default impact and likelihood scores are defined and bounded 1-5."""
    for category, (impact, likelihood) in CATEGORY_DEFAULTS.items():
        assert 1 <= impact <= 5, f"Impact {impact} out of bounds for {category}"
        assert 1 <= likelihood <= 5, f"Likelihood {likelihood} out of bounds for {category}"
