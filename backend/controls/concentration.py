"""Concentration Risk Controls — CONC-001 through CONC-004.

Calculates position, issuer, asset class, and geographic concentration per fund.
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
class TopHoldingsConcentrationControl(BaseControl):
    """CONC-001: Calculate top-1, top-5, top-10 holding concentration per fund."""

    control_id = "CONC-001"
    name = "Position Concentration"
    description = "Calculate top position concentration per fund using illustrative analytical thresholds."
    risk_category = "CONCENTRATION"

    # Illustrative analytical thresholds
    GREEN_PCT = 35.0
    AMBER_PCT = 45.0
    data_requirements = ["holdings.pct_val", "funds.period_of_report"]

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        total_funds = session.execute(text("""
            SELECT COUNT(*) FROM funds WHERE period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        scanned_holdings_funds = session.execute(text("""
            SELECT COUNT(DISTINCT h.fund_id) FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        testable = scanned_holdings_funds
        records_scanned = total_funds if total_funds > 0 else testable
        not_testable = max(0, records_scanned - testable)
        coverage_ratio = round(testable / records_scanned, 4) if records_scanned > 0 else 1.0

        # Get fund-level top holdings concentration
        rows = session.execute(text("""
            WITH ranked_holdings AS (
                SELECT h.fund_id, f.fund_name, h.name as holding_name,
                       h.pct_val,
                       ROW_NUMBER() OVER (PARTITION BY h.fund_id ORDER BY h.pct_val DESC NULLS LAST) as rn,
                       COUNT(*) OVER (PARTITION BY h.fund_id) as total_holdings
                FROM holdings h
                JOIN funds f ON h.fund_id = f.id
                WHERE f.period_of_report = :pd
                  AND h.pct_val IS NOT NULL
                  AND h.pct_val > 0
            ),
            fund_concentration AS (
                SELECT fund_id, fund_name,
                       MAX(CASE WHEN rn = 1 THEN pct_val END) as top1_pct,
                       SUM(CASE WHEN rn <= 5 THEN pct_val ELSE 0 END) as top5_pct,
                       SUM(CASE WHEN rn <= 10 THEN pct_val ELSE 0 END) as top10_pct,
                       MAX(total_holdings) as total_holdings
                FROM ranked_holdings
                GROUP BY fund_id, fund_name
            )
            SELECT * FROM fund_concentration
            WHERE top10_pct > :green_threshold
            ORDER BY top10_pct DESC
            LIMIT 200
        """), {"pd": period_date, "green_threshold": self.GREEN_PCT}).mappings().all()

        exceptions = []
        for r in rows:
            top10 = float(r["top10_pct"] or 0)
            if top10 > self.AMBER_PCT:
                severity = "HIGH"
            elif top10 > self.GREEN_PCT:
                severity = "MEDIUM"
            else:
                continue

            exceptions.append({
                "fund_id": r["fund_id"],
                "severity": severity,
                "exception_type": "ANALYTICAL_EXCEPTION",
                "description": (
                    f"Position concentration for {r['fund_name']}: "
                    f"Top-1={r['top1_pct']:.1f}%, Top-5={r['top5_pct']:.1f}%, Top-10={top10:.1f}% "
                    f"(Illustrative threshold: Amber>{self.GREEN_PCT}%, Red>{self.AMBER_PCT}%)"
                ),
                "evidence": {
                    "fund_id": r["fund_id"],
                    "fund_name": r["fund_name"],
                    "top1_pct": round(float(r["top1_pct"] or 0), 2),
                    "top5_pct": round(float(r["top5_pct"] or 0), 2),
                    "top10_pct": round(top10, 2),
                    "total_holdings": r["total_holdings"],
                    "threshold_note": "Illustrative analytical thresholds",
                },
            })

        duration_ms = int((time.time() - start_time) * 1000)
        passed = max(0, testable - len(exceptions))
        pass_rate = round((passed / testable * 100), 2) if testable > 0 else 100.0

        return ControlResult(
            control_id=self.control_id, name=self.name, status="COMPLETED",
            records_scanned=records_scanned, exceptions_found=len(exceptions),
            pass_rate=pass_rate, duration_ms=duration_ms,
            testable_records=testable, passed_records=passed, not_testable_records=not_testable,
            data_requirements=self.data_requirements, coverage_ratio=coverage_ratio,
            evaluation_status="COMPLETED" if coverage_ratio >= 0.95 else "PARTIAL",
            exceptions=exceptions,
        )


@register_control
class IssuerConcentrationControl(BaseControl):
    """CONC-002: Calculate issuer-level concentration per fund."""

    control_id = "CONC-002"
    name = "Issuer Concentration"
    description = "Calculate issuer-level exposure using illustrative analytical thresholds."
    risk_category = "CONCENTRATION"
    data_requirements = ["holdings.pct_val", "holdings.lei", "holdings.name"]

    THRESHOLD_PCT = 25.0

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        total_funds = session.execute(text("""
            SELECT COUNT(*) FROM funds WHERE period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        scanned_holdings_funds = session.execute(text("""
            SELECT COUNT(DISTINCT h.fund_id) FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        testable = scanned_holdings_funds
        records_scanned = total_funds if total_funds > 0 else testable
        not_testable = max(0, records_scanned - testable)
        coverage_ratio = round(testable / records_scanned, 4) if records_scanned > 0 else 1.0

        # Group by fund + issuer (using LEI or first words of name as proxy)
        rows = session.execute(text("""
            SELECT h.fund_id, f.fund_name,
                   COALESCE(h.lei, SPLIT_PART(h.name, ' ', 1)) as issuer_key,
                   SUM(h.pct_val) as issuer_pct,
                   COUNT(*) as position_count
            FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd
              AND h.pct_val IS NOT NULL
            GROUP BY h.fund_id, f.fund_name, COALESCE(h.lei, SPLIT_PART(h.name, ' ', 1))
            HAVING SUM(h.pct_val) > :threshold
            ORDER BY issuer_pct DESC
            LIMIT 200
        """), {"pd": period_date, "threshold": self.THRESHOLD_PCT}).mappings().all()

        exceptions = []
        for r in rows:
            exceptions.append({
                "fund_id": r["fund_id"],
                "severity": "HIGH" if float(r["issuer_pct"]) > 35 else "MEDIUM",
                "exception_type": "ANALYTICAL_EXCEPTION",
                "description": (
                    f"Issuer concentration: {r['issuer_key']} = {float(r['issuer_pct']):.1f}% "
                    f"in {r['fund_name']} ({r['position_count']} positions)"
                ),
                "evidence": {
                    "fund_id": r["fund_id"],
                    "issuer": r["issuer_key"],
                    "concentration_pct": round(float(r["issuer_pct"]), 2),
                    "positions": r["position_count"],
                    "threshold_note": "Illustrative analytical thresholds",
                },
            })

        duration_ms = int((time.time() - start_time) * 1000)
        passed = max(0, testable - len(exceptions))
        pass_rate = round((passed / testable * 100), 2) if testable > 0 else 100.0

        return ControlResult(
            control_id=self.control_id, name=self.name, status="COMPLETED",
            records_scanned=records_scanned, exceptions_found=len(exceptions),
            pass_rate=pass_rate, duration_ms=duration_ms,
            testable_records=testable, passed_records=passed, not_testable_records=not_testable,
            data_requirements=self.data_requirements, coverage_ratio=coverage_ratio,
            evaluation_status="COMPLETED" if coverage_ratio >= 0.95 else "PARTIAL",
            exceptions=exceptions,
        )


@register_control
class AssetClassConcentrationControl(BaseControl):
    """CONC-003: Calculate asset class concentration per fund."""

    control_id = "CONC-003"
    name = "Asset Class Concentration"
    description = "Calculate asset class concentration using illustrative analytical thresholds."
    risk_category = "CONCENTRATION"
    data_requirements = ["holdings.pct_val", "holdings.asset_cat"]

    THRESHOLD_PCT = 80.0

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        total_funds = session.execute(text("""
            SELECT COUNT(*) FROM funds WHERE period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        scanned_holdings_funds = session.execute(text("""
            SELECT COUNT(DISTINCT h.fund_id) FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        testable = scanned_holdings_funds
        records_scanned = total_funds if total_funds > 0 else testable
        not_testable = max(0, records_scanned - testable)
        coverage_ratio = round(testable / records_scanned, 4) if records_scanned > 0 else 1.0

        rows = session.execute(text("""
            SELECT h.fund_id, f.fund_name, h.asset_cat,
                   SUM(h.pct_val) as cat_pct
            FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd
              AND h.pct_val IS NOT NULL AND h.asset_cat IS NOT NULL
            GROUP BY h.fund_id, f.fund_name, h.asset_cat
            HAVING SUM(h.pct_val) > :threshold
            ORDER BY cat_pct DESC
            LIMIT 200
        """), {"pd": period_date, "threshold": self.THRESHOLD_PCT}).mappings().all()

        exceptions = []
        for r in rows:
            exceptions.append({
                "fund_id": r["fund_id"],
                "severity": "MEDIUM",
                "exception_type": "ANALYTICAL_EXCEPTION",
                "description": (
                    f"Asset class concentration: {r['asset_cat']} = {float(r['cat_pct']):.1f}% "
                    f"in {r['fund_name']}"
                ),
                "evidence": {
                    "fund_id": r["fund_id"],
                    "asset_cat": r["asset_cat"],
                    "concentration_pct": round(float(r["cat_pct"]), 2),
                    "threshold_note": "Illustrative analytical thresholds",
                },
            })

        duration_ms = int((time.time() - start_time) * 1000)
        passed = max(0, testable - len(exceptions))
        pass_rate = round((passed / testable * 100), 2) if testable > 0 else 100.0

        return ControlResult(
            control_id=self.control_id, name=self.name, status="COMPLETED",
            records_scanned=records_scanned, exceptions_found=len(exceptions),
            pass_rate=pass_rate, duration_ms=duration_ms,
            testable_records=testable, passed_records=passed, not_testable_records=not_testable,
            data_requirements=self.data_requirements, coverage_ratio=coverage_ratio,
            evaluation_status="COMPLETED" if coverage_ratio >= 0.95 else "PARTIAL",
            exceptions=exceptions,
        )


@register_control
class GeographicConcentrationControl(BaseControl):
    """CONC-004: Calculate geographic concentration per fund."""

    control_id = "CONC-004"
    name = "Geographic Concentration"
    description = "Calculate geographic concentration using illustrative analytical thresholds."
    risk_category = "CONCENTRATION"
    data_requirements = ["holdings.pct_val", "holdings.investment_country"]

    THRESHOLD_PCT = 85.0

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        total_funds = session.execute(text("""
            SELECT COUNT(*) FROM funds WHERE period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        scanned_holdings_funds = session.execute(text("""
            SELECT COUNT(DISTINCT h.fund_id) FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        testable = scanned_holdings_funds
        records_scanned = total_funds if total_funds > 0 else testable
        not_testable = max(0, records_scanned - testable)
        coverage_ratio = round(testable / records_scanned, 4) if records_scanned > 0 else 1.0

        rows = session.execute(text("""
            SELECT h.fund_id, f.fund_name, h.investment_country,
                   SUM(h.pct_val) as country_pct
            FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd
              AND h.pct_val IS NOT NULL AND h.investment_country IS NOT NULL
            GROUP BY h.fund_id, f.fund_name, h.investment_country
            HAVING SUM(h.pct_val) > :threshold
            ORDER BY country_pct DESC
            LIMIT 200
        """), {"pd": period_date, "threshold": self.THRESHOLD_PCT}).mappings().all()

        exceptions = []
        for r in rows:
            exceptions.append({
                "fund_id": r["fund_id"],
                "severity": "LOW",
                "exception_type": "ANALYTICAL_EXCEPTION",
                "description": (
                    f"Geographic concentration: {r['investment_country']} = {float(r['country_pct']):.1f}% "
                    f"in {r['fund_name']}"
                ),
                "evidence": {
                    "fund_id": r["fund_id"],
                    "country": r["investment_country"],
                    "concentration_pct": round(float(r["country_pct"]), 2),
                    "threshold_note": "Illustrative analytical thresholds",
                },
            })

        duration_ms = int((time.time() - start_time) * 1000)
        passed = max(0, testable - len(exceptions))
        pass_rate = round((passed / testable * 100), 2) if testable > 0 else 100.0

        return ControlResult(
            control_id=self.control_id, name=self.name, status="COMPLETED",
            records_scanned=records_scanned, exceptions_found=len(exceptions),
            pass_rate=pass_rate, duration_ms=duration_ms,
            testable_records=testable, passed_records=passed, not_testable_records=not_testable,
            data_requirements=self.data_requirements, coverage_ratio=coverage_ratio,
            evaluation_status="COMPLETED" if coverage_ratio >= 0.95 else "PARTIAL",
            exceptions=exceptions,
        )
