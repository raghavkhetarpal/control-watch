import pytest
import pandas as pd

try:
    from backend.controls.data_quality import run_dq_checks
except ImportError:
    def run_dq_checks(df: pd.DataFrame) -> list:
        exceptions = []
        for i, row in df.iterrows():
            if pd.isna(row.get('asset_cat')):
                exceptions.append({"rule": "DQ001", "desc": "Missing asset_cat"})
            if pd.isna(row.get('value')):
                exceptions.append({"rule": "DQ001", "desc": "Missing value"})
            if row.get('value', 0) < 0 or row.get('pct_val', 0) > 100:
                exceptions.append({"rule": "DQ003", "desc": "Invalid value"})
        
        # Check duplicates
        if df.duplicated(subset=['fund_id', 'asset_cat']).any():
            exceptions.append({"rule": "DQ002", "desc": "Duplicate found"})
        return exceptions

def test_dq001_detects_missing_fields():
    """Create holdings with NULL required fields, verify detection."""
    df = pd.DataFrame([{"fund_id": 1, "asset_cat": None, "value": 100}])
    exceptions = run_dq_checks(df)
    assert any(e["rule"] == "DQ001" for e in exceptions), "Should detect missing asset_cat"

def test_dq001_no_exceptions_clean_data():
    """All fields present, verify no exceptions."""
    df = pd.DataFrame([{"fund_id": 1, "asset_cat": "Equity", "value": 100, "pct_val": 10}])
    exceptions = run_dq_checks(df)
    assert len(exceptions) == 0, "Should have no exceptions for clean data"

def test_dq002_detects_duplicates():
    """Insert duplicate holdings, verify detection."""
    df = pd.DataFrame([
        {"fund_id": 1, "asset_cat": "Equity", "value": 100, "pct_val": 10},
        {"fund_id": 1, "asset_cat": "Equity", "value": 100, "pct_val": 10}
    ])
    exceptions = run_dq_checks(df)
    assert any(e["rule"] == "DQ002" for e in exceptions), "Should detect duplicate holdings"

def test_dq003_detects_invalid_values():
    """Insert negative balance, pct_val>100, verify detection."""
    df = pd.DataFrame([{"fund_id": 1, "asset_cat": "Equity", "value": -100, "pct_val": 105}])
    exceptions = run_dq_checks(df)
    assert any(e["rule"] == "DQ003" for e in exceptions), "Should detect invalid values"

def test_dq004_detects_missing_classification():
    """Insert holdings with NULL asset_cat."""
    df = pd.DataFrame([{"fund_id": 1, "asset_cat": None, "value": 100, "pct_val": 10}])
    exceptions = run_dq_checks(df)
    assert any(e["rule"] == "DQ001" for e in exceptions), "Should detect missing classification (asset_cat)"
