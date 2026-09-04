import streamlit as st
import os, sys
from sqlalchemy import text

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import get_engine, query_db
from backend.ai.copilot import AIAssistant
from backend.ai.evidence import collect_fund_evidence, collect_exception_evidence

st.title("🤖 AI Risk & Control Copilot")
st.caption("Evidence-grounded analytical copilot with strict prompt-injection defenses and deterministic source verification.")
st.info("⚠️ Disclaimer: Educational/research assistant. AI responses are strictly grounded in structured database evidence and do NOT determine authoritative risk scores or regulatory compliance.")

assistant = AIAssistant()

# Pre-built query triggers
col1, col2, col3 = st.columns(3)
if col1.button("Summarize Fund Concentration"):
    st.session_state.trigger_query = ("fund", "Summarize concentration and asset allocation risks")
if col2.button("Investigate Critical Exceptions"):
    st.session_state.trigger_query = ("exception", "Explain the highest severity exception and recommend remediation")
if col3.button("Explain KRI-001 Exposure"):
    st.session_state.trigger_query = ("kri", "Explain the concentration exposure KRI threshold breach")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "evidence" in msg:
            with st.expander("Grounded Evidence JSON"):
                st.json(msg["evidence"])

user_prompt = st.chat_input("Ask a question regarding funds, controls, or exceptions...")

trigger = getattr(st.session_state, "trigger_query", None)
if trigger:
    del st.session_state.trigger_query
    q_type, q_text = trigger
    user_prompt = q_text

if user_prompt:
    st.session_state.chat_history.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Gather real evidence from DB
    with get_engine().connect() as conn:
        sample_fund = conn.execute(text("SELECT id, fund_name FROM funds WHERE id IN (SELECT fund_id FROM holdings LIMIT 1)")).mappings().first()
        sample_exc = conn.execute(text("SELECT id, control_id, description, severity, evidence FROM control_exceptions WHERE severity = 'HIGH' LIMIT 1")).mappings().first()
        
        evidence = {
            "query": user_prompt,
            "sample_fund": dict(sample_fund) if sample_fund else {},
            "top_exception": dict(sample_exc) if sample_exc else {},
            "authoritative_source": "PostgreSQL 16 / SEC Form N-PORT Q3 2025"
        }

    response = assistant.analyze(user_prompt, "fund", evidence)
    
    with st.chat_message("assistant"):
        st.markdown(response.response)
        st.caption(f"Validation Status: **{response.validation_status}** | Latency: {response.latency_ms:.1f}ms")
        with st.expander("Grounded Evidence JSON"):
            st.json(evidence)

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": response.response,
        "evidence": evidence
    })
