import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
import os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import get_engine, query_db

st.title("⚙️ Control Health & Effectiveness Monitoring")
st.caption("Execution statistics across all 16 deterministic controls evaluated against SEC N-PORT portfolio filings.")

# 1. KCI High-level metrics
@st.cache_data(ttl=30)
def load_control_stats():
    with get_engine().connect() as conn:
        kcis = conn.execute(text("SELECT kci_id, name, value, unit, status FROM kci_snapshots WHERE period_date = (SELECT MAX(period_date) FROM kci_snapshots)")).mappings().all()
        controls = conn.execute(text("""
            SELECT ce.control_id, cd.name, cd.risk_category, ce.status,
                   ce.records_scanned, ce.exceptions_found, ce.pass_rate, ce.duration_ms
            FROM control_executions ce
            JOIN control_definitions cd ON ce.control_id = cd.control_id
            WHERE ce.period_date = (SELECT MAX(period_date) FROM control_executions)
            ORDER BY ce.control_id
        """)).mappings().all()
    return kcis, controls

kcis, controls = load_control_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Controls", f"{len(controls)} / 16")
avg_pass = sum(float(c["pass_rate"] or 0) for c in controls) / len(controls) if controls else 0.0
col2.metric("Mean Pass Rate", f"{avg_pass:.1f}%")
total_scanned = sum(int(c["records_scanned"] or 0) for c in controls)
col3.metric("Records Evaluated", f"{total_scanned:,}")
total_exceptions = sum(int(c["exceptions_found"] or 0) for c in controls)
col4.metric("Exceptions Generated", f"{total_exceptions:,}")

st.markdown("---")

# 2. Control Execution Detail Table
st.markdown("### Control Execution Results")
if controls:
    df_ctrl = pd.DataFrame([dict(c) for c in controls])
    df_ctrl["Status Badge"] = df_ctrl["pass_rate"].apply(
        lambda p: "🟢 PASS" if p == 100.0 else ("🟡 ATTENTION" if p >= 90.0 else "🔴 ACTION NEEDED")
    )
    df_ctrl["Pass Rate"] = df_ctrl["pass_rate"].apply(lambda p: f"{float(p):.2f}%")
    df_ctrl["Duration"] = df_ctrl["duration_ms"].apply(lambda d: f"{int(d)} ms")

    st.dataframe(
        df_ctrl[["control_id", "name", "risk_category", "records_scanned", "exceptions_found", "Pass Rate", "Duration", "Status Badge"]],
        column_config={
            "control_id": "Control ID",
            "name": "Control Name",
            "risk_category": "Risk Category",
            "records_scanned": "Records Scanned",
            "exceptions_found": "Exceptions Found",
            "Pass Rate": "Pass Rate",
            "Duration": "Runtime",
            "Status Badge": "Operational Status"
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No control execution records found for the latest period.")

st.markdown("---")

# 3. KCI Summary Cards
st.markdown("### Key Control Indicators (KCIs)")
if kcis:
    df_kci = pd.DataFrame([dict(k) for k in kcis])
    df_kci["Status"] = df_kci["status"].apply(lambda s: "🟢 GREEN" if s == "GREEN" else ("🟡 AMBER" if s == "AMBER" else "🔴 RED"))
    df_kci["Value"] = df_kci.apply(lambda r: f"{float(r['value']):.2f} {r['unit']}", axis=1)
    st.dataframe(
        df_kci[["kci_id", "name", "Value", "Status"]],
        column_config={
            "kci_id": "KCI ID",
            "name": "Indicator Name",
            "Value": "Measured Value",
            "Status": "Status"
        },
        use_container_width=True,
        hide_index=True
    )
