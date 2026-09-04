import zipfile
import tempfile
from pathlib import Path
from typing import Iterator, Dict, Any, List
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

class NPortParser:
    def __init__(self, zip_path: Path):
        self.zip_path = zip_path
        self.stats = {
            "rows_parsed": 0,
            "rows_skipped": 0,
            "files_processed": []
        }
    
    def get_stats(self) -> Dict[str, Any]:
        return self.stats

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to lowercase and snake_case."""
        df.columns = [col.strip().lower() for col in df.columns]
        return df

    def parse_tsv(self, filepath: Path, chunksize: int = 10000) -> Iterator[pd.DataFrame]:
        """Parse a TSV file in chunks, handling encoding and bad lines."""
        logger.info("Parsing TSV", file=str(filepath))
        try:
            chunks = pd.read_csv(
                filepath, 
                sep='\t', 
                chunksize=chunksize, 
                encoding='utf-8',
                on_bad_lines='warn',
                low_memory=False
            )
        except UnicodeDecodeError:
            logger.warning("UTF-8 decoding failed, falling back to latin-1", file=str(filepath))
            chunks = pd.read_csv(
                filepath, 
                sep='\t', 
                chunksize=chunksize, 
                encoding='latin-1',
                on_bad_lines='warn',
                low_memory=False
            )
            
        for chunk in chunks:
            self.stats["rows_parsed"] += len(chunk)
            chunk = self._normalize_columns(chunk)
            yield chunk

    def extract_and_parse(self) -> Dict[str, Iterator[pd.DataFrame]]:
        """
        Extract the zip file to a temporary directory and return iterators 
        for each relevant TSV file.
        """
        logger.info("Extracting ZIP", path=str(self.zip_path))
        temp_dir = tempfile.mkdtemp(prefix="nport_")
        target_files = {
            "SUBMISSION.tsv": "submission",
            "FUND_REPORTED_INFO.tsv": "fund_info",
            "FUND_REPORTED_HOLDING.tsv": "holding",
            "REGISTRANT.tsv": "registrant",
            "SERIES.tsv": "series"
        }
        
        extracted_paths = {}
        
        with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.filename in target_files:
                    extracted_path = zip_ref.extract(file_info, temp_dir)
                    key = target_files[file_info.filename]
                    extracted_paths[key] = Path(extracted_path)
                    self.stats["files_processed"].append(file_info.filename)
                    logger.info("Extracted file", filename=file_info.filename)
                    
        return {
            key: self.parse_tsv(path) for key, path in extracted_paths.items()
        }
