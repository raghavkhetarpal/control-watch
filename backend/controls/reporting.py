"""Reporting Controls — RPT-001 and RPT-002.

Monitors filing timeliness and detects missing reporting periods.
"""
import time

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from .base import BaseControl, ControlResult
from .registry import register_control

logger = structlog.get_logger(__name__)


@register_control
class ReportingTimelinessControl(BaseControl):
    """RPT-001: Monitor filing timeliness relative to reporting period end."""

    control_id = "RPT-001"
    name = "Reporting Timeliness"
    description = "Calculate days between reporting period end and filing date. Flag late filings."
    risk_category = "REPORTING"
    data_requirements = ["submissions.filing_date", "submissions.period_of_report"]

    AMBER_DAYS = 60
    RED_DAYS = 90

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        rows = session.execute(text("""
            SELECT s.accession_number, s.filing_date, s.period_of_report,
                   f.id as fund_id, f.fund_name,
                   (s.filing_date - s.period_of_report) as days_to_file
            FROM submissions s
            JOIN funds f ON f.accession_number = s.accession_number
            WHERE s.period_of_report = :pd
              AND s.filing_date IS NOT NULL
              AND s.period_of_report IS NOT NULL
        """), {"pd": period_date}).mappings().all()

        scanned = len(rows)
        exceptions = []

        for r in rows:
            days = r["days_to_file"]
            if days is None:
                continue
            days_int = days.days if hasattr(days, 'days') else int(days)

            if days_int > self.AMBER_DAYS:
                severity = "HIGH" if days_int > self.RED_DAYS else "MEDIUM"
                exceptions.append({
                    "fund_id": r["fund_id"],
                    "severity": severity,
                    "exception_type": "ANALYTICAL_EXCEPTION",
                    "description": (
                        f"Late filing: {r['fund_name']} filed {days_int} days after "
                        f"period end ({r['period_of_report']} → {r['filing_date']})"
                    ),
                    "evidence": {
                        "accession_number": r["accession_number"],
                        "fund_name": r["fund_name"],
                        "period_of_report": str(r["period_of_report"]),
                        "filing_date": str(r["filing_date"]),
                        "days_to_file": days_int,
                        "threshold_amber": self.AMBER_DAYS,
                        "threshold_red": self.RED_DAYS,
                    },
                })

        duration_ms = int((time.time() - start_time) * 1000)
        passed = max(0, scanned - len(exceptions))
        pass_rate = round((passed / scanned * 100), 2) if scanned > 0 else 100.0

        return ControlResult(
            control_id=self.control_id, name=self.name, status="COMPLETED",
            records_scanned=scanned, exceptions_found=len(exceptions),
            pass_rate=pass_rate, duration_ms=duration_ms,
            testable_records=scanned, passed_records=passed, not_testable_records=0,
            data_requirements=self.data_requirements, coverage_ratio=1.0,
            evaluation_status="COMPLETED",
            exceptions=exceptions,
        )


@register_control
class ReportingGapsControl(BaseControl):
    """RPT-002: Detect missing reporting periods for fund series."""

    control_id = "RPT-002"
    name = "Reporting Gaps"
    description = "For each fund series, identify expected quarters and flag gaps."
    risk_category = "REPORTING"
    data_requirements = ["fund_series.series_id", "submissions.period_of_report"]

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        # Find series with filings and check for gaps
        rows = session.execute(text("""
            SELECT fs.series_id, fs.series_name,
                   COUNT(DISTINCT s.period_of_report) as period_count,
                   MIN(s.period_of_report) as first_period,
                   MAX(s.period_of_report) as last_period
            FROM fund_series fs
            JOIN funds f ON f.series_id = fs.series_id
            JOIN submissions s ON f.accession_number = s.accession_number
            GROUP BY fs.series_id, fs.series_name
            HAVING COUNT(DISTINCT s.period_of_report) >= 1
        """)).mappings().all()

        scanned = len(rows)
        exceptions = []

        # Gap detection: if a series has first period but no current period filing
        for r in rows:
            if r["last_period"] and r["last_period"] < period_date:
                exceptions.append({
                    "severity": "LOW",
                    "exception_type": "DATA_AVAILABILITY",
                    "description": (
                        f"Reporting gap: {r['series_name']} last filed for {r['last_period']}, "
                        f"no filing for current period {period_date}"
                    ),
                    "evidence": {
                        "series_id": r["series_id"],
                        "series_name": r["series_name"],
                        "first_period": str(r["first_period"]),
                        "last_period": str(r["last_period"]),
                        "current_period": str(period_date),
                        "total_periods_filed": r["period_count"],
                    },
                })

        duration_ms = int((time.time() - start_time) * 1000)
        passed = max(0, scanned - len(exceptions))
        pass_rate = round((passed / scanned * 100), 2) if scanned > 0 else 100.0

        return ControlResult(
            control_id=self.control_id, name=self.name, status="COMPLETED",
            records_scanned=scanned, exceptions_found=len(exceptions),
            pass_rate=pass_rate, duration_ms=duration_ms,
            testable_records=scanned, passed_records=passed, not_testable_records=0,
            data_requirements=self.data_requirements, coverage_ratio=1.0,
            evaluation_status="COMPLETED",
            exceptions=exceptions,
        )
