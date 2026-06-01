import os
import sys
import time
import requests
from config.settings import settings

def header(text):
    print(f"\n{'='*50}")
    print(f" {text}")
    print(f"{'='*50}")

def ok(msg):
    print(f"  [OK] {msg}")

def warn(msg):
    print(f"  [WARN] {msg}")

def fail(msg):
    print(f"  [FAIL] {msg}")

def main():
    errors = 0
    warnings = 0

    header("JARVIS STARTUP VALIDATION (RESTORED VLM EDITION)")

    # ─── 1. Configuration Check ───
    header("1. Configuration Check")
    if os.path.exists(".env"):
        ok(".env file found")
    else:
        fail(".env file missing")
        errors += 1

    # ─── 2. API Key Validation ───
    header("2. API Key Validation")
    if settings.OPENROUTER_API_KEY:
        ok("OPENROUTER_API_KEY found")
    else:
        fail("OPENROUTER_API_KEY missing")
        errors += 1

    # ─── 3. Locked Model Verification ───
    header("3. Vision Model Verification (LOCKED)")
    target_model = "nvidia/nemotron-nano-12b-v2-vl:free"
    
    if settings.OPENROUTER_API_KEY:
        try:
            url = "https://openrouter.ai/api/v1/models"
            headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                available = [m['id'] for m in response.json().get('data', [])]
                
                if target_model in available:
                    ok(f"Confirmed: Working model '{target_model}' is AVAILABLE.")
                else:
                    fail(f"CRITICAL: Confirmed model '{target_model}' NOT FOUND in active list.")
                    errors += 1
            else:
                fail(f"OpenRouter API Error {response.status_code}: {response.text[:200]}")
                errors += 1
        except Exception as e:
            fail(f"Model verification failed: {e}")
            errors += 1
    else:
        fail("API Key missing - skipping verification.")
        errors += 1

    # ─── 4. Dependencies Check ───
    header("4. Core Module Check")
    deps = ["streamlit", "requests", "PIL", "cv2", "groq", "spotipy"]
    for dep in deps:
        try:
            __import__(dep)
            ok(f"Module '{dep}' ready")
        except ImportError:
            fail(f"Module '{dep}' missing")
            errors += 1

    header("STARTUP SUMMARY")
    print(f"  Errors:   {errors}")
    print(f"  Warnings: {warnings}")
    
    if errors > 0:
        print(f"\n  [!] CRITICAL: Revert failed. Please check OpenRouter status.")
        sys.exit(1)
    else:
        print("\n  [✔] SUCCESS: Confirmed VLM Pipeline restored.")
        sys.exit(0)

if __name__ == "__main__":
    main()
