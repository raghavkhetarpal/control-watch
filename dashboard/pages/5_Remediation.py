import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Remediation Tracking")

col1, col2, col3 = st.columns(3)
col1.metric("Mean Time to Resolve (MTTR)", "4.2 Days")
col2.metric("Repeat Issues", "12")
col3.metric("Issues Due Soon", "3")

tab1, tab2, tab3 = st.tabs(["Open Issues", "Overdue", "Due Soon"])

with tab1:
    st.dataframe(pd.DataFrame({
        "Issue ID": ["REM-001", "REM-002"],
        "Title": ["Update Valuation Model", "Review Concentration Limits"],
        "Owner": ["Alice", "Bob"],
        "Due Date": ["2026-09-10", "2026-09-15"]
    }))

with tab2:
    st.info("No overdue issues at this time.")

with tab3:
    st.dataframe(pd.DataFrame({
        "Issue ID": ["REM-003"],
        "Title": ["Quarterly Review",],
        "Owner": ["Charlie"],
        "Due Date": ["2026-09-05"]
    }))

st.markdown("### Owner Workload")
workload = pd.DataFrame({
    "Owner": ["Alice", "Bob", "Charlie", "Diana"],
    "Tasks": [5, 2, 8, 1]
})
fig = px.bar(workload, x="Owner", y="Tasks", title="Open Issues by Owner")
st.plotly_chart(fig, use_container_width=True)

st.markdown("### Create New Remediation")
with st.form("new_remediation"):
    title = st.text_input("Title")
    owner = st.selectbox("Owner", ["Alice", "Bob", "Charlie", "Diana"])
    due_date = st.date_input("Due Date")
    description = st.text_area("Description")
    submitted = st.form_submit_button("Create")
    if submitted:
        st.success("Remediation created successfully!")
