"""Unit tests for Remediation Tracking and repeat exception logic."""
from datetime import date, timedelta
import pytest
from unittest.mock import MagicMock

from backend.exceptions.remediation import (
    create_remediation,
    update_remediation_status,
    validate_remediation,
    get_overdue_remediations,
    get_remediation_stats,
    check_repeat_exceptions,
)


def test_create_remediation():
    """Test creating a remediation item."""
    mock_session = MagicMock()
    # Mock insert returning id
    insert_mock = MagicMock()
    insert_mock.scalar.return_value = 101
    # Mock transition check: returns INVESTIGATING so transition to REMEDIATION_PLANNED succeeds
    status_mock = MagicMock()
    status_mock.scalar.return_value = "INVESTIGATING"

    mock_session.execute.side_effect = [insert_mock, MagicMock(), status_mock, MagicMock(), MagicMock()]

    rem_id = create_remediation(
        session=mock_session,
        exception_id="1",
        owner="james.park",
        action="Obtain verified CUSIP from custodian",
        due_date=date.today() + timedelta(days=14),
        priority="HIGH",
        actor="lead_analyst",
    )
    assert rem_id == 101


def test_update_remediation_status():
    """Test updating remediation item status."""
    mock_session = MagicMock()
    row = MagicMock()
    row.status = "PLANNED"
    row.exception_id = "1"
    mock_session.execute.return_value.fetchone.return_value = row

    res = update_remediation_status(
        session=mock_session,
        remediation_id=101,
        new_status="IN_PROGRESS",
        actor="james.park",
        notes="Contacted custodian operations",
    )
    assert res is True
    assert mock_session.execute.called


def test_validate_remediation():
    """Test validating remediation item and marking VALIDATED."""
    mock_session = MagicMock()
    row = MagicMock()
    row.status = "COMPLETED"
    row.exception_id = "1"
    mock_session.execute.return_value.fetchone.return_value = row

    res = validate_remediation(
        session=mock_session,
        remediation_id=101,
        result="PASS",
        validator="quality_assurance_lead",
    )
    assert res is True
    assert mock_session.execute.called


def test_get_overdue_remediations():
    """Test retrieving overdue remediations."""
    mock_session = MagicMock()
    row = MagicMock()
    row._mapping = {
        "id": 101,
        "exception_id": "1",
        "owner": "james.park",
        "due_date": str(date.today() - timedelta(days=5)),
    }
    mock_session.execute.return_value.fetchall.return_value = [row]

    overdue = get_overdue_remediations(mock_session)
    assert len(overdue) == 1
    assert overdue[0]["id"] == 101


def test_get_remediation_stats():
    """Test aggregating remediation statistics."""
    mock_session = MagicMock()

    owner_mock = MagicMock()
    owner_mock.owner = "james.park"
    owner_mock.cnt = 3

    priority_mock = MagicMock()
    priority_mock.priority = "HIGH"
    priority_mock.cnt = 2

    res1 = MagicMock(); res1.scalar.return_value = 2  # overdue_count
    res2 = MagicMock(); res2.scalar.return_value = 4.5  # mttr_days
    res3 = MagicMock(); res3.fetchall.return_value = [owner_mock]
    res4 = MagicMock(); res4.fetchall.return_value = [priority_mock]

    mock_session.execute.side_effect = [res1, res2, res3, res4]

    stats = get_remediation_stats(mock_session)
    assert stats["overdue_count"] == 2
    assert stats["mttr_days"] == 4.5
    assert stats["by_owner"]["james.park"] == 3
    assert stats["by_priority"]["HIGH"] == 2


def test_check_repeat_exceptions():
    """Test detecting repeat exceptions on the same entity/control."""
    mock_session = MagicMock()
    current_row = MagicMock()
    current_row.fund_id = "1"
    current_row.control_id = "DQ-001"

    prev_row = MagicMock()
    prev_row.id = "5"

    res1 = MagicMock(); res1.fetchone.return_value = current_row
    res2 = MagicMock(); res2.fetchone.return_value = prev_row
    res3 = MagicMock()  # for update

    mock_session.execute.side_effect = [res1, res2, res3]

    is_repeat = check_repeat_exceptions(mock_session, exception_id="10")
    assert is_repeat is True
