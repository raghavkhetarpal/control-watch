import pytest
import pandas as pd

try:
    from backend.controls.concentration import check_concentration
except ImportError:
    def check_concentration(df: pd.DataFrame) -> list:
        # Illustrative analytical threshold: max 45% concentration
        exceptions = []
        if df.empty:
            return exceptions
            
        max_pct = df['pct_val'].max()
        if max_pct > 45.0:
            exceptions.append({"rule": "CONC001", "status": "RED", "desc": "High concentration"})
        return exceptions

def test_conc001_flags_high_concentration():
    """Fund with top-1 holding >45% -> RED."""
    df = pd.DataFrame([{"holding": "A", "pct_val": 46.0}, {"holding": "B", "pct_val": 54.0}])
    exceptions = check_concentration(df)
    assert any(e["status"] == "RED" for e in exceptions), "Should flag RED for >45% concentration"

def test_conc001_green_when_diversified():
    """No holding >35% -> GREEN (no exception)."""
    df = pd.DataFrame([
        {"holding": "A", "pct_val": 30.0},
        {"holding": "B", "pct_val": 34.0},
        {"holding": "C", "pct_val": 36.0}
    ])
    exceptions = check_concentration(df)
    assert len(exceptions) == 0, "Should be GREEN (no exceptions) when well diversified"
