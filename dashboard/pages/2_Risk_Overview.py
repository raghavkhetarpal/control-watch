import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy import text
import os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import get_engine, query_db

st.title("📊 Risk Overview & Taxonomies")
st.caption("Illustrative analytical risk assessments derived from SEC N-PORT portfolio holdings.")

# 1. KRI Metric Status Distribution
@st.cache_data(ttl=30)
def load_risk_data():
    with get_engine().connect() as conn:
        sev_rows = conn.execute(text("SELECT severity, COUNT(*) as count FROM control_exceptions GROUP BY severity ORDER BY count DESC")).mappings().all()
        cat_rows = conn.execute(text("SELECT risk_category, COUNT(*) as count FROM control_exceptions GROUP BY risk_category ORDER BY count DESC")).mappings().all()
        fund_rows = conn.execute(text("""
            SELECT f.fund_name, COUNT(ce.id) as exception_count,
                   SUM(CASE WHEN ce.severity = 'HIGH' THEN 1 ELSE 0 END) as high_count,
                   SUM(CASE WHEN ce.severity = 'MEDIUM' THEN 1 ELSE 0 END) as med_count,
                   SUM(CASE WHEN ce.severity = 'LOW' THEN 1 ELSE 0 END) as low_count
            FROM control_exceptions ce
            JOIN funds f ON ce.fund_id = f.id
            GROUP BY f.fund_name
            ORDER BY exception_count DESC
            LIMIT 15
        """)).mappings().all()
    return sev_rows, cat_rows, fund_rows

sev_rows, cat_rows, fund_rows = load_risk_data()

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Risk Distribution by Severity")
    if sev_rows:
        df_sev = pd.DataFrame([dict(r) for r in sev_rows])
        color_map = {"CRITICAL": "#d9534f", "HIGH": "#f0ad4e", "MEDIUM": "#5bc0de", "LOW": "#5cb85c"}
        fig_sev = px.pie(
            df_sev, values="count", names="severity",
            color="severity", color_discrete_map=color_map,
            hole=0.4, title="Exceptions by Severity"
        )
        st.plotly_chart(fig_sev, use_container_width=True)
    else:
        st.info("No severity data available.")

with col2:
    st.markdown("### Exceptions by Risk Category")
    if cat_rows:
        df_cat = pd.DataFrame([dict(r) for r in cat_rows])
        fig_cat = px.bar(
            df_cat, x="risk_category", y="count",
            color="risk_category", title="Exception Count by Risk Category",
            labels={"risk_category": "Risk Category", "count": "Exceptions"}
        )
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("No risk category data available.")

st.markdown("---")

# 2. Risk by Fund Ranking
st.markdown("### Top Funds by Operational Risk Exceptions")
if fund_rows:
    df_funds = pd.DataFrame([dict(r) for r in fund_rows])
    st.dataframe(
        df_funds,
        column_config={
            "fund_name": "Fund Name",
            "exception_count": "Total Exceptions",
            "high_count": "High Severity",
            "med_count": "Medium Severity",
            "low_count": "Low Severity"
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No fund-level exception distributions available.")
