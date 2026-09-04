"""Unit tests for Ingestion Validators."""
import pandas as pd
import pytest

from backend.ingestion.validators import Validator


def test_validator_empty_dataframe():
    """Empty dataframe should fail validation."""
    df = pd.DataFrame()
    res = Validator.pre_load_validation(df, "holdings", ["name", "value"])
    assert res["passed"] is False
    assert "empty" in res["reason"].lower()


def test_validator_missing_columns():
    """DataFrame missing required columns should fail validation."""
    df = pd.DataFrame({"name": ["Apple Inc."], "other": [123]})
    res = Validator.pre_load_validation(df, "holdings", ["name", "value", "cusip"])
    assert res["passed"] is False
    assert "missing" in res["reason"].lower()


def test_validator_valid_dataframe():
    """Valid DataFrame should pass validation."""
    df = pd.DataFrame({"name": ["Apple Inc."], "value": [1000.0], "cusip": ["037833100"]})
    res = Validator.pre_load_validation(df, "holdings", ["name", "value", "cusip"])
    assert res["passed"] is True
    assert res["reason"] == ""


def test_post_load_validation():
    """Post load validation check."""
    res = Validator.post_load_validation(None, run_id=1)
    assert res["passed"] is True
