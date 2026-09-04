"""Ingestion API routes."""
import structlog
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.models import IngestionRequest, IngestionResponse

logger = structlog.get_logger()

router = APIRouter()


@router.post("/run", response_model=IngestionResponse)
def run_ingestion(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger SEC N-PORT data ingestion."""
    try:
        from backend.ingestion.pipeline import run_pipeline

        result = run_pipeline(
            quarter=request.quarter,
            sample=request.sample,
            sample_size=request.sample_size,
        )
        return IngestionResponse(
            status="completed",
            quarter=request.quarter,
            rows_processed=result.get("rows_processed", 0),
            rows_rejected=result.get("rows_rejected", 0),
            duration_seconds=result.get("duration_seconds", 0),
            message=result.get("message", "Ingestion completed"),
        )
    except Exception as e:
        logger.error("ingestion_api_error", error=str(e))
        return IngestionResponse(
            status="failed",
            quarter=request.quarter,
            rows_processed=0,
            rows_rejected=0,
            duration_seconds=0,
            message=f"Ingestion failed: {str(e)}",
        )
