import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy import text
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import get_engine

st.title("Risk Overview")

# Mock data for KRI trend
dates = pd.date_range(start="2023-01-01", periods=10, freq="M")
kri_data = pd.DataFrame({
    "Date": dates,
    "Concentration Risk": [10, 12, 11, 15, 14, 13, 16, 18, 17, 15],
    "Liquidity Risk": [5, 6, 5, 4, 5, 7, 6, 8, 7, 9]
})

fig = px.line(kri_data, x="Date", y=["Concentration Risk", "Liquidity Risk"], title="KRI Trend (Derived)")
st.plotly_chart(fig, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    risk_dist = pd.DataFrame({"Severity": ["High", "Medium", "Low"], "Count": [5, 15, 30]})
    fig2 = px.pie(risk_dist, values="Count", names="Severity", title="Risk Distribution by Severity")
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    risk_cat = pd.DataFrame({"Category": ["Market", "Credit", "Liquidity", "Operational"], "Count": [20, 10, 15, 5]})
    fig3 = px.bar(risk_cat, x="Category", y="Count", title="Risk by Category")
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("### Risk by Fund Ranking")
st.dataframe(pd.DataFrame({
    "Fund": ["Fund A", "Fund B", "Fund C"],
    "Risk Score": [85, 65, 45],
    "Status": ["🔴 High", "🟡 Medium", "🟢 Low"]
}))
