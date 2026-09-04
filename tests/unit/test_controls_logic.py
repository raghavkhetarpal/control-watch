"""Unit tests for Controls framework, registry, and calculation logic."""
from datetime import date
import pytest
from unittest.mock import MagicMock

from backend.controls.base import BaseControl, ControlResult
from backend.controls.registry import get_all_controls, run_control, _CONTROLS
from backend.controls.liquidity import LIQUIDITY_MAP, DEBT_LIQUIDITY, LiquidityProxyControl
from backend.controls.valuation import StalePricesControl, ExtremePriceMovementsControl
from backend.controls.reporting import ReportingTimelinessControl, ReportingGapsControl
from backend.controls.classification import ClassificationChangesControl
from backend.controls.concentration import (
    TopHoldingsConcentrationControl,
    IssuerConcentrationControl,
    AssetClassConcentrationControl,
    GeographicConcentrationControl,
)
from backend.controls.data_quality import (
    MissingRequiredFieldsControl,
    DuplicateHoldingsControl,
    InvalidValuesControl,
    ClassificationConsistencyControl,
)


def test_control_result_dataclass():
    """Test ControlResult properties."""
    res = ControlResult(
        control_id="DQ-001",
        name="Missing Required Fields",
        status="COMPLETED",
        records_scanned=1000,
        exceptions_found=12,
        pass_rate=98.8,
        duration_ms=45,
        details={"scanned": 1000},
        exceptions=[{"id": 1}],
    )
    assert res.control_id == "DQ-001"
    assert res.pass_rate == 98.8
    assert len(res.exceptions) == 1


def test_registry_contains_all_controls():
    """Verify registry has all implemented controls registered."""
    controls = get_all_controls()
    control_ids = {c.control_id for c in controls}
    expected_ids = {
        "DQ-001", "DQ-002", "DQ-003", "DQ-004",
        "REC-001", "REC-002",
        "VAL-001", "VAL-002",
        "CONC-001", "CONC-002", "CONC-003", "CONC-004",
        "LIQ-001", "RPT-001", "RPT-002", "CLS-001",
    }
    for cid in expected_ids:
        assert cid in control_ids, f"Expected {cid} in registry"


def test_liquidity_classification_maps():
    """Verify liquidity categorization logic."""
    assert LIQUIDITY_MAP["EC"] == "HIGHLY_LIQUID"
    assert LIQUIDITY_MAP["STIV"] == "HIGHLY_LIQUID"
    assert LIQUIDITY_MAP["ABS"] == "LESS_LIQUID"
    assert DEBT_LIQUIDITY["USG"] == "HIGHLY_LIQUID"
    assert DEBT_LIQUIDITY["CORP"] == "MODERATELY_LIQUID"
    assert DEBT_LIQUIDITY["MUN"] == "LESS_LIQUID"


def test_concentration_thresholds():
    """Verify concentration control illustrative thresholds."""
    conc = TopHoldingsConcentrationControl()
    assert conc.GREEN_PCT == 35.0
    assert conc.AMBER_PCT == 45.0

    issuer_conc = IssuerConcentrationControl()
    assert issuer_conc.THRESHOLD_PCT == 25.0

    asset_conc = AssetClassConcentrationControl()
    assert asset_conc.THRESHOLD_PCT == 80.0

    geo_conc = GeographicConcentrationControl()
    assert geo_conc.THRESHOLD_PCT == 85.0


def test_reporting_timeliness_thresholds():
    """Verify timeliness thresholds."""
    rpt = ReportingTimelinessControl()
    assert rpt.AMBER_DAYS == 60
    assert rpt.RED_DAYS == 90


def test_valuation_controls_threshold():
    """Verify extreme price movement threshold."""
    val = ExtremePriceMovementsControl()
    assert val.CHANGE_THRESHOLD_PCT == 50.0


def test_data_quality_valid_categories():
    """Verify classification consistency control categories."""
    dq4 = ClassificationConsistencyControl()
    assert "EC" in dq4.VALID_ASSET_CATS
    assert "DBT" in dq4.VALID_ASSET_CATS
    assert "CORP" in dq4.VALID_ISSUER_CATS
    assert "USG" in dq4.VALID_ISSUER_CATS


def test_run_control_with_mock_session():
    """Test run_control creates execution record and handles results."""
    mock_session = MagicMock()
    mock_session.execute.return_value.scalar.return_value = 1
    mock_session.execute.return_value.mappings.return_value.all.return_value = []
    today = date(2025, 9, 30)
    result = run_control(mock_session, "CONC-001", today)
    assert result.control_id == "CONC-001"
    assert result.status in ["COMPLETED", "FAILED"]
