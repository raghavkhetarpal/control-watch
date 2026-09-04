"""Control registry — discovers, registers, and executes all controls."""
import time
import json

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Dict, Type

from .base import BaseControl, ControlResult

logger = structlog.get_logger(__name__)

# Registry for controls
_CONTROLS: Dict[str, Type[BaseControl]] = {}


def register_control(cls: Type[BaseControl]) -> Type[BaseControl]:
    """Decorator to register a control class."""
    _CONTROLS[cls.control_id] = cls
    return cls


def get_all_controls() -> List[BaseControl]:
    """Returns list of instantiated control objects."""
    return [cls() for cls in _CONTROLS.values()]


def run_control(session: Session, control_id: str, period_date) -> ControlResult:
    """Runs a single control and records execution + exceptions in the database."""
    cls = _CONTROLS.get(control_id)
    if not cls:
        raise ValueError(f"Control '{control_id}' not found in registry.")

    control = cls()
    logger.info("running_control", control_id=control_id, period_date=str(period_date))

    # Create execution record
    exec_id = session.execute(
        text("""
            INSERT INTO control_executions
                (control_id, period_date, started_at, status)
            VALUES
                (:control_id, :period_date, NOW(), 'RUNNING')
            RETURNING id
        """),
        {"control_id": control_id, "period_date": period_date}
    ).scalar()
    session.flush()

    try:
        start_ms = time.time()
        result = control.execute(session, period_date)
        duration_ms = int((time.time() - start_ms) * 1000)
        result.duration_ms = duration_ms

        # Insert individual exception records
        for exc_data in result.exceptions:
            evidence_json = json.dumps(exc_data.get("data", exc_data.get("evidence", {})), default=str)
            session.execute(
                text("""
                    INSERT INTO control_exceptions
                        (control_id, execution_id, fund_id, holding_id,
                         severity, status, risk_category, description,
                         evidence, period_date, detected_at)
                    VALUES
                        (:control_id, :exec_id, :fund_id, :holding_id,
                         :severity, 'DETECTED', :risk_category, :description,
                         CAST(:evidence AS jsonb), :period_date, NOW())
                """),
                {
                    "control_id": control_id,
                    "exec_id": exec_id,
                    "fund_id": exc_data.get("fund_id"),
                    "holding_id": exc_data.get("holding_id"),
                    "severity": exc_data.get("severity", "MEDIUM"),
                    "risk_category": control.risk_category,
                    "description": exc_data.get("description", "Control exception detected"),
                    "evidence": evidence_json,
                    "period_date": period_date,
                }
            )

        # Calculate pass rate
        if result.records_scanned > 0:
            result.pass_rate = round(
                (1 - result.exceptions_found / result.records_scanned) * 100, 2
            )
        else:
            result.pass_rate = 100.0

        # Update execution record
        session.execute(
            text("""
                UPDATE control_executions
                SET status = 'COMPLETED',
                    completed_at = NOW(),
                    records_scanned = :scanned,
                    exceptions_found = :exceptions_found,
                    pass_rate = :pass_rate,
                    duration_ms = :duration_ms
                WHERE id = :exec_id
            """),
            {
                "scanned": result.records_scanned,
                "exceptions_found": result.exceptions_found,
                "pass_rate": result.pass_rate,
                "duration_ms": duration_ms,
                "exec_id": exec_id,
            }
        )

        logger.info(
            "control_completed",
            control_id=control_id,
            records_scanned=result.records_scanned,
            exceptions_found=result.exceptions_found,
            pass_rate=result.pass_rate,
            duration_ms=duration_ms,
        )
        return result

    except Exception as e:
        logger.error("control_execution_failed", control_id=control_id, error=str(e))
        session.rollback()
        try:
            session.execute(
                text("""
                    UPDATE control_executions
                    SET status = 'FAILED', completed_at = NOW(),
                        error_message = :error
                    WHERE id = :exec_id
                """),
                {"exec_id": exec_id, "error": str(e)[:500]}
            )
            session.commit()
        except Exception:
            session.rollback()
        return ControlResult(
            control_id=control_id,
            name=control.name,
            status="FAILED",
            records_scanned=0,
            exceptions_found=0,
            pass_rate=0.0,
            duration_ms=0,
            details={"error": str(e)},
        )


def run_all_controls(session: Session, period_date) -> List[ControlResult]:
    """Executes all registered controls for the given period."""
    # Import all control modules to trigger registration
    from backend.controls import data_quality  # noqa: F401
    from backend.controls import reconciliation  # noqa: F401
    from backend.controls import valuation  # noqa: F401
    from backend.controls import concentration  # noqa: F401
    from backend.controls import liquidity  # noqa: F401
    from backend.controls import reporting  # noqa: F401
    from backend.controls import classification  # noqa: F401

    logger.info("running_all_controls", period_date=str(period_date), control_count=len(_CONTROLS))
    results = []
    for control_id in sorted(_CONTROLS.keys()):
        try:
            result = run_control(session, control_id, period_date)
            results.append(result)
        except Exception as e:
            logger.error("control_skipped", control_id=control_id, error=str(e))
            results.append(ControlResult(
                control_id=control_id,
                name=control_id,
                status="FAILED",
                records_scanned=0,
                exceptions_found=0,
                pass_rate=0.0,
                duration_ms=0,
            ))
    session.commit()
    return results
