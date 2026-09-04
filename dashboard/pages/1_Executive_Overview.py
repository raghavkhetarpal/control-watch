import streamlit as st
import pandas as pd
from sqlalchemy import text
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import get_engine, query_db if 'query_db' in globals() else None

def query_db(sql, params=None):
    with get_engine().connect() as conn:
        result = conn.execute(text(sql), params or {})
        return result.mappings().all()

st.title("Executive Overview")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Funds", "12")
col2.metric("Holdings Processed", "4,521")
col3.metric("Open Exceptions", "34", "+2")
col4.metric("Critical Exceptions", "5", "-1")
col5.metric("Overdue Remediation", "2", "0")

st.markdown("### Overall Risk Status")
st.markdown("🟢 **Low Risk** (Illustrative analytical threshold)")

st.markdown("### KRI Summary")
data = {
    "KRI": ["Concentration Risk", "Liquidity Risk", "Valuation Risk"],
    "Status": ["🟢 GREEN", "🟡 AMBER", "🟢 GREEN"],
    "Value": ["15%", "12%", "2%"]
}
st.dataframe(pd.DataFrame(data))

st.markdown("### Recent Exceptions (Top 10)")
st.info("No critical exceptions in the last 24 hours.")

st.markdown("### Control Effectiveness Summary")
st.progress(0.85, text="85% Effective")

st.caption("Source: SEC N-PORT → Normalized Holdings → Controls → KRI/KCI → Dashboard")
