"""Reconciliation Controls — REC-001 and REC-002.

Compares holdings between reporting periods and validates portfolio completeness.
"""
import time

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from .base import BaseControl, ControlResult
from .registry import register_control

logger = structlog.get_logger(__name__)


@register_control
class PeriodReconciliationControl(BaseControl):
    """REC-001: Compare holdings between T and T-1 reporting periods."""

    control_id = "REC-001"
    name = "Period-over-Period Reconciliation"
    description = "Compare holdings between consecutive reporting periods. Flag new, disappeared, and significantly changed positions."
    risk_category = "RECONCILIATION"

    VALUE_CHANGE_THRESHOLD = 50.0  # percent

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        # Find previous period
        prev_period = session.execute(text("""
            SELECT MAX(period_of_report) FROM submissions
            WHERE period_of_report < :pd
        """), {"pd": period_date}).scalar()

        if not prev_period:
            logger.info("rec001_no_previous_period", period=str(period_date))
            return ControlResult(
                control_id=self.control_id, name=self.name, status="COMPLETED",
                records_scanned=0, exceptions_found=0, pass_rate=100.0,
                duration_ms=int((time.time() - start_time) * 1000),
                details={"note": "No previous period available for reconciliation"},
            )

        # Count current period holdings
        scanned = session.execute(text("""
            SELECT COUNT(*) FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        exceptions = []

        # Find funds present in both periods
        fund_pairs = session.execute(text("""
            SELECT DISTINCT f_curr.id as curr_fund_id, f_curr.fund_name,
                   f_curr.series_id, f_prev.id as prev_fund_id
            FROM funds f_curr
            JOIN funds f_prev ON f_curr.series_id = f_prev.series_id
            WHERE f_curr.period_of_report = :curr_pd
              AND f_prev.period_of_report = :prev_pd
            LIMIT 100
        """), {"curr_pd": period_date, "prev_pd": prev_period}).mappings().all()

        for fp in fund_pairs:
            # Large value changes
            changes = session.execute(text("""
                SELECT h_curr.name, h_curr.cusip,
                       h_curr.value as curr_value, h_prev.value as prev_value,
                       h_curr.fund_id,
                       CASE WHEN h_prev.value != 0
                            THEN ABS((h_curr.value - h_prev.value) / h_prev.value * 100)
                            ELSE 0 END as value_change_pct
                FROM holdings h_curr
                JOIN holdings h_prev ON h_curr.cusip = h_prev.cusip
                    AND h_curr.cusip IS NOT NULL
                WHERE h_curr.fund_id = :curr_fid AND h_prev.fund_id = :prev_fid
                  AND h_prev.value != 0
                  AND ABS((h_curr.value - h_prev.value) / h_prev.value * 100) > :threshold
                LIMIT 50
            """), {
                "curr_fid": fp["curr_fund_id"],
                "prev_fid": fp["prev_fund_id"],
                "threshold": self.VALUE_CHANGE_THRESHOLD,
            }).mappings().all()

            for c in changes:
                exceptions.append({
                    "fund_id": c["fund_id"],
                    "severity": "HIGH" if float(c["value_change_pct"]) > 100 else "MEDIUM",
                    "description": (
                        f"Reconciliation exception: {c['name']} value changed "
                        f"{float(c['value_change_pct']):.1f}% "
                        f"(${float(c['prev_value'] or 0):,.0f} → ${float(c['curr_value'] or 0):,.0f}) — "
                        f"requires investigation"
                    ),
                    "evidence": {
                        "fund_name": fp["fund_name"],
                        "security": c["name"],
                        "cusip": c["cusip"],
                        "previous_value": str(c["prev_value"]),
                        "current_value": str(c["curr_value"]),
                        "change_pct": round(float(c["value_change_pct"]), 2),
                        "previous_period": str(prev_period),
                        "current_period": str(period_date),
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
class PortfolioCompletenessControl(BaseControl):
    """REC-002: Verify that holdings values sum to approximately the fund's reported total assets."""

    control_id = "REC-002"
    name = "Portfolio Completeness"
    description = "Compare sum of holdings values vs fund total_assets. Flag significant discrepancies."
    risk_category = "RECONCILIATION"

    TOLERANCE_PCT = 5.0

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        rows = session.execute(text("""
            SELECT f.id as fund_id, f.fund_name, f.total_assets,
                   COALESCE(SUM(h.value), 0) as holdings_total,
                   COUNT(h.id) as holding_count
            FROM funds f
            LEFT JOIN holdings h ON h.fund_id = f.id
            WHERE f.period_of_report = :pd
              AND f.total_assets IS NOT NULL AND f.total_assets > 0
            GROUP BY f.id, f.fund_name, f.total_assets
        """), {"pd": period_date}).mappings().all()

        scanned = len(rows)
        exceptions = []

        for r in rows:
            total_assets = float(r["total_assets"])
            holdings_total = float(r["holdings_total"])
            if total_assets > 0:
                diff_pct = abs(holdings_total - total_assets) / total_assets * 100
                if diff_pct > self.TOLERANCE_PCT:
                    exceptions.append({
                        "fund_id": r["fund_id"],
                        "severity": "HIGH" if diff_pct > 20 else "MEDIUM",
                        "description": (
                            f"Portfolio completeness gap: {r['fund_name']} — "
                            f"Holdings total ${holdings_total:,.0f} vs "
                            f"Reported total ${total_assets:,.0f} "
                            f"(difference: {diff_pct:.1f}%)"
                        ),
                        "evidence": {
                            "fund_id": r["fund_id"],
                            "fund_name": r["fund_name"],
                            "reported_total_assets": str(total_assets),
                            "calculated_holdings_total": str(holdings_total),
                            "difference_pct": round(diff_pct, 2),
                            "holding_count": r["holding_count"],
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
