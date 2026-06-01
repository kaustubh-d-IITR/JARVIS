# DEPLOYMENT AND ENVIRONMENT

JARVIS is designed to be hardware-agnostic and fully containerizable, relying on cloud APIs rather than local GPUs for AI processing.

## 1. Environment Configuration (`.env`)

The entire system is configured via a single `.env` file loaded dynamically by `config/settings.py`.

```env
# Perception (Vision)
OPENROUTER_API_KEY=sk-or-v1-...

# Reasoning (Chat)
GROQ_API_KEY=gsk_...

# Hearing (Speech-to-Text)
DEEPGRAM_API_KEY=...

# Context (Weather)
OPENWEATHER_API_KEY=...

# Action (Spotify Execution)
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8501/callback
```

## 2. Infrastructure Footprint

By decommissioning the local CNN/FER OpenCV pipeline, the deployment footprint has shrunk drastically:
- **No PyTorch/TensorFlow Required.**
- **No CUDA Dependencies.**
- Runs entirely on a standard Python 3.10+ runtime.

**Core Dependencies (`requirements.txt`):**
- `streamlit` (UI framework)
- `spotipy` (Spotify API)
- `groq` (Conversational LLM)
- `pillow`, `opencv-python-headless` (Basic image routing)
- `audio-recorder-streamlit` (Browser microphone access)

## 3. Application Lifecycle (Startup Scripts)

The application is launched via `run_jarvis.bat` (Windows) or `run_jarvis.sh` (Linux/Mac).

### The Boot Sequence (`startup_check.py`)
Before Streamlit binds to the port, `startup_check.py` performs a mandatory pre-flight validation:
1. Validates all `API_KEY`s exist in the `.env` file.
2. Checks that required python modules are available.
3. Sends an HTTP GET request to OpenRouter to ensure `nvidia/nemotron-nano-12b-v2-vl:free` is actively listed in the global model catalog.
4. If any check fails, the batch script terminates immediately with an explicit error, preventing confusing runtime crashes inside the Streamlit GUI.

## 4. Hardware Independence

- **Webcam:** Handled entirely by the browser (via `st.camera_input`). No backend video streaming loop is required.
- **Audio:** Handled by the browser microphone.
- This means the JARVIS backend can be hosted on a cheap cloud VPS (like Render or DigitalOcean), and the user can interact with the UI via their phone or laptop, and the camera/mic will utilize the client's local hardware automatically.
