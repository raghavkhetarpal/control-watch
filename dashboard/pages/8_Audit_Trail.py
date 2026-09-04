import streamlit as st
import pandas as pd

st.title("Audit Trail")

st.sidebar.markdown("### Filters")
object_type = st.sidebar.selectbox("Object Type", ["All", "Exception", "Remediation", "Control", "Fund"])
actor = st.sidebar.text_input("Actor (User/System)")
action = st.sidebar.selectbox("Action", ["All", "Create", "Update", "Delete", "Resolve"])

st.markdown("### Audit Events")

audit_data = pd.DataFrame({
    "Timestamp": ["2026-09-04 10:00:00", "2026-09-04 09:15:00", "2026-09-03 16:45:00"],
    "Actor": ["System", "Alice", "Bob"],
    "Action": ["Create", "Update", "Resolve"],
    "Object Type": ["Exception", "Remediation", "Exception"],
    "Object ID": ["EX-105", "REM-002", "EX-098"]
})

st.dataframe(audit_data, use_container_width=True)

st.markdown("### Event Details")
selected_event = st.selectbox("Select Event to View Diffs", ["None", "EX-105 Creation", "REM-002 Update"])

if selected_event != "None":
    with st.expander("Diff", expanded=True):
        st.markdown("**Old Value:**")
        st.json({"status": "Open", "assigned_to": None})
        st.markdown("**New Value:**")
        st.json({"status": "In Progress", "assigned_to": "Alice"})
