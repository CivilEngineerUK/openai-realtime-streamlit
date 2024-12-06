import asyncio
import json
import threading
from asyncio import run_coroutine_threadsafe

import streamlit as st

from constants import (AUTOSCROLL_SCRIPT, DOCS, HIDE_STREAMLIT_RUNNING_MAN_SCRIPT, OAI_LOGO_URL)
from utils import SimpleRealtime
from tools import get_current_time

st.set_page_config(layout="wide")

# Authentication check
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["show_splash_screen"] = True

if not st.session_state["authenticated"]:
    from splash_screen import SplashScreen

    SplashScreen.render()
    st.stop()


@st.cache_resource(show_spinner=False)
def create_loop():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    return loop, thread


if "event_loop" not in st.session_state:
    st.session_state.event_loop, worker_thread = create_loop()


def run_async(coroutine):
    return run_coroutine_threadsafe(coroutine, st.session_state.event_loop).result()


@st.cache_resource(show_spinner=False)
def setup_client():
    if "client" in st.session_state:
        return st.session_state.client
    client = SimpleRealtime(event_loop=st.session_state.event_loop, debug=True)
    # Add a sample tool if desired
    client.add_tool(get_current_time)
    return client


if "client" not in st.session_state:
    st.session_state.client = setup_client()


def handle_connection():
    if st.session_state.client.is_connected():
        try:
            run_async(st.session_state.client.disconnect())
            st.success("Disconnected from Realtime API")
        except Exception as e:
            st.error(f"Error disconnecting: {str(e)}")
    else:
        try:
            run_async(st.session_state.client.connect())
            if st.session_state.client.is_connected():
                st.success("Connected to Realtime API")
            else:
                st.error("Failed to connect to Realtime API")
        except Exception as e:
            st.error(f"Error connecting: {str(e)}")
    st.rerun()


def st_app():
    st.markdown(HIDE_STREAMLIT_RUNNING_MAN_SCRIPT, unsafe_allow_html=True)

    main_tab, docs_tab = st.tabs(["Console", "Docs"])

    with main_tab:
        st.markdown(f"<img src='{OAI_LOGO_URL}' width='30px'/> **realtime console**", unsafe_allow_html=True)

        with st.sidebar:
            button_text = "Disconnect" if st.session_state.client.is_connected() else "Connect"
            if st.button(button_text, type="primary"):
                handle_connection()

        st.session_state.show_full_events = st.checkbox("Show Full Event Payloads", value=False)

        st.markdown("### Logs")
        logs = st.session_state.client.logs
        if st.session_state.show_full_events:
            for _, _, log in logs:
                st.json(log, expanded=False)
        else:
            for time, event_type, log in logs:
                parsed = json.loads(log)
                if event_type == "server":
                    st.write(f"{time}\t:green[↓ server] {parsed.get('type', '')}")
                else:
                    st.write(f"{time}\t:blue[↑ client] {parsed.get('type', '')}")
        st.components.v1.html(AUTOSCROLL_SCRIPT, height=0)

        st.markdown("### Conversation")
        st.write(st.session_state.client.transcript)

        st.markdown("### Send a Message (JSON format)")
        input_text = st.text_area("Enter your message:", height=100)
        if st.button("Send", type="primary", disabled=not st.session_state.client.is_connected()):
            if input_text.strip():
                try:
                    event = json.loads(input_text)
                    with st.spinner("Sending message..."):
                        event_type = event.pop("type")
                        st.session_state.client.send(event_type, event)
                    st.success("Message sent successfully")
                except json.JSONDecodeError:
                    st.error("Invalid JSON input. Please check your message format.")
                except Exception as e:
                    st.error(f"Error sending message: {str(e)}")
            else:
                st.warning("Please enter a message before sending.")

    with docs_tab:
        st.markdown(DOCS)


if __name__ == '__main__':
    st_app()
