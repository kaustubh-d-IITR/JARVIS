"""
JARVIS — Startup Validation System
Checks all dependencies, files, APIs, and hardware before launch.
Run this before starting the application.
"""
import sys
import os

# Force UTF-8 output on Windows (prevents cp1252 encoding errors)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Color helpers for terminal output
class C:
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"

def ok(msg):    print(f"  {C.GREEN}[PASS]{C.RESET}  {msg}")
def fail(msg):  print(f"  {C.RED}[FAIL]{C.RESET}  {msg}")
def warn(msg):  print(f"  {C.YELLOW}[WARN]{C.RESET}  {msg}")
def info(msg):  print(f"  {C.CYAN}[INFO]{C.RESET}  {msg}")
def header(msg): print(f"\n{C.BOLD}{C.CYAN}{'='*50}\n  {msg}\n{'='*50}{C.RESET}")

def main():
    errors = 0
    warnings = 0

    header("JARVIS — Startup Validation")
    print()

    # ─── 1. Python Version ───
    header("1. Python Version")
    v = sys.version_info
    if v.major == 3 and v.minor >= 10:
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        fail(f"Python {v.major}.{v.minor}.{v.micro} — need 3.10+")
        errors += 1

    # ─── 2. Required Files ───
    header("2. Required Files")
    required_files = {
        ".env": "API keys configuration",
        "app.py": "Application entry point",
        "vision/fer_checkpoint.tar": "FER ResNet18 model weights (~85MB)",
        "vision/fer_resnet.py": "ResNet18 model architecture definition",
        "vision/emotion_detector.py": "Emotion detection module",
        "vision/posture_detector.py": "Posture detection module",
        "vision/webrtc_processor.py": "Video processor (local OpenCV)",
        "ui/dashboard.py": "Main Streamlit dashboard",
        "logic/decision_engine.py": "Intent matching brain",
        "spotify/spotify_controller.py": "Spotify playback controller",
        "voice/transcriber.py": "Deepgram transcription module",
        "llm/groq_client.py": "Groq LLM client",
        "llm/prompts.py": "LLM system prompt",
        "config/settings.py": "Settings and env loader",
    }
    for fpath, desc in required_files.items():
        if os.path.exists(fpath):
            size = os.path.getsize(fpath)
            ok(f"{fpath} ({size:,} bytes) — {desc}")
        else:
            fail(f"{fpath} MISSING — {desc}")
            errors += 1

    # ─── 3. Python Packages ───
    header("3. Python Packages")
    packages = {
        "streamlit": "Streamlit UI framework",
        "cv2": "OpenCV (computer vision)",
        "torch": "PyTorch (deep learning)",
        "torchvision": "TorchVision (transforms)",
        "mediapipe": "MediaPipe (pose detection)",
        "groq": "Groq LLM API client",
        "spotipy": "Spotify Web API client",
        "numpy": "NumPy (array math)",
        "requests": "HTTP client",
        "dotenv": "python-dotenv (.env loader)",
        "pydub": "Audio processing",
    }
    for pkg, desc in packages.items():
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "installed")
            ok(f"{pkg} ({ver}) — {desc}")
        except ImportError:
            fail(f"{pkg} NOT INSTALLED — {desc}")
            errors += 1

    # Optional package
    try:
        __import__("audio_recorder_streamlit")
        ok("audio_recorder_streamlit — Browser mic recorder")
    except ImportError:
        fail("audio_recorder_streamlit NOT INSTALLED — pip install audio-recorder-streamlit")
        errors += 1

    # ─── 4. PyTorch Device ───
    header("4. PyTorch Device")
    try:
        import torch
        if torch.cuda.is_available():
            gpu = torch.cuda.get_device_name(0)
            ok(f"CUDA available — {gpu}")
        else:
            ok("CPU mode (no CUDA GPU detected — this is fine for local use)")
        info(f"PyTorch version: {torch.__version__}")
    except Exception as e:
        fail(f"PyTorch error: {e}")
        errors += 1

    # ─── 5. Webcam Access ───
    header("5. Webcam Access")
    try:
        import cv2
        cam_found = False
        backends = []
        if sys.platform == "win32":
            backends = [(cv2.CAP_DSHOW, "DSHOW"), (None, "default")]
        else:
            backends = [(None, "default")]

        for idx in [0, 1, 2]:
            for backend_val, backend_name in backends:
                if backend_val is not None:
                    cap = cv2.VideoCapture(idx, backend_val)
                else:
                    cap = cv2.VideoCapture(idx)
                    
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        h, w = frame.shape[:2]
                        ok(f"Webcam accessible at index {idx} ({backend_name}) -- resolution {w}x{h}")
                        cam_found = True
                        cap.release()
                        break
                    cap.release()
            if cam_found:
                break
                
        if not cam_found:
            warn("No webcam detected on indices 0-2 (may be in use by another app)")
            warnings += 1
    except Exception as e:
        fail(f"Webcam error: {e}")
        errors += 1

    # ─── 6. FER Model Load Test ───
    header("6. FER Model Load Test")
    try:
        import torch
        from vision.fer_resnet import ResNet18
        model = ResNet18()
        ckpt_path = "vision/fer_checkpoint.tar"
        device = torch.device("cpu")
        ckpt = torch.load(ckpt_path, map_location=device)
        if "model_state_dict" in ckpt:
            model.load_state_dict(ckpt["model_state_dict"])
        elif "net" in ckpt:
            model.load_state_dict(ckpt["net"])
        elif "state_dict" in ckpt:
            model.load_state_dict(ckpt["state_dict"])
        else:
            model.load_state_dict(ckpt)
        model.eval()
        ok("FER ResNet18 model loaded and evaluated successfully")
        # Count parameters
        params = sum(p.numel() for p in model.parameters())
        info(f"Model parameters: {params:,}")
    except Exception as e:
        fail(f"FER model load error: {e}")
        errors += 1

    # ─── 7. API Keys ───
    header("7. API Keys (.env)")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        keys = {
            "SPOTIFY_CLIENT_ID": "Spotify OAuth",
            "SPOTIFY_CLIENT_SECRET": "Spotify OAuth",
            "SPOTIFY_REDIRECT_URI": "Spotify callback URL",
            "DEEPGRAM_API_KEY": "Deepgram speech-to-text",
            "GROQ_API_KEY": "Groq LLM inference",
            "OPENWEATHER_API_KEY": "OpenWeather context",
        }
        for key, desc in keys.items():
            val = os.getenv(key, "")
            if val:
                masked = val[:4] + "..." + val[-4:] if len(val) > 8 else "***"
                ok(f"{key} = {masked} — {desc}")
            else:
                warn(f"{key} not set — {desc} will be disabled")
                warnings += 1
    except Exception as e:
        fail(f".env loading error: {e}")
        errors += 1

    # ─── 8. MediaPipe Pose Model ───
    header("8. MediaPipe Pose Model")
    pose_model = "vision/pose_landmarker_lite.task"
    if os.path.exists(pose_model):
        size = os.path.getsize(pose_model)
        ok(f"{pose_model} ({size:,} bytes)")
    else:
        warn("Pose model not found — will auto-download on first use")
        warnings += 1

    # ─── 9. Stale Import Check ───
    header("9. Stale Code Check")
    stale_patterns = {
        "streamlit_webrtc": "Old WebRTC import (should be removed)",
        "deepface": "Old DeepFace import (replaced by PyTorch FER)",
        "tf_keras": "Old TF-Keras dependency (no longer needed)",
        "from av import": "Old av frame import (no longer needed)",
    }
    stale_files = [
        "ui/dashboard.py", "vision/emotion_detector.py",
        "vision/webrtc_processor.py", "app.py",
    ]
    found_stale = False
    for fpath in stale_files:
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        for pattern, desc in stale_patterns.items():
            if pattern in content:
                warn(f"Stale import '{pattern}' found in {fpath} — {desc}")
                warnings += 1
                found_stale = True
    if not found_stale:
        ok("No stale imports detected")

    # Summary
    header("VALIDATION SUMMARY")
    print()
    if errors == 0 and warnings == 0:
        print(f"  {C.GREEN}{C.BOLD}>> ALL CHECKS PASSED -- Ready to launch!{C.RESET}")
    elif errors == 0:
        print(f"  {C.YELLOW}{C.BOLD}>> {warnings} warning(s), 0 errors -- Can launch with reduced features.{C.RESET}")
    else:
        print(f"  {C.RED}{C.BOLD}>> {errors} error(s), {warnings} warning(s) -- Fix errors before launching.{C.RESET}")
    print()

    return errors


if __name__ == "__main__":
    errors = main()
    if errors > 0:
        print(f"\n  Fix the above {errors} error(s) and re-run this check.\n")
        sys.exit(1)
    else:
        print(f"  Run:  streamlit run app.py\n")
        sys.exit(0)
