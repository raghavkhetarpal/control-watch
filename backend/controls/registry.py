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


def _ensure_controls_loaded():
    """Ensure all control modules are imported to populate registry."""
    if not _CONTROLS:
        from backend.controls import data_quality  # noqa: F401
        from backend.controls import reconciliation  # noqa: F401
        from backend.controls import valuation  # noqa: F401
        from backend.controls import concentration  # noqa: F401
        from backend.controls import liquidity  # noqa: F401
        from backend.controls import reporting  # noqa: F401
        from backend.controls import classification  # noqa: F401


def get_all_controls() -> List[BaseControl]:
    """Returns list of instantiated control objects."""
    _ensure_controls_loaded()
    return [cls() for cls in _CONTROLS.values()]


def run_control(session: Session, control_id: str, period_date) -> ControlResult:
    """Runs a single control and records execution + exceptions in the database."""
    _ensure_controls_loaded()
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
        from backend.risk_engine.scoring import score_exception

        for exc_data in result.exceptions:
            exc_type = exc_data.get("exception_type", "ANALYTICAL_EXCEPTION")
            score, risk_lvl, breakdown = score_exception(exc_data)
            
            evidence_dict = dict(exc_data.get("data", exc_data.get("evidence", {})))
            evidence_dict["exception_type"] = exc_type
            evidence_dict["score_breakdown"] = breakdown
            evidence_json = json.dumps(evidence_dict, default=str)

            impact = breakdown.get("impact", 3)
            likelihood = breakdown.get("likelihood", 3)
            ce = breakdown.get("control_effectiveness", 3)
            inherent = impact * likelihood
            residual = max(1, int(inherent * (1 - (ce / 5.0) * 0.8))) if risk_lvl != "INSUFFICIENT_EVIDENCE" else 1

            session.execute(
                text("""
                    INSERT INTO control_exceptions
                        (control_id, execution_id, fund_id, holding_id,
                         severity, status, risk_category, description,
                         evidence, impact, likelihood, control_effectiveness,
                         risk_score, inherent_risk_score, residual_risk_score,
                         risk_level, period_date, detected_at)
                    VALUES
                        (:control_id, :exec_id, :fund_id, :holding_id,
                         :severity, 'DETECTED', :risk_category, :description,
                         CAST(:evidence AS jsonb), :impact, :likelihood, :ce,
                         :risk_score, :inherent, :residual,
                         :risk_level, :period_date, NOW())
                """),
                {
                    "control_id": control_id,
                    "exec_id": exec_id,
                    "fund_id": exc_data.get("fund_id"),
                    "holding_id": exc_data.get("holding_id"),
                    "severity": exc_data.get("severity", "MEDIUM") if exc_type != "DATA_AVAILABILITY" else "LOW",
                    "risk_category": control.risk_category,
                    "description": exc_data.get("description", "Control exception detected"),
                    "evidence": evidence_json,
                    "impact": impact,
                    "likelihood": likelihood,
                    "ce": ce,
                    "risk_score": score,
                    "inherent": inherent,
                    "residual": residual,
                    "risk_level": risk_lvl,
                    "period_date": period_date,
                }
            )

        # Calculate pass rate on testable records
        testable = result.testable_records if result.testable_records > 0 else result.records_scanned
        if testable > 0:
            analytical_exceptions = sum(
                1 for e in result.exceptions if e.get("exception_type") != "DATA_AVAILABILITY"
            )
            result.pass_rate = round(
                max(0.0, (1 - analytical_exceptions / testable) * 100), 2
            )
        else:
            result.pass_rate = 100.0

        if not result.data_requirements and getattr(control, "data_requirements", None):
            result.data_requirements = control.data_requirements

        metadata_json = json.dumps({
            "testable_records": result.testable_records,
            "passed_records": result.passed_records,
            "not_testable_records": result.not_testable_records,
            "data_requirements": result.data_requirements,
            "coverage_ratio": result.coverage_ratio,
            "evaluation_status": result.evaluation_status,
            "details": result.details,
        }, default=str)

        exec_status = result.status if result.status in ('COMPLETED', 'PARTIAL') else 'COMPLETED'

        # Update execution record
        session.execute(
            text("""
                UPDATE control_executions
                SET status = :status,
                    completed_at = NOW(),
                    records_scanned = :scanned,
                    exceptions_found = :exceptions_found,
                    pass_rate = :pass_rate,
                    duration_ms = :duration_ms,
                    execution_metadata = CAST(:metadata AS jsonb)
                WHERE id = :exec_id
            """),
            {
                "status": exec_status,
                "scanned": result.records_scanned,
                "exceptions_found": result.exceptions_found,
                "pass_rate": result.pass_rate,
                "duration_ms": duration_ms,
                "metadata": metadata_json,
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
