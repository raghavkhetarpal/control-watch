"""Classification Control — CLS-001.

Detects period-over-period classification reclassifications.
"""
import time

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from .base import BaseControl, ControlResult
from .registry import register_control

logger = structlog.get_logger(__name__)


@register_control
class ClassificationChangesControl(BaseControl):
    """CLS-001: Detect securities reclassified between reporting periods."""

    control_id = "CLS-001"
    name = "Classification Changes"
    description = "Detect period-over-period reclassifications of security asset_cat or issuer_cat."
    risk_category = "DATA_QUALITY"

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
                details={"note": "No previous period for classification comparison"},
            )

        # Find holdings in both periods with changed classifications
        rows = session.execute(text("""
            SELECT h_curr.id, h_curr.fund_id, f_curr.fund_name,
                   h_curr.name, h_curr.cusip,
                   h_curr.asset_cat as curr_asset_cat,
                   h_prev.asset_cat as prev_asset_cat,
                   h_curr.issuer_cat as curr_issuer_cat,
                   h_prev.issuer_cat as prev_issuer_cat
            FROM holdings h_curr
            JOIN funds f_curr ON h_curr.fund_id = f_curr.id
            JOIN funds f_prev ON f_curr.series_id = f_prev.series_id
                AND f_prev.period_of_report = :prev_pd
            JOIN holdings h_prev ON h_prev.fund_id = f_prev.id
                AND h_prev.cusip = h_curr.cusip AND h_curr.cusip IS NOT NULL
            WHERE f_curr.period_of_report = :curr_pd
              AND (
                  (h_curr.asset_cat IS DISTINCT FROM h_prev.asset_cat
                   AND h_curr.asset_cat IS NOT NULL AND h_prev.asset_cat IS NOT NULL)
                  OR
                  (h_curr.issuer_cat IS DISTINCT FROM h_prev.issuer_cat
                   AND h_curr.issuer_cat IS NOT NULL AND h_prev.issuer_cat IS NOT NULL)
              )
            LIMIT 200
        """), {"curr_pd": period_date, "prev_pd": prev_period}).mappings().all()

        scanned = session.execute(text("""
            SELECT COUNT(*) FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd AND h.cusip IS NOT NULL
        """), {"pd": period_date}).scalar() or 0

        exceptions = []
        for r in rows:
            changes = []
            if r["curr_asset_cat"] != r["prev_asset_cat"]:
                changes.append(f"asset_cat: {r['prev_asset_cat']}→{r['curr_asset_cat']}")
            if r["curr_issuer_cat"] != r["prev_issuer_cat"]:
                changes.append(f"issuer_cat: {r['prev_issuer_cat']}→{r['curr_issuer_cat']}")

            exceptions.append({
                "fund_id": r["fund_id"],
                "holding_id": r["id"],
                "severity": "LOW",
                "description": (
                    f"Classification change: {r['name']} ({r['cusip']}) — "
                    f"{', '.join(changes)} — requires review"
                ),
                "evidence": {
                    "name": r["name"],
                    "cusip": r["cusip"],
                    "current_asset_cat": r["curr_asset_cat"],
                    "previous_asset_cat": r["prev_asset_cat"],
                    "current_issuer_cat": r["curr_issuer_cat"],
                    "previous_issuer_cat": r["prev_issuer_cat"],
                    "previous_period": str(prev_period),
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
