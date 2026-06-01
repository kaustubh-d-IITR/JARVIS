import base64
import json
import time
import re
import traceback
from io import BytesIO
from PIL import Image
from config.settings import settings
from utils.logger import get_logger
import google.generativeai as genai

logger = get_logger(__name__)

class VLMEmotionAnalyzer:
    """
    Multimodal Emotion Analyzer using Google Gemini exclusively.
    """
    def __init__(self):
        self.selected_model = "gemini-2.5-flash"
        logger.info(f"[VLM] Initialized with model: {self.selected_model}")

    def _parse_and_validate_json(self, raw_content: str, latency: int) -> dict:
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
            "model_used": self.selected_model,
            "emotion": primary_emotion,
            "provider_error": None,
            "provider_used": "gemini"
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
            "provider_used": "none"
        }

    def analyze_snapshot(self, image_data) -> dict:
        """Runs facial-first multimodal reasoning exclusively using Gemini."""
        gemini_key = settings.GEMINI_API_KEY
        if not gemini_key:
            return self._get_safe_fallback_schema("GEMINI_API_KEY missing from settings")

        try:
            # 1. Image Pipeline with Compression
            if isinstance(image_data, Image.Image):
                img = image_data
            elif hasattr(image_data, 'getvalue'):
                img = Image.open(BytesIO(image_data.getvalue()))
            elif isinstance(image_data, bytes):
                img = Image.open(BytesIO(image_data))
            else:
                img = image_data
            
            img = img.convert("RGB")
            img.thumbnail((512, 512))
            
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

            logger.info("[VLM PROVIDER] Starting Gemini Vision analysis")
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(self.selected_model)
            
            t0 = time.time()
            response = model.generate_content([prompt, img])
            latency = round((time.time() - t0) * 1000)
            
            logger.info(f"[VLM PROVIDER] Gemini succeeded in {latency}ms")
            return self._parse_and_validate_json(response.text, latency)

        except Exception as e:
            logger.error("\n==================================================")
            logger.error("[VLM DEBUG] FAILURE TRACE")
            logger.error("=========================")
            logger.error(traceback.format_exc())
            return self._get_safe_fallback_schema(f"Fatal Error: {str(e)}")

    def analyze_emotion(self, image_data) -> dict:
        return self.analyze_snapshot(image_data)

    def get_debug_state(self):
        return {
            "selected_model": self.selected_model,
            "api_ready": bool(settings.GEMINI_API_KEY)
        }
