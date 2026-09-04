"""Holdings-related API routes."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.models import HoldingSummary, HoldingListResponse

router = APIRouter()


@router.get("", response_model=HoldingListResponse)
def list_holdings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    fund_id: Optional[int] = None,
    asset_cat: Optional[str] = None,
    country: Optional[str] = None,
    search: Optional[str] = None,
    min_value: Optional[float] = None,
    db: Session = Depends(get_db),
):
    """List holdings with pagination and filtering."""
    offset = (page - 1) * page_size
    conditions = []
    params: dict = {"limit": page_size, "offset": offset}

    if fund_id:
        conditions.append("h.fund_id = :fund_id")
        params["fund_id"] = fund_id
    if asset_cat:
        conditions.append("h.asset_cat = :asset_cat")
        params["asset_cat"] = asset_cat
    if country:
        conditions.append("h.investment_country = :country")
        params["country"] = country
    if search:
        conditions.append("(h.name ILIKE :search OR h.cusip ILIKE :search2 OR h.isin ILIKE :search3)")
        params["search"] = f"%{search}%"
        params["search2"] = f"%{search}%"
        params["search3"] = f"%{search}%"
    if min_value is not None:
        conditions.append("h.value >= :min_value")
        params["min_value"] = min_value

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    count_query = text(f"SELECT COUNT(*) FROM holdings h {where_clause}")
    total = db.execute(count_query, params).scalar() or 0

    query = text(f"""
        SELECT h.id, h.accession_number, h.holding_id, h.fund_id,
               h.name, h.cusip, h.isin, h.balance, h.units, h.value,
               h.pct_val, h.asset_cat, h.issuer_cat, h.investment_country
        FROM holdings h
        {where_clause}
        ORDER BY h.value DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(query, params).mappings().all()

    holdings = [HoldingSummary(**dict(row)) for row in rows]
    return HoldingListResponse(holdings=holdings, total=total, page=page, page_size=page_size)
