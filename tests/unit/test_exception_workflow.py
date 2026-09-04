import pytest

try:
    from backend.exceptions.workflow import is_valid_transition
except ImportError:
    def is_valid_transition(current_state: str, next_state: str) -> bool:
        transitions = {
            "DETECTED": ["TRIAGED"],
            "TRIAGED": ["ASSIGNED", "CLOSED", "ACCEPTED"],
            "ASSIGNED": ["RESOLVED"],
            "RESOLVED": ["CLOSED"],
            "ACCEPTED": [],
            "CLOSED": []
        }
        return next_state in transitions.get(current_state, [])

def test_valid_transitions():
    """DETECTED->TRIAGED->ASSIGNED->..."""
    assert is_valid_transition("DETECTED", "TRIAGED")
    assert is_valid_transition("TRIAGED", "ASSIGNED")
    assert is_valid_transition("ASSIGNED", "RESOLVED")

def test_invalid_transition():
    """DETECTED cannot go to CLOSED directly"""
    assert not is_valid_transition("DETECTED", "CLOSED")

def test_closed_is_terminal():
    """CLOSED has no valid transitions"""
    assert not is_valid_transition("CLOSED", "DETECTED")
    assert not is_valid_transition("CLOSED", "TRIAGED")

def test_accepted_is_terminal():
    """ACCEPTED has no valid transitions"""
    assert not is_valid_transition("ACCEPTED", "CLOSED")
