from llm.groq_client import GroqClient
from llm.prompts import SYSTEM_PROMPT, build_contextual_prompt
from spotify.spotify_controller import SpotifyController
from utils.helpers import get_spotify_playlist_for_emotion
from utils.logger import get_logger
import re

logger = get_logger(__name__)


class DecisionEngine:
    """
    Central logic that decides what JARVIS should say or do based on context.
    Separates the Decision Layer from Perception and Action.
    """
    def __init__(self, groq_client: GroqClient, spotify_client: SpotifyController):
        self.groq = groq_client
        self.spotify = spotify_client
        self._last_emotion = "neutral"

    def _extract_search_query(self, text: str) -> str:
        """
        Extract the actual song/artist search query from user text.
        Examples:
          "play Blue Eyes by Arijit Singh" -> "Blue Eyes Arijit Singh"
          "play a sad song of Arijit Singh" -> "sad Arijit Singh"
          "play some rap by Sidhu Moosewala" -> "rap Sidhu Moosewala"
          "play music" -> use emotion-based fallback
        """
        text_lower = text.lower()

        # Remove filler words to get the core query
        remove_words = [
            "play", "put on", "start playing", "i want to listen to",
            "can you play", "please play", "play me", "play a", "play some",
            "play the", "song", "music", "track", "a song", "some music",
            "for me", "please", "can you", "i want", "i would like",
            "by", "of", "from", "sung by"
        ]

        query = text_lower
        for word in remove_words:
            query = query.replace(word, " ")

        # Clean up extra spaces
        query = " ".join(query.split()).strip()

        # If query is empty or too short after stripping,
        # fall back to emotion-based playlist
        if len(query) < 3:
            return get_spotify_playlist_for_emotion(self._last_emotion)

        return query

    def process_voice_command(self, text: str, emotion: str = "neutral",
                               posture: str = "unknown", weather: dict = None) -> dict:
        """
        Takes transcribed voice text and context, decides the action, and gets LLM response.
        Returns a dict with response text and optionally a suggested action.
        """
        # Store emotion for fallback playlist selection
        self._last_emotion = emotion or "neutral"

        text_lower = text.lower().strip()
        words = text_lower.split()

        # ── PRIORITY 1: STOP/PAUSE (highest priority, checked first) ──
        # These words alone = pause, even if other words present
        HARD_STOP_WORDS = [
            "pause", "stop", "halt", "quiet", "silence",
            "mute", "enough", "no music", "turn off music",
            "stop music", "pause music", "stop the music",
            "pause the music", "stop it", "pause it"
        ]

        # Check if ANY stop phrase appears in the text
        pause_intent = any(word in text_lower for word in HARD_STOP_WORDS)

        # Extra check: if text is very short (1-3 words) and contains
        # stop-like words, treat as definite pause
        if len(words) <= 3 and any(w in HARD_STOP_WORDS for w in words):
            pause_intent = True

        # ── PRIORITY 2: SPECIFIC SONG/ARTIST REQUEST ──
        # Detect if user named a specific song or artist
        SPECIFIC_INDICATORS = [
            " by ", " of ", " from ", "song called", "track called",
            "sung by", "artist", "album", "singer"
        ]
        has_specific_request = any(ind in text_lower for ind in SPECIFIC_INDICATORS)

        # Also treat as specific if user mentions a content word after "play"
        # (non-common word that isn't a filler)
        COMMON_WORDS = {"play", "music", "song", "a", "the", "some",
                        "please", "me", "for", "any", "something", "now"}
        content_words = [w for w in words if w not in COMMON_WORDS and len(w) > 3]
        if len(content_words) >= 1:
            has_specific_request = True

        # ── PRIORITY 3: GENERIC PLAY (weather/emotion based) ──
        PLAY_WORDS = ["play", "put on", "start", "listen", "music", "song"]
        play_intent = any(word in text_lower for word in PLAY_WORDS)

        # ── EXECUTE IN PRIORITY ORDER ──
        action = None
        action_msg = ""

        if pause_intent:
            # Always pause if stop word detected, regardless of other words
            success, action_msg = self.spotify.pause_music()
            action = "paused"

        elif play_intent and has_specific_request:
            # User named something specific — search for exactly that
            search_query = self._extract_search_query(text)
            success, action_msg = self.spotify.play_music(query=search_query)
            action = f"playing: {action_msg}"

        elif play_intent:
            # Generic play — use emotion context
            query = get_spotify_playlist_for_emotion(self._last_emotion)
            success, action_msg = self.spotify.play_music(query=query)
            action = f"playing: {action_msg}"

        # Generate conversational response AFTER action so LLM knows what happened
        try:
            context_prompt = build_contextual_prompt(
                user_text=text,
                emotion=emotion or "neutral",
                posture=posture or "unknown",
                weather=weather or {},
                action_taken=action_msg if action else None
            )
            llm_response = self.groq.get_response(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=context_prompt
            )
        except Exception as e:
            logger.error(f"LLM response error: {e}")
            llm_response = "I heard you. Let me help with that."

        return {
            "response": llm_response,
            "action": action,
            "action_msg": action_msg
        }

    def evaluate_autonomous_state(self, emotion: str, confidence: float, posture: str, weather: dict) -> dict:
        """
        Called by the autonomous controller loop to see if JARVIS should suggest an action.
        Returns a dict with suggested_action or None.
        """
        if emotion in ["sad", "angry"] and confidence > 0.70:
            playlist_query = get_spotify_playlist_for_emotion(emotion)
            suggestion_text = f"I detected you might be feeling {emotion}. Would you like me to play a {playlist_query} playlist?"
            return {
                "suggested_action": "play_music",
                "query": playlist_query,
                "message": suggestion_text
            }

        return {"suggested_action": None}
