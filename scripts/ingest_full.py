#!/usr/bin/env python3
"""AWM ControlWatch — Full Dataset Ingestion Engine.

Executes streaming chunked ingestion of the complete SEC Form N-PORT Q3 2025 archive.
Achieves high-throughput loading using PostgreSQL COPY with memory safety and tracemalloc.
"""
import os
import sys
import time
import io
import zipfile
import tracemalloc
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.database.connection import engine, get_session
from backend.ingestion.sec_nport_downloader import download_sec_nport


def run_full_ingestion(year: int = 2025, quarter: int = 3):
    tracemalloc.start()
    t_start = time.time()
    quarter_str = f"{year}q{quarter}"
    print(f"============================================================")
    print(f"🚀 Starting Full-Dataset Ingestion for {quarter_str.upper()}")
    print(f"============================================================")

    # 1. Ensure archive is downloaded and verified
    download_meta = download_sec_nport(year, quarter)
    zip_path = Path(download_meta["path"])
    file_hash = download_meta["hash"]
    print(f"Archive: {zip_path.name} ({zip_path.stat().st_size:,} bytes | SHA-256: {file_hash})")

    # 2. Map accession_number -> fund_id
    with engine.connect() as conn:
        acc_to_fid = dict(conn.execute(text("SELECT accession_number, id FROM funds")).fetchall())
    print(f"Loaded {len(acc_to_fid):,} accession_number -> fund_id linkages from database.")

    # 3. Create or update ingestion_run record
    with get_session() as session:
        session.execute(text("""
            DELETE FROM ingestion_runs WHERE quarter = :q
        """), {"q": quarter_str})
        session.commit()
        run_id = session.execute(text("""
            INSERT INTO ingestion_runs (quarter, download_url, file_hash, started_at, status, is_sample)
            VALUES (:q, :url, :hash, NOW(), 'RUNNING', FALSE)
            RETURNING id
        """), {
            "q": quarter_str,
            "url": f"https://www.sec.gov/files/dera/data/form-n-port-data-sets/{year}q{quarter}_nport.zip",
            "hash": file_hash
        }).scalar()
        session.commit()
    print(f"Created ingestion_runs record: #{run_id} (is_sample=FALSE)")

    # 4. Truncate existing holdings table to guarantee clean state
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            print("Truncating holdings and suspending secondary indexes for bulk stream...")
            cur.execute("TRUNCATE TABLE holdings CASCADE")
            cur.execute("DROP INDEX IF EXISTS idx_holdings_cusip")
            cur.execute("DROP INDEX IF EXISTS idx_holdings_isin")
            cur.execute("DROP INDEX IF EXISTS idx_holdings_asset_cat")
            cur.execute("DROP INDEX IF EXISTS idx_holdings_issuer_cat")
            cur.execute("DROP INDEX IF EXISTS idx_holdings_country")
            cur.execute("DROP INDEX IF EXISTS idx_holdings_name")
            cur.execute("DROP INDEX IF EXISTS idx_holdings_fund")
            cur.execute("DROP INDEX IF EXISTS idx_holdings_accession")
            cur.execute("DROP INDEX IF EXISTS idx_holdings_natural")
            raw_conn.commit()

        # 5. Stream chunks from FUND_REPORTED_HOLDING.tsv
        CHUNK_SIZE = 100000
        total_rows = 0
        buf = io.StringIO()
        t_copy_start = time.time()

        columns = (
            'accession_number', 'holding_id', 'fund_id', 'name', 'title',
            'cusip', 'isin', 'lei', 'balance', 'units', 'currency_code',
            'value', 'pct_val', 'asset_cat', 'issuer_cat', 'investment_country',
            'payoff_profile', 'fair_value_level', 'is_restricted'
        )

        with zipfile.ZipFile(zip_path, 'r') as z:
            with z.open('FUND_REPORTED_HOLDING.tsv') as f:
                header = f.readline().decode('utf-8').strip().split('\t')
                h_idx = {h: i for i, h in enumerate(header)}

                chunk_count = 0
                for line in f:
                    parts = line.decode('utf-8', errors='replace').split('\t')
                    acc = parts[h_idx['ACCESSION_NUMBER']]
                    hid = parts[h_idx['HOLDING_ID']]
                    name = parts[h_idx['ISSUER_NAME']].replace('\t', ' ').replace('\n', ' ').replace('\r', '').replace('\\', '\\\\')
                    title = parts[h_idx['ISSUER_TITLE']].replace('\t', ' ').replace('\n', ' ').replace('\r', '').replace('\\', '\\\\')
                    cusip = parts[h_idx['ISSUER_CUSIP']].strip().upper()[:9]
                    isin = ''
                    lei = parts[h_idx['ISSUER_LEI']].strip()[:20] if parts[h_idx['ISSUER_LEI']] != 'N/A' else ''
                    bal = parts[h_idx['BALANCE']].strip() or '\\N'
                    units = parts[h_idx['UNIT']].strip()[:10]
                    curr = parts[h_idx['CURRENCY_CODE']].strip()[:3] or 'USD'
                    val = parts[h_idx['CURRENCY_VALUE']].strip() or '\\N'
                    pct = parts[h_idx['PERCENTAGE']].strip() or '\\N'
                    acat = parts[h_idx['ASSET_CAT']].strip()[:10]
                    icat = parts[h_idx['ISSUER_TYPE']].strip()[:10]
                    country = parts[h_idx['INVESTMENT_COUNTRY']].strip()[:3]
                    profile = parts[h_idx['PAYOFF_PROFILE']].strip()[:10]
                    fvl = parts[h_idx['FAIR_VALUE_LEVEL']].strip()[:5]
                    restr = 't' if parts[h_idx['IS_RESTRICTED_SECURITY']].strip().upper() == 'Y' else 'f'
                    fid = str(acc_to_fid.get(acc, '\\N'))

                    buf.write(f'{acc}\t{hid}\t{fid}\t{name}\t{title}\t{cusip}\t{isin}\t{lei}\t{bal}\t{units}\t{curr}\t{val}\t{pct}\t{acat}\t{icat}\t{country}\t{profile}\t{fvl}\t{restr}\n')
                    chunk_count += 1
                    total_rows += 1

                    if chunk_count >= CHUNK_SIZE:
                        buf.seek(0)
                        with raw_conn.cursor() as cur:
                            cur.copy_from(buf, 'holdings', sep='\t', null='\\N', columns=columns)
                        raw_conn.commit()
                        buf.seek(0)
                        buf.truncate(0)
                        chunk_count = 0
                        elapsed = time.time() - t_copy_start
                        rate = total_rows / elapsed if elapsed > 0 else 0
                        print(f"  Ingested {total_rows:,} holdings ({rate:,.0f} rows/s)...")

                # Final chunk
                if chunk_count > 0:
                    buf.seek(0)
                    with raw_conn.cursor() as cur:
                        cur.copy_from(buf, 'holdings', sep='\t', null='\\N', columns=columns)
                    raw_conn.commit()
                    buf.close()

        t_copy_elapsed = time.time() - t_copy_start
        print(f"✅ Streamed {total_rows:,} holdings in {t_copy_elapsed:.2f}s ({total_rows/t_copy_elapsed:,.0f} rows/s).")

        # 6. Rebuild Indexes
        t_idx_start = time.time()
        print("Rebuilding relational database indexes...")
        with raw_conn.cursor() as cur:
            cur.execute("CREATE UNIQUE INDEX idx_holdings_natural ON holdings(accession_number, holding_id)")
            cur.execute("CREATE INDEX idx_holdings_fund ON holdings(fund_id)")
            cur.execute("CREATE INDEX idx_holdings_cusip ON holdings(cusip)")
            cur.execute("CREATE INDEX idx_holdings_isin ON holdings(isin)")
            cur.execute("CREATE INDEX idx_holdings_asset_cat ON holdings(asset_cat)")
            cur.execute("CREATE INDEX idx_holdings_issuer_cat ON holdings(issuer_cat)")
            cur.execute("CREATE INDEX idx_holdings_country ON holdings(investment_country)")
            cur.execute("CREATE INDEX idx_holdings_name ON holdings(name)")
            cur.execute("CREATE INDEX idx_holdings_accession ON holdings(accession_number)")
            raw_conn.commit()
        t_idx_elapsed = time.time() - t_idx_start
        print(f"✅ Relational indexes rebuilt in {t_idx_elapsed:.2f}s.")

    finally:
        raw_conn.close()

    # 7. Update Reporting Periods
    print("Updating reporting_periods rollup statistics...")
    with get_session() as session:
        session.execute(text("""
            INSERT INTO reporting_periods (period_date, quarter, fund_count, holding_count)
            SELECT f.period_of_report, :quarter_str, COUNT(DISTINCT f.id), COUNT(h.id)
            FROM funds f
            LEFT JOIN holdings h ON h.fund_id = f.id
            WHERE f.period_of_report IS NOT NULL
            GROUP BY f.period_of_report
            ON CONFLICT (period_date) DO UPDATE
                SET fund_count = EXCLUDED.fund_count,
                    holding_count = EXCLUDED.holding_count
        """), {"quarter_str": quarter_str})

        t_total = time.time() - t_start
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        session.execute(text("""
            UPDATE ingestion_runs
            SET status = 'COMPLETED',
                completed_at = NOW(),
                rows_processed = :processed,
                rows_rejected = 0,
                duration_seconds = :dur
            WHERE id = :rid
        """), {"processed": total_rows, "dur": round(t_total, 2), "rid": run_id})
        session.commit()

    peak_mb = peak_mem / (1024 * 1024)
    print(f"============================================================")
    print(f"🎉 FULL INGESTION COMPLETED SUCCESSFULLY!")
    print(f"Total Holdings Loaded: {total_rows:,}")
    print(f"Total Duration:        {t_total:.2f} seconds ({t_total/60:.2f} minutes)")
    print(f"Overall Ingestion Rate: {total_rows/t_total:,.0f} rows/second")
    print(f"Peak Process Memory:   {peak_mb:.2f} MB")
    print(f"============================================================")

    return {
        "run_id": run_id,
        "quarter": quarter_str,
        "total_source_rows": total_rows,
        "rows_parsed": total_rows,
        "rows_normalized": total_rows,
        "rows_loaded": total_rows,
        "rows_rejected": 0,
        "rejection_reasons": {},
        "duration_seconds": round(t_total, 2),
        "peak_memory_mb": round(peak_mb, 2),
    }


if __name__ == "__main__":
    run_full_ingestion(2025, 3)
