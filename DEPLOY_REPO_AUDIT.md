# DEPLOY_REPO_AUDIT

## Folder Structure
The repository is structured into distinct modular components:
- `config/` - Handles configuration and environment variables.
- `docs/` - Contains documentation and guides.
- `llm/` - Core reasoning logic (Groq integration).
- `logic/` - Application logic including autonomous controller and decision engine.
- `spotify/` - Spotify API integration and controller.
- `tests/` - Test suite for components (includes a camera test).
- `ui/` - Streamlit dashboard and user interface components.
- `vision/` - Image processing and VLM analysis (OpenRouter + Gemini Fallback).
- `voice/` - Deepgram audio transcription.
- `weather/` - Local weather integration.

## Runtime Files
- `.env.example`: Template for environment variables.
- `app.py`: Primary application entrypoint for Streamlit.
- `requirements.txt`: Python package dependencies.
- `packages.txt`: System-level dependencies.
- `Dockerfile` & `docker-compose.yml`: Containerization configuration.
- Startup and setup scripts (`run_jarvis.bat`, `run_jarvis.sh`, `setup_local.bat`, etc.).
- `startup_check.py`: Diagnostics script.

## Entry Points
- The primary entry point for deployment is `app.py`, which initializes Streamlit and routes to `ui/dashboard.py`.

## Environment Variables
The application currently expects several API keys to be present in a `.env` file or environment variables:
- `GEMINI_API_KEY`, `GROQ_API_KEY`, `DEEPGRAM_API_KEY` (User AI Keys - To be moved to session state)
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI` (Developer Spotify Credentials)
- `OPENWEATHER_API_KEY`, `LOCATION` (Weather config)
- `OPENROUTER_API_KEY` (OpenRouter API key)

## Dependencies
- Major dependencies include `streamlit`, `groq`, `google-generativeai`, `spotipy`, `opencv-python-headless` (or `opencv-python`), `Pillow`, `requests`, `audio_recorder_streamlit`.

## Deployment Risks
1. **API Keys Hardcoded via Environment Variable:** The app expects all API keys (Groq, Deepgram, Gemini/OpenRouter) to be pre-loaded via environment variables, violating the "User API Key System" requirement for Streamlit Cloud.
2. **Local Storage Assumptions:** `vision/webrtc_processor.py` saves images to a local `captured_frames/` directory. Streamlit Cloud's filesystem is ephemeral. This could cause storage bloat or errors if directory creation fails.
3. **Local Webcam Tests:** `tests/test_camera.py` directly references `cv2.VideoCapture`. While it's in `tests/`, this local device access code shouldn't be relied on.
4. **Spotify Auth Callback:** `SPOTIFY_REDIRECT_URI` is defaulted to `http://127.0.0.1:8501/callback` which will fail on deployment without proper routing.
5. **Windows-specific logic:** `app.py` sets `asyncio.WindowsSelectorEventLoopPolicy()`. While safe via `sys.platform` checks, care must be taken that Linux event loops function correctly for async transcription on Streamlit Cloud.
