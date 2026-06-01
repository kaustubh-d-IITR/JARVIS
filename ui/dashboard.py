import streamlit as st
import asyncio
import time
import hashlib
import os
import cv2
import numpy as np
from PIL import Image
from config.settings import settings
from llm.groq_client import GroqClient
from spotify.spotify_controller import SpotifyController
from weather.weather_service import WeatherService
from logic.decision_engine import DecisionEngine
from logic.autonomous_controller import AutonomousController
from voice.transcriber import AudioTranscriber
from vision.webrtc_processor import JarvisVideoProcessor
from vision.vlm_emotion_analyzer import VLMEmotionAnalyzer

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
        st.session_state.video_processor = JarvisVideoProcessor()
        st.session_state.emotion_analyzer = VLMEmotionAnalyzer()

        # State Tracking
        st.session_state.current_emotion = "neutral"
        st.session_state.emotion_confidence = 0.0
        st.session_state.weather = st.session_state.weather_svc.get_weather()
        st.session_state.chat_history = []
        st.session_state.system_logs = []
        st.session_state.autonomous_mode = False
        
        # Voice State
        st.session_state.last_audio_hash = None
        st.session_state.processing_voice = False
        st.session_state.last_transcript = ""
        st.session_state.last_deepgram_ms = 0
        st.session_state.last_groq_ms = 0

        # Pipeline State
        st.session_state.pipeline_status = "idle" # idle, analyzing, finished, error
        st.session_state.last_image_id = None
        st.session_state.captured_image_path = None
        st.session_state.vlm_result = None
        st.session_state.groq_reasoning = ""
        st.session_state.spotify_action = ""
        st.session_state.api_latency = 0
        st.session_state.pending_suggestion = None
        
        st.session_state.initialized = True

def log_system(msg: str):
    """Adds a message to the UI system logs."""
    ts = time.strftime("%H:%M:%S")
    tag = "[SYSTEM]"
    if "CAMERA" in msg.upper(): tag = "[CAMERA]"
    elif "VLM" in msg.upper() or "VISION" in msg.upper(): tag = "[VLM]"
    elif "GROQ" in msg.upper(): tag = "[GROQ]"
    elif "SPOTIFY" in msg.upper(): tag = "[SPOTIFY]"
    elif "WEATHER" in msg.upper(): tag = "[WEATHER]"
    
    st.session_state.system_logs.insert(0, f"{tag} {ts} {msg}")
    if len(st.session_state.system_logs) > 50:
        st.session_state.system_logs.pop()

def _check_api_status():
    return {
        "spotify": bool(settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET),
        "deepgram": bool(settings.DEEPGRAM_API_KEY),
        "groq": bool(settings.GROQ_API_KEY),
        "weather": bool(settings.OPENWEATHER_API_KEY)
    }

def process_snapshot(image_data):
    """Trigger the AI pipeline after a browser-native snapshot is taken."""
    vp = st.session_state.video_processor
    analyzer = st.session_state.emotion_analyzer
    engine = st.session_state.decision_engine
    
    st.session_state.pipeline_status = "analyzing"
    log_system("CAMERA: Snapshot received from browser.")
    
    # 1. Save Image
    path = vp.save_snapshot(image_data)
    st.session_state.captured_image_path = path
    
    # 2. VLM Multimodal Analysis
    log_system("VLM: Reasoning about visual mood...")
    result = analyzer.analyze_snapshot(image_data)
    
    if not result or "error" in result:
        log_system(f"VLM: Analysis failed. Falling back to weather.")
        st.session_state.pipeline_status = "error"
        st.session_state.vlm_result = result
        # Fallback trigger logic
        decision = engine.evaluate_autonomous_state(
            emotion="neutral", confidence=0, posture="unknown", 
            weather=st.session_state.weather, face_detected=False
        )
        st.session_state.groq_reasoning = "Vision reasoning failed. Falling back to environmental context."
        st.session_state.spotify_action = f"Fallback: {decision.get('query')}"
        return

    st.session_state.vlm_result = result
    st.session_state.current_emotion = result.get("emotion", "neutral")
    st.session_state.emotion_confidence = result.get("confidence", 0.0)
    st.session_state.api_latency = result.get("api_latency_ms", 0)
    
    # 3. Decision & Spotify
    log_system(f"VLM: Emotion detected = {st.session_state.current_emotion}")
    log_system("GROQ: Interpreting mood and reasoning...")
    decision = engine.evaluate_autonomous_state(
        emotion=result.get("emotion", "neutral"),
        confidence=result.get("confidence", 0.0),
        posture=result.get("reasoning", "unknown"),
        weather=st.session_state.weather,
        face_detected=result.get("face_detected", False)
    )
    
    st.session_state.groq_reasoning = decision.get("message", "No clear suggestion.")
    
    if decision.get("suggested_action") == "play_music":
        log_system(f"SPOTIFY: Recommending {decision['query']}...")
        st.session_state.spotify_action = f"Recommendation: {decision['query']}"
        st.session_state.pending_suggestion = decision
    else:
        st.session_state.spotify_action = "No action suggested."
        
    st.session_state.pipeline_status = "finished"
    log_system("PIPELINE: Snapshot analysis complete.")

def render_dashboard():
    st.set_page_config(page_title="JARVIS AI Multimodal Assistant", layout="wide", initial_sidebar_state="expanded")

    keys_valid = st.session_state.get("keys_validated", False)
    
    with st.sidebar:
        st.title("🔑 AI Credentials")
        if not keys_valid:
            with st.form("api_keys_form"):
                gemini_key = st.text_input("Gemini API Key", type="password")
                groq_key = st.text_input("Groq API Key", type="password")
                deepgram_key = st.text_input("Deepgram API Key", type="password")
                openweather_key = st.text_input("OpenWeather API Key", type="password")
                
                submitted = st.form_submit_button("Verify Credentials & Connect Spotify")
                if submitted:
                    if gemini_key and groq_key and deepgram_key and openweather_key:
                        st.session_state.GEMINI_API_KEY = gemini_key
                        st.session_state.GROQ_API_KEY = groq_key
                        st.session_state.DEEPGRAM_API_KEY = deepgram_key
                        st.session_state.OPENWEATHER_API_KEY = openweather_key
                        st.session_state.keys_validated = True
                        
                        from spotify.spotify_controller import SpotifyController
                        temp_spotify = SpotifyController()
                        auth_url = temp_spotify.get_auth_url()
                        
                        if auth_url:
                            import streamlit.components.v1 as components
                            components.html(f"<script>window.location.href='{auth_url}';</script>", height=0)
                        else:
                            st.error("Spotify is disabled (missing dev credentials). Keys verified anyway.")
                            st.rerun()
                    else:
                        st.error("Please provide all four API keys.")
        else:
            st.success("API Keys Verified ✅")
            if st.button("Reset Keys"):
                st.session_state.keys_validated = False
                st.session_state.initialized = False
                st.rerun()

        st.divider()

    if not keys_valid:
        st.title("🤖 Welcome to JARVIS")
        st.markdown("### To continue, provide:")
        st.markdown("- ✓ **Gemini API Key**")
        st.markdown("- ✓ **Groq API Key**")
        st.markdown("- ✓ **Deepgram API Key**")
        st.markdown("- ✓ **OpenWeather API Key**")
        st.info("Please enter your API keys in the sidebar to unlock Camera, Voice, Emotion Detection, and Spotify Features.")
        return

    initialize_session_state()
    api_status = _check_api_status()

    # Handle Spotify OAuth callback
    params = st.query_params
    if "code" in params:
        code = params["code"]
        spotify = st.session_state.get("spotify")
        if spotify and not spotify.is_authenticated():
            success = spotify.handle_callback(code)
            if success:
                st.query_params.clear()
                st.success("Spotify connected successfully!")
                st.rerun()

    # ------------------
    # REST OF SIDEBAR
    # ------------------
    with st.sidebar:
        st.title("⚙️ Control Panel")
        st.subheader("🧠 Autonomous Mode")
        auto_toggle = st.toggle("Enable JARVIS Brain", value=st.session_state.autonomous_mode)
        if auto_toggle and not st.session_state.autonomous_mode:
            st.session_state.autonomous.start()
            st.session_state.autonomous_mode = True
            log_system("AUTONOMOUS: Brain activated.")
        elif not auto_toggle and st.session_state.autonomous_mode:
            st.session_state.autonomous.stop()
            st.session_state.autonomous_mode = False
            log_system("AUTONOMOUS: Brain deactivated.")

        st.divider()
        st.subheader("🎶 Spotify")
        if api_status["spotify"]:
            spotify = st.session_state.get("spotify")
            if spotify:
                status = spotify.get_status()
                if status["connected"]:
                    st.success(f"Connected: {status['user']} ✅")
                    if status["device"]:
                        st.caption(f"🎧 Playing on: {status['device']}")
                    else:
                        st.warning("No active device found")
                        st.caption("Open Spotify on your phone/PC")
                else:
                    st.warning("Spotify not connected ⚠️")
                    auth_url = spotify.get_auth_url()
                    if auth_url:
                        st.markdown(f"[**CONNECT SPOTIFY**]({auth_url})")
        else:
            st.error("🔒 Spotify disabled")
        
        st.divider()
        st.subheader("📋 System Monitor")
        log_container = st.container(height=300)
        for log in st.session_state.system_logs:
            log_container.text(log)

    # ------------------
    # MAIN BODY
    # ------------------
    st.title("🤖 JARVIS AI Multimodal Assistant")
    
    # Weather Context
    if api_status["weather"]:
        w = st.session_state.weather
        st.caption(f"⛅ Context: {settings.LOCATION} | {w.get('temperature')}°C | {w.get('condition')}")

    # Autonomous Suggestion Alerts
    if st.session_state.get("autonomous_mode"):
        suggestion = st.session_state.autonomous.get_and_clear_suggestion()
        if suggestion:
            st.session_state.pending_suggestion = suggestion

    if st.session_state.get("pending_suggestion"):
        s = st.session_state.pending_suggestion
        st.success(f"💡 **JARVIS Suggestion:** {s['message']}")
        col_sugg1, col_sugg2, _ = st.columns([1, 1, 8])
        with col_sugg1:
            if st.button("Accept", key="accept_sugg", type="primary"):
                st.session_state.spotify.play_music(query=s["query"])
                st.session_state.pending_suggestion = None
                st.rerun()
        with col_sugg2:
            if st.button("Dismiss", key="dismiss_sugg"):
                st.session_state.pending_suggestion = None
                st.rerun()

    st.divider()

    # Pipeline Layout
    col_main, col_monitor = st.columns([1.2, 1])

    with col_main:
        st.subheader("📸 Mood Snapshot")
        cam_image = st.camera_input("Take a snapshot for JARVIS to analyze your mood")
        
        if cam_image:
            img_id = hashlib.md5(cam_image.getvalue()).hexdigest()
            if st.session_state.get("last_image_id") != img_id:
                st.session_state.last_image_id = img_id
                process_snapshot(cam_image)
                st.rerun()

        if st.session_state.pipeline_status == "analyzing":
            st.warning("🔄 Gemini Vision Reasoning... Please wait.")
        elif st.session_state.pipeline_status == "finished":
            st.success("✅ Analysis Complete.")
            if st.session_state.captured_image_path:
                st.image(st.session_state.captured_image_path, caption="Analyzed Snapshot", use_container_width=True)
        elif st.session_state.pipeline_status == "error":
            st.error("❌ Perception Pipeline Failed.")

    with col_monitor:
        st.subheader("🔍 AI Pipeline Monitor")
        tab_snapshot, tab_vlm, tab_groq, tab_spotify = st.tabs([
            "📸 Snapshot", "🧠 Vision LLM", "🧠 Groq", "🎶 Spotify"
        ])
        
        with tab_snapshot:
            if st.session_state.captured_image_path:
                st.markdown(f"**Source:** Browser Snapshot")
                st.markdown(f"**Path:** `{os.path.basename(st.session_state.captured_image_path)}`")
            else:
                st.caption("Capture a snapshot to begin.")

        with tab_vlm:
            res = st.session_state.vlm_result
            if res and "error" not in res:
                col1, col2, col3 = st.columns(3)
                col1.metric("Primary", res.get('primary_emotion', 'N/A').upper())
                col2.metric("Secondary", res.get('secondary_emotion', 'N/A'))
                col3.metric("Confidence", f"{res.get('confidence', 0):.1%}")
                
                st.divider()
                st.markdown("**Detected Facial Cues:**")
                cues = res.get("facial_cues", [])
                if cues:
                    st.write(", ".join([f"• {c}" for c in cues]))
                
                st.divider()
                st.markdown(f"**Mood Summary:** {res.get('mood_summary')}")
                st.caption(f"**Music Vibe:** {res.get('music_vibe')} | Latency: {st.session_state.api_latency}ms")
                
                provider_error = res.get("provider_error")
                if provider_error:
                    st.error(f"VLM Provider Issue: {provider_error}")
            elif res and "error" in res:
                st.error(f"VLM Error: {res['error']}")
            else:
                st.caption("Waiting for analysis...")

        with tab_groq:
            if st.session_state.groq_reasoning:
                st.markdown("**Interpreted Context**")
                st.info(st.session_state.groq_reasoning)
            else:
                st.caption("Waiting for reasoning...")

        with tab_spotify:
            if st.session_state.spotify_action:
                st.success(st.session_state.spotify_action)
                if st.session_state.spotify:
                    stat = st.session_state.spotify.get_status()
                    if stat.get("device"):
                        st.caption(f"Target Device: {stat['device']}")
            else:
                st.caption("No action decided yet.")

    st.divider()
    
    # Voice Section
    col_voice, col_chat = st.columns([1, 1])
    with col_voice:
        st.subheader("🎙️ Voice Command")
        if _HAS_AUDIO_RECORDER:
            audio_bytes = audio_recorder(
                text="Click to record",
                recording_color="#e74c3c",
                neutral_color="#27ae60",
                icon_size="2x",
                pause_threshold=3.0
            )
            
            if audio_bytes and not st.session_state.get("processing_voice", False):
                audio_hash = hashlib.md5(audio_bytes).hexdigest()
                if st.session_state.get('last_audio_hash') != audio_hash:
                    st.session_state.last_audio_hash = audio_hash
                    st.session_state.processing_voice = True
                    log_system("VOICE: Processing command...")
                    
                    try:
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                            f.write(audio_bytes)
                            temp_audio_path = f.name

                        t0 = time.perf_counter()
                        transcript = asyncio.run(st.session_state.transcriber.transcribe_audio_async(temp_audio_path))
                        st.session_state.last_deepgram_ms = round((time.perf_counter() - t0) * 1000)
                        st.session_state.last_transcript = transcript

                        if transcript and not transcript.startswith("Error"):
                            st.session_state.chat_history.append({"role": "user", "text": transcript})
                            
                            t1 = time.perf_counter()
                            result = st.session_state.decision_engine.process_voice_command(
                                text=transcript,
                                emotion=st.session_state.current_emotion,
                                posture="unknown",
                                weather=st.session_state.weather
                            )
                            st.session_state.last_groq_ms = round((time.perf_counter() - t1) * 1000)
                            st.session_state.chat_history.append({"role": "assistant", "text": result["response"]})
                            log_system("GROQ: Voice command processed.")
                    finally:
                        st.session_state.processing_voice = False
                    st.rerun()
                
    with col_chat:
        st.subheader("💬 Chat History")
        chat_container = st.container(height=300)
        for chat in st.session_state.chat_history:
            chat_container.chat_message(chat["role"]).write(chat["text"])

    # ============================
    # DEVELOPER DEBUG PANEL
    # ============================
    with st.expander("🔧 Developer Debug Panel", expanded=False):
        tab_v, tab_v2, tab_s, tab_st = st.tabs(["👁️ Vision VLM", "🎙️ Voice", "🔌 Services", "📊 State"])

        with tab_v:
            st.json(st.session_state.emotion_analyzer.get_debug_state())
            if st.session_state.get("vlm_result"):
                st.divider()
                st.json(st.session_state.vlm_result)

        with tab_v2:
            st.metric("Deepgram Latency", f"{st.session_state.get('last_deepgram_ms', 0)}ms")
            st.metric("Groq Latency", f"{st.session_state.get('last_groq_ms', 0)}ms")
            st.info(f"Last Transcript: {st.session_state.get('last_transcript')}")

        with tab_s:
            st.json(api_status)
            if st.session_state.get("spotify"):
                st.write(st.session_state.spotify.get_status())

        with tab_st:
            st.write(st.session_state)

if __name__ == "__main__":
    render_dashboard()
