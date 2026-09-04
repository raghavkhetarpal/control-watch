import time
from pathlib import Path
from typing import Optional
import structlog
import pandas as pd
from sqlalchemy import text
from backend.database.connection import engine, get_session
from backend.ingestion.sec_nport_downloader import download_sec_nport
from backend.ingestion.sec_nport_parser import NPortParser
from backend.ingestion.normalizer import DataNormalizer
from backend.ingestion.validators import Validator

logger = structlog.get_logger(__name__)

class IngestionPipeline:
    def __init__(self, year: int, quarter: int, sample_size: int = 5000, is_sample: bool = False):
        self.year = year
        self.quarter = quarter
        self.sample_size = sample_size
        self.is_sample = is_sample
        self.run_id = None
        self.stats = {
            "rows_processed": 0,
            "rows_rejected": 0
        }

    def _init_run(self, session, url: str, file_hash: str) -> int:
        """Create or resume an ingestion run."""
        query = text("""
            INSERT INTO ingestion_runs 
            (quarter, download_url, file_hash, started_at, status, is_sample, sample_size)
            VALUES (:q, :url, :hash, NOW(), 'RUNNING', :is_sample, :sample)
            RETURNING id
        """)
        q_str = f"{self.year}Q{self.quarter}"
        res = session.execute(query, {
            "q": q_str, "url": url, "hash": file_hash, 
            "is_sample": self.is_sample, "sample": self.sample_size
        })
        session.commit()
        return res.scalar()

    def _mark_run_status(self, session, status: str, error_message: str = None):
        if not self.run_id:
            return
        query = text("""
            UPDATE ingestion_runs 
            SET status = :status, error_message = :err, completed_at = NOW(),
                rows_processed = :processed, rows_rejected = :rejected
            WHERE id = :rid
        """)
        session.execute(query, {
            "status": status, "err": error_message, 
            "processed": self.stats["rows_processed"],
            "rejected": self.stats["rows_rejected"],
            "rid": self.run_id
        })
        session.commit()

    def _load_chunk(self, df: pd.DataFrame, table_name: str):
        # Basic approach: push to sql with pandas
        # For production robustness, we use raw INSERT statements, but to_sql works well here.
        if df.empty:
            return
            
        with engine.begin() as conn:
            # We assume df has the exact columns mapped.
            # Append rows
            df.to_sql(table_name, con=conn, if_exists='append', index=False, method='multi', chunksize=1000)
            self.stats["rows_processed"] += len(df)

    def run(self, data_dir: Optional[Path] = None):
        start_time = time.time()
        session = get_session()
        
        try:
            # 1. Download
            download_meta = download_sec_nport(self.year, self.quarter, data_dir)
            url = f"https://www.sec.gov/files/dera/data/form-n-port-data-sets/{self.year}q{self.quarter}_nport.zip"
            
            # Check if this quarter was already processed
            q_str = f"{self.year}Q{self.quarter}"
            existing = session.execute(
                text("SELECT id, status FROM ingestion_runs WHERE quarter = :q AND status = 'COMPLETED'"),
                {"q": q_str}
            ).fetchone()
            
            if existing:
                logger.info("Quarter already ingested", quarter=q_str, run_id=existing.id)
                return
                
            self.run_id = self._init_run(session, url, download_meta["hash"])
            
            # 2. Extract & Parse
            parser = NPortParser(download_meta["path"])
            iterators = parser.extract_and_parse()
            
            # 3 & 4. Normalize & Load Submissions
            if "submission" in iterators:
                for chunk in iterators["submission"]:
                    norm_df = DataNormalizer.normalize_submission(chunk)
                    norm_df['ingestion_run_id'] = self.run_id
                    # Select only columns in DB
                    db_cols = ['accession_number', 'filing_date', 'period_of_report', 'filing_type', 'is_amendment', 'ingestion_run_id']
                    load_df = norm_df[[c for c in db_cols if c in norm_df.columns]]
                    val_res = Validator.pre_load_validation(load_df, 'submissions', ['accession_number'])
                    if val_res["passed"]:
                        self._load_chunk(load_df, 'submissions')
                    else:
                        self.stats["rows_rejected"] += len(load_df)
                        logger.warning("Validation failed", table="submissions", reason=val_res["reason"])

            # Extend similarly for registrants, series, funds... (skeleton for holdings below)
            if "holding" in iterators:
                holding_count = 0
                for chunk in iterators["holding"]:
                    norm_df = DataNormalizer.normalize_holding(chunk)
                    # We might need to map DB columns carefully
                    # This is just an illustrative representation for mapping
                    if self.is_sample and holding_count >= self.sample_size:
                        break
                    
                    self._load_chunk(norm_df, 'holdings')
                    holding_count += len(norm_df)
            
            # Post validation
            Validator.post_load_validation(session, self.run_id)
            
            self._mark_run_status(session, "COMPLETED")
            logger.info("Ingestion completed successfully", run_id=self.run_id, duration=time.time()-start_time)
            
        except Exception as e:
            logger.error("Ingestion failed", error=str(e))
            self._mark_run_status(session, "FAILED", error_message=str(e))
            raise e
        finally:
            session.close()

        return {
            "run_id": self.run_id,
            "duration": time.time() - start_time,
            "stats": self.stats
        }
