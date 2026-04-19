

import streamlit as st
import requests
import os
import json

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Travel Agent Pro", layout="wide")

# UI State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

# Sidebar with "Developer Mode"
with st.sidebar:
    st.title("⚙️ Admin Panel")
    dev_mode = st.toggle("Enable Developer Tracing", value=True)
    st.info("Tracing shows the 'Inner Monologue' of the AI Agent.")
    
    if st.button("Clear Cache"):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.markdown("""
    **Example Queries:**
    - "Find me flights from London to Paris for tomorrow."
    - "What's the weather in Tokyo?"
    - "I'm in London, show me flights to Berlin this week and check the weather there."
    """)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Chat")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Checking flights & weather..."):
                r = requests.post(
                    f"{BACKEND_URL}/chat",
                    json={"message": prompt, "session_id": st.session_state.session_id},
                    timeout=60
                )
                # (optional but recommended) handle errors cleanly
                data = r.json()
                st.write(data["response"])
                st.session_state.messages.append({"role": "assistant", "content": data["response"]})
                st.rerun()

with col2:
    if dev_mode:
        st.subheader("🕵️ Agent Traces")
        try:
            trace_res = requests.get(f"{BACKEND_URL}/traces/{st.session_state.session_id}").json()
            for trace in trace_res.get("traces", []):
                with st.expander(f"Step: {trace.get('event', 'LLM Thought')}"):
                    st.json(trace)
        except:
            st.write("No traces yet. Start a conversation!")