import os
import time
import glob
import json
from pathlib import Path
from dotenv import load_dotenv

# Step 2: Load ENV Variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
print(f"GEMINI_API_KEY EXISTS = {bool(api_key)}")

if not api_key:
    print("[WARNING] GEMINI_API_KEY is not set in the environment variables.")
    exit(1)

# Step 3: Use REAL Gemini SDK
try:
    import google.generativeai as genai
    from PIL import Image
except ImportError as e:
    print(f"[ERROR] Required packages not found: {e}")
    print("Please install google-generativeai and pillow.")
    exit(1)

genai.configure(api_key=api_key)

# Step 4: Load Image
latest_capture = None
if os.path.exists("captured_frames/latest_capture.jpg"):
    latest_capture = "captured_frames/latest_capture.jpg"
else:
    # find newest image in session_*
    sessions = sorted(glob.glob("captured_frames/session_*"), key=os.path.getmtime, reverse=True)
    for session in sessions:
        images = sorted(glob.glob(os.path.join(session, "*.jpg")), key=os.path.getmtime, reverse=True)
        if images:
            latest_capture = images[0]
            break

if not latest_capture:
    print("[ERROR] No images found in captured_frames/")
    exit(1)

try:
    img = Image.open(latest_capture)
    print(f"Exact image path: {latest_capture}")
    print(f"Image dimensions: {img.size}")
    print(f"File size: {os.path.getsize(latest_capture)} bytes")
except Exception as e:
    print(f"[ERROR] Could not load image: {e}")
    exit(1)

# Step 5: Send to Gemini Vision
model_name = "gemini-2.5-flash"
prompt = """Analyze the person's facial emotion in this image. Return ONLY valid JSON with:
face_detected,
primary_emotion,
secondary_emotion,
confidence,
facial_cues,
mood_summary,
music_vibe"""

print("\n==================================================")
print("[GEMINI DEBUG] API key loaded status:", bool(api_key))
print("[GEMINI DEBUG] Gemini model used:", model_name)
print("[GEMINI DEBUG] Request started...")

t0 = time.time()
try:
    model = genai.GenerativeModel(model_name)
    response = model.generate_content([prompt, img])
    latency = time.time() - t0
    
    print(f"[GEMINI DEBUG] Request latency: {latency:.2f} seconds")
    print(f"[GEMINI DEBUG] Raw Gemini response:\n{response.text}")
    
    # Strip markdown and parse JSON
    import re
    raw_content = response.text
    json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
    json_str = json_match.group(0) if json_match else raw_content
    
    parsed = json.loads(json_str)
    print(f"[GEMINI DEBUG] Parsed JSON:\n{json.dumps(parsed, indent=2)}")
    
    print("\n[GEMINI TEST SUCCESS]")
except Exception as e:
    latency = time.time() - t0
    print(f"[GEMINI DEBUG] Request latency: {latency:.2f} seconds")
    print(f"[GEMINI DEBUG] Exceptions:\n{str(e)}")
    import traceback
    print(f"[GEMINI DEBUG] Stack trace:\n{traceback.format_exc()}")
    print("\n[GEMINI TEST FAILED] Exact reason:", str(e))
