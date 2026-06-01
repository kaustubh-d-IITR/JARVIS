# GitHub Deployment Checklist

## Files Ready To Commit

- `.env.example`
- `README.md`
- `config/settings.py`
- `logic/autonomous_controller.py`
- `logic/decision_engine.py`
- `requirements.txt` (Needs `google-generativeai` added)
- `setup_local.bat`
- `setup_local.sh`
- `spotify/spotify_controller.py`
- `startup_check.py`
- `ui/dashboard.py`
- `vision/webrtc_processor.py`
- `vision/vlm_emotion_analyzer.py`
- `tests/test_gemini_vision.py`
- `utils/clear_hf_cache.py`
- `DEPLOYMENT_AUDIT.md` (Self)

**Deletions to commit:**
- `tests/test_fer_pipeline.py`
- `vision/emotion_detector.py`
- `vision/fer_checkpoint.tar`
- `vision/fer_resnet.py`
- `vision/posture_detector.py`

## Files That Should Never Be Committed

- `.env`
- `captured_frames/`
- `temp_audio.wav` (if present)
- `__pycache__/`
- `venv/`, `env/`, `.venv/`
- `.streamlit/secrets.toml`
- Any user credentials or tokens
- `.DS_Store`, `Thumbs.db`

## Recommended .gitignore

The existing `.gitignore` covers almost everything, but it is missing:
- `captured_frames/`
- `logs/`
- `node_modules/` (if any future frontend integration happens)
- `scratch/`

I will append these safely to `.gitignore` before committing.
