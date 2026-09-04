import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import date, timedelta
import os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import get_engine, query_db
from backend.exceptions.remediation import create_remediation, update_remediation_status, validate_remediation

st.title("🛠️ Remediation Tracking & Governance")
st.caption("Action plan tracking, owner assignment, due dates, and four-eyes independent validation.")

@st.cache_data(ttl=30)
def load_remediations():
    with get_engine().connect() as conn:
        items = conn.execute(text("""
            SELECT r.id, r.exception_id, r.owner, r.action_description, r.due_date,
                   r.priority, r.status, r.validation_result, r.validated_by, r.completed_at,
                   ce.control_id, ce.severity
            FROM remediation_items r
            JOIN control_exceptions ce ON r.exception_id = ce.id
            ORDER BY r.id DESC
        """)).mappings().all()
    return items

items = load_remediations()

col1, col2, col3 = st.columns(3)
col1.metric("Total Remediation Actions", f"{len(items)}")
open_actions = sum(1 for i in items if i["status"] in ["OPEN", "IN_PROGRESS"])
col2.metric("Active Actions", f"{open_actions}")
validated_actions = sum(1 for i in items if i["status"] == "VALIDATED")
col3.metric("Validated / Closed", f"{validated_actions}")

st.markdown("---")

tab1, tab2 = st.tabs(["Active & Completed Actions", "Create New Remediation"])

with tab1:
    if items:
        df_rem = pd.DataFrame([dict(i) for i in items])
        st.dataframe(
            df_rem[["id", "exception_id", "control_id", "priority", "status", "owner", "due_date", "action_description"]],
            column_config={
                "id": "Action ID",
                "exception_id": "Exception ID",
                "control_id": "Control",
                "priority": "Priority",
                "status": "Remediation Status",
                "owner": "Owner",
                "due_date": "Due Date",
                "action_description": "Planned Corrective Action"
            },
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Update Action Lifecycle")
        action_id = st.selectbox("Select Action to Update:", [i["id"] for i in items])
        if action_id:
            sel = next(i for i in items if i["id"] == action_id)
            st.markdown(f"**Current Status:** `{sel['status']}` | **Owner:** `{sel['owner']}`")
            col_a, col_b = st.columns(2)
            actor = col_a.text_input("Operator Actor ID", value="remediation_mgr")
            notes = col_b.text_input("Operational Notes", value="Desk review completed")

            if sel["status"] == "OPEN":
                if st.button("Start Execution (IN_PROGRESS)"):
                    with get_engine().connect() as conn:
                        update_remediation_status(conn, action_id, "IN_PROGRESS", actor, notes)
                        conn.commit()
                    st.success("Remediation is now IN_PROGRESS.")
                    st.rerun()

            elif sel["status"] == "IN_PROGRESS":
                if st.button("Complete Action (Pending Validation)"):
                    with get_engine().connect() as conn:
                        update_remediation_status(conn, action_id, "COMPLETED", actor, notes)
                        conn.commit()
                    st.success("Action marked COMPLETED. Ready for independent risk validation.")
                    st.rerun()

            elif sel["status"] == "COMPLETED":
                val_result = st.selectbox("Validation Assessment", ["PASS", "FAIL"])
                if st.button("Submit Independent Validation"):
                    with get_engine().connect() as conn:
                        validate_remediation(conn, action_id, val_result, actor)
                        conn.commit()
                    st.success(f"Validation recorded with result: {val_result}.")
                    st.rerun()
    else:
        st.info("No remediation records exist yet.")

with tab2:
    st.markdown("### Plan Remediation for Open Exception")
    with st.form("create_rem_form"):
        # Load eligible exceptions
        with get_engine().connect() as conn:
            cand_rows = conn.execute(text("SELECT id, control_id, description FROM control_exceptions WHERE status IN ('DETECTED', 'TRIAGED', 'INVESTIGATING') LIMIT 50")).fetchall()
        
        cand_options = {f"Exc #{r[0]} ({r[1]}): {r[2][:60]}...": r[0] for r in cand_rows}
        if cand_options:
            sel_exc_label = st.selectbox("Select Exception to Remediate", list(cand_options.keys()))
            exc_target_id = cand_options[sel_exc_label]
            owner_val = st.text_input("Remediation Owner", value="portfolio_ops_lead")
            action_desc = st.text_area("Corrective Action Description", value="Review position limits with portfolio manager and adjust sizing if necessary.")
            priority_val = st.selectbox("Priority", ["HIGH", "MEDIUM", "LOW", "CRITICAL"], index=0)
            due_date_val = st.date_input("Target Completion Date", value=date.today() + timedelta(days=14))
            submit_btn = st.form_submit_button("Submit Remediation Plan")

            if submit_btn:
                with get_engine().connect() as conn:
                    new_id = create_remediation(
                        conn, str(exc_target_id), owner_val, action_desc, due_date_val, priority_val, "dashboard_operator"
                    )
                    conn.commit()
                st.success(f"Remediation item #{new_id} created successfully!")
                st.rerun()
        else:
            st.info("No open unassigned exceptions eligible for new remediation.")
