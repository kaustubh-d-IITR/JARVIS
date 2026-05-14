import os
import cv2
import pyaudio
import requests
from dotenv import load_dotenv

def check_env_vars():
    """Checks if all required environment variables are set."""
    load_dotenv()
    required_keys = [
        "SPOTIFY_CLIENT_ID",
        "SPOTIFY_CLIENT_SECRET",
        "DEEPGRAM_API_KEY",
        "GROQ_API_KEY",
        "OPENWEATHER_API_KEY"
    ]
    
    missing = []
    for key in required_keys:
        if not os.getenv(key):
            missing.append(key)
            
    if missing:
        print(f"[FAIL] Missing API Keys in .env: {', '.join(missing)}")
        return False
    print("[OK] All API keys found in .env")
    return True

def check_camera():
    """Validates camera access."""
    camera_index = int(os.getenv("CAMERA_INDEX", 0))
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"[FAIL] Camera at index {camera_index} is unavailable or locked.")
        return False
    ret, frame = cap.read()
    if not ret:
        print(f"[FAIL] Cannot read frames from camera at index {camera_index}.")
        cap.release()
        return False
    cap.release()
    print("[OK] Camera access verified.")
    return True

def check_microphone():
    """Validates microphone access."""
    p = pyaudio.PyAudio()
    try:
        default_device = p.get_default_input_device_info()
        print(f"[OK] Microphone access verified: {default_device.get('name')}")
        p.terminate()
        return True
    except IOError:
        print("[FAIL] No default microphone found or microphone is locked.")
        p.terminate()
        return False

def run_all_checks():
    print("=========================================")
    print("      JARVIS Startup Validation          ")
    print("=========================================\n")
    
    env_ok = check_env_vars()
    cam_ok = check_camera()
    mic_ok = check_microphone()
    
    print("\n=========================================")
    if env_ok and cam_ok and mic_ok:
        print("[OK] ALL SYSTEMS GO. Launching JARVIS...")
        return True
    else:
        print("[WARN] Some checks failed. JARVIS may run with limited functionality.")
        return False

if __name__ == "__main__":
    run_all_checks()
