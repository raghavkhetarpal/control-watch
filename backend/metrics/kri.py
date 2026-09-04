"""
KRI (Key Risk Indicator) framework module.
"""
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional
from sqlalchemy import text
import structlog
import json

logger = structlog.get_logger(__name__)

@dataclass
class KRIResult:
    kri_id: str
    name: str
    description: str
    period_date: date
    numerator: float
    denominator: float
    value: float
    unit: str
    threshold_green: float
    threshold_amber: float
    threshold_red: float
    status: str
    trend: str
    previous_value: Optional[float]
    metadata: Dict[str, Any]

def _determine_status(value: float, green: float, amber: float, red: float, lower_is_better: bool = True) -> str:
    """Determine the status (GREEN/AMBER/RED) based on thresholds."""
    if lower_is_better:
        if value < amber:
            return "GREEN"
        elif value < red:
            return "AMBER"
        else:
            return "RED"
    else:
        if value > amber:
            return "GREEN"
        elif value > red:
            return "AMBER"
        else:
            return "RED"

def _determine_trend(value: float, previous: Optional[float], lower_is_better: bool = True) -> str:
    """Determine the trend compared to previous snapshot."""
    if previous is None:
        return "STABLE"
    
    diff = value - previous
    if abs(diff) < 0.001:
        return "STABLE"
        
    if lower_is_better:
        return "IMPROVING" if diff < 0 else "DETERIORATING"
    else:
        return "IMPROVING" if diff > 0 else "DETERIORATING"

def calculate_kri_001(session, period_date: date) -> KRIResult:
    """KRI-001 Concentration Exposure: max(top-10 holding %) across all funds for the period."""
    query = text('''
        SELECT COALESCE(MAX(CAST(evidence->>'top10_pct' AS FLOAT)), 0.0) as max_exposure
        FROM control_exceptions
        WHERE period_date = :period_date AND control_id = 'CONC-001'
    ''')
    result = session.execute(query, {"period_date": period_date}).scalar()
    
    # Defaults if no data
    value = float(result) if result is not None else 0.0
    
    return _create_kri_result(
        session, period_date, "KRI-001", "Concentration Exposure", 
        "max(top-10 holding %) across all funds for the period (Derived)",
        value, 1.0, value, "%", 35.0, 35.0, 45.0, True
    )

def calculate_kri_002(session, period_date: date) -> KRIResult:
    """KRI-002 Reconciliation Exception Rate: analytical recon exceptions / testable reconciliations."""
    query = text('''
        SELECT 
            COALESCE(SUM(CASE 
                WHEN (execution_metadata->>'analytical_exceptions') IS NOT NULL 
                THEN (execution_metadata->>'analytical_exceptions')::int
                ELSE exceptions_found END), 0) as numerator,
            COALESCE(SUM(CASE 
                WHEN (execution_metadata->>'testable_records') IS NOT NULL 
                THEN (execution_metadata->>'testable_records')::int
                ELSE records_scanned END), 0) as denominator
        FROM control_executions
        WHERE period_date = :period_date AND control_id LIKE 'REC-%'
    ''')
    row = session.execute(query, {"period_date": period_date}).fetchone()
    num = float(row.numerator or 0)
    den = float(row.denominator or 0)
    val = round((num / den * 100), 2) if den > 0 else 0.0
    
    return _create_kri_result(
        session, period_date, "KRI-002", "Reconciliation Exception Rate", 
        "analytical recon exceptions / total testable reconciliations (Derived)",
        num, den, val, "%", 5.0, 5.0, 15.0, True
    )

def calculate_kri_003(session, period_date: date) -> KRIResult:
    """KRI-003 Data Quality Exception Rate."""
    query = text('''
        SELECT 
            SUM(exceptions_found) as numerator,
            SUM(records_scanned) as denominator
        FROM control_executions
        WHERE period_date = :period_date AND control_id LIKE 'DQ-%'
    ''')
    row = session.execute(query, {"period_date": period_date}).fetchone()
    num = float(row.numerator or 0)
    den = float(row.denominator or 0)
    val = (num / den * 100) if den > 0 else 0.0
    
    return _create_kri_result(
        session, period_date, "KRI-003", "Data Quality Exception Rate", 
        "DQ exceptions / total records scanned across DQ controls (Derived)",
        num, den, val, "%", 2.0, 2.0, 10.0, True
    )

def calculate_kri_004(session, period_date: date) -> KRIResult:
    """KRI-004 Valuation Anomaly Rate."""
    query = text('''
        SELECT 
            SUM(exceptions_found) as numerator,
            SUM(records_scanned) as denominator
        FROM control_executions
        WHERE period_date = :period_date AND control_id LIKE 'VAL-%'
    ''')
    row = session.execute(query, {"period_date": period_date}).fetchone()
    num = float(row.numerator or 0)
    den = float(row.denominator or 0)
    val = (num / den * 100) if den > 0 else 0.0
    
    return _create_kri_result(
        session, period_date, "KRI-004", "Valuation Anomaly Rate", 
        "valuation exceptions / total holdings with valuations (Derived)",
        num, den, val, "%", 3.0, 3.0, 10.0, True
    )

def calculate_kri_005(session, period_date: date) -> KRIResult:
    """KRI-005 Reporting Timeliness."""
    query = text('''
        SELECT 
            AVG(filing_date - period_of_report) as avg_delay
        FROM submissions
        WHERE period_of_report = :period_date
    ''')
    result = session.execute(query, {"period_date": period_date}).scalar()
    val = float(result) if result is not None else 0.0
    
    return _create_kri_result(
        session, period_date, "KRI-005", "Reporting Timeliness", 
        "avg filing delay (days) (Derived)",
        val, 1.0, val, "days", 45.0, 45.0, 75.0, True
    )

def calculate_kri_006(session, period_date: date) -> KRIResult:
    """KRI-006 Exception Aging."""
    query = text('''
        SELECT AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - detected_at))/86400) as avg_age
        FROM control_exceptions
        WHERE status NOT IN ('CLOSED', 'ACCEPTED')
    ''')
    result = session.execute(query).scalar()
    val = float(result) if result is not None else 0.0
    
    return _create_kri_result(
        session, period_date, "KRI-006", "Exception Aging", 
        "avg age (days) of open exceptions (Derived)",
        val, 1.0, val, "days", 14.0, 14.0, 30.0, True
    )

def calculate_kri_007(session, period_date: date) -> KRIResult:
    """KRI-007 Repeat Exception Rate."""
    query = text('''
        SELECT 
            COUNT(CASE WHEN is_repeat = TRUE THEN 1 END) as numerator,
            COUNT(*) as denominator
        FROM control_exceptions
        WHERE period_date = :period_date
    ''')
    row = session.execute(query, {"period_date": period_date}).fetchone()
    num = float(row.numerator or 0)
    den = float(row.denominator or 0)
    val = (num / den * 100) if den > 0 else 0.0
    
    return _create_kri_result(
        session, period_date, "KRI-007", "Repeat Exception Rate", 
        "repeat exceptions / total exceptions (Derived)",
        num, den, val, "%", 5.0, 5.0, 15.0, True
    )

def _create_kri_result(
    session, period_date: date, kri_id: str, name: str, description: str,
    num: float, den: float, val: float, unit: str, 
    green: float, amber: float, red: float, lower_is_better: bool
) -> KRIResult:
    
    # Get previous value
    prev_query = text('''
        SELECT value FROM kri_snapshots 
        WHERE kri_id = :kri_id AND period_date < :period_date 
        ORDER BY period_date DESC LIMIT 1
    ''')
    prev_val = session.execute(prev_query, {"kri_id": kri_id, "period_date": period_date}).scalar()
    
    status = _determine_status(val, green, amber, red, lower_is_better)
    trend = _determine_trend(val, prev_val, lower_is_better)
    
    res = KRIResult(
        kri_id=kri_id, name=name, description=description, period_date=period_date,
        numerator=num, denominator=den, value=val, unit=unit,
        threshold_green=green, threshold_amber=amber, threshold_red=red,
        status=status, trend=trend, previous_value=prev_val, metadata={"illustrative_analytical_thresholds": True}
    )
    
    # Save to kri_snapshots
    insert_query = text('''
        INSERT INTO kri_snapshots (
            kri_id, name, description, period_date, numerator, denominator, 
            value, unit, threshold_green, threshold_amber, threshold_red, 
            status, trend, previous_value, metadata
        ) VALUES (
            :kri_id, :name, :description, :period_date, :num, :den, 
            :val, :unit, :green, :amber, :red, 
            :status, :trend, :prev, :metadata
        )
        ON CONFLICT (kri_id, period_date) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            numerator = EXCLUDED.numerator,
            denominator = EXCLUDED.denominator,
            value = EXCLUDED.value,
            unit = EXCLUDED.unit,
            threshold_green = EXCLUDED.threshold_green,
            threshold_amber = EXCLUDED.threshold_amber,
            threshold_red = EXCLUDED.threshold_red,
            status = EXCLUDED.status,
            trend = EXCLUDED.trend,
            previous_value = EXCLUDED.previous_value,
            metadata = EXCLUDED.metadata,
            created_at = NOW()
    ''')
    session.execute(insert_query, {
        "kri_id": res.kri_id, "name": res.name, "description": res.description,
        "period_date": res.period_date, "num": res.numerator, "den": res.denominator,
        "val": res.value, "unit": res.unit, "green": res.threshold_green,
        "amber": res.threshold_amber, "red": res.threshold_red,
        "status": res.status, "trend": res.trend, "prev": res.previous_value,
        "metadata": json.dumps(res.metadata)
    })
    
    return res

def calculate_all_kris(session, period_date: date) -> List[KRIResult]:
    """Calculate all KRIs for a given period."""
    logger.info("Calculating all KRIs", period_date=period_date)
    results = [
        calculate_kri_001(session, period_date),
        calculate_kri_002(session, period_date),
        calculate_kri_003(session, period_date),
        calculate_kri_004(session, period_date),
        calculate_kri_005(session, period_date),
        calculate_kri_006(session, period_date),
        calculate_kri_007(session, period_date)
    ]
    logger.info("Calculated all KRIs", count=len(results))
    return results
