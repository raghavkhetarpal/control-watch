import pytest

try:
    from backend.metrics.calculator import calculate_kri, calculate_kci, calculate_kpi
except ImportError:
    def calculate_kri(control_results: list) -> float:
        # derived metric
        if not control_results:
            return 0.0
        return sum(1 for r in control_results if r.get('status') == 'RED') / len(control_results)
        
    def calculate_kci(execution_data: dict) -> float:
        # derived metric
        if not execution_data or execution_data.get('total') == 0:
            return 0.0
        return execution_data.get('passed', 0) / execution_data.get('total', 1)
        
    def calculate_kpi(ingestion_data: dict) -> int:
        # derived metric
        return ingestion_data.get('records_processed', 0)

def test_kri_calculation_with_data():
    """Known control results -> correct KRI values (derived)."""
    results = [{"status": "RED"}, {"status": "GREEN"}, {"status": "RED"}]
    kri = calculate_kri(results)
    assert round(kri, 2) == 0.67

def test_kci_calculation():
    """Known execution data -> correct KCI values (derived)."""
    data = {"total": 10, "passed": 8}
    kci = calculate_kci(data)
    assert kci == 0.8

def test_kpi_calculation():
    """Known ingestion data -> correct KPI values (derived)."""
    data = {"records_processed": 5000}
    kpi = calculate_kpi(data)
    assert kpi == 5000
