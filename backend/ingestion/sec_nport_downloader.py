import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import structlog
import os

logger = structlog.get_logger(__name__)

SEC_URL_PATTERN = "https://www.sec.gov/files/dera/data/form-n-port-data-sets/{year}q{quarter}_nport.zip"
DEFAULT_DATA_DIR = Path(os.getenv("SEC_DATA_DIR", "./data"))

class DownloaderError(Exception):
    pass

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(httpx.RequestError),
    reraise=True
)
def download_file_with_retry(url: str, output_path: Path, client: httpx.Client) -> None:
    """Download file with exponential backoff on failure."""
    logger.info("Starting download", url=url, dest=str(output_path))
    with client.stream("GET", url) as response:
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)

def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def download_sec_nport(year: int, quarter: int, data_dir: Optional[Path] = None, client_kwargs: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Download SEC N-PORT zip file for the specified year and quarter.
    """
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    
    url = SEC_URL_PATTERN.format(year=year, quarter=quarter)
    filename = f"{year}q{quarter}_nport.zip"
    output_path = data_dir / filename
    
    start_time = time.time()
    
    headers = {
        "User-Agent": "AWM_ControlWatch_Bot/1.0 (Contact: admin@example.com)"
    }
    
    kwargs = client_kwargs or {}
    kwargs.setdefault("headers", headers)
    kwargs.setdefault("timeout", 60.0)
    kwargs.setdefault("follow_redirects", True)
    
    try:
        with httpx.Client(**kwargs) as client:
            head_resp = client.head(url)
            head_resp.raise_for_status()
            
            # Simple check to skip re-download if file already exists with same size
            remote_size = int(head_resp.headers.get("Content-Length", 0))
            if output_path.exists() and output_path.stat().st_size == remote_size and remote_size > 0:
                logger.info("File already exists with matching size. Skipping download.", path=str(output_path))
            else:
                download_file_with_retry(url, output_path, client)
                
    except Exception as e:
        logger.error("Download failed", url=url, error=str(e))
        raise DownloaderError(f"Failed to download {url}: {e}")
        
    duration = time.time() - start_time
    file_size = output_path.stat().st_size
    file_hash = calculate_sha256(output_path)
    
    logger.info("Download complete", path=str(output_path), size=file_size, hash=file_hash, duration=duration)
    
    return {
        "path": output_path,
        "size": file_size,
        "hash": file_hash,
        "duration": duration,
        "year": year,
        "quarter": quarter
    }
