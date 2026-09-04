"""Fund-related API routes."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.models import FundSummary, FundDetail, FundListResponse

router = APIRouter()


@router.get("", response_model=FundListResponse)
def list_funds(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    period: Optional[date] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all funds with pagination and filtering."""
    offset = (page - 1) * page_size
    conditions = []
    params: dict = {"limit": page_size, "offset": offset}

    if period:
        conditions.append("f.period_of_report = :period")
        params["period"] = period
    if search:
        conditions.append("(f.fund_name ILIKE :search OR f.cik ILIKE :search2)")
        params["search"] = f"%{search}%"
        params["search2"] = f"%{search}%"

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    count_query = text(f"SELECT COUNT(*) FROM funds f {where_clause}")
    total = db.execute(count_query, params).scalar() or 0

    query = text(f"""
        SELECT f.id, f.accession_number, f.series_id, f.cik, f.fund_name,
               f.total_assets, f.net_assets, f.period_of_report, f.filing_date
        FROM funds f
        {where_clause}
        ORDER BY f.fund_name ASC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(query, params).mappings().all()

    funds = [FundSummary(**dict(row)) for row in rows]
    return FundListResponse(funds=funds, total=total, page=page, page_size=page_size)


@router.get("/{fund_id}", response_model=FundDetail)
def get_fund(fund_id: int, db: Session = Depends(get_db)):
    """Get detailed fund information."""
    query = text("""
        SELECT f.id, f.accession_number, f.series_id, f.cik, f.fund_name,
               f.total_assets, f.net_assets, f.total_liabilities,
               f.period_of_report, f.filing_date,
               r.registrant_name,
               (SELECT COUNT(*) FROM holdings h WHERE h.fund_id = f.id) as holding_count,
               (SELECT COUNT(*) FROM control_exceptions ce WHERE ce.fund_id = f.id AND ce.status != 'CLOSED') as exception_count
        FROM funds f
        LEFT JOIN registrants r ON f.cik = r.cik
        WHERE f.id = :fund_id
    """)
    row = db.execute(query, {"fund_id": fund_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Fund not found")
    return FundDetail(**dict(row))
