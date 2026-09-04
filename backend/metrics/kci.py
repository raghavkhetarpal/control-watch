"""
KCI (Key Control Indicator) framework module.
"""
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional
from sqlalchemy import text
import structlog
import json

logger = structlog.get_logger(__name__)

@dataclass
class KCIResult:
    kci_id: str
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
    control_id: Optional[str] = None

def _determine_status(value: float, green: float, amber: float, red: float, lower_is_better: bool = False) -> str:
    """Determine the status (GREEN/AMBER/RED) based on illustrative analytical thresholds."""
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

def _determine_trend(value: float, previous: Optional[float], lower_is_better: bool = False) -> str:
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

def _create_kci_result(
    session, period_date: date, kci_id: str, name: str, description: str,
    num: float, den: float, val: float, unit: str, 
    green: float, amber: float, red: float, lower_is_better: bool
) -> KCIResult:
    
    prev_query = text('''
        SELECT value FROM kci_snapshots 
        WHERE kci_id = :kci_id AND period_date < :period_date 
        ORDER BY period_date DESC LIMIT 1
    ''')
    prev_val = session.execute(prev_query, {"kci_id": kci_id, "period_date": period_date}).scalar()
    
    status = _determine_status(val, green, amber, red, lower_is_better)
    trend = _determine_trend(val, prev_val, lower_is_better)
    
    res = KCIResult(
        kci_id=kci_id, name=name, description=description, period_date=period_date,
        numerator=num, denominator=den, value=val, unit=unit,
        threshold_green=green, threshold_amber=amber, threshold_red=red,
        status=status, trend=trend, previous_value=prev_val, metadata={"illustrative_analytical_thresholds": True}
    )
    
    insert_query = text('''
        INSERT INTO kci_snapshots (
            kci_id, control_id, name, description, period_date, numerator, denominator, 
            value, unit, threshold_green, threshold_amber, threshold_red, 
            status, trend, previous_value, metadata
        ) VALUES (
            :kci_id, :control_id, :name, :description, :period_date, :num, :den, 
            :val, :unit, :green, :amber, :red, 
            :status, :trend, :prev, :metadata
        )
        ON CONFLICT (kci_id, period_date) DO UPDATE SET
            control_id = EXCLUDED.control_id,
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
        "kci_id": res.kci_id, "control_id": res.control_id, "name": res.name, "description": res.description,
        "period_date": res.period_date, "num": res.numerator, "den": res.denominator,
        "val": res.value, "unit": res.unit, "green": res.threshold_green,
        "amber": res.threshold_amber, "red": res.threshold_red,
        "status": res.status, "trend": res.trend, "prev": res.previous_value,
        "metadata": json.dumps(res.metadata)
    })
    
    return res

def calculate_kci_001(session, period_date: date) -> KCIResult:
    """KCI-001 Control Execution Rate."""
    query = text('''
        SELECT COUNT(DISTINCT control_id) as executed
        FROM control_executions
        WHERE period_date = :period_date
    ''')
    executed = float(session.execute(query, {"period_date": period_date}).scalar() or 0)
    den = float(session.execute(text("SELECT COUNT(*) FROM control_definitions WHERE is_active = TRUE")).scalar() or 16.0)
    val = (executed / den) * 100 if den > 0 else 0.0
    
    return _create_kci_result(
        session, period_date, "KCI-001", "Control Execution Rate", 
        "controls executed / total active controls (Derived)",
        executed, den, val, "%", 95.0, 85.0, 85.0, False
    )

def calculate_kci_002(session, period_date: date) -> KCIResult:
    """KCI-002 Control Pass Rate."""
    query = text('''
        SELECT 
            COUNT(CASE WHEN exceptions_found = 0 THEN 1 END) as numerator,
            COUNT(*) as denominator
        FROM control_executions
        WHERE period_date = :period_date
    ''')
    row = session.execute(query, {"period_date": period_date}).fetchone()
    num = float(row.numerator or 0)
    den = float(row.denominator or 0)
    val = (num / den * 100) if den > 0 else 100.0
    
    return _create_kci_result(
        session, period_date, "KCI-002", "Control Pass Rate", 
        "executions with 0 exceptions / total executions (Derived)",
        num, den, val, "%", 90.0, 75.0, 75.0, False
    )

def calculate_kci_003(session, period_date: date, kci_002_val: float) -> KCIResult:
    """KCI-003 Control Failure Rate."""
    val = 100.0 - kci_002_val
    return _create_kci_result(
        session, period_date, "KCI-003", "Control Failure Rate", 
        "1 - pass rate (Derived)",
        val, 100.0, val, "%", 10.0, 10.0, 25.0, True
    )

def calculate_kci_004(session, period_date: date) -> KCIResult:
    """KCI-004 Evidence Completeness."""
    query = text('''
        SELECT 
            COUNT(CASE WHEN evidence IS NOT NULL AND evidence::text != '{}' THEN 1 END) as numerator,
            COUNT(*) as denominator
        FROM control_exceptions
        WHERE period_date = :period_date
    ''')
    row = session.execute(query, {"period_date": period_date}).fetchone()
    num = float(row.numerator or 0)
    den = float(row.denominator or 0)
    val = (num / den * 100) if den > 0 else 100.0
    
    return _create_kci_result(
        session, period_date, "KCI-004", "Evidence Completeness", 
        "exceptions with non-empty evidence JSON / total exceptions (Derived)",
        num, den, val, "%", 95.0, 80.0, 80.0, False
    )

def calculate_kci_005(session, period_date: date) -> KCIResult:
    """KCI-005 Repeat Control Failure Rate."""
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
    
    return _create_kci_result(
        session, period_date, "KCI-005", "Repeat Control Failure Rate", 
        "repeat exception count / total exception count (Derived)",
        num, den, val, "%", 5.0, 5.0, 15.0, True
    )

def calculate_kci_006(session, period_date: date) -> KCIResult:
    """KCI-006 Overdue Remediation Rate."""
    query = text('''
        SELECT 
            COUNT(CASE WHEN due_date < CURRENT_DATE THEN 1 END) as numerator,
            COUNT(*) as denominator
        FROM remediation_items
        WHERE status NOT IN ('COMPLETED', 'CLOSED')
    ''')
    row = session.execute(query).fetchone()
    num = float(row.numerator or 0)
    den = float(row.denominator or 0)
    val = (num / den * 100) if den > 0 else 0.0
    
    return _create_kci_result(
        session, period_date, "KCI-006", "Overdue Remediation Rate", 
        "overdue remediations / total open remediations (Derived)",
        num, den, val, "%", 10.0, 10.0, 25.0, True
    )

def calculate_kci_007(session, period_date: date, kci_001_val: float) -> KCIResult:
    """KCI-007 Control Coverage."""
    # Since we lack control definition tables here, this is conceptually similar to KCI-001
    return _create_kci_result(
        session, period_date, "KCI-007", "Control Coverage", 
        "controls with >=1 execution this period / total active controls (Derived)",
        kci_001_val, 100.0, kci_001_val, "%", 95.0, 85.0, 85.0, False
    )

def calculate_all_kcis(session, period_date: date) -> List[KCIResult]:
    """Calculate all KCIs for a given period."""
    logger.info("Calculating all KCIs", period_date=period_date)
    kci_001 = calculate_kci_001(session, period_date)
    kci_002 = calculate_kci_002(session, period_date)
    
    results = [
        kci_001,
        kci_002,
        calculate_kci_003(session, period_date, kci_002.value),
        calculate_kci_004(session, period_date),
        calculate_kci_005(session, period_date),
        calculate_kci_006(session, period_date),
        calculate_kci_007(session, period_date, kci_001.value)
    ]
    logger.info("Calculated all KCIs", count=len(results))
    return results
