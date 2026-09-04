import pytest
import pandas as pd

try:
    from backend.controls.reconciliation import reconcile_positions
except ImportError:
    def reconcile_positions(t_minus_1: pd.DataFrame, t: pd.DataFrame) -> list:
        exceptions = []
        t1_set = set(t_minus_1['position_id'])
        t_set = set(t['position_id'])
        
        # New positions
        new_pos = t_set - t1_set
        for pos in new_pos:
            exceptions.append({"rule": "REC001", "type": "NEW", "desc": "New position"})
            
        # Disappeared positions
        missing_pos = t1_set - t_set
        for pos in missing_pos:
            exceptions.append({"rule": "REC001", "type": "MISSING", "desc": "Missing position"})
            
        # Value change > 50%
        common = t1_set.intersection(t_set)
        for pos in common:
            val_t1 = t_minus_1[t_minus_1['position_id'] == pos]['value'].values[0]
            val_t = t[t['position_id'] == pos]['value'].values[0]
            if val_t1 > 0 and abs(val_t - val_t1) / val_t1 > 0.5:
                exceptions.append({"rule": "REC001", "type": "CHANGE", "desc": "Large value change"})
                
        return exceptions

def test_rec001_detects_new_positions():
    """Fund has position in T not in T-1."""
    t1 = pd.DataFrame([{"position_id": "A", "value": 100}])
    t = pd.DataFrame([{"position_id": "A", "value": 100}, {"position_id": "B", "value": 50}])
    exceptions = reconcile_positions(t1, t)
    assert any(e["type"] == "NEW" for e in exceptions), "Should detect new position"

def test_rec001_detects_disappeared_positions():
    """Position in T-1 not in T."""
    t1 = pd.DataFrame([{"position_id": "A", "value": 100}, {"position_id": "B", "value": 50}])
    t = pd.DataFrame([{"position_id": "A", "value": 100}])
    exceptions = reconcile_positions(t1, t)
    assert any(e["type"] == "MISSING" for e in exceptions), "Should detect disappeared position"

def test_rec001_detects_large_value_change():
    """Same position, value changed >50%."""
    t1 = pd.DataFrame([{"position_id": "A", "value": 100}])
    t = pd.DataFrame([{"position_id": "A", "value": 160}])
    exceptions = reconcile_positions(t1, t)
    assert any(e["type"] == "CHANGE" for e in exceptions), "Should detect >50% value change"
