# SYSTEM SEQUENCE FLOW

This document explains the step-by-step execution path for the primary workflows in JARVIS.

## Workflow 1: System Boot & Initialization

1. User executes `run_jarvis.bat`.
2. Execution hits `startup_check.py`.
3. Startup checks load `.env`.
4. Startup attempts a live `requests.get` to OpenRouter `/models` to verify `nvidia/nemotron-nano-12b-v2-vl:free` is available.
5. If validation passes, `streamlit run app.py` is invoked.
6. `app.py` sets the asyncio loop and calls `render_dashboard()`.
7. `ui/dashboard.py` calls `initialize_session_state()`.
8. Memory instances of `VLMEmotionAnalyzer`, `DecisionEngine`, `SpotifyController`, and `AutonomousController` are created once.
9. Streamlit renders the UI, waiting for user input.

## Workflow 2: Manual Webcam Snapshot

1. User clicks the "Take a snapshot" button in Streamlit.
2. `st.camera_input` yields a binary `UploadedFile` object.
3. The UI hashes the file. If it's new, it calls `process_snapshot()`.
4. `JarvisVideoProcessor.save_snapshot()` writes the raw JPEG to `captured_frames/`.
5. `VLMEmotionAnalyzer.analyze_snapshot()` is invoked.
   - Converts the image to base64.
   - Injects base64 into the Facial Priority Prompt.
   - Transmits to OpenRouter API.
6. OpenRouter returns a JSON string.
7. VLM Analyzer parses the JSON and returns it to `dashboard.py`.
8. `dashboard.py` updates `st.session_state.current_emotion`.
9. `dashboard.py` calls `DecisionEngine.evaluate_autonomous_state()`.
10. The Decision Engine maps the emotion to a music query using `get_spotify_playlist_for_emotion()`.
11. `dashboard.py` renders the recommendation to the UI and updates the Pipeline Monitor.

## Workflow 3: Voice Command Override

1. User clicks the microphone icon (`audio_recorder_streamlit`).
2. App records audio and yields WAV bytes.
3. Audio bytes are saved locally to `temp_audio.wav`.
4. `AudioTranscriber.transcribe_audio_async()` is called.
5. Audio is uploaded to Deepgram Nova-2.
6. Deepgram returns the transcript string.
7. `DecisionEngine.process_voice_command()` receives the transcript.
8. Engine parses for explicit intents (e.g., "pause", "play X").
9. If "play X", `SpotifyController.play_music(query="X")` is called.
10. `SpotifyController` hits Spotify API to search, grab the URI, and command the active device to play.
11. The action result ("Playing X") and transcript are sent to `GroqClient.get_response()`.
12. Groq returns conversational text ("Sure thing, putting on X now!").
13. `dashboard.py` appends text to chat history and rerenders the UI.

## Workflow 4: Autonomous Background Processing

1. User toggles "Enable JARVIS Brain" on the sidebar.
2. `AutonomousController.start()` spawns a daemon thread running `_loop()`.
3. Every 5 seconds, the thread wakes up.
4. It checks if `time.time() - last_action_time < 60` (Cooldown). If yes, it sleeps again.
5. If off cooldown, it grabs `st.session_state.current_emotion` (last analyzed by camera).
6. It passes this data to `DecisionEngine.evaluate_autonomous_state()`.
7. If the Engine decides action is needed (e.g., High Confidence Sadness), it returns a payload.
8. The Thread pushes this payload into `self.latest_suggestion`.
9. On the next Streamlit rerun (caused by any UI interaction), `dashboard.py` detects the suggestion and renders a massive "JARVIS Suggestion" alert box with [Accept] / [Dismiss] buttons.
