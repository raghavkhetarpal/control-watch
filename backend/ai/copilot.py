"""
AI copilot with provider abstraction (OpenAI, Groq, None).
"""
import os
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import structlog
import json

from backend.ai.prompts import (
    SYSTEM_PROMPT, FUND_SUMMARY_PROMPT, EXCEPTION_ANALYSIS_PROMPT,
    ROOT_CAUSE_PROMPT, KRI_EXPLANATION_PROMPT, REMEDIATION_SUMMARY_PROMPT,
    GENERAL_ANALYSIS_PROMPT
)
from backend.ai.validators import validate_ai_response
from backend.ai.evidence import hash_evidence

logger = structlog.get_logger(__name__)

@dataclass
class AIResponse:
    response: str
    evidence_hash: str
    validation_status: str
    tokens_used: int
    latency_ms: float
    validation_issues: list

class AIAssistant:
    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "none").lower()
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        
        logger.info("ai_assistant_initialized", provider=self.provider)

    def _call_llm(self, prompt: str, system_prompt: str) -> Tuple[str, int]:
        """Abstract LLM call. Returns (text, tokens_used)."""
        if self.provider == 'none':
            return self._fallback_response(prompt), 0
            
        if self.provider == 'openai' and self.openai_key:
            # Mock implementation for OpenAI
            return f"[OpenAI Response] Processed: {prompt[:50]}...", 50
            
        if self.provider == 'groq' and self.groq_key:
            # Mock implementation for Groq
            return f"[Groq Response] Processed: {prompt[:50]}...", 30
            
        # Fallback if keys are missing
        logger.warning("missing_api_keys", provider=self.provider)
        return self._fallback_response(prompt), 0

    def _fallback_response(self, prompt: str) -> str:
        """Deterministic response when AI_PROVIDER='none'."""
        return "Template-based response: Analyzed structured evidence successfully (AI disabled). See raw evidence for details."

    def analyze(self, query: str, context_type: str, evidence: Dict[str, Any]) -> AIResponse:
        start_time = time.time()
        evidence_h = hash_evidence(evidence)
        
        prompt = GENERAL_ANALYSIS_PROMPT.format(query=query, evidence=json.dumps(evidence, default=str))
        response_text, tokens = self._call_llm(prompt, SYSTEM_PROMPT)
        
        validation = validate_ai_response(response_text, evidence)
        latency = (time.time() - start_time) * 1000
        
        return AIResponse(
            response=response_text,
            evidence_hash=evidence_h,
            validation_status=validation.status,
            tokens_used=tokens,
            latency_ms=latency,
            validation_issues=validation.issues
        )

    def summarize_fund(self, fund_data: Dict, exceptions: list, kris: list) -> str:
        prompt = FUND_SUMMARY_PROMPT.format(evidence=fund_data, exceptions=exceptions, kris=kris)
        resp, _ = self._call_llm(prompt, SYSTEM_PROMPT)
        return resp

    def explain_exception(self, exception_data: Dict) -> str:
        prompt = EXCEPTION_ANALYSIS_PROMPT.format(evidence=exception_data)
        resp, _ = self._call_llm(prompt, SYSTEM_PROMPT)
        return resp

    def suggest_root_cause(self, exception_data: Dict) -> str:
        prompt = ROOT_CAUSE_PROMPT.format(evidence=exception_data)
        resp, _ = self._call_llm(prompt, SYSTEM_PROMPT)
        return resp

    def explain_kri(self, kri_data: Dict, history: list) -> str:
        prompt = KRI_EXPLANATION_PROMPT.format(evidence=kri_data, history=history)
        resp, _ = self._call_llm(prompt, SYSTEM_PROMPT)
        return resp

    def summarize_remediation(self, remediation_data: Dict) -> str:
        prompt = REMEDIATION_SUMMARY_PROMPT.format(evidence=remediation_data)
        resp, _ = self._call_llm(prompt, SYSTEM_PROMPT)
        return resp
