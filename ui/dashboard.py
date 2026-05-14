import streamlit as st
import cv2
import asyncio
import time
from config.settings import settings
from vision.emotion_detector import EmotionDetector
from vision.posture_detector import PostureDetector
from vision.camera_manager import CameraManager
from voice.recorder import AudioRecorder
from voice.transcriber import AudioTranscriber
from llm.groq_client import GroqClient
from spotify.spotify_controller import SpotifyController
from weather.weather_service import WeatherService
from logic.decision_engine import DecisionEngine
from logic.autonomous_controller import AutonomousController
import startup_check

def initialize_session_state():
    """Initialize all Streamlit session state variables to prevent reset on rerun."""
    if 'initialized' not in st.session_state:
        # Core Services
        st.session_state.emotion_detector = EmotionDetector(skip_frames=5)
        st.session_state.posture_detector = PostureDetector()
        st.session_state.camera_manager = CameraManager(
            st.session_state.posture_detector,
            st.session_state.emotion_detector
        )
        st.session_state.recorder = AudioRecorder()
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
        st.session_state.is_recording = False
        st.session_state.autonomous_mode = False
        st.session_state.camera_running = False
        
        # Hardware
        st.session_state.has_camera = startup_check.check_camera()
        
        st.session_state.initialized = True

def log_system(msg: str):
    """Adds a message to the UI system logs."""
    st.session_state.system_logs.insert(0, msg)
    if len(st.session_state.system_logs) > 20:
        st.session_state.system_logs.pop()

def get_current_state_for_autonomous():
    """Callback for the background autonomous thread."""
    return (
        st.session_state.current_emotion,
        st.session_state.emotion_confidence,
        st.session_state.current_posture,
        st.session_state.weather
    )

def release_camera():
    if 'camera_manager' in st.session_state:
        st.session_state.camera_manager.stop()
    st.session_state.camera_running = False

def render_dashboard():
    st.set_page_config(page_title="JARVIS AI Assistant", layout="wide", initial_sidebar_state="expanded")
    initialize_session_state()
    
    # ------------------
    # SIDEBAR: Settings & Logs
    # ------------------
    with st.sidebar:
        st.title("⚙️ Control Panel")
        
        # Autonomous Toggle
        st.subheader("🧠 Autonomous Mode")
        auto_toggle = st.toggle("Enable JARVIS Brain", value=st.session_state.autonomous_mode)
        
        if auto_toggle and not st.session_state.autonomous_mode:
            st.session_state.autonomous.start(get_current_state_for_autonomous)
            st.session_state.autonomous_mode = True
            log_system("Autonomous mode started.")
        elif not auto_toggle and st.session_state.autonomous_mode:
            st.session_state.autonomous.stop()
            st.session_state.autonomous_mode = False
            log_system("Autonomous mode stopped.")
            
        st.divider()
        st.subheader("🎶 Spotify Auth")
        if not st.session_state.spotify.is_authenticated():
            url = st.session_state.spotify.get_auth_url()
            if url:
                st.error("Not Authenticated")
                st.markdown(f"[Login to Spotify]({url})")
        else:
            st.success("Authenticated")
            if st.button("⏯️ Play/Pause Music"):
                st.session_state.spotify.play_music()

        st.divider()
        st.subheader("🖥️ System Logs")
        log_container = st.container(height=300)
        for log in st.session_state.system_logs:
            log_container.text(log)
            
        st.divider()
        if st.button("🔌 Release Camera"):
            release_camera()
            log_system("Camera forcefully released.")

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
            st.write("Loaded OS Environment Variables (Snippet):")
            for key in ["SPOTIFY_CLIENT_ID", "DEEPGRAM_API_KEY", "GROQ_API_KEY", "OPENWEATHER_API_KEY"]:
                st.write(f"- `{key}`: `{'FOUND' if getattr(settings, key) else 'MISSING'}`")
            st.write(f"Current Working Directory: `{__import__('os').getcwd()}`")

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
    # UNIFIED USER PERCEPTION
    # ------------------
    st.subheader("👁️ Live User Perception")
    
    if not st.session_state.get('has_camera', False):
        st.warning(f"No camera detected at index {settings.CAMERA_INDEX}. Vision capabilities are disabled.")
        camera_disabled = True
    else:
        camera_disabled = False

    col_controls1, col_controls2, _ = st.columns([1, 1, 2])
    with col_controls1:
        if not st.session_state.camera_running:
            if st.button("👁️ Start Perception (Camera)", use_container_width=True, disabled=camera_disabled):
                success = st.session_state.camera_manager.start()
                if success:
                    st.session_state.camera_running = True
                    st.rerun()
                else:
                    st.error("Failed to start camera thread. It may be locked by another app.")
        else:
            if st.button("🛑 Stop Perception", use_container_width=True):
                release_camera()
                st.rerun()
                
    with col_controls2:
        if st.button("🎙️ Speak to JARVIS" if not st.session_state.is_recording else "🛑 Stop Recording", type="primary", use_container_width=True):
            if not st.session_state.is_recording:
                st.session_state.recorder.start_recording()
                st.session_state.is_recording = True
                log_system("Started voice recording.")
                st.rerun()
            else:
                wav_path = st.session_state.recorder.stop_recording()
                st.session_state.is_recording = False
                log_system("Stopped voice recording. Processing...")
                
                with st.spinner("Transcribing via Deepgram..."):
                    transcript = asyncio.run(st.session_state.transcriber.transcribe_audio_async(wav_path))
                    
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
                st.rerun()

    st.divider()

    # ------------------
    # DISPLAY AREAS
    # ------------------
    col_vision, col_chat = st.columns([1, 1])

    with col_vision:
        # Camera Fragment
        @st.fragment(run_every=0.5)
        def render_camera_stream():
            if st.session_state.camera_running:
                frame, emotion, conf, posture, status = st.session_state.camera_manager.get_latest_data()
                
                if frame is not None:
                    st.image(frame, channels="RGB", use_container_width=True)
                    
                    stat1, stat2 = st.columns(2)
                    stat1.metric("Detected Emotion", f"{emotion.capitalize()}", f"{int(conf*100)}% conf")
                    stat2.metric("Body Posture", f"{posture.capitalize()}")
                    
                    st.session_state.current_emotion = emotion
                    st.session_state.emotion_confidence = conf
                    st.session_state.current_posture = posture
                else:
                    st.info(f"⏳ **Thread Status:** {status}")
            else:
                st.info("Camera is currently off. Click 'Start Perception' to begin.")
                
        render_camera_stream()

    with col_chat:
        # Chat History
        st.subheader("💬 Interaction History")
        chat_container = st.container(height=400)
        for chat in st.session_state.chat_history:
            if chat["role"] == "user":
                chat_container.chat_message("user").write(chat["text"])
            else:
                chat_container.chat_message("assistant").write(chat["text"])
