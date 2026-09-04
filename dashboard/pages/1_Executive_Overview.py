import streamlit as st
import pandas as pd
from sqlalchemy import text
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import get_engine, query_db

st.title("🛡️ Executive Overview")

# 1. Metric Cards
@st.cache_data(ttl=30)
def load_metrics():
    with get_engine().connect() as conn:
        total_funds = conn.execute(text("SELECT COUNT(*) FROM funds")).scalar() or 0
        total_holdings = conn.execute(text("SELECT COUNT(*) FROM holdings")).scalar() or 0
        open_exc = conn.execute(text("SELECT COUNT(*) FROM control_exceptions WHERE status != 'CLOSED'")).scalar() or 0
        crit_exc = conn.execute(text("SELECT COUNT(*) FROM control_exceptions WHERE severity = 'CRITICAL'")).scalar() or 0
        overdue_rem = conn.execute(text("SELECT COUNT(*) FROM remediation_items WHERE due_date < CURRENT_DATE AND status NOT IN ('COMPLETED', 'VALIDATED', 'CLOSED')")).scalar() or 0
        return total_funds, total_holdings, open_exc, crit_exc, overdue_rem

funds_cnt, holdings_cnt, open_cnt, crit_cnt, overdue_cnt = load_metrics()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Funds", f"{funds_cnt:,}")
col2.metric("Holdings Ingested", f"{holdings_cnt:,}")
col3.metric("Open Exceptions", f"{open_cnt:,}")
col4.metric("Critical Exceptions", f"{crit_cnt:,}")
col5.metric("Overdue Remediation", f"{overdue_cnt:,}")

st.markdown("---")

# 2. Overall Risk Status
st.markdown("### Overall Risk Status")
if crit_cnt > 0:
    st.error(f"🔴 **CRITICAL RISK** — {crit_cnt} critical exceptions require immediate operational intervention.")
elif open_cnt > 100:
    st.warning(f"🟡 **AMBER RISK** — {open_cnt:,} operational exceptions detected across portfolio controls. Active remediation required.")
else:
    st.success("🟢 **LOW RISK** — Portfolio controls operating within normal tolerances.")
st.caption("Illustrative analytical threshold for operational risk monitoring.")

# 3. KRI Summary Table
st.markdown("### Key Risk Indicators (KRIs)")
@st.cache_data(ttl=30)
def load_kris():
    rows = query_db("""
        SELECT kri_id, name, value, unit, status, trend, threshold_green, threshold_amber, threshold_red
        FROM kri_snapshots
        WHERE period_date = (SELECT MAX(period_date) FROM kri_snapshots)
        ORDER BY kri_id
    """)
    return rows

kri_rows = load_kris()
if kri_rows:
    df_kri = pd.DataFrame([dict(r) for r in kri_rows])
    df_kri["Status"] = df_kri["status"].apply(lambda s: "🟢 GREEN" if s == "GREEN" else ("🟡 AMBER" if s == "AMBER" else "🔴 RED"))
    df_kri["Value"] = df_kri.apply(lambda r: f"{float(r['value']):.2f} {r['unit']}", axis=1)
    df_kri["Thresholds"] = df_kri.apply(lambda r: f"G: <{r['threshold_green']} | A: <{r['threshold_amber']} | R: >{r['threshold_red']}", axis=1)
    st.dataframe(
        df_kri[["kri_id", "name", "Value", "Status", "trend", "Thresholds"]],
        column_config={
            "kri_id": "KRI ID",
            "name": "Indicator Name",
            "Value": "Current Value",
            "Status": "RAG Status",
            "trend": "Trend",
            "Thresholds": "Illustrative Limits"
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No KRI snapshot data available. Run controls to generate metrics.")

# 4. Recent Exceptions Table
st.markdown("### Recent Detected Exceptions (Top 10)")
@st.cache_data(ttl=30)
def load_recent_exceptions():
    rows = query_db("""
        SELECT ce.id, ce.control_id, f.fund_name, ce.severity, ce.status, ce.description, ce.detected_at
        FROM control_exceptions ce
        LEFT JOIN funds f ON ce.fund_id = f.id
        ORDER BY ce.id DESC
        LIMIT 10
    """)
    return rows

recent_exc = load_recent_exceptions()
if recent_exc:
    df_exc = pd.DataFrame([dict(r) for r in recent_exc])
    st.dataframe(
        df_exc[["id", "control_id", "severity", "status", "description", "fund_name"]],
        column_config={
            "id": "ID",
            "control_id": "Control",
            "severity": "Severity",
            "status": "Status",
            "description": "Description",
            "fund_name": "Fund"
        },
        use_container_width=True,
        hide_index=True
    )

st.markdown("---")
st.caption("Data Lineage: SEC Form N-PORT Bulk Datasets (2025Q3) → Chunked Ingestion → Normalized Database Schema → 16 Deterministic Controls → KRI Engine → Executive Dashboard.")
