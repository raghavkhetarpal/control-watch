import streamlit as st
import pandas as pd
from sqlalchemy import text
import json
import os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app import get_engine, query_db
from backend.exceptions.manager import transition_exception, assign_exception

st.title("🚨 Exception Management & Triage")
st.caption("Investigate, triage, assign, and remediate operational and data exceptions detected across funds.")

# 1. Sidebar Filters
st.sidebar.markdown("### Filter Exceptions")
taxonomy_filter = st.sidebar.multiselect(
    "Exception Taxonomy",
    ["ANALYTICAL_EXCEPTION", "DATA_QUALITY_EXCEPTION", "DATA_AVAILABILITY"],
    default=["ANALYTICAL_EXCEPTION", "DATA_QUALITY_EXCEPTION", "DATA_AVAILABILITY"]
)
severity_filter = st.sidebar.multiselect("Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"], default=["CRITICAL", "HIGH", "MEDIUM", "LOW"])
status_filter = st.sidebar.multiselect("Status", ["DETECTED", "TRIAGED", "ASSIGNED", "INVESTIGATING", "REMEDIATION_PLANNED", "REMEDIATION_IN_PROGRESS", "VALIDATION", "CLOSED"], default=["DETECTED", "TRIAGED", "ASSIGNED", "INVESTIGATING", "REMEDIATION_PLANNED", "REMEDIATION_IN_PROGRESS", "VALIDATION"])

@st.cache_data(ttl=30)
def load_exceptions(taxonomies, severities, statuses):
    if not severities or not statuses or not taxonomies:
        return []
    with get_engine().connect() as conn:
        rows = conn.execute(
            text("""
                SELECT ce.id, ce.control_id, ce.severity, ce.risk_level, ce.status, ce.risk_category,
                       COALESCE(ce.evidence->>'exception_type', 'ANALYTICAL_EXCEPTION') as exception_type,
                       f.fund_name, ce.description, ce.detected_at, ce.evidence
                FROM control_exceptions ce
                LEFT JOIN funds f ON ce.fund_id = f.id
                WHERE ce.severity = ANY(:sevs)
                  AND ce.status = ANY(:stats)
                  AND COALESCE(ce.evidence->>'exception_type', 'ANALYTICAL_EXCEPTION') = ANY(:taxes)
                ORDER BY ce.id DESC
                LIMIT 100
            """),
            {"sevs": list(severities), "stats": list(statuses), "taxes": list(taxonomies)}
        ).mappings().all()
    return rows

exceptions = load_exceptions(tuple(taxonomy_filter), tuple(severity_filter), tuple(status_filter))

st.markdown(f"### Active Exceptions ({len(exceptions)} displayed)")
if exceptions:
    df_exc = pd.DataFrame([dict(e) for e in exceptions])
    st.dataframe(
        df_exc[["id", "control_id", "exception_type", "severity", "risk_level", "status", "risk_category", "fund_name", "description"]],
        column_config={
            "id": "Exception ID",
            "control_id": "Control",
            "exception_type": "Taxonomy Type",
            "severity": "Severity",
            "risk_level": "Risk Level",
            "status": "Lifecycle Status",
            "risk_category": "Category",
            "fund_name": "Fund Name",
            "description": "Finding Description"
        },
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")
    st.markdown("### Exception Deep Dive & Evidence Investigation")
    selected_id = st.selectbox("Select Exception ID to inspect evidence:", [e["id"] for e in exceptions])

    if selected_id:
        selected_row = next((e for e in exceptions if e["id"] == selected_id), None)
        if selected_row:
            col_l, col_r = st.columns([2, 1])
            with col_l:
                st.markdown(f"**Control:** `{selected_row['control_id']}` | **Severity:** `{selected_row['severity']}` | **Status:** `{selected_row['status']}`")
                st.markdown(f"**Fund:** {selected_row['fund_name'] or 'N/A'}")
                st.markdown(f"**Description:** {selected_row['description']}")
                st.markdown("#### Structured Evidence JSON")
                st.json(selected_row["evidence"])

            with col_r:
                st.markdown("#### Operational Actions")
                action_user = st.text_input("Analyst / Reviewer ID", value="analyst_ops")
                
                if selected_row["status"] == "DETECTED":
                    if st.button("Mark as TRIAGED"):
                        with get_engine().connect() as conn:
                            transition_exception(conn, selected_row["id"], "TRIAGED", action_user, "Triaged via dashboard")
                            conn.commit()
                        st.success("Exception moved to TRIAGED. Refresh to update.")
                        st.rerun()

                elif selected_row["status"] == "TRIAGED":
                    assigned_to = st.text_input("Assignee Name", value="portfolio_risk_desk")
                    if st.button("Assign Exception"):
                        with get_engine().connect() as conn:
                            assign_exception(conn, selected_row["id"], assigned_to, action_user)
                            conn.commit()
                        st.success("Exception assigned. Refresh to update.")
                        st.rerun()

                elif selected_row["status"] == "ASSIGNED":
                    if st.button("Begin Investigation"):
                        with get_engine().connect() as conn:
                            transition_exception(conn, selected_row["id"], "INVESTIGATING", action_user, "Investigation initiated")
                            conn.commit()
                        st.success("Exception moved to INVESTIGATING.")
                        st.rerun()

                # View Audit Events for this exception
                with get_engine().connect() as conn:
                    audit_rows = conn.execute(
                        text("SELECT timestamp, actor, action, reason FROM audit_events WHERE object_type = 'EXCEPTION' AND object_id = :oid ORDER BY timestamp DESC"),
                        {"oid": str(selected_id)}
                    ).mappings().all()
                if audit_rows:
                    st.markdown("#### Audit Trail")
                    for a in audit_rows:
                        st.caption(f"⏱️ `{a['timestamp']}` — **{a['actor']}** ({a['action']}): {a['reason'] or 'No reason provided'}")

else:
    st.info("No exceptions match the selected filter criteria.")
