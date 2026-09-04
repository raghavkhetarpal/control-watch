#!/usr/bin/env python3
"""AWM ControlWatch - Bootstrap Script.

Initializes the database, downloads SEC N-PORT data, runs ingestion,
executes controls, and calculates KRI/KCI/KPI metrics.

Usage:
    python scripts/bootstrap.py              # Full pipeline with default quarter
    python scripts/bootstrap.py --sample     # Quick sample mode (5000 holdings)
    python scripts/bootstrap.py --quarter 2025q3
    python scripts/bootstrap.py --sample --sample-size 2000
"""
import argparse
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog

logger = structlog.get_logger()


def main():
    parser = argparse.ArgumentParser(description="AWM ControlWatch Bootstrap")
    parser.add_argument(
        "--quarter",
        default=os.environ.get("SEC_DEFAULT_QUARTER", "2025q3"),
        help="SEC N-PORT quarter to ingest (e.g., 2025q3)",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Use sample mode with limited holdings",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=int(os.environ.get("SEC_SAMPLE_SIZE", "5000")),
        help="Number of holdings in sample mode (default: 5000)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download if data already cached",
    )
    parser.add_argument(
        "--skip-controls",
        action="store_true",
        help="Skip control execution",
    )
    args = parser.parse_args()

    start_time = time.time()
    logger.info("bootstrap_starting", quarter=args.quarter, sample=args.sample)

    # ── Step 1: Initialize Database ──
    logger.info("step_1_init_database")
    try:
        from backend.database.connection import init_db
        init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
        print(f"\n❌ Database initialization failed: {e}")
        print("Make sure PostgreSQL is running and DATABASE_URL is configured.")
        print("Try: docker-compose up -d db")
        sys.exit(1)

    # ── Step 2: Seed Users ──
    logger.info("step_2_seed_users")
    try:
        from backend.database.connection import get_session
        from sqlalchemy import text

        with get_session() as session:
            session.execute(text("""
                INSERT INTO users (username, display_name, email, role)
                VALUES
                    ('admin', 'Admin User', 'admin@example.com', 'ADMIN'),
                    ('analyst1', 'Sarah Chen', 'sarah.chen@example.com', 'ANALYST'),
                    ('analyst2', 'James Park', 'james.park@example.com', 'ANALYST'),
                    ('manager1', 'Maria Rodriguez', 'maria.rodriguez@example.com', 'MANAGER')
                ON CONFLICT (username) DO NOTHING
            """))
        logger.info("users_seeded")
    except Exception as e:
        logger.warning("user_seeding_failed", error=str(e))

    # ── Step 3: Run Ingestion Pipeline ──
    logger.info("step_3_ingestion", quarter=args.quarter)
    try:
        from backend.ingestion.pipeline import run_pipeline

        result = run_pipeline(
            quarter=args.quarter,
            sample=args.sample,
            sample_size=args.sample_size,
        )
        logger.info(
            "ingestion_completed",
            rows_processed=result.get("rows_processed", 0),
            rows_rejected=result.get("rows_rejected", 0),
            duration=result.get("duration_seconds", 0),
        )
        print(f"\n✅ Ingestion completed: {result.get('rows_processed', 0)} rows processed")
    except Exception as e:
        logger.error("ingestion_failed", error=str(e))
        print(f"\n❌ Ingestion failed: {e}")
        print("Continuing with whatever data is available...")

    # ── Step 4: Run Controls ──
    if not args.skip_controls:
        logger.info("step_4_run_controls")
        try:
            from backend.controls.registry import run_all_controls
            from backend.database.connection import get_session
            from sqlalchemy import text

            with get_session() as session:
                # Determine the period date from ingested data
                period_row = session.execute(text(
                    "SELECT MAX(period_of_report) FROM submissions"
                )).scalar()
                if period_row:
                    period_date = period_row
                    logger.info("running_controls", period=str(period_date))
                    results = run_all_controls(session, period_date)
                    total_exceptions = sum(r.exceptions_found for r in results)
                    print(f"\n✅ Controls executed: {len(results)} controls, {total_exceptions} exceptions found")
                else:
                    logger.warning("no_period_data_for_controls")
                    print("\n⚠️  No period data available for control execution")
        except Exception as e:
            logger.error("controls_failed", error=str(e))
            print(f"\n⚠️  Control execution failed: {e}")

    # ── Step 5: Calculate KRI/KCI/KPI ──
    if not args.skip_controls:
        logger.info("step_5_calculate_metrics")
        try:
            from backend.metrics.kri import calculate_all_kris
            from backend.metrics.kci import calculate_all_kcis
            from backend.metrics.kpi import calculate_all_kpis
            from backend.database.connection import get_session
            from sqlalchemy import text

            with get_session() as session:
                period_row = session.execute(text(
                    "SELECT MAX(period_of_report) FROM submissions"
                )).scalar()
                if period_row:
                    period_date = period_row
                    kris = calculate_all_kris(session, period_date)
                    kcis = calculate_all_kcis(session, period_date)
                    kpis = calculate_all_kpis(session, period_date)
                    print(f"\n✅ Metrics calculated: {len(kris)} KRIs, {len(kcis)} KCIs, {len(kpis)} KPIs")

                    # Print KRI summary
                    print("\n📊 KRI Summary:")
                    print(f"  {'ID':<10} {'Name':<35} {'Value':>10} {'Status':<8}")
                    print("  " + "-" * 70)
                    for kri in kris:
                        status_icon = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}.get(kri.status, "⚪")
                        print(f"  {kri.kri_id:<10} {kri.name:<35} {kri.value:>9.2f}% {status_icon} {kri.status:<8}")
        except Exception as e:
            logger.error("metrics_failed", error=str(e))
            print(f"\n⚠️  Metrics calculation failed: {e}")

    # ── Summary ──
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"🏁 Bootstrap completed in {elapsed:.1f} seconds")
    print(f"{'='*60}")
    print(f"\nQuarter: {args.quarter}")
    print(f"Sample mode: {'Yes' if args.sample else 'No'}")
    print(f"\nNext steps:")
    print(f"  • Start API:       uvicorn backend.main:app --reload")
    print(f"  • Start Dashboard: streamlit run dashboard/app.py")
    print(f"  • Run tests:       pytest tests/ -v")
    print(f"  • API docs:        http://localhost:8000/docs")
    print(f"  • Dashboard:       http://localhost:8501")


if __name__ == "__main__":
    main()
