# Docker Deployment Plan

## Runtime Architecture

JARVIS will run inside a lightweight `python:3.11-slim` container. It relies heavily on external cloud APIs (OpenRouter, Gemini, Deepgram, Groq, OpenWeather, Spotify) for all ML and perception tasks, keeping the container footprint extremely small. The local application purely orchestrates the UI, device I/O (camera/mic via WebRTC), and state management.

## Exposed Ports

- **8501**: Streamlit's default port. Required to access the web dashboard from the host machine.

## Volume Requirements

- No persistent local database is used.
- Optional: Bind mount for `captured_frames/` if long-term storage of session captures is required, though typical Docker deployments will let this remain ephemeral since it's just runtime telemetry.

## Environment Variables

The following secrets must be passed to the container (e.g., via `--env-file .env`):
- `OPENROUTER_API_KEY` (Primary Vision)
- `GEMINI_API_KEY` (Fallback Vision)
- `GROQ_API_KEY` (LLM Reasoning)
- `DEEPGRAM_API_KEY` (Voice Transcription)
- `OPENWEATHER_API_KEY` (Context)
- `SPOTIFY_CLIENT_ID` (Music Integration)
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_REDIRECT_URI`

## Startup Sequence

1. `ENV PYTHONUNBUFFERED=1` ensures logs stream to Docker immediately.
2. OS-level dependencies (if any, like `libgl1` for OpenCV) are installed.
3. Python packages from `requirements.txt` are installed.
4. Source code is copied.
5. The container launches using:
   `CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]`
