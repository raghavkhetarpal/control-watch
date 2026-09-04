"""
KPI (Key Performance Indicator) framework module.
"""
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List
from sqlalchemy import text
import structlog
import json

logger = structlog.get_logger(__name__)

@dataclass
class KPIResult:
    kpi_id: str
    name: str
    description: str
    period_date: date
    value: float
    unit: str
    metadata: Dict[str, Any]

def _create_kpi_result(
    session, period_date: date, kpi_id: str, name: str, description: str,
    val: float, unit: str
) -> KPIResult:
    
    metadata = {"derived": True, "illustrative_analytical_thresholds": False}
    res = KPIResult(
        kpi_id=kpi_id, name=name, description=description, 
        period_date=period_date, value=val, unit=unit, metadata=metadata
    )
    
    insert_query = text('''
        INSERT INTO kpi_snapshots (
            kpi_id, name, description, period_date, 
            value, unit, metadata
        ) VALUES (
            :kpi_id, :name, :description, :period_date, 
            :val, :unit, :metadata
        )
        ON CONFLICT (kpi_id, period_date) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            value = EXCLUDED.value,
            unit = EXCLUDED.unit,
            metadata = EXCLUDED.metadata,
            created_at = NOW()
    ''')
    session.execute(insert_query, {
        "kpi_id": res.kpi_id, "name": res.name, "description": res.description,
        "period_date": res.period_date, "val": res.value, "unit": res.unit,
        "metadata": json.dumps(res.metadata)
    })
    
    return res

def calculate_kpi_001(session, period_date: date) -> KPIResult:
    """KPI-001 Funds Processed."""
    query = text('''
        SELECT COUNT(*) 
        FROM funds 
        WHERE period_of_report = :period_date
    ''')
    val = float(session.execute(query, {"period_date": period_date}).scalar() or 0)
    return _create_kpi_result(session, period_date, "KPI-001", "Funds Processed", "count of funds for period", val, "funds")

def calculate_kpi_002(session, period_date: date) -> KPIResult:
    """KPI-002 Holdings Processed."""
    query = text('''
        SELECT COUNT(*) 
        FROM holdings h
        JOIN funds f ON h.fund_id = f.id
        WHERE f.period_of_report = :period_date
    ''')
    val = float(session.execute(query, {"period_date": period_date}).scalar() or 0)
    return _create_kpi_result(session, period_date, "KPI-002", "Holdings Processed", "count of holdings for period", val, "holdings")

def calculate_kpi_003(session, period_date: date) -> KPIResult:
    """KPI-003 Total Records Processed."""
    query = text('''
        SELECT COALESCE(SUM(rows_processed), 0) 
        FROM ingestion_runs
    ''')
    val = float(session.execute(query).scalar() or 0)
    return _create_kpi_result(session, period_date, "KPI-003", "Total Records Processed", "sum across ingestion_runs", val, "records")

def calculate_kpi_004(session, period_date: date) -> KPIResult:
    """KPI-004 Controls Executed."""
    query = text('''
        SELECT COUNT(*) 
        FROM control_executions 
        WHERE period_date = :period_date
    ''')
    val = float(session.execute(query, {"period_date": period_date}).scalar() or 0)
    return _create_kpi_result(session, period_date, "KPI-004", "Controls Executed", "count of control_executions for period", val, "executions")

def calculate_kpi_005(session, period_date: date) -> KPIResult:
    """KPI-005 Exceptions Generated."""
    query = text('''
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN evidence->>'exception_type' = 'ANALYTICAL_EXCEPTION' THEN 1 END) as analytical,
            COUNT(CASE WHEN evidence->>'exception_type' = 'DATA_QUALITY_EXCEPTION' THEN 1 END) as dq,
            COUNT(CASE WHEN evidence->>'exception_type' = 'DATA_AVAILABILITY' THEN 1 END) as data_avail
        FROM control_exceptions 
        WHERE period_date = :period_date
    ''')
    row = session.execute(query, {"period_date": period_date}).fetchone()
    val = float(row.total or 0) if row else 0.0
    res = _create_kpi_result(session, period_date, "KPI-005", "Exceptions Generated", "count of control_exceptions for period", val, "exceptions")
    if row:
        res.metadata.update({
            "analytical_exceptions": int(row.analytical or 0),
            "data_quality_exceptions": int(row.dq or 0),
            "data_availability_items": int(row.data_avail or 0),
        })
    return res

def calculate_kpi_006(session, period_date: date) -> KPIResult:
    """KPI-006 Avg Processing Time."""
    query = text('''
        SELECT AVG(duration_ms) 
        FROM control_executions 
        WHERE period_date = :period_date
    ''')
    val = float(session.execute(query, {"period_date": period_date}).scalar() or 0)
    return _create_kpi_result(session, period_date, "KPI-006", "Avg Processing Time", "avg duration_ms from control_executions", val, "ms")

def calculate_kpi_007(session, period_date: date) -> KPIResult:
    """KPI-007 Remediation Turnaround."""
    query = text('''
        SELECT AVG(EXTRACT(EPOCH FROM (completed_at - (
            SELECT timestamp FROM audit_events 
            WHERE object_type='REMEDIATION' AND object_id=remediation_items.id::text AND action='CREATE' LIMIT 1
        )))/86400) 
        FROM remediation_items 
        WHERE status = 'COMPLETED'
    ''')
    val = float(session.execute(query).scalar() or 0)
    return _create_kpi_result(session, period_date, "KPI-007", "Remediation Turnaround", "avg days from creation to completion for completed remediations", val, "days")

def calculate_kpi_008(session, period_date: date) -> KPIResult:
    """KPI-008 Automation Coverage."""
    return _create_kpi_result(session, period_date, "KPI-008", "Automation Coverage", "100% (all controls are automated)", 100.0, "%")

def calculate_all_kpis(session, period_date: date) -> List[KPIResult]:
    """Calculate all KPIs for a given period."""
    logger.info("Calculating all KPIs", period_date=period_date)
    results = [
        calculate_kpi_001(session, period_date),
        calculate_kpi_002(session, period_date),
        calculate_kpi_003(session, period_date),
        calculate_kpi_004(session, period_date),
        calculate_kpi_005(session, period_date),
        calculate_kpi_006(session, period_date),
        calculate_kpi_007(session, period_date),
        calculate_kpi_008(session, period_date)
    ]
    logger.info("Calculated all KPIs", count=len(results))
    return results
