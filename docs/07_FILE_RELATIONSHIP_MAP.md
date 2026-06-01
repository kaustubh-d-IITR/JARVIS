# FILE RELATIONSHIP MAP

This document maps the repository's folder structure and import dependencies, clarifying which component calls which.

## 1. Directory Structure

```text
JARVIS/
├── .env                          # Secret API Keys (Not tracked in git)
├── app.py                        # Streamlit Entry Point
├── startup_check.py              # Pre-flight environment validation
├── requirements.txt              # Dependency List
├── run_jarvis.bat                # Windows Launcher
│
├── config/
│   └── settings.py               # Central environment configuration & secrets loader
│
├── llm/
│   ├── groq_client.py            # Conversational reasoning client
│   └── prompts.py                # System context and prompt compilation
│
├── logic/
│   ├── autonomous_controller.py  # Background loop threading
│   └── decision_engine.py        # Central intelligence & routing
│
├── spotify/
│   └── spotify_controller.py     # Spotipy OAuth and Playback execution
│
├── ui/
│   └── dashboard.py              # Main Streamlit UI components
│
├── utils/
│   ├── helpers.py                # Emotion-to-playlist static mapping
│   ├── clear_hf_cache.py         # [DEPRECATED] Leftover from HF pipeline
│   └── logger.py                 # Central logging config
│
├── vision/
│   ├── vlm_emotion_analyzer.py   # OpenRouter Multimodal reasoning logic
│   └── webrtc_processor.py       # Snapshot saving utility
│
├── voice/
│   └── transcriber.py            # Deepgram Speech-to-Text
│
└── weather/
    └── weather_service.py        # OpenWeatherMap data fetching
```

## 2. Core Import Dependencies

Below is the conceptual dependency tree. Arrows (`->`) indicate "Imports and Uses".

### UI & Bootstrap
- `app.py` -> `ui/dashboard.py`
- `ui/dashboard.py` -> `config/settings.py` (for UI conditionals)
- `ui/dashboard.py` -> All Controller/Service layers (Initializes them into Session State)

### The Decision Engine (`logic/decision_engine.py`)
This is the most highly coupled file in the system.
- `logic/decision_engine.py` -> `llm/groq_client.py` (Passes contexts for chatting)
- `logic/decision_engine.py` -> `llm/prompts.py` (Gets prompt templates)
- `logic/decision_engine.py` -> `spotify/spotify_controller.py` (Triggers music)
- `logic/decision_engine.py` -> `utils/helpers.py` (Gets playlist string arrays)

### Background Controller (`logic/autonomous_controller.py`)
- `logic/autonomous_controller.py` -> `logic/decision_engine.py` (Passes state for evaluation every 5s)

### Vision Subsystem (`vision/vlm_emotion_analyzer.py`)
This system is completely decoupled from the rest of the logic. It only reports to the dashboard.
- `vision/vlm_emotion_analyzer.py` -> `config/settings.py` (Gets OpenRouter Key)
- `vision/webrtc_processor.py` -> `PIL`, `cv2` (Handles raw image saving)

## 3. Data Workflow Hierarchy

To understand how data moves through JARVIS:

1. **RAW DATA INGEST:** `ui/dashboard.py` (Gets Bytes from Webcam or Mic)
2. **PERCEPTION:**
   - Image Bytes -> `vision/vlm_emotion_analyzer.py` -> Returns JSON Emotion
   - Audio Bytes -> `voice/transcriber.py` -> Returns Text Transcript
3. **CONTEXT AGGREGATION:** `ui/dashboard.py` combines Emotion, Text, and Weather.
4. **DECISION:** Combined Context -> `logic/decision_engine.py`.
5. **ACTION:** Decision Engine -> `spotify/spotify_controller.py` (Plays music) & `llm/groq_client.py` (Generates text).
6. **RENDER:** Action results -> `ui/dashboard.py` (Renders to screen).
