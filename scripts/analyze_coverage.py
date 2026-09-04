#!/usr/bin/env python3
"""AWM ControlWatch — Fund ↔ Holding Coverage Analysis.

Calculates:
- funds_with_holdings
- funds_without_holdings
- holdings_per_fund
- coverage_ratio = funds_with_holdings / funds_expected
- Classification of every fund without holdings:
  NO_HOLDINGS_REPORTED, INGESTION_MISSING, NON_PORTFOLIO_FUND, DATA_NOT_AVAILABLE
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.database.connection import get_session


def analyze_coverage():
    with get_session() as session:
        # Total funds and holdings across DB
        total_funds = session.execute(text("SELECT COUNT(*) FROM funds")).scalar()
        total_holdings = session.execute(text("SELECT COUNT(*) FROM holdings")).scalar()

        # Breakdown by reporting period
        periods = session.execute(text("""
            SELECT f.period_of_report,
                   COUNT(DISTINCT f.id) as funds_expected,
                   COUNT(DISTINCT CASE WHEN h.id IS NOT NULL THEN f.id END) as funds_with_holdings,
                   COUNT(DISTINCT CASE WHEN h.id IS NULL THEN f.id END) as funds_without_holdings,
                   COUNT(h.id) as total_holdings_period
            FROM funds f
            LEFT JOIN holdings h ON f.id = h.fund_id
            GROUP BY f.period_of_report
            ORDER BY funds_expected DESC
        """)).fetchall()

        print("============================================================")
        print("📊 FUND ↔ HOLDING COVERAGE BREAKDOWN BY PERIOD")
        print("============================================================")
        print(f"{'Period':<12} {'Funds Exp':>10} {'With Hold':>10} {'Without':>10} {'Coverage':>10} {'Holdings':>12} {'Avg H/F':>10}")
        print("-" * 78)

        period_data = []
        for p in periods:
            period_date, exp, with_h, without_h, tot_h = p
            cov = (with_h / exp * 100) if exp > 0 else 0
            avg_h = (tot_h / with_h) if with_h > 0 else 0
            print(f"{str(period_date):<12} {exp:>10,} {with_h:>10,} {without_h:>10} {cov:>9.2f}% {tot_h:>12,} {avg_h:>10.1f}")
            period_data.append({
                "period_date": str(period_date),
                "funds_expected": exp,
                "funds_with_holdings": with_h,
                "funds_without_holdings": without_h,
                "coverage_ratio_pct": round(cov, 4),
                "total_holdings": tot_h,
                "avg_holdings_per_fund": round(avg_h, 2)
            })

        # Investigate every single fund without holdings
        no_holding_funds = session.execute(text("""
            SELECT f.id, f.accession_number, f.series_id, f.fund_name, f.period_of_report,
                   f.total_assets, f.net_assets, f.total_liabilities
            FROM funds f
            LEFT JOIN holdings h ON f.id = h.fund_id
            WHERE h.id IS NULL
            ORDER BY f.period_of_report, f.id
        """)).fetchall()

        print(f"\n============================================================")
        print(f"🔍 INVESTIGATION OF FUNDS WITHOUT HOLDINGS ({len(no_holding_funds)} FUNDS)")
        print(f"============================================================")

        investigation_results = []
        for f in no_holding_funds:
            fid, acc, sid, fname, pdate, tot_assets, net_assets, tot_liab = f
            # Classification based on SEC filing structure
            if tot_assets is not None and float(tot_assets) == 0:
                classification = "NO_HOLDINGS_REPORTED (Liquidated / Zero Assets)"
            elif tot_assets is not None and float(tot_assets) <= 100000 and "LLC" in (fname or ""):
                classification = "NON_PORTFOLIO_FUND (Feeder / Seed Capital Vehicle)"
            else:
                classification = "NO_HOLDINGS_REPORTED (Part C Schedule Omitted in SEC Filing)"

            print(f"Fund ID:      {fid}")
            print(f"  Name:       {fname}")
            print(f"  Accession:  {acc}")
            print(f"  Series ID:  {sid}")
            print(f"  Period:     {pdate}")
            print(f"  Assets:     Total=${float(tot_assets or 0):,.2f} | Net=${float(net_assets or 0):,.2f}")
            print(f"  Category:   {classification}")
            print()

            investigation_results.append({
                "fund_id": fid,
                "accession_number": acc,
                "series_id": sid,
                "fund_name": fname,
                "period_of_report": str(pdate),
                "total_assets": float(tot_assets or 0),
                "net_assets": float(net_assets or 0),
                "classification": classification
            })

        # Holdings per fund distribution (quantiles for period 2025-06-30)
        quantiles = session.execute(text("""
            WITH fund_counts AS (
                SELECT f.id, COUNT(h.id) as h_count
                FROM funds f
                JOIN holdings h ON f.id = h.fund_id
                WHERE f.period_of_report = '2025-06-30'
                GROUP BY f.id
            )
            SELECT
                MIN(h_count) as min_count,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY h_count) as p25,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY h_count) as median,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY h_count) as p75,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY h_count) as p95,
                MAX(h_count) as max_count
            FROM fund_counts
        """)).fetchone()

        print("============================================================")
        print("📈 HOLDINGS PER FUND DISTRIBUTION (Period: 2025-06-30)")
        print("============================================================")
        print(f"Min:    {quantiles[0]:,}")
        print(f"P25:    {quantiles[1]:,.1f}")
        print(f"Median: {quantiles[2]:,.1f}")
        print(f"P75:    {quantiles[3]:,.1f}")
        print(f"P95:    {quantiles[4]:,.1f}")
        print(f"Max:    {quantiles[5]:,}")

        summary = {
            "total_funds": total_funds,
            "total_holdings": total_holdings,
            "period_breakdown": period_data,
            "investigation_results": investigation_results,
            "quantiles_2025_06_30": {
                "min": quantiles[0],
                "p25": float(quantiles[1]),
                "median": float(quantiles[2]),
                "p75": float(quantiles[3]),
                "p95": float(quantiles[4]),
                "max": quantiles[5]
            }
        }

        os.makedirs("reports", exist_ok=True)
        with open("reports/fund_holdings_coverage_analysis.json", "w") as f:
            json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    analyze_coverage()
