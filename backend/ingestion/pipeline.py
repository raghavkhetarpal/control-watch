"""SEC N-PORT Ingestion Pipeline.

Orchestrates downloading, streaming extraction, chunked parsing,
data normalization, validation, and relational PostgreSQL loading.

Hierarchy:
submissions -> registrants -> fund_series -> funds -> holdings -> reporting_periods
"""
import os
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd
import structlog
from sqlalchemy import text

from backend.database.connection import engine, SessionLocal
from backend.ingestion.sec_nport_downloader import download_sec_nport
from backend.ingestion.sec_nport_parser import NPortParser
from backend.ingestion.normalizer import DataNormalizer
from backend.ingestion.validators import Validator

logger = structlog.get_logger(__name__)


class IngestionPipeline:
    def __init__(self, year: int, quarter: int, sample_size: int = 5000, is_sample: bool = False):
        self.year = year
        self.quarter = quarter
        self.quarter_str = f"{year}Q{quarter}"
        self.sample_size = sample_size
        self.is_sample = is_sample
        self.run_id = None
        self.stats = {
            "rows_processed": 0,
            "rows_rejected": 0,
            "submissions_loaded": 0,
            "registrants_loaded": 0,
            "series_loaded": 0,
            "funds_loaded": 0,
            "holdings_loaded": 0,
        }

    def _init_run(self, session, url: str, file_hash: str) -> int:
        """Create or resume an ingestion run record in the database."""
        # If an in-progress or failed run exists, reuse it
        existing = session.execute(
            text("SELECT id FROM ingestion_runs WHERE quarter = :q AND file_hash = :hash ORDER BY id DESC LIMIT 1"),
            {"q": self.quarter_str, "hash": file_hash}
        ).fetchone()

        if existing:
            session.execute(text("""
                UPDATE ingestion_runs 
                SET started_at = NOW(), status = 'RUNNING', error_message = NULL,
                    is_sample = :is_sample, sample_size = :sample
                WHERE id = :id
            """), {
                "id": existing.id,
                "is_sample": self.is_sample,
                "sample": self.sample_size if self.is_sample else None,
            })
            session.commit()
            return existing.id

        query = text("""
            INSERT INTO ingestion_runs 
                (quarter, download_url, file_hash, started_at, status, is_sample, sample_size)
            VALUES
                (:q, :url, :hash, NOW(), 'RUNNING', :is_sample, :sample)
            RETURNING id
        """)
        res = session.execute(query, {
            "q": self.quarter_str,
            "url": url,
            "hash": file_hash,
            "is_sample": self.is_sample,
            "sample": self.sample_size if self.is_sample else None,
        })
        session.commit()
        return res.scalar()

    def _mark_run_status(self, session, status: str, error_message: str = None, duration: float = 0.0):
        if not self.run_id:
            return
        query = text("""
            UPDATE ingestion_runs 
            SET status = :status,
                error_message = :err,
                completed_at = NOW(),
                duration_seconds = :duration,
                rows_processed = :processed,
                rows_rejected = :rejected
            WHERE id = :rid
        """)
        session.execute(query, {
            "status": status,
            "err": error_message[:500] if error_message else None,
            "duration": round(duration, 2),
            "processed": self.stats["rows_processed"],
            "rejected": self.stats["rows_rejected"],
            "rid": self.run_id,
        })
        session.commit()

    def run(self, data_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Execute end-to-end ingestion pipeline."""
        start_time = time.time()
        session = SessionLocal()

        try:
            # 1. Download & Verify Checksum
            download_meta = download_sec_nport(self.year, self.quarter, data_dir)
            url = f"https://www.sec.gov/files/dera/data/form-n-port-data-sets/{self.year}q{self.quarter}_nport.zip"

            # Check if this quarter was already processed
            existing = session.execute(
                text("SELECT id FROM ingestion_runs WHERE quarter = :q AND file_hash = :hash AND status = 'COMPLETED'"),
                {"q": self.quarter_str, "hash": download_meta["hash"]}
            ).fetchone()

            if existing:
                logger.info("Quarter already ingested", quarter=self.quarter_str, run_id=existing.id)
                session.close()
                return {
                    "run_id": existing.id,
                    "quarter": self.quarter_str,
                    "status": "already_ingested",
                    "duration_seconds": 0,
                    "rows_processed": 0,
                    "rows_rejected": 0,
                    "message": f"Quarter {self.quarter_str} already ingested in run {existing.id} (idempotent skip)",
                }

            self.run_id = self._init_run(session, url, download_meta["hash"])
            logger.info("ingestion_run_started", run_id=self.run_id, quarter=self.quarter_str, is_sample=self.is_sample)

            # 2. Extract & Parse TSVs
            parser = NPortParser(download_meta["path"])
            iterators = parser.extract_and_parse()

            # We maintain an in-memory map of accession_number -> (filing_date, period_of_report, cik)
            submission_meta = {}
            registrant_cik_map = {}

            # ── Step A: Submissions ──
            if "submission" in iterators:
                for chunk in iterators["submission"]:
                    norm_df = DataNormalizer.normalize_submission(chunk)
                    norm_df["ingestion_run_id"] = self.run_id
                    db_cols = ["accession_number", "filing_date", "period_of_report", "filing_type", "is_amendment", "ingestion_run_id"]
                    load_df = norm_df[[c for c in db_cols if c in norm_df.columns]].dropna(subset=["accession_number"])

                    val_res = Validator.pre_load_validation(load_df, "submissions", ["accession_number"])
                    if val_res["passed"]:
                        # Cache metadata for fund linkage
                        for _, row in load_df.iterrows():
                            submission_meta[row["accession_number"]] = {
                                "filing_date": row.get("filing_date"),
                                "period_of_report": row.get("period_of_report"),
                            }

                        with engine.begin() as conn:
                            # Batch insert with ON CONFLICT DO NOTHING
                            for row in load_df.to_dict(orient="records"):
                                conn.execute(text("""
                                    INSERT INTO submissions (accession_number, filing_date, period_of_report, filing_type, is_amendment, ingestion_run_id)
                                    VALUES (:accession_number, :filing_date, :period_of_report, :filing_type, :is_amendment, :ingestion_run_id)
                                    ON CONFLICT (accession_number) DO NOTHING
                                """), row)
                        self.stats["submissions_loaded"] += len(load_df)
                        self.stats["rows_processed"] += len(load_df)
                    else:
                        self.stats["rows_rejected"] += len(load_df)

            # ── Step B: Registrants ──
            if "registrant" in iterators:
                for chunk in iterators["registrant"]:
                    norm_df = DataNormalizer.normalize_registrant(chunk)
                    if "cik" in norm_df.columns and "registrant_name" in norm_df.columns:
                        load_df = norm_df.dropna(subset=["cik", "registrant_name"]).copy()
                        load_df["cik"] = load_df["cik"].astype(str).str.zfill(10)

                        for _, r in load_df.iterrows():
                            if "accession_number" in r:
                                registrant_cik_map[r["accession_number"]] = r["cik"]

                        dedup_df = load_df.drop_duplicates(subset=["cik"])
                        with engine.begin() as conn:
                            for row in dedup_df.to_dict(orient="records"):
                                conn.execute(text("""
                                    INSERT INTO registrants (cik, registrant_name, lei, street1, city, state, country, zip, phone)
                                    VALUES (:cik, :registrant_name, :lei, :address1, :city, :state, :country, :zip, :phone)
                                    ON CONFLICT (cik) DO NOTHING
                                """), {
                                    "cik": row["cik"],
                                    "registrant_name": str(row["registrant_name"])[:255],
                                    "lei": str(row.get("lei"))[:20] if pd.notna(row.get("lei")) else None,
                                    "address1": str(row.get("address1"))[:255] if pd.notna(row.get("address1")) else None,
                                    "city": str(row.get("city"))[:100] if pd.notna(row.get("city")) else None,
                                    "state": str(row.get("state"))[:10] if pd.notna(row.get("state")) else None,
                                    "country": str(row.get("country"))[:10] if pd.notna(row.get("country")) else "US",
                                    "zip": str(row.get("zip"))[:20] if pd.notna(row.get("zip")) else None,
                                    "phone": str(row.get("phone"))[:30] if pd.notna(row.get("phone")) else None,
                                })
                        self.stats["registrants_loaded"] += len(dedup_df)
                        self.stats["rows_processed"] += len(load_df)

            # ── Step C: Fund Info & Series ──
            # Map of (accession_number, series_id) -> fund_id
            accession_to_fund_id = {}

            if "fund_info" in iterators:
                for chunk in iterators["fund_info"]:
                    norm_df = DataNormalizer.normalize_fund_info(chunk)
                    
                    # 1. Process and load series and funds
                    with engine.begin() as conn:
                        for _, frow in norm_df.iterrows():
                            acc = frow.get("accession_number")
                            if not acc:
                                continue
                            raw_sid = frow.get("series_id")
                            cik = registrant_cik_map.get(acc)
                            fname = str(frow.get("series_name", f"Fund {acc}"))[:255]

                            if pd.isna(raw_sid) or str(raw_sid).lower() in ("nan", "none", ""):
                                sid = f"S_{cik}" if cik else f"S_{acc.replace('-', '')[-10:]}"
                            else:
                                sid = str(raw_sid).strip()[:20]

                            # Ensure series exists in fund_series
                            conn.execute(text("""
                                INSERT INTO fund_series (series_id, cik, series_name)
                                VALUES (:series_id, :cik, :series_name)
                                ON CONFLICT (series_id) DO NOTHING
                            """), {"series_id": sid, "cik": cik, "series_name": fname})

                            # Insert into funds
                            meta = submission_meta.get(acc, {})
                            p_date = meta.get("period_of_report")
                            f_date = meta.get("filing_date")

                            t_assets = float(frow.get("total_assets")) if pd.notna(frow.get("total_assets")) else None
                            n_assets = float(frow.get("net_assets")) if pd.notna(frow.get("net_assets")) else None
                            t_liab = float(frow.get("total_liabilities")) if pd.notna(frow.get("total_liabilities")) else None

                            res = conn.execute(text("""
                                INSERT INTO funds (accession_number, series_id, cik, fund_name, total_assets, net_assets, total_liabilities, period_of_report, filing_date)
                                VALUES (:acc, :sid, :cik, :fname, :t_assets, :n_assets, :t_liab, :p_date, :f_date)
                                ON CONFLICT (accession_number, series_id) DO UPDATE
                                    SET total_assets = EXCLUDED.total_assets,
                                        net_assets = EXCLUDED.net_assets,
                                        total_liabilities = EXCLUDED.total_liabilities
                                RETURNING id
                            """), {
                                "acc": acc, "sid": sid, "cik": cik, "fname": fname,
                                "t_assets": t_assets, "n_assets": n_assets, "t_liab": t_liab,
                                "p_date": p_date, "f_date": f_date,
                            })
                            fid = res.scalar()
                            if fid:
                                accession_to_fund_id[acc] = fid
                                accession_to_fund_id[(acc, sid)] = fid

                    self.stats["funds_loaded"] += len(norm_df)
                    self.stats["series_loaded"] += len(norm_df)
                    self.stats["rows_processed"] += len(norm_df)

            # Ensure accession_to_fund_id is populated from DB if any were missed
            with engine.connect() as conn:
                f_rows = conn.execute(text("SELECT id, accession_number, series_id FROM funds")).mappings().all()
                for fr in f_rows:
                    accession_to_fund_id[fr["accession_number"]] = fr["id"]
                    if fr["series_id"]:
                        accession_to_fund_id[(fr["accession_number"], fr["series_id"])] = fr["id"]

            # ── Step D: Holdings ──
            if "holding" in iterators:
                holding_total = 0
                for chunk in iterators["holding"]:
                    norm_df = DataNormalizer.normalize_holding(chunk)

                    # Limit sample if requested
                    if self.is_sample and holding_total >= self.sample_size:
                        logger.info("Sample holding limit reached", limit=self.sample_size)
                        break

                    # Map fund_id
                    records_to_insert = []
                    for _, hrow in norm_df.iterrows():
                        acc = hrow.get("accession_number")
                        hid = str(hrow.get("holding_id", ""))
                        if not acc or not hid:
                            continue

                        fund_id = accession_to_fund_id.get(acc)
                        # Clean values
                        balance = float(hrow.get("balance")) if pd.notna(hrow.get("balance")) else None
                        val = float(hrow.get("value")) if pd.notna(hrow.get("value")) else None
                        pct_val = float(hrow.get("pct_val")) if pd.notna(hrow.get("pct_val")) else None

                        records_to_insert.append({
                            "accession_number": acc,
                            "holding_id": hid[:50],
                            "fund_id": fund_id,
                            "name": str(hrow.get("name", ""))[:255] if pd.notna(hrow.get("name")) else None,
                            "title": str(hrow.get("title", ""))[:255] if pd.notna(hrow.get("title")) else None,
                            "cusip": str(hrow.get("cusip", ""))[:9] if pd.notna(hrow.get("cusip")) else None,
                            "isin": str(hrow.get("isin", ""))[:12] if pd.notna(hrow.get("isin")) else None,
                            "lei": str(hrow.get("lei", ""))[:20] if pd.notna(hrow.get("lei")) else None,
                            "balance": balance,
                            "units": str(hrow.get("units", ""))[:10] if pd.notna(hrow.get("units")) else None,
                            "currency_code": str(hrow.get("currency_code", "USD"))[:3],
                            "value": val,
                            "pct_val": pct_val,
                            "asset_cat": str(hrow.get("asset_cat", ""))[:10] if pd.notna(hrow.get("asset_cat")) else None,
                            "issuer_cat": str(hrow.get("issuer_cat", ""))[:10] if pd.notna(hrow.get("issuer_cat")) else None,
                            "investment_country": str(hrow.get("investment_country", ""))[:3] if pd.notna(hrow.get("investment_country")) else None,
                            "payoff_profile": str(hrow.get("payoff_profile", ""))[:10] if pd.notna(hrow.get("payoff_profile")) else None,
                            "fair_value_level": str(hrow.get("fair_value_level", ""))[:5] if pd.notna(hrow.get("fair_value_level")) else None,
                            "is_restricted": bool(hrow.get("is_restricted", False)),
                        })

                        if self.is_sample and (holding_total + len(records_to_insert)) >= self.sample_size:
                            break

                    # Batch insert
                    if records_to_insert:
                        with engine.begin() as conn:
                            for rec in records_to_insert:
                                conn.execute(text("""
                                    INSERT INTO holdings (
                                        accession_number, holding_id, fund_id, name, title,
                                        cusip, isin, lei, balance, units, currency_code,
                                        value, pct_val, asset_cat, issuer_cat, investment_country,
                                        payoff_profile, fair_value_level, is_restricted
                                    ) VALUES (
                                        :accession_number, :holding_id, :fund_id, :name, :title,
                                        :cusip, :isin, :lei, :balance, :units, :currency_code,
                                        :value, :pct_val, :asset_cat, :issuer_cat, :investment_country,
                                        :payoff_profile, :fair_value_level, :is_restricted
                                    )
                                    ON CONFLICT (accession_number, holding_id) DO NOTHING
                                """), rec)

                        holding_total += len(records_to_insert)
                        self.stats["holdings_loaded"] += len(records_to_insert)
                        self.stats["rows_processed"] += len(records_to_insert)

            # ── Step E: Reporting Periods Rollup ──
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO reporting_periods (period_date, quarter, fund_count, holding_count)
                    SELECT f.period_of_report, :quarter_str, COUNT(DISTINCT f.id), COUNT(h.id)
                    FROM funds f
                    LEFT JOIN holdings h ON h.fund_id = f.id
                    WHERE f.period_of_report IS NOT NULL
                    GROUP BY f.period_of_report
                    ON CONFLICT (period_date) DO UPDATE
                        SET fund_count = EXCLUDED.fund_count,
                            holding_count = EXCLUDED.holding_count
                """), {"quarter_str": self.quarter_str})

            # Post load validation
            Validator.post_load_validation(session, self.run_id)

            duration = time.time() - start_time
            self._mark_run_status(session, "COMPLETED", duration=duration)
            logger.info("ingestion_completed", run_id=self.run_id, duration_seconds=duration, stats=self.stats)

            return {
                "run_id": self.run_id,
                "quarter": self.quarter_str,
                "status": "completed",
                "duration_seconds": duration,
                "rows_processed": self.stats["rows_processed"],
                "rows_rejected": self.stats["rows_rejected"],
                "funds_loaded": self.stats["funds_loaded"],
                "holdings_loaded": self.stats["holdings_loaded"],
                "message": f"Successfully ingested {self.quarter_str}: {self.stats['funds_loaded']} funds, {self.stats['holdings_loaded']} holdings",
            }

        except Exception as e:
            logger.error("ingestion_failed", error=str(e), exc_info=True)
            duration = time.time() - start_time
            self._mark_run_status(session, "FAILED", error_message=str(e), duration=duration)
            raise e
        finally:
            session.close()


def run_pipeline(quarter: str, sample: bool = False, sample_size: int = 5000, data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Helper entry point for API and bootstrap scripts."""
    m = re.match(r"^(\d{4})[Qq](\d)$", quarter.strip())
    if not m:
        raise ValueError(f"Invalid quarter format '{quarter}'. Expected format: YYYYqQ (e.g. 2025q3)")
    year = int(m.group(1))
    q = int(m.group(2))

    pipeline = IngestionPipeline(year=year, quarter=q, sample_size=sample_size, is_sample=sample)
    return pipeline.run(data_dir=data_dir)
