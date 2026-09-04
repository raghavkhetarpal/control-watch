"""Liquidity Control — LIQ-001.

Analytical liquidity-risk indicator based on asset classification.
This is NOT an official regulatory liquidity calculation.
"""
import time

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from .base import BaseControl, ControlResult
from .registry import register_control

logger = structlog.get_logger(__name__)


# Liquidity classification mapping (illustrative)
LIQUIDITY_MAP = {
    "EC": "HIGHLY_LIQUID",       # Equity - Common
    "EP": "HIGHLY_LIQUID",       # Equity - Preferred
    "STIV": "HIGHLY_LIQUID",     # Short-term investments
    "MF": "HIGHLY_LIQUID",       # Mutual funds
    "DBT": "MODERATELY_LIQUID",  # Debt (default; refined by issuer)
    "ABS": "LESS_LIQUID",        # Asset-backed securities
    "OTHER": "LESS_LIQUID",      # Other
    "DE": "LESS_LIQUID",         # Derivatives
    "FND": "MODERATELY_LIQUID",  # Fund shares
}

# Issuer-type refinement for debt
DEBT_LIQUIDITY = {
    "USG": "HIGHLY_LIQUID",    # US Government
    "USGA": "HIGHLY_LIQUID",   # US Government Agency
    "CORP": "MODERATELY_LIQUID",
    "MUN": "LESS_LIQUID",
    "FGN": "MODERATELY_LIQUID",
}


@register_control
class LiquidityProxyControl(BaseControl):
    """LIQ-001: Analytical liquidity-risk indicator based on asset classification.

    Note: This is an analytical proxy, NOT an official regulatory liquidity calculation.
    It classifies holdings into liquidity buckets based on asset type and issuer category.
    """

    control_id = "LIQ-001"
    name = "Liquidity Proxy"
    description = "Analytical liquidity-risk indicator based on asset classification. NOT a regulatory calculation."
    risk_category = "LIQUIDITY"

    ILLIQUID_AMBER_PCT = 15.0
    ILLIQUID_RED_PCT = 25.0
    data_requirements = ["holdings.asset_cat", "holdings.issuer_cat", "holdings.pct_val"]

    def execute(self, session: Session, period_date) -> ControlResult:
        start_time = time.time()

        total_funds = session.execute(text("""
            SELECT COUNT(*) FROM funds WHERE period_of_report = :pd
        """), {"pd": period_date}).scalar() or 0

        # Get holdings with classifications
        rows = session.execute(text("""
            SELECT h.fund_id, f.fund_name, h.asset_cat, h.issuer_cat,
                   h.pct_val, h.value
            FROM holdings h
            JOIN funds f ON h.fund_id = f.id
            WHERE f.period_of_report = :pd
              AND h.pct_val IS NOT NULL
        """), {"pd": period_date}).mappings().all()

        # Aggregate by fund
        fund_liquidity: dict = {}
        for r in rows:
            fid = r["fund_id"]
            if fid not in fund_liquidity:
                fund_liquidity[fid] = {
                    "fund_name": r["fund_name"],
                    "HIGHLY_LIQUID": 0.0,
                    "MODERATELY_LIQUID": 0.0,
                    "LESS_LIQUID": 0.0,
                    "ILLIQUID": 0.0,
                }

            asset_cat = r["asset_cat"] or "OTHER"
            issuer_cat = r["issuer_cat"]
            pct = float(r["pct_val"] or 0)

            # Determine liquidity bucket
            if asset_cat == "DBT" and issuer_cat:
                bucket = DEBT_LIQUIDITY.get(issuer_cat, "MODERATELY_LIQUID")
            else:
                bucket = LIQUIDITY_MAP.get(asset_cat, "ILLIQUID")

            fund_liquidity[fid][bucket] += pct

        testable = len(fund_liquidity)
        records_scanned = total_funds if total_funds > 0 else testable
        not_testable = max(0, records_scanned - testable)
        coverage_ratio = round(testable / records_scanned, 4) if records_scanned > 0 else 1.0

        exceptions = []

        for fid, data in fund_liquidity.items():
            illiquid_pct = data["ILLIQUID"] + data["LESS_LIQUID"]
            if illiquid_pct > self.ILLIQUID_AMBER_PCT:
                severity = "HIGH" if illiquid_pct > self.ILLIQUID_RED_PCT else "MEDIUM"
                exceptions.append({
                    "fund_id": fid,
                    "severity": severity,
                    "exception_type": "ANALYTICAL_EXCEPTION",
                    "description": (
                        f"Analytical liquidity-risk indicator: {data['fund_name']} has "
                        f"{illiquid_pct:.1f}% in less-liquid/illiquid assets "
                        f"(Illustrative threshold: Amber>{self.ILLIQUID_AMBER_PCT}%, Red>{self.ILLIQUID_RED_PCT}%)"
                    ),
                    "evidence": {
                        "fund_id": fid,
                        "fund_name": data["fund_name"],
                        "highly_liquid_pct": round(data["HIGHLY_LIQUID"], 2),
                        "moderately_liquid_pct": round(data["MODERATELY_LIQUID"], 2),
                        "less_liquid_pct": round(data["LESS_LIQUID"], 2),
                        "illiquid_pct": round(data["ILLIQUID"], 2),
                        "total_illiquid_pct": round(illiquid_pct, 2),
                        "note": "Analytical liquidity-risk indicator (NOT a regulatory calculation)",
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
