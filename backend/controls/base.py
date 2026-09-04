import time
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
import structlog
import uuid

logger = structlog.get_logger(__name__)

@dataclass
class ControlResult:
    control_id: str
    name: str
    status: str  # COMPLETED, FAILED, PARTIAL
    records_scanned: int
    exceptions_found: int
    pass_rate: float
    duration_ms: int
    details: Dict[str, Any] = field(default_factory=dict)
    exceptions: List[Dict[str, Any]] = field(default_factory=list)

class BaseControl(ABC):
    control_id: str
    name: str
    description: str
    risk_category: str

    @abstractmethod
    def execute(self, session: Session, period_date: str) -> ControlResult:
        pass

    def _create_exception(self, entity_id: str, severity: str, description: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to create an exception record structure."""
        return {
            "entity_id": entity_id,
            "severity": severity,
            "description": description,
            "data": data
        }
