import asyncio
import base64
import json
import threading
from asyncio import run_coroutine_threadsafe

import streamlit as st

from constants import (AUTOSCROLL_SCRIPT, DOCS,
                      HIDE_STREAMLIT_RUNNING_MAN_SCRIPT, OAI_LOGO_URL)
from utils import SimpleRealtime
from audio_browser import BrowserAudioRecorder
from splash_screen import SplashScreen

# function calling
from tools import get_current_time

st.set_page_config(layout="wide")

# Authentication check
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["show_splash_screen"] = True

if not st.session_state["authenticated"]:
    SplashScreen.render()
    st.stop()

if "audio_stream_started" not in st.session_state:
    st.session_state.audio_stream_started = False

def handle_browser_audio(audio_data):
    """
    Callback function to handle audio data from the browser
    """
    if st.session_state.client and st.session_state.client.is_connected():
        st.session_state.client.send("input_audio_buffer.append", {"audio": audio_data})

@st.cache_resource(show_spinner=False)
def create_loop():
    """
    Creates an event loop we can globally cache and then run in a
    separate thread.
    """
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever)
    thread.start()
    return loop, thread

st.session_state.event_loop, worker_thread = create_loop()

def run_async(coroutine):
    """
    Helper for running an async function in the globally cached event loop we
    just created.
    """
    return run_coroutine_threadsafe(coroutine, st.session_state.event_loop).result()

@st.cache_resource(show_spinner=False)
def setup_client():
    """
    Globally cached SimpleRealtime client with time function tool added.
    """
    if client := st.session_state.get("client"):
        return client
    client = SimpleRealtime(event_loop=st.session_state.event_loop, audio_buffer_cb=handle_browser_audio, debug=True)

    # Add the time function tool
    client.add_tool(get_current_time)
    return client

if "client" not in st.session_state:
    st.session_state.client = setup_client()

if "recorder" not in st.session_state:
    st.session_state.recorder = BrowserAudioRecorder(audio_callback=handle_browser_audio)
if "recording" not in st.session_state:
    st.session_state.recording = False

def toggle_recording():
    if not st.session_state.client.is_connected():
        st.error("Please connect to the API first")
        return

    st.session_state.recording = not st.session_state.recording

    if st.session_state.recording:
        st.session_state.recorder.start_recording()
    else:
        st.session_state.recorder.stop_recording()
        if st.session_state.client.is_connected():
            st.session_state.client.send("input_audio_buffer.commit")
            st.session_state.client.send("response.create")

@st.fragment(run_every=1)
def logs_text_area():
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

@st.fragment(run_every=1)
def response_area():
    st.markdown("**conversation**")
    st.write(st.session_state.client.transcript)

def handle_connection():
    if st.session_state.client.is_connected():
        try:
            run_async(st.session_state.client.disconnect())
            st.success("Disconnected from OpenAI Realtime API")
            st.session_state.recording = False  # Stop recording if active
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
    st.rerun()

def st_app():
    """
    Our main streamlit app function.
    """
    st.markdown(HIDE_STREAMLIT_RUNNING_MAN_SCRIPT, unsafe_allow_html=True)

    main_tab, docs_tab = st.tabs(["Console", "Docs"])

    with main_tab:
        st.markdown(f"<img src='{OAI_LOGO_URL}' width='30px'/>   **realtime console**", unsafe_allow_html=True)

        with st.sidebar:
            button_text = "Disconnect" if st.session_state.client.is_connected() else "Connect"
            if st.button(button_text, type="primary"):
                handle_connection()

        st.session_state.show_full_events = st.checkbox("Show Full Event Payloads", value=False)
        with st.container(height=300, key="logs_container"):
            logs_text_area()

        with st.container(height=300, key="response_container"):
            response_area()

        col1, col2 = st.columns([1, 4])
        with col1:
            button_text = "Stop Recording" if st.session_state.recording else "Send Audio"
            st.button(button_text, on_click=toggle_recording, type="primary",
                     disabled=not st.session_state.client.is_connected())

        _ = st.text_area("Enter your message:", key="input_text_area", height=200)

        def clear_input_cb():
            st.session_state.last_input = st.session_state.input_text_area
            st.session_state.input_text_area = ""

        if st.button("Send", on_click=clear_input_cb, type="primary",
                    disabled=not st.session_state.client.is_connected()):
            if st.session_state.get("last_input"):
                try:
                    event = json.loads(st.session_state.get("last_input"))
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

    # Handle received audio from the server
    if hasattr(st.session_state.client, "received_audio"):
        audio_data = st.session_state.client.received_audio
        if audio_data:
            st.audio(audio_data, format="audio/wav")

if __name__ == '__main__':
    st_app()