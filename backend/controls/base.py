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
    status: str  # COMPLETED, FAILED, PARTIAL, NOT_TESTABLE
    records_scanned: int
    exceptions_found: int
    pass_rate: float
    duration_ms: int
    testable_records: int = 0
    passed_records: int = 0
    not_testable_records: int = 0
    data_requirements: List[str] = field(default_factory=list)
    coverage_ratio: float = 1.0
    evaluation_status: str = "COMPLETED"  # COMPLETED, PARTIAL, NOT_TESTABLE
    details: Dict[str, Any] = field(default_factory=dict)
    exceptions: List[Dict[str, Any]] = field(default_factory=list)

class BaseControl(ABC):
    control_id: str
    name: str
    description: str
    risk_category: str
    data_requirements: List[str] = field(default_factory=list)

    @abstractmethod
    def execute(self, session: Session, period_date: str) -> ControlResult:
        pass

    def _create_exception(
        self,
        entity_id: str,
        severity: str,
        description: str,
        data: Dict[str, Any],
        exception_type: str = "ANALYTICAL_EXCEPTION",
        fund_id: Optional[int] = None,
        holding_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Helper to create an exception record structure with taxonomy classification."""
        return {
            "entity_id": entity_id,
            "fund_id": fund_id,
            "holding_id": holding_id,
            "severity": severity,
            "description": description,
            "exception_type": exception_type,
            "data": data,
            "evidence": data,
        }
