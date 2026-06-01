import base64
import requests
import json
import time
import re
import traceback
import os
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image
from config.settings import settings
from utils.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

class VLMEmotionAnalyzer:
    """
    Multimodal Emotion Analyzer.
    Features automatic fallback and retry logic for OpenRouter APIs.
    """
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        
        self.primary_model = "nvidia/nemotron-nano-12b-v2-vl:free"
        self.fallback_model = "nvidia/nemotron-nano-12b-v2-vl:free"
        self.selected_model = self.primary_model
        
        self.last_successful_result = None
        
        logger.info(f"[VLM] Initialized with primary model: {self.selected_model}")

    def _parse_and_validate_json(self, raw_content: str, latency: int, model_used: str) -> dict:
        """Robustly extracts and validates JSON from VLM responses."""
        logger.info("\n==================================================")
        logger.info("[VLM DEBUG] JSON EXTRACTION")
        logger.info("===========================")
        logger.info(f"* extracted content before parsing:\n{raw_content}")

        # 1. Strip markdown and extract first valid JSON block
        json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        json_str = json_match.group(0) if json_match else raw_content
        
        logger.info(f"* cleaned JSON text:\n{json_str}")
            
        parsed = {}
        try:
            parsed = json.loads(json_str)
            logger.info(f"* parsed dict keys: {list(parsed.keys())}")
            expected_keys = {"face_detected", "primary_emotion", "secondary_emotion", "confidence", "facial_cues", "mood_summary", "music_vibe"}
            missing_keys = expected_keys - set(parsed.keys())
            logger.info(f"* missing keys: {list(missing_keys)}")
        except Exception as e:
            logger.error("\n==================================================")
            logger.error("[VLM DEBUG] FAILURE TRACE")
            logger.error("=========================")
            logger.error(traceback.format_exc())
            
        if not parsed:
            raise ValueError("Invalid JSON returned by provider")

        # 2. Validate required keys and fill missing with safe defaults
        primary_emotion = parsed.get("primary_emotion", "neutral").lower()
        
        return {
            "face_detected": bool(parsed.get("face_detected", True)),
            "primary_emotion": primary_emotion,
            "secondary_emotion": str(parsed.get("secondary_emotion", "neutral")),
            "confidence": float(parsed.get("confidence", 0.0)),
            "facial_cues": parsed.get("facial_cues", []) if isinstance(parsed.get("facial_cues"), list) else [],
            "mood_summary": str(parsed.get("mood_summary", "No summary available.")),
            "music_vibe": str(parsed.get("music_vibe", "chill")),
            "api_latency_ms": latency,
            "model_used": model_used,
            "emotion": primary_emotion,  # Maintained for backward compatibility with older dashboard fields
            "provider_error": None,
            "provider_used": "gemini_fallback" if "gemini" in model_used.lower() else "openrouter_primary"
        }

    def _get_safe_fallback_schema(self, reason: str) -> dict:
        """Returns a guaranteed safe schema to prevent frontend crashes."""
        print(f"[VLM PROVIDER ERROR] Exact provider error: {reason}")
        return {
            "face_detected": False,
            "primary_emotion": "neutral",
            "secondary_emotion": "none",
            "confidence": 0.0,
            "facial_cues": [],
            "mood_summary": reason,
            "music_vibe": "chill",
            "api_latency_ms": 0,
            "model_used": self.selected_model,
            "emotion": "neutral",
            "provider_error": reason,
            "provider_used": "fallback_cache" if getattr(self, 'last_successful_result', None) else "none"
        }

    def _handle_fallback(self, reason: str) -> dict:
        """State preservation logic: returns last cached result if available."""
        if self.last_successful_result is not None:
            logger.info("\n==================================================")
            logger.info("[VLM CACHE] Using last successful result due to provider failure.")
            logger.info(f"[VLM CACHE] Last valid emotion reused: {self.last_successful_result.get('emotion')}")
            logger.info(f"[VLM CACHE] Previous confidence reused: {self.last_successful_result.get('confidence')}")
            logger.info(f"[VLM PROVIDER ERROR] Exact provider error: {reason}")
            
            print("[VLM CACHE] Using last successful result due to provider failure.")
            print(f"[VLM CACHE] Last valid emotion reused: {self.last_successful_result.get('emotion')}")
            print(f"[VLM CACHE] Previous confidence reused: {self.last_successful_result.get('confidence')}")
            print(f"[VLM PROVIDER ERROR] Exact provider error: {reason}")
            
            cached_result = self.last_successful_result.copy()
            # Append warnings
            cached_result["provider_warning"] = "Vision provider temporarily overloaded"
            cached_result["provider_error"] = "Vision provider temporarily overloaded"
            return cached_result
        else:
            return self._get_safe_fallback_schema(reason)

    def _run_gemini_fallback(self, img: Image.Image, prompt: str) -> dict:
        gemini_key = os.getenv("GEMINI_API_KEY")

        print("=" * 60)
        print("[GEMINI DEBUG] ENV CHECK")
        print("GEMINI_API_KEY EXISTS =", bool(gemini_key))

        if gemini_key:
            print("FIRST 10 CHARS =", gemini_key[:10])

        print("=" * 60)

        print("[VLM PROVIDER] Switching to Gemini Vision fallback")
        logger.info("[VLM PROVIDER] Switching to Gemini Vision fallback")
        
        if not gemini_key:
            print("[DIAGNOSTIC] GEMINI_API_KEY is missing from environment variables.")
            raise ValueError("GEMINI_API_KEY is missing from environment variables.")
            
        t0 = time.time()
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content([prompt, img])
            latency = round((time.time() - t0) * 1000)
            
            print("[VLM PROVIDER] Gemini fallback succeeded")
            logger.info("[VLM PROVIDER] Gemini fallback succeeded")
            logger.info(f"* Gemini latency: {latency}ms")
            logger.info("* Gemini model name: gemini-2.5-flash")
            
            return self._parse_and_validate_json(response.text, latency, "gemini-2.5-flash")
        except Exception as e:
            print("[VLM PROVIDER] Gemini fallback failed")
            logger.error("[VLM PROVIDER] Gemini fallback failed")
            logger.error(traceback.format_exc())
            raise Exception(f"Gemini fallback failed: {str(e)}")

    def analyze_snapshot(self, image_data) -> dict:
        """Runs facial-first multimodal reasoning with strict timeout and no retries."""
        if not self.api_key:
            return self._handle_fallback("OPENROUTER_API_KEY missing")

        try:
            # 1. Image Pipeline with Compression
            try:
                if isinstance(image_data, Image.Image):
                    img = image_data
                elif hasattr(image_data, 'getvalue'):
                    img = Image.open(BytesIO(image_data.getvalue()))
                elif isinstance(image_data, bytes):
                    img = Image.open(BytesIO(image_data))
                else:
                    img = image_data
                
                # Resize to max 512x512, preserving aspect ratio
                img = img.convert("RGB")
                img.thumbnail((512, 512))
                resized_dimensions = img.size
                
                # Compress heavily using JPEG
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=55)
                image_bytes = buffer.getvalue()
            except Exception as e:
                logger.error(f"[VLM] Image processing failed: {e}")
                return self._handle_fallback(f"Image processing failed: {str(e)}")

            base64_image = base64.b64encode(image_bytes).decode('utf-8')

            # 2. Refined Prompt (Facial Priority)
            prompt = """
            Analyze the person's facial expression in this image.
            
            STRICT RULES:
            1. PRIORITIZE facial muscles, eyes, smile, and jaw tension.
            2. IGNORE background, room lighting, wall colors, or isolation context.
            3. If the face is neutral and relaxed, classify as 'calm' or 'neutral'.
            
            Return ONLY valid JSON:
            {
              "face_detected": true,
              "primary_emotion": "happy/sad/neutral/angry/calm/excited/tired",
              "secondary_emotion": "string",
              "confidence": 0.0 to 1.0,
              "facial_cues": ["cue 1", "cue 2", "cue 3"],
              "mood_summary": "1-sentence summary",
              "music_vibe": "style of music"
            }
            """

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/kaustubh-d-IITR/JARVIS",
                "X-Title": "JARVIS VLM Assistant"
            }

            current_model = self.primary_model
            last_error_reason = ""

            payload = {
                "model": current_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                "response_format": {"type": "json_object"}
            }

            masked_key = f"{self.api_key[:6]}...{self.api_key[-4:]}" if self.api_key and len(self.api_key) > 10 else "HIDDEN"
            masked_headers = headers.copy()
            masked_headers["Authorization"] = f"Bearer {masked_key}"
            payload_str = json.dumps(payload)
            
            payload_size_bytes = len(payload_str.encode('utf-8'))
            payload_size_kb = payload_size_bytes / 1024

            logger.info("\n==================================================")
            logger.info("[VLM DEBUG] START REQUEST")
            logger.info("=========================")
            logger.info(f"1. Selected model name: {current_model}")
            logger.info(f"2. Resized image dimensions: {resized_dimensions}")
            logger.info(f"3. OpenRouter endpoint: {self.url}")
            logger.info(f"4. Final compressed payload size: {payload_size_kb:.2f} KB ({payload_size_bytes} bytes)")
            logger.info(f"5. Base64 image exists: {bool(base64_image)}")
            logger.info(f"6. Request timeout value: 30s")
            logger.info(f"7. Exact headers being sent: {masked_headers}")

            print(f"[VLM PROVIDER] Using OpenRouter Nvidia")
            print(f"[VLM REQUEST] MODEL = {current_model}")
            request_start = time.time()
            t0 = request_start
            
            try:
                response = requests.post(self.url, headers=headers, json=payload, timeout=30)
                latency = round((time.time() - t0) * 1000)
                
                print(f"[VLM TOTAL LATENCY] {(time.time()-request_start):.2f}s")
                print(f"[VLM RESPONSE STATUS] = {response.status_code}")
                
                logger.info("\n==================================================")
                logger.info("[VLM DEBUG] RAW RESPONSE")
                logger.info("========================")
                logger.info(f"* exact API latency: {latency}ms")
                logger.info(f"* exact request timeout value: 30s")
                logger.info(f"* response.status_code: {response.status_code}")
                logger.info(f"* response.headers: {dict(response.headers)}")
                logger.info(f"* FULL raw response.text:\n{response.text}")
                
                if response.status_code == 200:
                    response_json = response.json()
                    
                    if "error" in response_json:
                        error_code = response_json["error"].get("code")
                        error_message = response_json["error"].get("message")
                        
                        if error_code in [502, 503, 504]:
                            raise requests.exceptions.Timeout(
                                f"Provider overloaded ({error_code})"
                            )
                        else:
                            raise Exception(f"Provider returned error ({error_code}): {error_message}")
                            
                    content = response_json.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                    
                    # Apply strong JSON extraction
                    result = self._parse_and_validate_json(content, latency, current_model)
                    
                    if result.get("face_detected"):
                        self.last_successful_result = result.copy()
                    
                    self.selected_model = current_model
                    return result
                    
                elif response.status_code in [502, 503, 504]:
                    last_error_reason = f"Vision provider temporarily unavailable ({response.status_code})"
                else:
                    last_error_reason = f"API Error ({response.status_code})"
                    
            except requests.exceptions.Timeout as e:
                logger.error("[VLM DEBUG] OpenRouter Timeout")
                last_error_reason = "Vision API timeout"
                
            except Exception as e:
                logger.error(f"[VLM DEBUG] OpenRouter Exception: {e}")
                if "Invalid JSON" in str(e):
                    last_error_reason = "Invalid JSON returned by provider"
                else:
                    last_error_reason = str(e)
            
            print("[VLM PROVIDER] OpenRouter failed")
            
            # --- GEMINI FALLBACK TRIGGER ---
            try:
                gemini_result = self._run_gemini_fallback(img, prompt)
                
                if gemini_result.get("face_detected"):
                    self.last_successful_result = gemini_result.copy()
                
                self.selected_model = "gemini-2.5-flash"
                return gemini_result
                
            except Exception as gemini_e:
                last_error_reason = f"OpenRouter failed ({last_error_reason}) | {str(gemini_e)}"
                return self._handle_fallback(last_error_reason)

        except Exception as e:
            logger.error("\n==================================================")
            logger.error("[VLM DEBUG] FAILURE TRACE")
            logger.error("=========================")
            logger.error(traceback.format_exc())
            return self._handle_fallback(f"Fatal Error: {str(e)}")

    def analyze_emotion(self, image_data) -> dict:
        return self.analyze_snapshot(image_data)

    def get_debug_state(self):
        return {
            "selected_model": self.selected_model,
            "primary_model": self.primary_model,
            "fallback_model": self.fallback_model,
            "api_ready": bool(self.api_key)
        }
