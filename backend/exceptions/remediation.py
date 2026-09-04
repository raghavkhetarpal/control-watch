"""
Remediation tracking module.
"""
from typing import Dict, Any, List, Optional
from datetime import date
from sqlalchemy import text
import structlog
import json

from backend.exceptions.manager import transition_exception

logger = structlog.get_logger(__name__)

def _create_audit_event(session, actor: str, action: str, object_id: str, 
                        old_value: Dict, new_value: Dict, reason: Optional[str] = None):
    query = text('''
        INSERT INTO audit_events (
            timestamp, actor, action, object_type, object_id, 
            old_value, new_value, reason
        ) VALUES (
            CURRENT_TIMESTAMP, :actor, :action, 'REMEDIATION', :object_id,
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

def create_remediation(session, exception_id: str, owner: str, action: str, due_date: date, priority: str, actor: str) -> int:
    """
    Creates remediation_items record and audit_event.
    Transitions exception to REMEDIATION_PLANNED.
    """
    query = text('''
        INSERT INTO remediation_items (
            exception_id, owner, action_description, due_date, priority, status
        ) VALUES (
            :exception_id, :owner, :action, :due_date, :priority, 'OPEN'
        ) RETURNING id
    ''')
    
    result = session.execute(query, {
        "exception_id": exception_id,
        "owner": owner,
        "action": action,
        "due_date": due_date,
        "priority": priority
    })
    
    remediation_id = result.scalar()
    
    _create_audit_event(
        session, actor, "CREATE", str(remediation_id),
        {}, {"owner": owner, "action": action, "due_date": str(due_date), "priority": priority},
        "Initial creation"
    )
    
    # Transition the exception
    transition_exception(session, exception_id, "REMEDIATION_PLANNED", actor, "Remediation created")
    
    return remediation_id

def update_remediation_status(session, remediation_id: int, new_status: str, actor: str, notes: Optional[str] = None) -> bool:
    """Update remediation status."""
    query = text("SELECT status, exception_id FROM remediation_items WHERE id = :id")
    row = session.execute(query, {"id": remediation_id}).fetchone()
    
    if not row:
        return False
        
    old_status = row.status
    exception_id = row.exception_id
    
    update_query = text('''
        UPDATE remediation_items 
        SET status = :status, notes = :notes
        WHERE id = :id
    ''')
    
    if new_status == 'COMPLETED':
        update_query = text('''
            UPDATE remediation_items 
            SET status = :status, notes = :notes, completed_at = CURRENT_TIMESTAMP
            WHERE id = :id
        ''')
        
    session.execute(update_query, {"status": new_status, "notes": notes, "id": remediation_id})
    
    _create_audit_event(
        session, actor, "STATUS_CHANGE", str(remediation_id),
        {"status": old_status}, {"status": new_status, "notes": notes}, None
    )
    
    # Optional: sync exception status based on remediation status
    if new_status == 'IN_PROGRESS':
        try:
            transition_exception(session, exception_id, "REMEDIATION_IN_PROGRESS", actor, f"Remediation {remediation_id} started")
        except ValueError:
            pass # Ignore if invalid transition
            
    elif new_status == 'COMPLETED':
        try:
            transition_exception(session, exception_id, "VALIDATION", actor, f"Remediation {remediation_id} completed, pending validation")
        except ValueError:
            pass

    return True

def validate_remediation(session, remediation_id: int, result: str, validator: str) -> bool:
    """Validate a completed remediation."""
    query = text("SELECT status, exception_id FROM remediation_items WHERE id = :id")
    row = session.execute(query, {"id": remediation_id}).fetchone()
    
    if not row or row.status != 'COMPLETED':
        return False
        
    update_query = text('''
        UPDATE remediation_items 
        SET validation_result = :result, validated_at = CURRENT_TIMESTAMP, validated_by = :validator, status = 'VALIDATED'
        WHERE id = :id
    ''')
    session.execute(update_query, {"result": result, "validator": validator, "id": remediation_id})
    
    _create_audit_event(
        session, validator, "VALIDATE", str(remediation_id),
        {"status": "COMPLETED"}, {"status": "VALIDATED", "result": result}, None
    )
    
    if result.upper() == 'PASS':
        try:
            transition_exception(session, row.exception_id, "CLOSED", validator, "Remediation validated successfully")
        except ValueError:
            pass
    else:
        try:
            transition_exception(session, row.exception_id, "REMEDIATION_IN_PROGRESS", validator, "Remediation validation failed")
            # Set remediation back to in progress
            session.execute(text("UPDATE remediation_items SET status = 'IN_PROGRESS' WHERE id = :id"), {"id": remediation_id})
        except ValueError:
            pass
            
    return True

def get_overdue_remediations(session) -> List[Dict]:
    """Get list of overdue remediations."""
    query = text('''
        SELECT * FROM remediation_items 
        WHERE status NOT IN ('COMPLETED', 'CLOSED') 
        AND due_date < CURRENT_DATE
    ''')
    rows = session.execute(query).fetchall()
    return [dict(r._mapping) for r in rows]

def get_remediation_stats(session) -> Dict[str, Any]:
    """Get remediation statistics."""
    stats = {}
    
    # Overdue count
    query_overdue = text("SELECT COUNT(*) FROM remediation_items WHERE status NOT IN ('COMPLETED', 'CLOSED') AND due_date < CURRENT_DATE")
    stats['overdue_count'] = session.execute(query_overdue).scalar() or 0
    
    # MTTR (Mean Time To Remediate) in days
    query_mttr = text('''
        SELECT AVG(EXTRACT(EPOCH FROM (completed_at - (
            SELECT timestamp FROM audit_events 
            WHERE object_type='REMEDIATION' AND object_id=remediation_items.id::text AND action='CREATE' LIMIT 1
        )))/86400) 
        FROM remediation_items 
        WHERE status = 'COMPLETED'
    ''')
    stats['mttr_days'] = float(session.execute(query_mttr).scalar() or 0)
    
    # By owner
    query_owner = text("SELECT owner, COUNT(*) as cnt FROM remediation_items WHERE status NOT IN ('COMPLETED', 'CLOSED') GROUP BY owner")
    stats['by_owner'] = {r.owner: r.cnt for r in session.execute(query_owner).fetchall()}
    
    # By priority
    query_priority = text("SELECT priority, COUNT(*) as cnt FROM remediation_items WHERE status NOT IN ('COMPLETED', 'CLOSED') GROUP BY priority")
    stats['by_priority'] = {r.priority: r.cnt for r in session.execute(query_priority).fetchall()}
    
    return stats

def check_repeat_exceptions(session, exception_id: str) -> bool:
    """Checks if same fund+control had a previous closed exception."""
    query = text('''
        SELECT fund_id, control_id FROM control_exceptions WHERE id = :id
    ''')
    current = session.execute(query, {"id": exception_id}).fetchone()
    
    if not current or not current.fund_id:
        return False
        
    check_query = text('''
        SELECT id FROM control_exceptions 
        WHERE fund_id = :fund_id 
        AND control_id = :control_id 
        AND status = 'CLOSED' 
        AND id != :id
        LIMIT 1
    ''')
    prev = session.execute(check_query, {
        "fund_id": current.fund_id, 
        "control_id": current.control_id, 
        "id": exception_id
    }).fetchone()
    
    if prev:
        # Mark current as repeat
        update_query = text('''
            UPDATE control_exceptions 
            SET is_repeat = TRUE, previous_exception_id = :prev_id
            WHERE id = :id
        ''')
        session.execute(update_query, {"prev_id": prev.id, "id": exception_id})
        return True
        
    return False
