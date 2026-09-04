import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Control Monitoring")

st.markdown("### Control Health Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Total Controls", "24")
col2.metric("Average Pass Rate", "92%")
col3.metric("Failing Controls", "2")

st.markdown("### Filter Controls")
category = st.selectbox("Risk Category", ["All", "Market", "Credit", "Liquidity", "Operational"])

st.markdown("### Control Health Detail")
controls_data = pd.DataFrame({
    "Control": ["Limit Check", "Price Variance", "Stale Price", "Duration Limit"],
    "Execution Rate": ["100%", "98%", "100%", "100%"],
    "Pass Rate": ["95%", "80%", "99%", "100%"],
    "Exceptions": [5, 20, 1, 0],
    "Repeat Failures": [1, 5, 0, 0],
    "Effectiveness": ["High", "Medium", "High", "High"],
    "Status": ["🟢 GREEN", "🟡 AMBER", "🟢 GREEN", "🟢 GREEN"]
})
st.dataframe(controls_data, use_container_width=True)

st.markdown("### Control Effectiveness Trend")
trend_data = pd.DataFrame({
    "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
    "Effectiveness Score": [90, 88, 92, 85, 95]
})
fig = px.line(trend_data, x="Month", y="Effectiveness Score", title="Average Control Effectiveness Over Time")
st.plotly_chart(fig, use_container_width=True)
