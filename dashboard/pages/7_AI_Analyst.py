import streamlit as st

st.title("AI Analyst Copilot 🤖")
st.caption("Educational/research AI analyst. Does NOT use Goldman Sachs proprietary models.")

st.markdown("### Quick Queries")
col1, col2, col3, col4 = st.columns(4)
if col1.button("Summarize Fund"):
    st.session_state.chat_input = "Please summarize the risk profile of Fund A."
if col2.button("Explain KRI"):
    st.session_state.chat_input = "Explain the recent spike in Liquidity Risk."
if col3.button("Priority Exceptions"):
    st.session_state.chat_input = "What are the top 3 priority exceptions right now?"
if col4.button("Remediation Status"):
    st.session_state.chat_input = "Give me a summary of overdue remediations."

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "evidence" in msg:
            with st.expander("View Evidence"):
                st.json(msg["evidence"])

prompt = st.chat_input("Ask the AI Analyst...")
if prompt or st.session_state.get("chat_input"):
    actual_prompt = prompt or st.session_state.chat_input
    if "chat_input" in st.session_state:
        del st.session_state.chat_input
        
    st.session_state.messages.append({"role": "user", "content": actual_prompt})
    with st.chat_message("user"):
        st.markdown(actual_prompt)
        
    with st.chat_message("assistant"):
        response = f"I am a simulated AI Analyst. You asked: '{actual_prompt}'. In a full implementation, I would analyze the database and SEC data to answer this."
        st.markdown(response)
        with st.expander("View Evidence"):
            st.json({"source": "Mock Data", "confidence": 0.95})
        st.session_state.messages.append({"role": "assistant", "content": response, "evidence": {"source": "Mock Data"}})
