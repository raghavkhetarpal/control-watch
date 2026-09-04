"""
Exception lifecycle manager.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import text
import structlog
import json

logger = structlog.get_logger(__name__)

# Valid status transitions
VALID_TRANSITIONS = {
    "DETECTED": ["TRIAGED", "ACCEPTED", "CLOSED"],
    "TRIAGED": ["ASSIGNED", "ACCEPTED", "CLOSED"],
    "ASSIGNED": ["INVESTIGATING", "ACCEPTED"],
    "INVESTIGATING": ["REMEDIATION_PLANNED", "ACCEPTED", "CLOSED"],
    "REMEDIATION_PLANNED": ["REMEDIATION_IN_PROGRESS"],
    "REMEDIATION_IN_PROGRESS": ["VALIDATION"],
    "VALIDATION": ["CLOSED", "REMEDIATION_IN_PROGRESS"],
    "CLOSED": [],
    "ACCEPTED": []
}

def _create_audit_event(session, actor: str, action: str, object_id: str, 
                        old_value: Dict, new_value: Dict, reason: Optional[str] = None):
    query = text('''
        INSERT INTO audit_events (
            timestamp, actor, action, object_type, object_id, 
            old_value, new_value, reason
        ) VALUES (
            CURRENT_TIMESTAMP, :actor, :action, 'EXCEPTION', :object_id,
            :old_value, :new_value, :reason
        )
    ''')
    session.execute(query, {
        "actor": actor,
        "action": action,
        "object_id": object_id,
        "old_value": json.dumps(old_value),
        "new_value": json.dumps(new_value),
        "reason": reason
    })

def transition_exception(session, exception_id: str, new_status: str, actor: str, reason: str = None) -> bool:
    """Transition an exception to a new status."""
    query = text("SELECT status FROM control_exceptions WHERE id = :id")
    current_status = session.execute(query, {"id": exception_id}).scalar()
    
    if not current_status:
        logger.error("Exception not found", exception_id=exception_id)
        return False
        
    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        logger.error("Invalid transition", current_status=current_status, new_status=new_status)
        raise ValueError(f"Invalid transition from {current_status} to {new_status}")
        
    update_query = text("UPDATE control_exceptions SET status = :status WHERE id = :id")
    if new_status == 'CLOSED':
        update_query = text("UPDATE control_exceptions SET status = :status, closed_at = CURRENT_TIMESTAMP WHERE id = :id")
        
    session.execute(update_query, {"status": new_status, "id": exception_id})
    
    _create_audit_event(
        session, actor, "STATUS_CHANGE", exception_id, 
        {"status": current_status}, {"status": new_status}, reason
    )
    
    logger.info("Exception transitioned", exception_id=exception_id, new_status=new_status)
    return True

def assign_exception(session, exception_id: str, assigned_to: str, actor: str) -> bool:
    """Assigns and transitions to ASSIGNED."""
    query = text("SELECT status, assigned_to FROM control_exceptions WHERE id = :id")
    row = session.execute(query, {"id": exception_id}).fetchone()
    if not row:
        return False
        
    current_status = row.status
    old_assigned = row.assigned_to
    
    if current_status not in ["DETECTED", "TRIAGED", "ASSIGNED"]:
        raise ValueError(f"Cannot assign exception in status {current_status}")
        
    update_query = text('''
        UPDATE control_exceptions 
        SET assigned_to = :assigned_to, assigned_at = CURRENT_TIMESTAMP, status = 'ASSIGNED'
        WHERE id = :id
    ''')
    session.execute(update_query, {"assigned_to": assigned_to, "id": exception_id})
    
    _create_audit_event(
        session, actor, "ASSIGN", exception_id,
        {"assigned_to": old_assigned, "status": current_status},
        {"assigned_to": assigned_to, "status": "ASSIGNED"}, None
    )
    return True

def get_exception_detail(session, exception_id: str) -> dict:
    """Get full exception detail with risk scores, evidence, audit trail."""
    query = text("SELECT * FROM control_exceptions WHERE id = :id")
    row = session.execute(query, {"id": exception_id}).fetchone()
    if not row:
        return {}
        
    result = dict(row._mapping)
    
    audit_query = text("SELECT * FROM audit_events WHERE object_type = 'EXCEPTION' AND object_id = :id ORDER BY timestamp DESC")
    audit_rows = session.execute(audit_query, {"id": str(exception_id)}).fetchall()
    result['audit_trail'] = [dict(r._mapping) for r in audit_rows]
    
    return result

def get_exceptions(session, filters: Dict[str, Any]) -> List[dict]:
    """Filtered list with pagination."""
    # Simplified filtering
    query_str = "SELECT * FROM control_exceptions WHERE 1=1"
    params = {}
    
    if "status" in filters:
        query_str += " AND status = :status"
        params["status"] = filters["status"]
    
    if "severity" in filters:
        query_str += " AND severity = :severity"
        params["severity"] = filters["severity"]
        
    query_str += " LIMIT :limit OFFSET :offset"
    params["limit"] = filters.get("limit", 50)
    params["offset"] = filters.get("offset", 0)
    
    rows = session.execute(text(query_str), params).fetchall()
    return [dict(r._mapping) for r in rows]

def set_root_cause(session, exception_id: str, category: str, description: str, actor: str) -> bool:
    """Set root cause for an exception."""
    query = text("SELECT root_cause_category, root_cause_description FROM control_exceptions WHERE id = :id")
    row = session.execute(query, {"id": exception_id}).fetchone()
    if not row:
        return False
        
    update_query = text('''
        UPDATE control_exceptions 
        SET root_cause_category = :category, root_cause_description = :desc
        WHERE id = :id
    ''')
    session.execute(update_query, {"category": category, "desc": description, "id": exception_id})
    
    _create_audit_event(
        session, actor, "SET_ROOT_CAUSE", exception_id,
        {"category": row.root_cause_category, "description": row.root_cause_description},
        {"category": category, "description": description}, None
    )
    return True

def bulk_triage(session, exception_ids: List[str], actor: str) -> int:
    """Triage multiple exceptions at once."""
    success_count = 0
    for eid in exception_ids:
        try:
            if transition_exception(session, eid, "TRIAGED", actor, "Bulk triage"):
                success_count += 1
        except ValueError:
            pass
    return success_count
