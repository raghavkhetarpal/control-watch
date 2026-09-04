"""Exception-related API routes."""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.models import (
    ExceptionSummary,
    ExceptionDetail,
    ExceptionListResponse,
    AssignExceptionRequest,
    RemediateExceptionRequest,
    UpdateStatusRequest,
    SetRootCauseRequest,
)

router = APIRouter()


@router.get("", response_model=ExceptionListResponse)
def list_exceptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    severity: Optional[str] = None,
    status: Optional[str] = None,
    risk_category: Optional[str] = None,
    control_id: Optional[str] = None,
    fund_id: Optional[int] = None,
    assigned_to: Optional[str] = None,
    is_repeat: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """List exceptions with filtering and pagination."""
    offset = (page - 1) * page_size
    conditions = []
    params: dict = {"limit": page_size, "offset": offset}

    if severity:
        conditions.append("ce.severity = :severity")
        params["severity"] = severity
    if status:
        conditions.append("ce.status = :status")
        params["status"] = status
    if risk_category:
        conditions.append("ce.risk_category = :risk_category")
        params["risk_category"] = risk_category
    if control_id:
        conditions.append("ce.control_id = :control_id")
        params["control_id"] = control_id
    if fund_id:
        conditions.append("ce.fund_id = :fund_id")
        params["fund_id"] = fund_id
    if assigned_to:
        conditions.append("ce.assigned_to = :assigned_to")
        params["assigned_to"] = assigned_to
    if is_repeat is not None:
        conditions.append("ce.is_repeat = :is_repeat")
        params["is_repeat"] = is_repeat

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    count_query = text(f"SELECT COUNT(*) FROM control_exceptions ce {where_clause}")
    total = db.execute(count_query, params).scalar() or 0

    query = text(f"""
        SELECT ce.id, ce.control_id, cd.name as control_name,
               ce.fund_id, f.fund_name,
               ce.severity, ce.status, ce.risk_category,
               ce.description, ce.risk_score, ce.risk_level,
               ce.assigned_to, ce.detected_at, ce.due_date,
               ce.period_date, ce.is_repeat,
               EXTRACT(DAY FROM NOW() - ce.detected_at)::int as age_days
        FROM control_exceptions ce
        LEFT JOIN control_definitions cd ON ce.control_id = cd.control_id
        LEFT JOIN funds f ON ce.fund_id = f.id
        {where_clause}
        ORDER BY
            CASE ce.severity
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                WHEN 'LOW' THEN 4
            END,
            ce.detected_at DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(query, params).mappings().all()
    exceptions = [ExceptionSummary(**dict(row)) for row in rows]

    return ExceptionListResponse(
        exceptions=exceptions, total=total, page=page, page_size=page_size
    )


@router.get("/{exception_id}", response_model=ExceptionDetail)
def get_exception(exception_id: int, db: Session = Depends(get_db)):
    """Get detailed exception information with evidence and audit trail."""
    query = text("""
        SELECT ce.id, ce.control_id, cd.name as control_name,
               ce.execution_id, ce.fund_id, f.fund_name,
               ce.holding_id, ce.severity, ce.status, ce.risk_category,
               ce.description, ce.evidence,
               ce.impact, ce.likelihood, ce.control_effectiveness,
               ce.risk_score, ce.risk_level,
               ce.inherent_risk_score, ce.residual_risk_score,
               ce.root_cause_category, ce.root_cause_description,
               ce.assigned_to, ce.assigned_at,
               ce.detected_at, ce.due_date, ce.closed_at,
               ce.period_date, ce.is_repeat, ce.previous_exception_id,
               EXTRACT(DAY FROM NOW() - ce.detected_at)::int as age_days
        FROM control_exceptions ce
        LEFT JOIN control_definitions cd ON ce.control_id = cd.control_id
        LEFT JOIN funds f ON ce.fund_id = f.id
        WHERE ce.id = :exception_id
    """)
    row = db.execute(query, {"exception_id": exception_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Exception not found")

    result = dict(row)

    # Get audit trail
    audit_query = text("""
        SELECT id, timestamp, actor, action, object_type, object_id,
               old_value, new_value, reason
        FROM audit_events
        WHERE object_type = 'exception' AND object_id = :obj_id
        ORDER BY timestamp DESC
        LIMIT 50
    """)
    audit_rows = db.execute(audit_query, {"obj_id": str(exception_id)}).mappings().all()
    result["audit_trail"] = [dict(row) for row in audit_rows]

    # Get remediation items
    rem_query = text("""
        SELECT id, exception_id, owner, action_description, due_date,
               priority, status, validation_result, completed_at, notes, created_at
        FROM remediation_items
        WHERE exception_id = :exception_id
        ORDER BY created_at DESC
    """)
    rem_rows = db.execute(rem_query, {"exception_id": exception_id}).mappings().all()
    result["remediation_items"] = [dict(row) for row in rem_rows]

    return ExceptionDetail(**result)


@router.post("/{exception_id}/assign")
def assign_exception(
    exception_id: int,
    request: AssignExceptionRequest,
    db: Session = Depends(get_db),
):
    """Assign an exception to an analyst."""
    # Verify exception exists
    check = db.execute(
        text("SELECT id, status FROM control_exceptions WHERE id = :id"),
        {"id": exception_id}
    ).mappings().first()
    if not check:
        raise HTTPException(status_code=404, detail="Exception not found")

    # Update assignment
    db.execute(
        text("""
            UPDATE control_exceptions
            SET assigned_to = :assigned_to, assigned_at = NOW(),
                status = 'ASSIGNED', updated_at = NOW()
            WHERE id = :id
        """),
        {"assigned_to": request.assigned_to, "id": exception_id}
    )

    # Create audit event
    db.execute(
        text("""
            INSERT INTO audit_events (actor, action, object_type, object_id,
                                      old_value, new_value, reason)
            VALUES (:actor, 'ASSIGNED', 'exception', :obj_id,
                    :old_val, :new_val, :reason)
        """),
        {
            "actor": request.actor,
            "obj_id": str(exception_id),
            "old_val": f'{{"status": "{check["status"]}"}}',
            "new_val": f'{{"status": "ASSIGNED", "assigned_to": "{request.assigned_to}"}}',
            "reason": request.reason,
        }
    )
    db.commit()

    return {"status": "success", "message": f"Exception {exception_id} assigned to {request.assigned_to}"}


@router.post("/{exception_id}/remediate")
def create_remediation(
    exception_id: int,
    request: RemediateExceptionRequest,
    db: Session = Depends(get_db),
):
    """Create a remediation item for an exception."""
    # Verify exception exists
    check = db.execute(
        text("SELECT id, status FROM control_exceptions WHERE id = :id"),
        {"id": exception_id}
    ).mappings().first()
    if not check:
        raise HTTPException(status_code=404, detail="Exception not found")

    # Create remediation item
    result = db.execute(
        text("""
            INSERT INTO remediation_items (exception_id, owner, action_description,
                                           due_date, priority)
            VALUES (:exception_id, :owner, :action, :due_date, :priority)
            RETURNING id
        """),
        {
            "exception_id": exception_id,
            "owner": request.owner,
            "action": request.action_description,
            "due_date": request.due_date,
            "priority": request.priority,
        }
    )
    rem_id = result.scalar()

    # Update exception status
    db.execute(
        text("""
            UPDATE control_exceptions
            SET status = 'REMEDIATION_PLANNED', updated_at = NOW(),
                due_date = :due_date
            WHERE id = :id
        """),
        {"id": exception_id, "due_date": request.due_date}
    )

    # Create audit event
    db.execute(
        text("""
            INSERT INTO audit_events (actor, action, object_type, object_id,
                                      new_value, reason)
            VALUES (:actor, 'REMEDIATION_CREATED', 'exception', :obj_id,
                    :new_val, :reason)
        """),
        {
            "actor": request.actor,
            "obj_id": str(exception_id),
            "new_val": f'{{"remediation_id": {rem_id}, "owner": "{request.owner}", "due_date": "{request.due_date}"}}',
            "reason": f"Remediation planned: {request.action_description}",
        }
    )
    db.commit()

    return {
        "status": "success",
        "remediation_id": rem_id,
        "message": f"Remediation created for exception {exception_id}",
    }


@router.post("/{exception_id}/status")
def update_exception_status(
    exception_id: int,
    request: UpdateStatusRequest,
    db: Session = Depends(get_db),
):
    """Update exception status with audit trail."""
    VALID_TRANSITIONS = {
        "DETECTED": ["TRIAGED", "ASSIGNED", "ACCEPTED"],
        "TRIAGED": ["ASSIGNED", "ACCEPTED"],
        "ASSIGNED": ["INVESTIGATING", "ACCEPTED"],
        "INVESTIGATING": ["REMEDIATION_PLANNED", "ACCEPTED"],
        "REMEDIATION_PLANNED": ["REMEDIATION_IN_PROGRESS"],
        "REMEDIATION_IN_PROGRESS": ["VALIDATION"],
        "VALIDATION": ["CLOSED", "REMEDIATION_PLANNED"],
        "ACCEPTED": [],
        "CLOSED": [],
    }

    check = db.execute(
        text("SELECT id, status FROM control_exceptions WHERE id = :id"),
        {"id": exception_id}
    ).mappings().first()
    if not check:
        raise HTTPException(status_code=404, detail="Exception not found")

    current_status = check["status"]
    new_status = request.status

    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {current_status} to {new_status}. "
                   f"Valid transitions: {VALID_TRANSITIONS.get(current_status, [])}"
        )

    update_fields = "status = :new_status, updated_at = NOW()"
    if new_status == "CLOSED":
        update_fields += ", closed_at = NOW()"

    db.execute(
        text(f"UPDATE control_exceptions SET {update_fields} WHERE id = :id"),
        {"new_status": new_status, "id": exception_id}
    )

    db.execute(
        text("""
            INSERT INTO audit_events (actor, action, object_type, object_id,
                                      old_value, new_value, reason)
            VALUES (:actor, 'STATUS_CHANGE', 'exception', :obj_id,
                    :old_val, :new_val, :reason)
        """),
        {
            "actor": request.actor,
            "obj_id": str(exception_id),
            "old_val": f'{{"status": "{current_status}"}}',
            "new_val": f'{{"status": "{new_status}"}}',
            "reason": request.reason,
        }
    )
    db.commit()

    return {"status": "success", "old_status": current_status, "new_status": new_status}


@router.post("/{exception_id}/root-cause")
def set_root_cause(
    exception_id: int,
    request: SetRootCauseRequest,
    db: Session = Depends(get_db),
):
    """Set root cause for an exception."""
    check = db.execute(
        text("SELECT id FROM control_exceptions WHERE id = :id"),
        {"id": exception_id}
    ).mappings().first()
    if not check:
        raise HTTPException(status_code=404, detail="Exception not found")

    db.execute(
        text("""
            UPDATE control_exceptions
            SET root_cause_category = :category,
                root_cause_description = :description,
                updated_at = NOW()
            WHERE id = :id
        """),
        {
            "category": request.category,
            "description": request.description,
            "id": exception_id,
        }
    )

    db.execute(
        text("""
            INSERT INTO audit_events (actor, action, object_type, object_id,
                                      new_value, reason)
            VALUES (:actor, 'ROOT_CAUSE_SET', 'exception', :obj_id,
                    :new_val, :reason)
        """),
        {
            "actor": request.actor,
            "obj_id": str(exception_id),
            "new_val": f'{{"root_cause_category": "{request.category}"}}',
            "reason": request.description,
        }
    )
    db.commit()

    return {"status": "success", "message": "Root cause set"}
