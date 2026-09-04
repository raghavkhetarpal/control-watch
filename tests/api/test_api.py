"""API endpoint tests using FastAPI TestClient with dependency override."""
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.connection import get_db


class MockMappingResult:
    def __init__(self, data=None):
        self._data = data or []

    def mappings(self):
        return self

    def all(self):
        return self._data

    def first(self):
        return self._data[0] if self._data else None

    def scalar(self):
        if self._data and isinstance(self._data[0], dict):
            return list(self._data[0].values())[0]
        return 0


def create_mock_db_session():
    mock_session = MagicMock()

    def mock_execute(query, params=None):
        query_str = str(query).lower()
        if "risk_category" in query_str and "group by" in query_str:
            return MockMappingResult([{"risk_category": "DATA_QUALITY", "cnt": 1}])
        elif "count(*)" in query_str and "filter" in query_str:
            return MockMappingResult([{"total": 5, "critical": 0, "high": 1, "open_count": 2}])
        elif "count(*)" in query_str:
            return MockMappingResult([{"count": 5}])
        elif "from funds" in query_str:
            return MockMappingResult([{
                "id": 1,
                "accession_number": "0001752724-23-000001",
                "series_id": "S000001",
                "cik": "0001752724",
                "fund_name": "Test Core Equity Fund",
                "total_assets": 50000000.0,
                "net_assets": 48000000.0,
                "period_of_report": "2023-09-30",
                "filing_date": "2023-11-28",
            }])
        elif "from control_definitions" in query_str:
            return MockMappingResult([{
                "control_id": "DQ-001",
                "name": "Missing Required Fields",
                "description": "Checks required holdings fields",
                "risk_category": "DATA_QUALITY",
                "control_type": "DETECTIVE",
                "frequency": "ON_INGESTION",
                "is_active": True,
                "thresholds": {},
            }])
        elif "group by risk_category" in query_str:
            return MockMappingResult([{"risk_category": "DATA_QUALITY", "cnt": 1}])
        elif "from control_exceptions" in query_str:
            return MockMappingResult([{
                "id": 1,
                "control_id": "DQ-001",
                "control_name": "Missing Required Fields",
                "fund_id": 1,
                "fund_name": "Test Core Equity Fund",
                "severity": "HIGH",
                "status": "DETECTED",
                "risk_category": "DATA_QUALITY",
                "description": "Missing required fields",
                "risk_score": 64,
                "risk_level": "HIGH",
                "assigned_to": None,
                "detected_at": "2023-12-01T10:00:00",
                "due_date": None,
                "period_date": "2023-09-30",
                "is_repeat": False,
                "age_days": 5,
            }])
        elif "from kri_snapshots" in query_str:
            return MockMappingResult([{
                "kri_id": "KRI-001",
                "name": "Concentration Exposure",
                "description": "Max top-10 holding pct",
                "period_date": "2023-09-30",
                "numerator": 38.5,
                "denominator": 100.0,
                "value": 38.5,
                "unit": "PERCENTAGE",
                "threshold_green": 35.0,
                "threshold_amber": 45.0,
                "threshold_red": 45.0,
                "status": "AMBER",
                "trend": "STABLE",
                "previous_value": 37.0,
                "metadata": {},
            }])
        elif "from kci_snapshots" in query_str:
            return MockMappingResult([{
                "kci_id": "KCI-001",
                "name": "Control Execution Rate",
                "description": "Executed controls ratio",
                "period_date": "2023-09-30",
                "numerator": 16.0,
                "denominator": 16.0,
                "value": 100.0,
                "unit": "PERCENTAGE",
                "threshold_green": 95.0,
                "threshold_amber": 85.0,
                "threshold_red": 85.0,
                "status": "GREEN",
                "trend": "STABLE",
                "previous_value": 100.0,
                "control_id": None,
                "metadata": {},
            }])
        elif "from remediation_items" in query_str:
            return MockMappingResult([{"count": 0}])
        return MockMappingResult([])

    mock_session.execute = mock_execute
    return mock_session


@pytest.fixture(autouse=True)
def override_db():
    app.dependency_overrides[get_db] = lambda: create_mock_db_session()
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def test_health_endpoint():
    """GET /health returns 200 with status info."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "database" in data


def test_list_funds():
    """GET /funds returns paginated response."""
    response = client.get("/funds")
    assert response.status_code == 200
    data = response.json()
    assert "funds" in data
    assert "total" in data
    assert len(data["funds"]) > 0
    assert data["funds"][0]["fund_name"] == "Test Core Equity Fund"


def test_list_controls():
    """GET /controls returns list of control definitions."""
    response = client.get("/controls")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["control_id"] == "DQ-001"


def test_list_exceptions():
    """GET /exceptions returns paginated list of exceptions."""
    response = client.get("/exceptions")
    assert response.status_code == 200
    data = response.json()
    assert "exceptions" in data
    assert "total" in data
    assert len(data["exceptions"]) > 0
    assert data["exceptions"][0]["severity"] == "HIGH"


def test_get_kris():
    """GET /kris returns list of KRI snapshots."""
    response = client.get("/kris")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["kri_id"] == "KRI-001"


def test_risk_summary():
    """GET /risk-summary returns comprehensive risk overview."""
    response = client.get("/risk-summary")
    assert response.status_code == 200
    data = response.json()
    assert "overall_risk_level" in data
    assert "total_exceptions" in data
    assert "kri_summary" in data
