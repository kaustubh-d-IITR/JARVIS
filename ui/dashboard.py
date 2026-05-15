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
from audio_recorder_streamlit import audio_recorder

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
        
        st.session_state.initialized = True

def log_system(msg: str):
    """Adds a message to the UI system logs."""
    st.session_state.system_logs.insert(0, msg)
    if len(st.session_state.system_logs) > 20:
        st.session_state.system_logs.pop()

@st.cache_resource(show_spinner="Loading AI Vision Models... (This takes ~10 seconds on first boot)")
def preload_models():
    import numpy as np
    from vision.emotion_detector import EmotionDetector
    # Force PyTorch model to load weights on the main thread
    detector = EmotionDetector()
    detector.detect_emotion(np.zeros((224, 224, 3), dtype=np.uint8))
    return True

def render_dashboard():
    st.set_page_config(page_title="JARVIS AI Assistant", layout="wide", initial_sidebar_state="expanded")
    preload_models()
    initialize_session_state()
    
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
    # SIDEBAR: Settings & Logs
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
                    st.error("Spotify API keys missing in .env")

        st.divider()
        st.subheader("🖥️ System Logs")
        log_container = st.container(height=300)
        for log in st.session_state.system_logs:
            log_container.text(log)
            
    # ------------------
    # MAIN BODY
    # ------------------
    st.title("🤖 JARVIS")
    
    # Check for missing API keys
    missing_keys = []
    for key in ["SPOTIFY_CLIENT_ID", "DEEPGRAM_API_KEY", "GROQ_API_KEY", "OPENWEATHER_API_KEY"]:
        if not getattr(settings, key):
            missing_keys.append(key)
            
    if missing_keys:
        st.warning(f"⚠️ Missing API Keys in .env: {', '.join(missing_keys)}")
        with st.expander("Show .env Debug Logs"):
            st.json(settings.DEBUG_INFO)

    # Weather Widget
    w = st.session_state.weather
    st.info(f"⛅ Context: Location={settings.LOCATION} | Temp={w.get('temperature')}°C | Condition={w.get('condition')}")

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

        # Live feed display
        if vp._running:
            frame = vp.get_frame()
            if frame is not None:
                st.image(
                    frame,
                    channels="RGB",
                    use_container_width=True,
                    caption="Live Perception Feed"
                )
            else:
                st.info("⏳ Initializing camera and loading AI model...")
        else:
            st.info("Click START Camera to begin emotion detection.")

        @st.fragment(run_every=1.0)
        def render_metrics():
            if "video_processor" not in st.session_state:
                return
            vp = st.session_state.video_processor
            if not vp._running:
                return

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

            # Emotion context caption
            st.caption(f"Dominant emotion over last 3 seconds: "
                       f"**{emotion}** at {conf:.0%} confidence")
        render_metrics()
            
        st.divider()
        st.subheader("🎙️ Speak to JARVIS")
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

        # Reject recordings that are too short to be a real command
        # Real speech is at least 0.5 seconds = ~8000 bytes at 16kHz
        if audio_bytes is not None and len(audio_bytes) < 8000:
            audio_bytes = None  # Ignore — too short, likely noise

        # Prevent processing if already processing a command
        if st.session_state.get("processing_voice", False):
            st.info("Processing previous command...")
        elif audio_bytes:
            audio_hash = hashlib.md5(audio_bytes).hexdigest()
            if st.session_state.get('last_audio_hash') != audio_hash:
                st.session_state.last_audio_hash = audio_hash
                st.session_state.processing_voice = True
                st.session_state.last_transcript = "⏳ Transcribing..."
                try:
                    log_system("Voice received from browser. Processing...")
                    with open("temp_audio.wav", "wb") as f:
                        f.write(audio_bytes)
                    
                    with st.spinner("Transcribing via Deepgram..."):
                        transcript = asyncio.run(st.session_state.transcriber.transcribe_audio_async("temp_audio.wav"))
                    
                    st.session_state.last_transcript = transcript
                    
                    # Only process non-empty transcripts
                    if transcript and transcript.strip() and not transcript.startswith("Error"):
                        st.session_state.chat_history.append({"role": "user", "text": transcript})
                        
                        with st.spinner("JARVIS is thinking..."):
                            result = st.session_state.decision_engine.process_voice_command(
                                text=transcript,
                                emotion=st.session_state.current_emotion,
                                posture=st.session_state.current_posture,
                                weather=st.session_state.weather
                            )
                            
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
