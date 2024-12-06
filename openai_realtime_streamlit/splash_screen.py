# openai_realtime_streamlit/splash_screen.py
import streamlit as st
import os

class SplashScreen:
    @staticmethod
    def render():
        with st.container():
            st.markdown(
                """
                <div style='text-align: center; margin-top: 25vh;'>
                    <h1 style='font-size: 3em; margin-bottom: 1em;'>OpenAI Realtime POC</h1>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Center the password input and button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                password = st.text_input("Enter Password", type="password")
                if st.button("Submit", use_container_width=True):
                    correct_password = os.environ.get("PASSWORD")
                    if password == correct_password:
                        st.session_state["authenticated"] = True
                        st.session_state["show_splash_screen"] = False
                        st.rerun()
                    else:
                        st.error("Incorrect password")