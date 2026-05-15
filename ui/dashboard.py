import streamlit as st
import asyncio
import time
import hashlib
from config.settings import settings
from llm.groq_client import GroqClient
from spotify.spotify_controller import SpotifyController
from weather.weather_service import WeatherService
from logic.decision_engine import DecisionEngine
from logic.autonomous_controller import AutonomousController
from voice.transcriber import AudioTranscriber
from vision.webrtc_processor import JarvisVideoProcessor

# Conditional import — gracefully handle missing audio_recorder
try:
    from audio_recorder_streamlit import audio_recorder
    _HAS_AUDIO_RECORDER = True
except ImportError:
    _HAS_AUDIO_RECORDER = False


def initialize_session_state():
    """Initialize all Streamlit session state variables to prevent reset on rerun."""
    if 'initialized' not in st.session_state:
        # Core Services
        st.session_state.transcriber = AudioTranscriber()
        st.session_state.groq = GroqClient()
        st.session_state.spotify = SpotifyController()
        st.session_state.weather_svc = WeatherService()

        st.session_state.decision_engine = DecisionEngine(st.session_state.groq, st.session_state.spotify)
        st.session_state.autonomous = AutonomousController(st.session_state.decision_engine)

        # State Tracking
        st.session_state.current_emotion = "neutral"
        st.session_state.emotion_confidence = 0.0
        st.session_state.current_posture = "unknown"
        st.session_state.weather = st.session_state.weather_svc.get_weather()

        st.session_state.chat_history = []
        st.session_state.system_logs = []
        st.session_state.autonomous_mode = False
        st.session_state.last_audio_hash = None
        st.session_state.video_processor = JarvisVideoProcessor()

        # Timing trackers
        st.session_state.last_deepgram_ms = 0
        st.session_state.last_groq_ms = 0

        st.session_state.initialized = True


def log_system(msg: str):
    """Adds a message to the UI system logs."""
    ts = time.strftime("%H:%M:%S")
    st.session_state.system_logs.insert(0, f"[{ts}] {msg}")
    if len(st.session_state.system_logs) > 50:
        st.session_state.system_logs.pop()


@st.cache_resource(show_spinner="Loading AI Vision Models... (This takes ~10 seconds on first boot)")
def preload_models():
    import numpy as np
    from vision.emotion_detector import EmotionDetector
    # Force PyTorch model to load weights on the main thread
    detector = EmotionDetector()
    detector.detect_emotion(np.zeros((224, 224, 3), dtype=np.uint8))
    return True


def _check_api_status():
    """Returns dict of API availability for first-run UX."""
    return {
        "spotify": bool(settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET),
        "deepgram": bool(settings.DEEPGRAM_API_KEY),
        "groq": bool(settings.GROQ_API_KEY),
        "weather": bool(settings.OPENWEATHER_API_KEY),
    }


def render_dashboard():
    st.set_page_config(page_title="JARVIS AI Assistant", layout="wide", initial_sidebar_state="expanded")
    preload_models()
    initialize_session_state()

    api_status = _check_api_status()

    # Handle Spotify OAuth callback
    query_params = st.query_params
    if "code" in query_params:
        code = query_params["code"]
        spotify = st.session_state.get("spotify")
        if spotify and not spotify.is_authenticated():
            success = spotify.handle_callback(code)
            if success:
                st.query_params.clear()
                st.success("Spotify connected successfully!")
                st.rerun()

    # ------------------
    # SIDEBAR
    # ------------------
    with st.sidebar:
        st.title("⚙️ Control Panel")

        # Autonomous Toggle
        st.subheader("🧠 Autonomous Mode")
        auto_toggle = st.toggle("Enable JARVIS Brain", value=st.session_state.autonomous_mode)

        if auto_toggle and not st.session_state.autonomous_mode:
            st.session_state.autonomous.start()
            st.session_state.autonomous_mode = True
            log_system("Autonomous mode started.")
        elif not auto_toggle and st.session_state.autonomous_mode:
            st.session_state.autonomous.stop()
            st.session_state.autonomous_mode = False
            log_system("Autonomous mode stopped.")

        st.divider()
        st.subheader("🎶 Spotify")
        if api_status["spotify"]:
            spotify = st.session_state.get("spotify")
            if spotify:
                if spotify.is_authenticated():
                    st.success("Spotify connected")
                else:
                    auth_url = spotify.get_auth_url()
                    if auth_url:
                        st.warning("Spotify not connected")
                        st.markdown(f"[Connect Spotify]({auth_url})")
                        st.caption("Click above, then come back here after authorizing.")
        else:
            st.error("🔒 Spotify disabled — SPOTIFY_CLIENT_ID / SECRET missing in .env")

        st.divider()
        st.subheader("🖥️ System Logs")
        log_container = st.container(height=300)
        for log in st.session_state.system_logs:
            log_container.text(log)

    # ------------------
    # MAIN BODY
    # ------------------
    st.title("🤖 JARVIS")

    # First-run warnings with graceful feature disabling
    missing_keys = []
    for key_name, available in api_status.items():
        if not available:
            missing_keys.append(key_name.upper())
    if missing_keys:
        st.warning(f"⚠️ Missing API keys: {', '.join(missing_keys)} — some features disabled.")
        with st.expander("Show .env Debug Info"):
            st.json(settings.DEBUG_INFO)

    # Weather Widget
    w = st.session_state.weather
    if api_status["weather"]:
        st.info(f"⛅ Context: Location={settings.LOCATION} | "
                f"Temp={w.get('temperature')}°C | Condition={w.get('condition')}")
    else:
        st.caption("⛅ Weather API not configured — using defaults.")

    # Autonomous Suggestion Alerts
    if st.session_state.autonomous_mode:
        suggestion = st.session_state.autonomous.get_and_clear_suggestion()
        if suggestion:
            st.session_state.pending_suggestion = suggestion

    if hasattr(st.session_state, 'pending_suggestion') and st.session_state.pending_suggestion:
        s = st.session_state.pending_suggestion
        st.success(f"💡 **JARVIS Suggestion:** {s['message']}")
        col_sugg1, col_sugg2, _ = st.columns([1, 1, 8])
        with col_sugg1:
            if st.button("Accept", key="accept_sugg", type="primary"):
                st.session_state.spotify.play_music(query=s["query"])
                log_system(f"Accepted suggestion. Played {s['query']}")
                st.session_state.pending_suggestion = None
                st.rerun()
        with col_sugg2:
            if st.button("Dismiss", key="dismiss_sugg"):
                st.session_state.pending_suggestion = None
                st.rerun()

    # ------------------
    # LOCAL USER PERCEPTION
    # ------------------
    st.subheader("👁️ Live Local Perception")

    col_vision, col_chat = st.columns([1, 1])

    with col_vision:
        # Ensure video_processor exists
        if "video_processor" not in st.session_state:
            st.session_state.video_processor = JarvisVideoProcessor()
        vp = st.session_state.video_processor

        # Camera control buttons
        col_start, col_stop = st.columns([1, 1])
        with col_start:
            if not vp._running:
                if st.button("▶ START Camera", type="primary", key="cam_start"):
                    vp.start()
                    st.rerun()
        with col_stop:
            if vp._running:
                if st.button("⏹ STOP Camera", key="cam_stop"):
                    vp.stop()
                    st.rerun()

        # Live feed + metrics — MUST be in same fragment to update together
        @st.fragment(run_every=0.5)
        def render_live_feed():
            if "video_processor" not in st.session_state:
                return
            vp = st.session_state.video_processor

            if not vp._running:
                # Check if there's an error message from a failed start
                debug = vp.get_debug_state()
                if debug.get("error"):
                    st.error(f"Camera Error: {debug['error']}")
                return

            # Get and display frame
            frame = vp.get_frame()
            if frame is not None:
                st.image(
                    frame,
                    channels="RGB",
                    use_container_width=True,
                )
            else:
                st.info("⏳ Initializing camera and loading AI model...")
                return

            # Get state and display metrics
            emotion, conf, posture = vp.get_state()

            # Update session state
            st.session_state.current_emotion = emotion
            st.session_state.emotion_confidence = conf
            st.session_state.current_posture = posture

            # Update autonomous controller
            if "autonomous" in st.session_state:
                st.session_state.autonomous.update_state(
                    emotion=emotion,
                    confidence=conf,
                    posture=posture,
                    weather=st.session_state.get("weather", {})
                )

            # Display metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Emotion", emotion.capitalize())
            col2.metric("Confidence", f"{conf:.0%}")
            col3.metric("Posture", posture.capitalize())

            st.caption(f"Dominant emotion over last 3 seconds: "
                       f"**{emotion}** at {conf:.0%} confidence")
        render_live_feed()

        st.divider()

        # ── VOICE RECORDING ──
        st.subheader("🎙️ Speak to JARVIS")

        # Graceful degradation if APIs are missing
        if not api_status["deepgram"]:
            st.error("🔒 Voice disabled — DEEPGRAM_API_KEY missing in .env")
        elif not _HAS_AUDIO_RECORDER:
            st.error("🔒 Voice disabled — audio_recorder_streamlit not installed")
        else:
            audio_bytes = audio_recorder(
                text="Click to record",
                recording_color="#e74c3c",
                neutral_color="#27ae60",
                icon_name="microphone",
                icon_size="2x",
                pause_threshold=3.0,
                sample_rate=16000,
                energy_threshold=0.05
            )
            st.caption("🎙️ Click mic → speak your command → click again to stop. "
                       "For best results, lower speaker volume while recording.")

            # Show last transcript
            last_transcript = st.session_state.get("last_transcript", "")
            if last_transcript:
                st.markdown("**🎙️ JARVIS heard:**")
                st.info(f'"{last_transcript}"')
            else:
                st.caption("Your voice command will appear here after recording.")

            # Reject recordings too short
            if audio_bytes is not None and len(audio_bytes) < 8000:
                audio_bytes = None

            # Prevent concurrent processing
            if st.session_state.get("processing_voice", False):
                st.info("Processing previous command...")
            elif audio_bytes:
                audio_hash = hashlib.md5(audio_bytes).hexdigest()
                if st.session_state.get('last_audio_hash') != audio_hash:
                    st.session_state.last_audio_hash = audio_hash
                    st.session_state.processing_voice = True
                    st.session_state.last_transcript = "⏳ Transcribing..."
                    try:
                        log_system("Voice received. Processing...")
                        with open("temp_audio.wav", "wb") as f:
                            f.write(audio_bytes)

                        t0 = time.perf_counter()
                        with st.spinner("Transcribing via Deepgram..."):
                            transcript = asyncio.run(
                                st.session_state.transcriber.transcribe_audio_async("temp_audio.wav")
                            )
                        st.session_state.last_deepgram_ms = round((time.perf_counter() - t0) * 1000)

                        st.session_state.last_transcript = transcript

                        if transcript and transcript.strip() and not transcript.startswith("Error"):
                            st.session_state.chat_history.append({"role": "user", "text": transcript})

                            t1 = time.perf_counter()
                            with st.spinner("JARVIS is thinking..."):
                                result = st.session_state.decision_engine.process_voice_command(
                                    text=transcript,
                                    emotion=st.session_state.current_emotion,
                                    posture=st.session_state.current_posture,
                                    weather=st.session_state.weather
                                )
                            st.session_state.last_groq_ms = round((time.perf_counter() - t1) * 1000)

                            st.session_state.chat_history.append({"role": "jarvis", "text": result["response"]})
                            if result.get("action_msg"):
                                log_system(f"Action: {result['action_msg']}")
                        else:
                            log_system("Voice recording was empty or unclear. Try again.")
                    finally:
                        st.session_state.processing_voice = False
                    st.rerun()

    with col_chat:
        # Chat History
        st.subheader("💬 Interaction History")
        chat_container = st.container(height=500)
        for chat in st.session_state.chat_history:
            if chat["role"] == "user":
                chat_container.chat_message("user").write(f"🎙️ {chat['text']}")
            else:
                chat_container.chat_message("assistant").write(chat["text"])

    # ============================
    # DEVELOPER DEBUG PANEL
    # ============================
    with st.expander("🔧 Developer Debug Panel", expanded=False):
        tab_vision, tab_voice, tab_services, tab_state = st.tabs([
            "👁️ Vision", "🎙️ Voice", "🔌 Services", "📊 Full State"
        ])

        with tab_vision:
            vp = st.session_state.get("video_processor")
            if vp:
                debug = vp.get_debug_state()
                col_d1, col_d2, col_d3 = st.columns(3)
                col_d1.metric("Camera FPS", f"{debug['fps']}")
                col_d2.metric("Inference", f"{debug['inference_ms']}ms")
                col_d3.metric("Frames", f"{debug['frame_count']}")

                col_d4, col_d5, col_d6 = st.columns(3)
                col_d4.metric("Face Detected", "✅" if debug['face_detected'] else "❌")
                col_d5.metric("Buffer Fill", f"{debug['buffer_size']}/{debug['buffer_max']}")
                col_d6.metric("Uptime", f"{debug['uptime_seconds']}s")

                # Majority vote breakdown
                st.markdown("**Emotion Vote Buffer:**")
                votes = debug.get("vote_counts", {})
                if votes:
                    for emo, count in sorted(votes.items(), key=lambda x: -x[1]):
                        pct = count / max(debug["buffer_size"], 1)
                        st.progress(pct, text=f"{emo}: {count} votes ({pct:.0%})")
                else:
                    st.caption("No votes yet — start camera first.")

                # Raw probabilities toggle
                show_probs = st.checkbox("Show Raw FER Probabilities", key="show_fer_probs")
                if show_probs and vp._running:
                    frame = vp.get_frame()
                    if frame is not None and vp._emotion_detector:
                        import cv2
                        bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        probs = vp._emotion_detector.get_all_probabilities(bgr_frame)
                        st.markdown("**Live FER Probabilities:**")
                        for emo in ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']:
                            p = probs.get(emo, 0.0)
                            st.progress(min(p, 1.0), text=f"{emo}: {p:.1%}")

                st.json(debug)
            else:
                st.caption("Video processor not initialized.")

        with tab_voice:
            st.metric("Last Deepgram Latency", f"{st.session_state.get('last_deepgram_ms', 0)}ms")
            st.metric("Last Groq Latency", f"{st.session_state.get('last_groq_ms', 0)}ms")
            st.markdown("**Last Transcript:**")
            st.code(st.session_state.get("last_transcript", "(none)"))
            st.markdown("**Processing Lock:**")
            st.code(f"processing_voice = {st.session_state.get('processing_voice', False)}")

        with tab_services:
            st.markdown("**API Status:**")
            for name, available in api_status.items():
                if available:
                    st.success(f"✅ {name.upper()} — configured")
                else:
                    st.error(f"❌ {name.upper()} — missing API key")

            st.divider()
            st.markdown("**Spotify Auth:**")
            spotify = st.session_state.get("spotify")
            if spotify:
                st.code(f"authenticated = {spotify.is_authenticated()}")

            st.markdown("**Autonomous Controller:**")
            auto = st.session_state.get("autonomous")
            if auto:
                st.code(f"running = {auto.is_running}\n"
                        f"cooldown = {auto.cooldown}s\n"
                        f"last_action = {auto.last_action_time}")

            st.markdown("**Weather Data:**")
            st.json(st.session_state.get("weather", {}))

        with tab_state:
            st.markdown("**Full Session State Keys:**")
            state_keys = {}
            for key in sorted(st.session_state.keys()):
                val = st.session_state[key]
                if isinstance(val, (str, int, float, bool, type(None))):
                    state_keys[key] = val
                elif isinstance(val, (list, dict)):
                    state_keys[key] = f"({type(val).__name__}, len={len(val)})"
                else:
                    state_keys[key] = f"<{type(val).__name__}>"
            st.json(state_keys)

            st.markdown("**System Logs (last 50):**")
            for log in st.session_state.get("system_logs", []):
                st.text(log)
