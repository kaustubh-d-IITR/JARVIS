# Deployment Audit Report

## Repository Overview

- **Total File Count:** 399
- **Python Files:** 28
- **Config Files:** `.env`, `.env.example`, `.gitignore`, `requirements.txt`, `config/settings.py`
- **Assets:** `README.md`, `SYSTEM_MANUAL.md`, `docs/`
- **Models:** No explicit ML models stored locally.
- **Hidden Files:** 0 explicitly tracked hidden files in the repository root outside `.git` and `.env`.

### Complete Folder Tree (Root Level)

- `.git/`
- `__pycache__/`
- `captured_frames/`
- `config/`
- `docs/`
- `llm/`
- `logic/`
- `scratch/`
- `spotify/`
- `tests/`
- `ui/`
- `utils/`
- `vision/`
- `voice/`
- `weather/`

## Critical Runtime Files

- **Entry Point File:** `app.py`
- **Streamlit Entry File:** `ui/dashboard.py`
- **Startup Scripts:** `run_jarvis.bat`, `run_jarvis.sh`, `run_local.bat`, `run_local.sh`, `setup_local.bat`, `setup_local.sh`, `startup_check.py`
- **Requirements File:** `requirements.txt`
- **Environment Configuration:** `.env` and `.env.example`
- **Docker-Relevant Files:** Currently missing `Dockerfile`, `docker-compose.yml`, and `.dockerignore`.

## Deployment Risks

- **Missing Dependencies:** `google-generativeai` (required for Gemini fallback) is absent from `requirements.txt`.
- **Hardcoded Paths / Local-Only References:** Windows-specific paths like `venv\Scripts\activate.bat` exist in `run_jarvis.bat` and `setup_local.bat`, posing cross-platform issues without Dockerization.
- **Missing Environment Variables:** No production defaults exist; secrets are managed strictly through `.env`.
- **Temporary Artifacts:** `captured_frames/` contains runtime images and `temp_audio.wav` might be created locally. These must be excluded.

## Git Status

- **Branch:** `main` (Up to date with `origin/main`)
- **Modified Files:** `.env.example`, `README.md`, `config/settings.py`, `logic/autonomous_controller.py`, `logic/decision_engine.py`, `requirements.txt`, `setup_local.bat`, `setup_local.sh`, `spotify/spotify_controller.py`, `startup_check.py`, `ui/dashboard.py`, `vision/webrtc_processor.py`.
- **Deleted Files:** `tests/test_fer_pipeline.py`, `vision/emotion_detector.py`, `vision/fer_checkpoint.tar`, `vision/fer_resnet.py`, `vision/posture_detector.py`.
- **Untracked Files:** `captured_frames/`, `docs/`, `scratch/`, `tests/test_gemini_vision.py`, `utils/clear_hf_cache.py`, `vision/vlm_emotion_analyzer.py`.
