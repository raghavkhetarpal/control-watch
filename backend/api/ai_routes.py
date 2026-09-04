"""
AI API routes and schema.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, text
from sqlalchemy.orm import declarative_base
from datetime import datetime
import structlog

from backend.ai.copilot import AIAssistant
from backend.ai.evidence import collect_fund_evidence

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])

Base = declarative_base()

class AIAnalysis(Base):
    """Database model for tracking AI analysis requests and responses."""
    __tablename__ = 'ai_analysis'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_type = Column(String, nullable=False)
    query = Column(String)
    context_summary = Column(String)
    evidence_hash = Column(String, nullable=False)
    evidence = Column(JSON, nullable=False)
    response = Column(String, nullable=False)
    provider = Column(String)
    model = Column(String)
    validation_status = Column(String, nullable=False)  # CHECK IN ('PENDING','VALIDATED','FLAGGED','REJECTED')
    validation_issues = Column(JSON)
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    requested_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class AIAnalyzeRequest(BaseModel):
    query: str
    context_type: str
    context_id: str

class AIAnalyzeResponse(BaseModel):
    analysis: str
    validation_status: str
    disclaimer: str = "This analysis is AI-generated and should be reviewed by an analyst."

# Mock session dependency
def get_db():
    yield None

@router.post("/analyze", response_model=AIAnalyzeResponse)
def analyze_endpoint(request: AIAnalyzeRequest, db = Depends(get_db)):
    """Analyze context using AI."""
    assistant = AIAssistant()
    
    # Collect evidence based on type
    if request.context_type == 'fund':
        evidence = collect_fund_evidence(db, request.context_id)
    else:
        evidence = {"context_id": request.context_id, "type": request.context_type}
        
    result = assistant.analyze(request.query, request.context_type, evidence)
    
    # In a real implementation, we would persist the analysis to the ai_analysis table here
    logger.info("ai_analysis_complete", status=result.validation_status)
    
    return AIAnalyzeResponse(
        analysis=result.response,
        validation_status=result.validation_status
    )
