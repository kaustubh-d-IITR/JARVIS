# FRONTEND UI FLOW

The JARVIS UI is built entirely on **Streamlit** (`app.py`, `ui/dashboard.py`). It is designed as a real-time, event-driven dashboard that gracefully handles heavy multimodal background tasks without blocking user interaction.

## 1. Application Entry Point (`app.py`)

The entry point is incredibly lightweight. It sets the `asyncio` event loop policy (crucial for Windows environments running Deepgram audio tasks) and delegates rendering directly to `render_dashboard()` in `ui/dashboard.py`.

## 2. Session State Management

Because Streamlit reruns the entire script from top to bottom on every user interaction, state must be meticulously preserved. `initialize_session_state()` ensures:
- **Singletons:** Controllers (Groq, Spotify, VLM, DecisionEngine) are initialized exactly once.
- **Data Persistence:** Chat history, system logs, pipeline status, and last processed image hashes are stored in `st.session_state`.
- **Thread Safety:** Variables shared with the background `AutonomousController` are managed safely.

## 3. UI Layout & Architecture

The Dashboard is split into three core zones:

### A. The Control Panel (Sidebar)
- **Autonomous Mode Toggle:** Starts/Stops the background polling thread.
- **Spotify Authentication:** Displays connection status, active listening device (e.g., "🎧 Playing on: Web Player"), and handles the OAuth login button.
- **System Monitor (Logs):** A scrollable container displaying real-time events. `log_system()` intercepts major pipeline events (e.g., `[VLM] Reasoning about visual mood...`) and pushes them here for transparency.

### B. The Multimodal Pipeline (Main View)
- **Camera Input:** Uses `st.camera_input()`. When an image is captured, `hashlib.md5()` verifies it's a *new* image. If so, it calls `process_snapshot()`.
- **Pipeline Monitor Tabs:**
  - **📸 Snapshot:** Shows file paths and capture source.
  - **🧠 Vision LLM:** Displays high-fidelity VLM outputs: Primary Emotion, Secondary Emotion, Confidence, and granular **Detected Facial Cues** (e.g., "relaxed eyes").
  - **🧠 Groq:** Displays the conversational reasoning output.
  - **🎶 Spotify:** Shows the exact playback execution string.

### C. Voice & Chat (Bottom View)
- **Audio Recorder:** Uses the custom `audio_recorder_streamlit` component. When audio bytes are captured, they are hashed, saved temporarily, and sent to Deepgram.
- **Chat History:** Renders the back-and-forth communication between the User's voice transcripts and JARVIS's Groq-generated responses.

## 4. The Event-Driven Workflow

1. **Capture:** User clicks the camera button.
2. **Locking:** `st.session_state.pipeline_status` is set to `"analyzing"`, triggering a "Please wait" UI warning.
3. **Perception:** `process_snapshot()` synchronously blocks to hit the OpenRouter VLM.
4. **Resolution:** The UI updates with the extracted JSON, updates the Pipeline Monitor, triggers the `DecisionEngine`, and resets status to `"finished"`.
5. **Rerun:** `st.rerun()` is called to force Streamlit to immediately reflect the new state.

## 5. Developer Debug Panel

Hidden inside an `st.expander` at the bottom of the page, this panel is critical for engineering observability. 
- It tracks specific milliseconds for API latency (Deepgram ms, Groq ms, VLM ms).
- It dumps raw `vlm_result` JSON payloads to verify API schemas.
- It displays exact model versions currently locked into the configuration.
