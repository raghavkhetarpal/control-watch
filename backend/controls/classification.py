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
    data_requirements = [
        "holdings.asset_cat (T)", "holdings.issuer_cat (T)",
        "holdings.asset_cat (T-1)", "holdings.issuer_cat (T-1)"
    ]

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        scanned = session.execute(text("""
            SELECT COUNT(*) FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd AND h.cusip IS NOT NULL
        """), {"pd": period_date}).scalar() or 0

        prev_period = session.execute(text("""
            SELECT MAX(period_of_report) FROM submissions
            WHERE period_of_report < :pd
        """), {"pd": period_date}).scalar()

        if not prev_period:
            duration_ms = int((time.time() - start_time) * 1000)
            return ControlResult(
                control_id=self.control_id, name=self.name, status="COMPLETED",
                records_scanned=scanned, exceptions_found=0, pass_rate=100.0,
                duration_ms=duration_ms,
                testable_records=0, passed_records=0, not_testable_records=scanned,
                data_requirements=self.data_requirements, coverage_ratio=0.0,
                evaluation_status="NOT_TESTABLE",
                details={"note": "No previous period for classification comparison"},
            )

        # Count common positions
        testable = session.execute(text("""
            SELECT COUNT(*)
            FROM holdings h_curr
            JOIN funds f_curr ON h_curr.fund_id = f_curr.id
            JOIN funds f_prev ON f_curr.series_id = f_prev.series_id
                AND f_prev.period_of_report = :prev_pd
            JOIN holdings h_prev ON h_prev.fund_id = f_prev.id
                AND h_prev.cusip = h_curr.cusip AND h_curr.cusip IS NOT NULL
            WHERE f_curr.period_of_report = :curr_pd
        """), {"curr_pd": period_date, "prev_pd": prev_period}).scalar() or 0

        not_testable = max(0, scanned - testable)
        coverage_ratio = round(testable / scanned, 4) if scanned > 0 else 0.0

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
                "exception_type": "ANALYTICAL_EXCEPTION",
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
        passed = max(0, testable - len(exceptions))
        pass_rate = round((passed / testable * 100), 2) if testable > 0 else 100.0
        eval_status = "COMPLETED" if coverage_ratio >= 0.8 else ("PARTIAL" if testable > 0 else "NOT_TESTABLE")

        return ControlResult(
            control_id=self.control_id, name=self.name, status="COMPLETED",
            records_scanned=scanned, exceptions_found=len(exceptions),
            pass_rate=pass_rate, duration_ms=duration_ms,
            testable_records=testable, passed_records=passed, not_testable_records=not_testable,
            data_requirements=self.data_requirements, coverage_ratio=coverage_ratio,
            evaluation_status=eval_status,
            exceptions=exceptions,
        )
