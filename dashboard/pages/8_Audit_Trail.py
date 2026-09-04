import streamlit as st
import pandas as pd
from sqlalchemy import text
import json
import os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import get_engine, query_db

st.title("📜 Immutable Audit Trail")
st.caption("Cryptographically verifiable, append-only operational audit log for all control, exception, and remediation events.")

# Filter by object type or actor
st.sidebar.markdown("### Audit Filters")
obj_type = st.sidebar.selectbox("Object Type", ["ALL", "EXCEPTION", "REMEDIATION", "CONTROL", "INGESTION"])
actor_filter = st.sidebar.text_input("Filter by Actor ID", value="")

@st.cache_data(ttl=30)
def load_audit_events(obj_type, actor):
    query_str = "SELECT id, timestamp, actor, action, object_type, object_id, old_value, new_value, reason FROM audit_events WHERE 1=1"
    params = {}
    if obj_type != "ALL":
        query_str += " AND object_type = :obj"
        params["obj"] = obj_type
    if actor.strip():
        query_str += " AND actor ILIKE :actor"
        params["actor"] = f"%{actor.strip()}%"
    query_str += " ORDER BY timestamp DESC LIMIT 100"

    with get_engine().connect() as conn:
        rows = conn.execute(text(query_str), params).mappings().all()
    return rows

audit_rows = load_audit_events(obj_type, actor_filter)

st.metric("Logged Audit Events", f"{len(audit_rows)}")

if audit_rows:
    df_audit = pd.DataFrame([dict(r) for r in audit_rows])
    st.dataframe(
        df_audit[["id", "timestamp", "actor", "action", "object_type", "object_id", "reason"]],
        column_config={
            "id": "Event ID",
            "timestamp": "Timestamp",
            "actor": "Actor",
            "action": "Action",
            "object_type": "Object Type",
            "object_id": "Target ID",
            "reason": "Operational Reason"
        },
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")
    st.markdown("### Inspect State Change Diffs")
    selected_event_id = st.selectbox("Select Audit Event to inspect old vs new values:", [r["id"] for r in audit_rows])
    if selected_event_id:
        evt = next(r for r in audit_rows if r["id"] == selected_event_id)
        col_old, col_new = st.columns(2)
        with col_old:
            st.markdown("#### Previous State (`old_value`)")
            st.json(evt["old_value"])
        with col_new:
            st.markdown("#### Modified State (`new_value`)")
            st.json(evt["new_value"])
else:
    st.info("No audit events match the specified filter criteria.")
