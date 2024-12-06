import queue
from streamlit.components.v1 import html


class BrowserAudioRecorder:
    def __init__(self, sample_rate=24_000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_queue = queue.Queue()
        self.is_recording = False

    def start_recording(self):
        self.is_recording = True
        # Inject JavaScript for browser audio recording
        html("""
            <script>
                const startRecording = async () => {
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                        const mediaRecorder = new MediaRecorder(stream);
                        const audioChunks = [];

                        mediaRecorder.ondataavailable = (event) => {
                            audioChunks.push(event.data);
                        };

                        mediaRecorder.onstop = () => {
                            const audioBlob = new Blob(audioChunks);
                            const reader = new FileReader();
                            reader.readAsDataURL(audioBlob);
                            reader.onloadend = () => {
                                const base64data = reader.result;
                                // Send to Streamlit
                                window.parent.postMessage({
                                    type: "streamlit:audioData",
                                    data: base64data
                                }, "*");
                            };
                        };

                        mediaRecorder.start(100); // Collect data every 100ms
                    } catch (err) {
                        console.error("Error accessing microphone:", err);
                    }
                };

                startRecording();
            </script>
        """)

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            # Inject JavaScript to stop recording
            html("""
                <script>
                    if (window.mediaRecorder) {
                        window.mediaRecorder.stop();
                    }
                </script>
            """)

    def get_audio_chunk(self):
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None