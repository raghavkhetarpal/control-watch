"""Pydantic models for API request/response schemas."""
from datetime import date, datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ============================================================
# Fund Schemas
# ============================================================

class FundSummary(BaseModel):
    id: int
    accession_number: str
    series_id: Optional[str] = None
    cik: Optional[str] = None
    fund_name: Optional[str] = None
    total_assets: Optional[float] = None
    net_assets: Optional[float] = None
    period_of_report: Optional[date] = None
    filing_date: Optional[date] = None

    class Config:
        from_attributes = True


class FundDetail(FundSummary):
    total_liabilities: Optional[float] = None
    registrant_name: Optional[str] = None
    holding_count: Optional[int] = None
    exception_count: Optional[int] = None
    risk_level: Optional[str] = None


class FundListResponse(BaseModel):
    funds: list[FundSummary]
    total: int
    page: int
    page_size: int


# ============================================================
# Holding Schemas
# ============================================================

class HoldingSummary(BaseModel):
    id: int
    accession_number: str
    holding_id: Optional[str] = None
    fund_id: Optional[int] = None
    name: Optional[str] = None
    cusip: Optional[str] = None
    isin: Optional[str] = None
    balance: Optional[float] = None
    units: Optional[str] = None
    value: Optional[float] = None
    pct_val: Optional[float] = None
    asset_cat: Optional[str] = None
    issuer_cat: Optional[str] = None
    investment_country: Optional[str] = None

    class Config:
        from_attributes = True


class HoldingListResponse(BaseModel):
    holdings: list[HoldingSummary]
    total: int
    page: int
    page_size: int


# ============================================================
# Control Schemas
# ============================================================

class ControlDefinition(BaseModel):
    control_id: str
    name: str
    description: Optional[str] = None
    risk_category: str
    control_type: str
    frequency: Optional[str] = None
    is_active: bool = True
    thresholds: Optional[dict] = None


class ControlExecution(BaseModel):
    id: int
    control_id: str
    period_date: Optional[date] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    records_scanned: int = 0
    exceptions_found: int = 0
    pass_rate: Optional[float] = None
    duration_ms: Optional[int] = None


class ControlDetailResponse(BaseModel):
    definition: ControlDefinition
    recent_executions: list[ControlExecution]
    total_executions: int
    avg_pass_rate: Optional[float] = None
    last_execution: Optional[ControlExecution] = None


# ============================================================
# Exception Schemas
# ============================================================

class ExceptionSummary(BaseModel):
    id: int
    control_id: str
    control_name: Optional[str] = None
    fund_id: Optional[int] = None
    fund_name: Optional[str] = None
    severity: str
    status: str
    risk_category: Optional[str] = None
    description: str
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    assigned_to: Optional[str] = None
    detected_at: datetime
    due_date: Optional[date] = None
    period_date: Optional[date] = None
    is_repeat: bool = False
    age_days: Optional[int] = None


class ExceptionDetail(ExceptionSummary):
    execution_id: Optional[int] = None
    holding_id: Optional[int] = None
    evidence: Optional[dict] = None
    impact: Optional[int] = None
    likelihood: Optional[int] = None
    control_effectiveness: Optional[int] = None
    inherent_risk_score: Optional[int] = None
    residual_risk_score: Optional[int] = None
    root_cause_category: Optional[str] = None
    root_cause_description: Optional[str] = None
    assigned_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    previous_exception_id: Optional[int] = None
    audit_trail: list[dict] = []
    remediation_items: list[dict] = []


class ExceptionListResponse(BaseModel):
    exceptions: list[ExceptionSummary]
    total: int
    page: int
    page_size: int


class AssignExceptionRequest(BaseModel):
    assigned_to: str
    actor: str = "analyst"
    reason: Optional[str] = None


class RemediateExceptionRequest(BaseModel):
    action_description: str
    owner: str
    due_date: date
    priority: str = "MEDIUM"
    actor: str = "analyst"


class UpdateStatusRequest(BaseModel):
    status: str
    actor: str = "analyst"
    reason: Optional[str] = None


class SetRootCauseRequest(BaseModel):
    category: str
    description: str
    actor: str = "analyst"


# ============================================================
# Metrics Schemas
# ============================================================

class KRISnapshot(BaseModel):
    kri_id: str
    name: str
    description: Optional[str] = None
    period_date: date
    numerator: Optional[float] = None
    denominator: Optional[float] = None
    value: float
    unit: str = "PERCENTAGE"
    threshold_green: Optional[float] = None
    threshold_amber: Optional[float] = None
    threshold_red: Optional[float] = None
    status: str = "GREEN"
    trend: str = "STABLE"
    previous_value: Optional[float] = None
    metadata: Optional[dict] = None


class KCISnapshot(BaseModel):
    kci_id: str
    name: str
    description: Optional[str] = None
    period_date: date
    numerator: Optional[float] = None
    denominator: Optional[float] = None
    value: float
    unit: str = "PERCENTAGE"
    threshold_green: Optional[float] = None
    threshold_amber: Optional[float] = None
    threshold_red: Optional[float] = None
    status: str = "GREEN"
    trend: str = "STABLE"
    previous_value: Optional[float] = None
    control_id: Optional[str] = None
    metadata: Optional[dict] = None


class KPISnapshot(BaseModel):
    kpi_id: str
    name: str
    description: Optional[str] = None
    period_date: date
    value: float
    unit: str = "COUNT"
    metadata: Optional[dict] = None


class RiskSummary(BaseModel):
    overall_risk_level: str
    total_exceptions: int
    critical_exceptions: int
    high_exceptions: int
    open_exceptions: int
    overdue_remediations: int
    kri_summary: list[KRISnapshot]
    kci_summary: list[KCISnapshot]
    risk_by_category: dict[str, int]


# ============================================================
# Audit Schemas
# ============================================================

class AuditEvent(BaseModel):
    id: int
    timestamp: datetime
    actor: str
    action: str
    object_type: str
    object_id: str
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    reason: Optional[str] = None


class AuditEventListResponse(BaseModel):
    events: list[AuditEvent]
    total: int
    page: int
    page_size: int


# ============================================================
# AI Schemas
# ============================================================

class AIAnalyzeRequest(BaseModel):
    query: str
    context_type: str = "general"
    fund_id: Optional[int] = None
    exception_id: Optional[int] = None
    control_id: Optional[str] = None


class AIAnalyzeResponse(BaseModel):
    response: str
    evidence_summary: Optional[str] = None
    validation_status: str = "PENDING"
    validation_issues: list[str] = []
    provider: Optional[str] = None
    disclaimer: str = (
        "AI-generated analysis based on structured evidence. "
        "This is not an authoritative risk assessment. "
        "All findings should be reviewed by a qualified analyst."
    )


# ============================================================
# Ingestion Schemas
# ============================================================

class IngestionRequest(BaseModel):
    quarter: str = Field(default="2025q3", pattern=r"^\d{4}q[1-4]$")
    sample: bool = False
    sample_size: int = 5000


class IngestionResponse(BaseModel):
    status: str
    quarter: str
    rows_processed: int
    rows_rejected: int
    duration_seconds: float
    message: str


# ============================================================
# Remediation Schemas
# ============================================================

class RemediationItem(BaseModel):
    id: int
    exception_id: int
    owner: Optional[str] = None
    action_description: str
    due_date: Optional[date] = None
    priority: str = "MEDIUM"
    status: str = "OPEN"
    validation_result: Optional[str] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime


class RemediationStats(BaseModel):
    total_open: int
    total_overdue: int
    total_due_soon: int
    mttr_days: Optional[float] = None
    repeat_issues: int
    by_owner: dict[str, int]
    by_priority: dict[str, int]
