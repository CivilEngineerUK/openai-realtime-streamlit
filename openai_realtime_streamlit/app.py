import asyncio
import base64
import json
import threading
from asyncio import run_coroutine_threadsafe

import streamlit as st
from constants import (AUTOSCROLL_SCRIPT, DOCS, HIDE_STREAMLIT_RUNNING_MAN_SCRIPT, OAI_LOGO_URL)
from utils import SimpleRealtime
from tools import get_current_time

# st_audiorec for audio input
from st_audiorec import st_audiorec

st.set_page_config(layout="wide")

# Authentication check
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["show_splash_screen"] = True

# If not authenticated, show splash and stop
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
    # Add the time function tool
    client.add_tool(get_current_time)
    return client


if "client" not in st.session_state:
    st.session_state.client = setup_client()


def handle_connection():
    if st.session_state.client.is_connected():
        try:
            run_async(st.session_state.client.disconnect())
            st.success("Disconnected from OpenAI Realtime API")
        except Exception as e:
            st.error(f"Error disconnecting: {str(e)}")
    else:
        try:
            run_async(st.session_state.client.connect())
            if st.session_state.client.is_connected():
                st.success("Connected to OpenAI Realtime API")
            else:
                st.error("Failed to connect to OpenAI Realtime API")
        except Exception as e:
            st.error(f"Error connecting to OpenAI Realtime API: {str(e)}")
    st.experimental_rerun()


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
        logs_container = st.empty()
        with logs_container:
            logs = st.session_state.client.logs
            if st.session_state.show_full_events:
                for _, _, log in logs:
                    st.json(log, expanded=False)
            else:
                for time, event_type, log in logs:
                    if event_type == "server":
                        st.write(f"{time}\t:green[↓ server] {json.loads(log)['type']}")
                    else:
                        st.write(f"{time}\t:blue[↑ client] {json.loads(log)['type']}")
            st.components.v1.html(AUTOSCROLL_SCRIPT, height=0)

        st.markdown("### Conversation")
        st.write(st.session_state.client.transcript)

        st.markdown("### Send a Message")
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

        st.markdown("### Record and Send Audio")
        # Record audio using st_audiorec
        audio_data = st_audiorec()
        if audio_data is not None:
            # audio_data is a numpy array representing the recorded audio data
            # Convert it to WAV in memory if needed or send as is, depending on your client logic
            st.audio(audio_data, format="audio/wav")
            # If your client expects a certain format, you can send it here
            # Example: st.session_state.client.send("input_audio_buffer.append", {"audio": YOUR_ENCODED_AUDIO})
            # After finishing sending audio:
            # st.session_state.client.send("input_audio_buffer.commit")
            # st.session_state.client.send("response.create")

    with docs_tab:
        st.markdown(DOCS)


if __name__ == '__main__':
    st_app()
