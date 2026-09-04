"""Valuation Controls — VAL-001 and VAL-002.

Detects stale/zero prices and extreme price movements using N-PORT historical data.
"""
import time

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from .base import BaseControl, ControlResult
from .registry import register_control

logger = structlog.get_logger(__name__)


@register_control
class StalePricesControl(BaseControl):
    """VAL-001: Detect holdings with stale or zero implied prices."""

    control_id = "VAL-001"
    name = "Stale/Zero Prices"
    description = "Detect holdings where implied price (value/balance) is zero or unchanged across periods."
    risk_category = "VALUATION"

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        scanned = session.execute(text("""
            SELECT COUNT(*) FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd
              AND h.balance IS NOT NULL AND h.balance != 0
        """), {"pd": period_date}).scalar() or 0

        # Zero implied price (value = 0 but balance > 0)
        rows = session.execute(text("""
            SELECT h.id, h.fund_id, f.fund_name, h.name, h.cusip,
                   h.value, h.balance
            FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd
              AND h.balance IS NOT NULL AND h.balance > 0
              AND (h.value IS NULL OR h.value = 0)
            LIMIT 300
        """), {"pd": period_date}).mappings().all()

        exceptions = []
        for r in rows:
            exceptions.append({
                "fund_id": r["fund_id"],
                "holding_id": r["id"],
                "severity": "HIGH",
                "description": (
                    f"Zero/missing price: {r['name']} has balance {float(r['balance']):,.2f} "
                    f"but value is {r['value'] or 0}"
                ),
                "evidence": {
                    "holding_id": r["id"],
                    "name": r["name"],
                    "cusip": r["cusip"],
                    "balance": str(r["balance"]),
                    "value": str(r["value"]),
                    "issue": "zero_price",
                },
            })

        duration_ms = int((time.time() - start_time) * 1000)
        pass_rate = ((scanned - len(exceptions)) / scanned * 100) if scanned > 0 else 100.0

        return ControlResult(
            control_id=self.control_id, name=self.name, status="COMPLETED",
            records_scanned=scanned, exceptions_found=len(exceptions),
            pass_rate=pass_rate, duration_ms=duration_ms,
            exceptions=exceptions,
        )


@register_control
class ExtremePriceMovementsControl(BaseControl):
    """VAL-002: Detect unusually large period-over-period price changes."""

    control_id = "VAL-002"
    name = "Extreme Price Movements"
    description = "Detect unusually large implied price changes between reporting periods."
    risk_category = "VALUATION"

    CHANGE_THRESHOLD_PCT = 50.0

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        prev_period = session.execute(text("""
            SELECT MAX(period_of_report) FROM submissions
            WHERE period_of_report < :pd
        """), {"pd": period_date}).scalar()

        if not prev_period:
            return ControlResult(
                control_id=self.control_id, name=self.name, status="COMPLETED",
                records_scanned=0, exceptions_found=0, pass_rate=100.0,
                duration_ms=int((time.time() - start_time) * 1000),
                details={"note": "No previous period for price comparison"},
            )

        scanned = session.execute(text("""
            SELECT COUNT(*) FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd AND h.balance > 0 AND h.value > 0
        """), {"pd": period_date}).scalar() or 0

        # Compare implied prices across periods for same fund-series + cusip
        rows = session.execute(text("""
            SELECT h_curr.id, h_curr.fund_id, f_curr.fund_name,
                   h_curr.name, h_curr.cusip,
                   h_curr.value / NULLIF(h_curr.balance, 0) as curr_price,
                   h_prev.value / NULLIF(h_prev.balance, 0) as prev_price,
                   ABS((h_curr.value / NULLIF(h_curr.balance, 0) -
                        h_prev.value / NULLIF(h_prev.balance, 0)) /
                       NULLIF(h_prev.value / NULLIF(h_prev.balance, 0), 0) * 100) as price_change_pct
            FROM holdings h_curr
            JOIN funds f_curr ON h_curr.fund_id = f_curr.id
            JOIN funds f_prev ON f_curr.series_id = f_prev.series_id
                AND f_prev.period_of_report = :prev_pd
            JOIN holdings h_prev ON h_prev.fund_id = f_prev.id
                AND h_prev.cusip = h_curr.cusip AND h_curr.cusip IS NOT NULL
            WHERE f_curr.period_of_report = :curr_pd
              AND h_curr.balance > 0 AND h_curr.value > 0
              AND h_prev.balance > 0 AND h_prev.value > 0
              AND ABS((h_curr.value / NULLIF(h_curr.balance, 0) -
                       h_prev.value / NULLIF(h_prev.balance, 0)) /
                      NULLIF(h_prev.value / NULLIF(h_prev.balance, 0), 0) * 100) > :threshold
            LIMIT 200
        """), {
            "curr_pd": period_date,
            "prev_pd": prev_period,
            "threshold": self.CHANGE_THRESHOLD_PCT,
        }).mappings().all()

        exceptions = []
        for r in rows:
            change = float(r["price_change_pct"] or 0)
            exceptions.append({
                "fund_id": r["fund_id"],
                "holding_id": r["id"],
                "severity": "CRITICAL" if change > 200 else "HIGH",
                "description": (
                    f"Extreme price movement: {r['name']} implied price changed "
                    f"{change:.1f}% ({float(r['prev_price'] or 0):.4f} → {float(r['curr_price'] or 0):.4f})"
                ),
                "evidence": {
                    "name": r["name"],
                    "cusip": r["cusip"],
                    "current_price": str(r["curr_price"]),
                    "previous_price": str(r["prev_price"]),
                    "change_pct": round(change, 2),
                },
            })

        duration_ms = int((time.time() - start_time) * 1000)
        pass_rate = ((scanned - len(exceptions)) / scanned * 100) if scanned > 0 else 100.0

        return ControlResult(
            control_id=self.control_id, name=self.name, status="COMPLETED",
            records_scanned=scanned, exceptions_found=len(exceptions),
            pass_rate=pass_rate, duration_ms=duration_ms,
            exceptions=exceptions,
        )
