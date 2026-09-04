"""Unit tests for Exception Manager state machine and transition workflows."""
import pytest
from unittest.mock import MagicMock

from backend.exceptions.manager import (
    VALID_TRANSITIONS,
    transition_exception,
    assign_exception,
    set_root_cause,
    bulk_triage,
)


def test_state_machine_valid_paths():
    """Verify all valid lifecycle transition paths."""
    assert "TRIAGED" in VALID_TRANSITIONS["DETECTED"]
    assert "ACCEPTED" in VALID_TRANSITIONS["DETECTED"]
    assert "ASSIGNED" in VALID_TRANSITIONS["TRIAGED"]
    assert "INVESTIGATING" in VALID_TRANSITIONS["ASSIGNED"]
    assert "REMEDIATION_PLANNED" in VALID_TRANSITIONS["INVESTIGATING"]
    assert "REMEDIATION_IN_PROGRESS" in VALID_TRANSITIONS["REMEDIATION_PLANNED"]
    assert "VALIDATION" in VALID_TRANSITIONS["REMEDIATION_IN_PROGRESS"]
    assert "CLOSED" in VALID_TRANSITIONS["VALIDATION"]


def test_terminal_states():
    """Verify CLOSED and ACCEPTED are terminal states with no subsequent transitions."""
    assert VALID_TRANSITIONS["CLOSED"] == []
    assert VALID_TRANSITIONS["ACCEPTED"] == []


def test_transition_exception_success():
    """Test transition_exception updates status."""
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = "DETECTED"
    mock_session.execute.return_value = mock_result

    res = transition_exception(mock_session, exception_id="1", new_status="TRIAGED", actor="analyst_1")
    assert res is True
    assert mock_session.execute.called


def test_transition_exception_invalid():
    """Test invalid transition raises ValueError."""
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = "DETECTED"
    mock_session.execute.return_value = mock_result

    # DETECTED cannot jump directly to VALIDATION
    with pytest.raises(ValueError):
        transition_exception(mock_session, exception_id="1", new_status="VALIDATION", actor="analyst_1")


def test_assign_exception():
    """Test assign_exception transitions status to ASSIGNED."""
    mock_session = MagicMock()
    row = MagicMock()
    row.status = "TRIAGED"
    row.assigned_to = None
    mock_session.execute.return_value.fetchone.return_value = row

    res = assign_exception(mock_session, exception_id="1", assigned_to="sarah.chen", actor="lead_analyst")
    assert res is True
    assert mock_session.execute.called


def test_set_root_cause():
    """Test setting root cause on an exception."""
    mock_session = MagicMock()
    row = MagicMock()
    row.root_cause_category = "UNKNOWN"
    row.root_cause_description = ""
    mock_session.execute.return_value.fetchone.return_value = row

    res = set_root_cause(mock_session, exception_id="1", category="DATA_QUALITY", description="Missing identifier", actor="analyst")
    assert res is True
    assert mock_session.execute.called


def test_bulk_triage():
    """Test bulk triage across multiple exceptions."""
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = "DETECTED"
    mock_session.execute.return_value = mock_result

    count = bulk_triage(mock_session, exception_ids=["1", "2", "3"], actor="lead_analyst")
    assert count == 3
