"""Metrics API routes (KRI, KCI, KPI, Risk Summary)."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.models import KRISnapshot, KCISnapshot, KPISnapshot, RiskSummary

router = APIRouter()


@router.get("/kris", response_model=list[KRISnapshot])
def get_kris(
    period: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """Get all KRI snapshots for a period (defaults to latest)."""
    if period:
        query = text("""
            SELECT kri_id, name, description, period_date, numerator, denominator,
                   value, unit, threshold_green, threshold_amber, threshold_red,
                   status, trend, previous_value, metadata
            FROM kri_snapshots
            WHERE period_date = :period
            ORDER BY kri_id
        """)
        rows = db.execute(query, {"period": period}).mappings().all()
    else:
        query = text("""
            SELECT DISTINCT ON (kri_id) kri_id, name, description, period_date,
                   numerator, denominator, value, unit,
                   threshold_green, threshold_amber, threshold_red,
                   status, trend, previous_value, metadata
            FROM kri_snapshots
            ORDER BY kri_id, period_date DESC
        """)
        rows = db.execute(query).mappings().all()

    return [KRISnapshot(**dict(row)) for row in rows]


@router.get("/kcis", response_model=list[KCISnapshot])
def get_kcis(
    period: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """Get all KCI snapshots for a period (defaults to latest)."""
    if period:
        query = text("""
            SELECT kci_id, name, description, period_date, numerator, denominator,
                   value, unit, threshold_green, threshold_amber, threshold_red,
                   status, trend, previous_value, control_id, metadata
            FROM kci_snapshots
            WHERE period_date = :period
            ORDER BY kci_id
        """)
        rows = db.execute(query, {"period": period}).mappings().all()
    else:
        query = text("""
            SELECT DISTINCT ON (kci_id) kci_id, name, description, period_date,
                   numerator, denominator, value, unit,
                   threshold_green, threshold_amber, threshold_red,
                   status, trend, previous_value, control_id, metadata
            FROM kci_snapshots
            ORDER BY kci_id, period_date DESC
        """)
        rows = db.execute(query).mappings().all()

    return [KCISnapshot(**dict(row)) for row in rows]


@router.get("/kpis", response_model=list[KPISnapshot])
def get_kpis(
    period: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """Get all KPI snapshots for a period (defaults to latest)."""
    if period:
        query = text("""
            SELECT kpi_id, name, description, period_date, value, unit, metadata
            FROM kpi_snapshots
            WHERE period_date = :period
            ORDER BY kpi_id
        """)
        rows = db.execute(query, {"period": period}).mappings().all()
    else:
        query = text("""
            SELECT DISTINCT ON (kpi_id) kpi_id, name, description, period_date,
                   value, unit, metadata
            FROM kpi_snapshots
            ORDER BY kpi_id, period_date DESC
        """)
        rows = db.execute(query).mappings().all()

    return [KPISnapshot(**dict(row)) for row in rows]


@router.get("/risk-summary", response_model=RiskSummary)
def get_risk_summary(
    period: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """Get overall risk summary with KRI/KCI data."""
    # Exception counts
    exc_query = text("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE severity = 'CRITICAL') as critical,
            COUNT(*) FILTER (WHERE severity = 'HIGH') as high,
            COUNT(*) FILTER (WHERE status NOT IN ('CLOSED', 'ACCEPTED')) as open_count
        FROM control_exceptions
    """)
    exc_stats = db.execute(exc_query).mappings().first()

    # Overdue remediations
    overdue_query = text("""
        SELECT COUNT(*) FROM remediation_items
        WHERE status IN ('OPEN', 'IN_PROGRESS') AND due_date < CURRENT_DATE
    """)
    overdue_count = db.execute(overdue_query).scalar() or 0

    # Risk by category
    cat_query = text("""
        SELECT risk_category, COUNT(*) as cnt
        FROM control_exceptions
        WHERE status NOT IN ('CLOSED', 'ACCEPTED')
        AND risk_category IS NOT NULL
        GROUP BY risk_category
    """)
    cat_rows = db.execute(cat_query).mappings().all()
    risk_by_category = {row["risk_category"]: row["cnt"] for row in cat_rows}

    # Get latest KRIs
    kri_query = text("""
        SELECT DISTINCT ON (kri_id) kri_id, name, description, period_date,
               numerator, denominator, value, unit,
               threshold_green, threshold_amber, threshold_red,
               status, trend, previous_value, metadata
        FROM kri_snapshots
        ORDER BY kri_id, period_date DESC
    """)
    kri_rows = db.execute(kri_query).mappings().all()
    kri_summary = [KRISnapshot(**dict(row)) for row in kri_rows]

    # Get latest KCIs
    kci_query = text("""
        SELECT DISTINCT ON (kci_id) kci_id, name, description, period_date,
               numerator, denominator, value, unit,
               threshold_green, threshold_amber, threshold_red,
               status, trend, previous_value, control_id, metadata
        FROM kci_snapshots
        ORDER BY kci_id, period_date DESC
    """)
    kci_rows = db.execute(kci_query).mappings().all()
    kci_summary = [KCISnapshot(**dict(row)) for row in kci_rows]

    # Determine overall risk level
    critical = exc_stats["critical"] if exc_stats else 0
    high = exc_stats["high"] if exc_stats else 0
    red_kris = sum(1 for k in kri_summary if k.status == "RED")

    if critical > 0 or red_kris >= 2:
        overall = "CRITICAL"
    elif high > 2 or red_kris >= 1:
        overall = "HIGH"
    elif high > 0 or any(k.status == "AMBER" for k in kri_summary):
        overall = "MEDIUM"
    else:
        overall = "LOW"

    return RiskSummary(
        overall_risk_level=overall,
        total_exceptions=exc_stats["total"] if exc_stats else 0,
        critical_exceptions=critical,
        high_exceptions=high,
        open_exceptions=exc_stats["open_count"] if exc_stats else 0,
        overdue_remediations=overdue_count,
        kri_summary=kri_summary,
        kci_summary=kci_summary,
        risk_by_category=risk_by_category,
    )
