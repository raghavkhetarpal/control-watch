import streamlit as st
import pandas as pd

st.title("Exception Management")

st.sidebar.markdown("### Filters")
severity = st.sidebar.multiselect("Severity", ["Critical", "High", "Medium", "Low"])
status = st.sidebar.multiselect("Status", ["Open", "In Progress", "Resolved"])
fund = st.sidebar.multiselect("Fund", ["Fund A", "Fund B", "Fund C"])

st.markdown("### Active Exceptions")

exceptions_data = pd.DataFrame({
    "ID": ["EX-101", "EX-102", "EX-103"],
    "Fund": ["Fund A", "Fund B", "Fund A"],
    "Control": ["Limit Check", "Price Variance", "Duration Limit"],
    "Severity": ["High", "Medium", "Low"],
    "Status": ["Open", "In Progress", "Open"],
    "Age (Days)": [2, 5, 1]
})

st.dataframe(exceptions_data, use_container_width=True, hide_index=True)

st.markdown("### Exception Detail")
selected_ex = st.selectbox("Select Exception ID to view details", ["None", "EX-101", "EX-102", "EX-103"])

if selected_ex != "None":
    with st.expander(f"Details for {selected_ex}", expanded=True):
        st.json({"evidence": "Limit exceeded by 5%", "threshold": "10%", "actual": "15%"})
        st.markdown("**Audit Trail**")
        st.text("2026-09-01: Exception triggered\n2026-09-02: Assigned to analyst")
        
        col1, col2 = st.columns(2)
        with col1:
            st.button("Assign to Me")
        with col2:
            st.button("Update Status to Resolved")
