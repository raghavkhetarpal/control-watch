#!/usr/bin/env python3
"""AWM ControlWatch - Ingestion Script.

Runs the SEC N-PORT data ingestion pipeline.

Usage:
    python scripts/ingest.py --quarter 2025q3
    python scripts/ingest.py --quarter 2025q3 --sample --sample-size 5000
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.connection import init_db
from backend.ingestion.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="SEC N-PORT Data Ingestion")
    parser.add_argument("--quarter", required=True, help="Quarter (e.g., 2025q3)")
    parser.add_argument("--sample", action="store_true", help="Sample mode")
    parser.add_argument("--sample-size", type=int, default=5000)
    args = parser.parse_args()

    print(f"Initializing database...")
    init_db()

    print(f"Starting ingestion for {args.quarter}...")
    result = run_pipeline(
        quarter=args.quarter,
        sample=args.sample,
        sample_size=args.sample_size,
    )
    print(f"Ingestion result: {result}")


if __name__ == "__main__":
    main()
