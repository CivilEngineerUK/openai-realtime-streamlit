import base64
import streamlit as st
from streamlit.components.v1 import html


class BrowserAudioRecorder:
    def __init__(self, audio_callback=None):
        self.is_recording = False
        self.audio_callback = audio_callback

    def start_recording(self):
        self.is_recording = True
        # Inject JavaScript for browser audio recording
        html("""
            <script>
                let mediaRecorder;
                let audioChunks = [];

                const startRecording = async () => {
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                        mediaRecorder = new MediaRecorder(stream);

                        mediaRecorder.ondataavailable = (event) => {
                            audioChunks.push(event.data);
                            // Convert the latest chunk to base64 and send it
                            const reader = new FileReader();
                            reader.readAsDataURL(new Blob([event.data]));
                            reader.onloadend = () => {
                                const base64data = reader.result.split(',')[1];
                                window.parent.postMessage({
                                    type: "streamlit:audioData",
                                    data: base64data
                                }, "*");
                            };
                        };

                        mediaRecorder.start(100); // Collect data every 100ms
                        window.mediaRecorder = mediaRecorder;
                    } catch (err) {
                        console.error("Error accessing microphone:", err);
                    }
                };

                startRecording();
            </script>
        """, height=0)

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            html("""
                <script>
                    if (window.mediaRecorder && window.mediaRecorder.state === 'recording') {
                        window.mediaRecorder.stop();
                        window.mediaRecorder.stream.getTracks().forEach(track => track.stop());
                    }
                </script>
            """, height=0)