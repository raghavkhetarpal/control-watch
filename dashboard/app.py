import os
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(
    page_title="AWM ControlWatch",
    page_icon="🛡️",
    layout="wide"
)

@st.cache_resource
def get_engine():
    return create_engine(os.environ.get('DATABASE_URL', 'postgresql://awm:awm_password@localhost:5432/awm_controlwatch'))

def query_db(sql, params=None):
    with get_engine().connect() as conn:
        result = conn.execute(text(sql), params or {})
        return result.mappings().all()

st.sidebar.title("Navigation")
st.sidebar.info("Select a page above to navigate.")

st.title("🛡️ AWM ControlWatch")
st.markdown("""
Welcome to the AWM ControlWatch Dashboard. 
Use the sidebar to navigate through the various views including Executive Overview, Risk Analysis, Control Monitoring, and more.
""")

st.markdown("---")
st.caption("Educational/research implementation based on publicly available SEC data. Does NOT replicate Goldman Sachs proprietary systems.")
