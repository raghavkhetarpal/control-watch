"""Audit events API routes."""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.models import AuditEvent, AuditEventListResponse

router = APIRouter()


@router.get("", response_model=AuditEventListResponse)
def list_audit_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    object_type: Optional[str] = None,
    object_id: Optional[str] = None,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    since: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """List audit events with filtering and pagination."""
    offset = (page - 1) * page_size
    conditions = []
    params: dict = {"limit": page_size, "offset": offset}

    if object_type:
        conditions.append("ae.object_type = :object_type")
        params["object_type"] = object_type
    if object_id:
        conditions.append("ae.object_id = :object_id")
        params["object_id"] = object_id
    if actor:
        conditions.append("ae.actor = :actor")
        params["actor"] = actor
    if action:
        conditions.append("ae.action = :action")
        params["action"] = action
    if since:
        conditions.append("ae.timestamp >= :since")
        params["since"] = since

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    count_query = text(f"SELECT COUNT(*) FROM audit_events ae {where_clause}")
    total = db.execute(count_query, params).scalar() or 0

    query = text(f"""
        SELECT ae.id, ae.timestamp, ae.actor, ae.action,
               ae.object_type, ae.object_id,
               ae.old_value, ae.new_value, ae.reason
        FROM audit_events ae
        {where_clause}
        ORDER BY ae.timestamp DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(query, params).mappings().all()
    events = [AuditEvent(**dict(row)) for row in rows]

    return AuditEventListResponse(events=events, total=total, page=page, page_size=page_size)
