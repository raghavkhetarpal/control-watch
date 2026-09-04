"""Control-related API routes."""
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.models import ControlDefinition, ControlDetailResponse, ControlExecution

router = APIRouter()


@router.get("", response_model=list[ControlDefinition])
def list_controls(
    risk_category: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """List all control definitions."""
    conditions = []
    params: dict = {}

    if risk_category:
        conditions.append("cd.risk_category = :risk_category")
        params["risk_category"] = risk_category
    if is_active is not None:
        conditions.append("cd.is_active = :is_active")
        params["is_active"] = is_active

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    query = text(f"""
        SELECT cd.control_id, cd.name, cd.description, cd.risk_category,
               cd.control_type, cd.frequency, cd.is_active, cd.thresholds
        FROM control_definitions cd
        {where_clause}
        ORDER BY cd.control_id
    """)
    rows = db.execute(query, params).mappings().all()
    return [ControlDefinition(**dict(row)) for row in rows]


@router.get("/{control_id}", response_model=ControlDetailResponse)
def get_control(control_id: str, db: Session = Depends(get_db)):
    """Get detailed control information with recent executions."""
    # Get definition
    def_query = text("""
        SELECT cd.control_id, cd.name, cd.description, cd.risk_category,
               cd.control_type, cd.frequency, cd.is_active, cd.thresholds
        FROM control_definitions cd
        WHERE cd.control_id = :control_id
    """)
    def_row = db.execute(def_query, {"control_id": control_id}).mappings().first()
    if not def_row:
        raise HTTPException(status_code=404, detail="Control not found")

    # Get recent executions
    exec_query = text("""
        SELECT ce.id, ce.control_id, ce.period_date, ce.started_at, ce.completed_at,
               ce.status, ce.records_scanned, ce.exceptions_found,
               ce.pass_rate, ce.duration_ms
        FROM control_executions ce
        WHERE ce.control_id = :control_id
        ORDER BY ce.started_at DESC
        LIMIT 20
    """)
    exec_rows = db.execute(exec_query, {"control_id": control_id}).mappings().all()
    executions = [ControlExecution(**dict(row)) for row in exec_rows]

    # Get total count and avg pass rate
    stats_query = text("""
        SELECT COUNT(*) as total,
               AVG(pass_rate) as avg_pass_rate
        FROM control_executions
        WHERE control_id = :control_id AND status = 'COMPLETED'
    """)
    stats = db.execute(stats_query, {"control_id": control_id}).mappings().first()

    return ControlDetailResponse(
        definition=ControlDefinition(**dict(def_row)),
        recent_executions=executions,
        total_executions=stats["total"] if stats else 0,
        avg_pass_rate=round(float(stats["avg_pass_rate"]), 2) if stats and stats["avg_pass_rate"] else None,
        last_execution=executions[0] if executions else None,
    )
