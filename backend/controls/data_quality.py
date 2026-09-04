"""Data Quality Controls — DQ-001 through DQ-004.

Checks for missing fields, duplicates, invalid values, and classification consistency
in SEC N-PORT holdings data.

All thresholds are illustrative analytical thresholds for educational purposes.
"""
import time

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from .base import BaseControl, ControlResult
from .registry import register_control

logger = structlog.get_logger(__name__)


@register_control
class MissingRequiredFieldsControl(BaseControl):
    """DQ-001: Detect missing critical fields in holdings data."""

    control_id = "DQ-001"
    name = "Missing Required Fields"
    description = "Detect missing critical fields such as name, value, balance, percentage, and security identifiers."
    risk_category = "DATA_QUALITY"

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        # Count total holdings for the period (via fund linkage)
        scanned = session.execute(text("""
            SELECT COUNT(*) FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        if scanned == 0:
            # Try without fund join (holdings may not have fund_id set)
            scanned = session.execute(text("""
                SELECT COUNT(*) FROM holdings h
                JOIN submissions s ON h.accession_number = s.accession_number
                WHERE s.period_of_report = :pd
            """), {"pd": period_date}).scalar() or 0

        # Find holdings with missing required fields
        rows = session.execute(text("""
            SELECT h.id, h.fund_id, h.name, h.value, h.balance, h.pct_val,
                   h.cusip, h.isin, h.accession_number
            FROM holdings h
            JOIN submissions s ON h.accession_number = s.accession_number
            WHERE s.period_of_report = :pd
              AND (h.name IS NULL
                   OR h.value IS NULL
                   OR (h.cusip IS NULL AND h.isin IS NULL))
            LIMIT 1000
        """), {"pd": period_date}).mappings().all()

        exceptions = []
        for r in rows:
            missing = []
            if r["name"] is None:
                missing.append("name")
            if r["value"] is None:
                missing.append("value")
            if r["cusip"] is None and r["isin"] is None:
                missing.append("identifier(cusip/isin)")

            exceptions.append({
                "fund_id": r["fund_id"],
                "holding_id": r["id"],
                "severity": "HIGH" if "value" in missing else "MEDIUM",
                "description": f"Missing required fields: {', '.join(missing)}",
                "evidence": {
                    "holding_id": r["id"],
                    "accession_number": r["accession_number"],
                    "missing_fields": missing,
                    "name": r["name"],
                    "value": str(r["value"]) if r["value"] else None,
                },
            })

        duration_ms = int((time.time() - start_time) * 1000)
        pass_rate = ((scanned - len(exceptions)) / scanned * 100) if scanned > 0 else 100.0

        logger.info("dq001_completed", records=scanned, exceptions=len(exceptions), duration_ms=duration_ms)

        return ControlResult(
            control_id=self.control_id, name=self.name, status="COMPLETED",
            records_scanned=scanned, exceptions_found=len(exceptions),
            pass_rate=pass_rate, duration_ms=duration_ms,
            exceptions=exceptions,
        )


@register_control
class DuplicateHoldingsControl(BaseControl):
    """DQ-002: Detect duplicate holdings based on natural keys."""

    control_id = "DQ-002"
    name = "Duplicate Holdings"
    description = "Detect duplicate holdings based on accession_number + cusip/name composite key."
    risk_category = "DATA_QUALITY"

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        scanned = session.execute(text("""
            SELECT COUNT(*) FROM holdings h
            JOIN submissions s ON h.accession_number = s.accession_number
            WHERE s.period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        rows = session.execute(text("""
            SELECT h.accession_number, h.cusip, h.name, COUNT(*) as cnt,
                   MIN(h.fund_id) as fund_id
            FROM holdings h
            JOIN submissions s ON h.accession_number = s.accession_number
            WHERE s.period_of_report = :pd
              AND h.cusip IS NOT NULL
            GROUP BY h.accession_number, h.cusip, h.name
            HAVING COUNT(*) > 1
            LIMIT 500
        """), {"pd": period_date}).mappings().all()

        exceptions = []
        for r in rows:
            exceptions.append({
                "fund_id": r["fund_id"],
                "severity": "MEDIUM" if r["cnt"] == 2 else "HIGH",
                "description": f"Duplicate holding: {r['name'] or r['cusip']} appears {r['cnt']} times",
                "evidence": {
                    "accession_number": r["accession_number"],
                    "cusip": r["cusip"],
                    "name": r["name"],
                    "duplicate_count": r["cnt"],
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
class InvalidValuesControl(BaseControl):
    """DQ-003: Detect invalid or impossible values in holdings data."""

    control_id = "DQ-003"
    name = "Invalid Values"
    description = "Detect negative quantities, impossible percentages, and invalid numeric values."
    risk_category = "DATA_QUALITY"

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        scanned = session.execute(text("""
            SELECT COUNT(*) FROM holdings h
            JOIN submissions s ON h.accession_number = s.accession_number
            WHERE s.period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        # Negative balance where units indicate shares (NS)
        negative_balance = session.execute(text("""
            SELECT h.id, h.fund_id, h.name, h.balance, h.units, h.value, h.pct_val
            FROM holdings h
            JOIN submissions s ON h.accession_number = s.accession_number
            WHERE s.period_of_report = :pd
              AND h.balance < 0 AND h.units = 'NS'
            LIMIT 500
        """), {"pd": period_date}).mappings().all()

        # Impossible percentages
        impossible_pct = session.execute(text("""
            SELECT h.id, h.fund_id, h.name, h.pct_val
            FROM holdings h
            JOIN submissions s ON h.accession_number = s.accession_number
            WHERE s.period_of_report = :pd
              AND (h.pct_val > 100 OR h.pct_val < -100)
            LIMIT 500
        """), {"pd": period_date}).mappings().all()

        exceptions = []
        for r in negative_balance:
            exceptions.append({
                "fund_id": r["fund_id"],
                "holding_id": r["id"],
                "severity": "HIGH",
                "description": f"Negative share balance: {r['name']} has balance {r['balance']}",
                "evidence": {
                    "holding_id": r["id"],
                    "name": r["name"],
                    "balance": str(r["balance"]),
                    "units": r["units"],
                    "issue": "negative_balance",
                },
            })

        for r in impossible_pct:
            exceptions.append({
                "fund_id": r["fund_id"],
                "holding_id": r["id"],
                "severity": "HIGH",
                "description": f"Impossible percentage: {r['name']} has pct_val {r['pct_val']}",
                "evidence": {
                    "holding_id": r["id"],
                    "name": r["name"],
                    "pct_val": str(r["pct_val"]),
                    "issue": "impossible_percentage",
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
class ClassificationConsistencyControl(BaseControl):
    """DQ-004: Check consistency of security/asset classifications."""

    control_id = "DQ-004"
    name = "Classification Consistency"
    description = "Check that holdings have valid asset category and issuer category classifications."
    risk_category = "DATA_QUALITY"

    VALID_ASSET_CATS = {"EC", "EP", "DBT", "ABS", "STIV", "MF", "OTHER", "FND", "DE"}
    VALID_ISSUER_CATS = {"CORP", "USG", "USGA", "MUN", "FGN", "OTHER"}

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        scanned = session.execute(text("""
            SELECT COUNT(*) FROM holdings h
            JOIN submissions s ON h.accession_number = s.accession_number
            WHERE s.period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        # Missing classifications
        rows = session.execute(text("""
            SELECT h.id, h.fund_id, h.name, h.asset_cat, h.issuer_cat
            FROM holdings h
            JOIN submissions s ON h.accession_number = s.accession_number
            WHERE s.period_of_report = :pd
              AND (h.asset_cat IS NULL OR h.issuer_cat IS NULL)
            LIMIT 500
        """), {"pd": period_date}).mappings().all()

        exceptions = []
        for r in rows:
            missing = []
            if r["asset_cat"] is None:
                missing.append("asset_cat")
            if r["issuer_cat"] is None:
                missing.append("issuer_cat")

            exceptions.append({
                "fund_id": r["fund_id"],
                "holding_id": r["id"],
                "severity": "LOW",
                "description": f"Missing classification: {', '.join(missing)} for {r['name']}",
                "evidence": {
                    "holding_id": r["id"],
                    "name": r["name"],
                    "asset_cat": r["asset_cat"],
                    "issuer_cat": r["issuer_cat"],
                    "missing": missing,
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
