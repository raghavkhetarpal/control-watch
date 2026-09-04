"""Unit tests for KRI, KCI, and KPI metrics evaluation logic."""
from datetime import date
import pytest

from backend.metrics.kri import (
    _determine_status as kri_status,
    _determine_trend as kri_trend,
    KRIResult,
)
from backend.metrics.kci import (
    _determine_status as kci_status,
    _determine_trend as kci_trend,
    KCIResult,
)
from backend.metrics.kpi import KPIResult


def test_kri_status_lower_is_better():
    """Lower is better (e.g. exception rate): value < amber -> GREEN, < red -> AMBER, >= red -> RED."""
    assert kri_status(2.0, green=1.0, amber=5.0, red=15.0, lower_is_better=True) == "GREEN"
    assert kri_status(7.5, green=1.0, amber=5.0, red=15.0, lower_is_better=True) == "AMBER"
    assert kri_status(20.0, green=1.0, amber=5.0, red=15.0, lower_is_better=True) == "RED"


def test_kri_trend():
    """Test trend calculation comparing current against previous period."""
    assert kri_trend(5.0, previous=10.0, lower_is_better=True) == "IMPROVING"
    assert kri_trend(10.0, previous=5.0, lower_is_better=True) == "DETERIORATING"
    assert kri_trend(5.0, previous=5.0, lower_is_better=True) == "STABLE"
    assert kri_trend(5.0, previous=None, lower_is_better=True) == "STABLE"


def test_kci_status_higher_is_better():
    """Higher is better (e.g. pass rate): value > amber -> GREEN, > red -> AMBER, <= red -> RED."""
    # When lower_is_better=False, amber is the green cutoff, red is the amber cutoff
    assert kci_status(90.0, green=95.0, amber=85.0, red=75.0, lower_is_better=False) == "GREEN"
    assert kci_status(80.0, green=95.0, amber=85.0, red=75.0, lower_is_better=False) == "AMBER"
    assert kci_status(70.0, green=95.0, amber=85.0, red=75.0, lower_is_better=False) == "RED"


def test_kci_trend():
    """Test KCI trend logic when higher is better."""
    # When lower_is_better=False: increase = IMPROVING, decrease = DETERIORATING
    assert kci_trend(95.0, previous=90.0, lower_is_better=False) == "IMPROVING"
    assert kci_trend(85.0, previous=90.0, lower_is_better=False) == "DETERIORATING"
    assert kci_trend(90.0, previous=90.0, lower_is_better=False) == "STABLE"


def test_metric_dataclasses():
    """Test instantiation and attributes of KRI, KCI, and KPI dataclasses."""
    today = date(2025, 9, 30)
    kri = KRIResult(
        kri_id="KRI-001",
        name="Concentration Exposure",
        description="Top position concentration",
        period_date=today,
        numerator=35.0,
        denominator=100.0,
        value=35.0,
        unit="PERCENTAGE",
        threshold_green=35.0,
        threshold_amber=45.0,
        threshold_red=45.0,
        status="GREEN",
        trend="STABLE",
        previous_value=34.0,
        metadata={"note": "Illustrative analytical threshold"},
    )
    assert kri.kri_id == "KRI-001"
    assert kri.status == "GREEN"

    kci = KCIResult(
        kci_id="KCI-001",
        name="Control Execution Rate",
        description="Execution health",
        period_date=today,
        numerator=16.0,
        denominator=16.0,
        value=100.0,
        unit="PERCENTAGE",
        threshold_green=95.0,
        threshold_amber=85.0,
        threshold_red=85.0,
        status="GREEN",
        trend="STABLE",
        previous_value=100.0,
        control_id="ALL",
        metadata={},
    )
    assert kci.kci_id == "KCI-001"
    assert kci.value == 100.0

    kpi = KPIResult(
        kpi_id="KPI-001",
        name="Funds Processed",
        description="Total funds processed",
        period_date=today,
        value=150.0,
        unit="COUNT",
        metadata={},
    )
    assert kpi.kpi_id == "KPI-001"
    assert kpi.value == 150.0
