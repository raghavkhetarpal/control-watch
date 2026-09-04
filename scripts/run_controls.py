#!/usr/bin/env python3
"""AWM ControlWatch - Run Controls Script.

Executes all controls against the latest reporting period.

Usage:
    python scripts/run_controls.py
    python scripts/run_controls.py --period 2025-09-30
    python scripts/run_controls.py --control DQ-001
"""
import argparse
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.database.connection import get_session
from backend.controls.registry import run_all_controls, run_control
from backend.metrics.kri import calculate_all_kris
from backend.metrics.kci import calculate_all_kcis
from backend.metrics.kpi import calculate_all_kpis


def main():
    parser = argparse.ArgumentParser(description="Run Controls")
    parser.add_argument("--period", type=str, help="Period date (YYYY-MM-DD)")
    parser.add_argument("--control", type=str, help="Specific control ID to run")
    parser.add_argument("--skip-metrics", action="store_true", help="Skip KRI/KCI/KPI calculation")
    args = parser.parse_args()

    with get_session() as session:
        # Determine period
        if args.period:
            period_date = date.fromisoformat(args.period)
        else:
            period_date = session.execute(
                text("SELECT MAX(period_of_report) FROM submissions")
            ).scalar()
            if not period_date:
                print("❌ No data found. Run ingestion first.")
                sys.exit(1)

        print(f"Period: {period_date}")

        # Run controls
        if args.control:
            print(f"Running control {args.control}...")
            result = run_control(session, args.control, period_date)
            print(f"  {result.control_id}: {result.exceptions_found} exceptions "
                  f"({result.pass_rate:.1f}% pass rate, {result.duration_ms}ms)")
        else:
            print("Running all controls...")
            results = run_all_controls(session, period_date)
            print(f"\n{'Control':<12} {'Exceptions':>12} {'Pass Rate':>12} {'Duration':>12}")
            print("-" * 52)
            for r in results:
                print(f"{r.control_id:<12} {r.exceptions_found:>12} {r.pass_rate:>11.1f}% {r.duration_ms:>10}ms")
            total = sum(r.exceptions_found for r in results)
            print(f"\nTotal: {total} exceptions across {len(results)} controls")

        # Calculate metrics
        if not args.skip_metrics:
            print("\nCalculating KRI/KCI/KPI metrics...")
            kris = calculate_all_kris(session, period_date)
            kcis = calculate_all_kcis(session, period_date)
            kpis = calculate_all_kpis(session, period_date)
            print(f"  {len(kris)} KRIs, {len(kcis)} KCIs, {len(kpis)} KPIs calculated")


if __name__ == "__main__":
    main()
