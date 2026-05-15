from llm.groq_client import GroqClient
from llm.prompts import SYSTEM_PROMPT, build_contextual_prompt
from spotify.spotify_controller import SpotifyController
from utils.helpers import get_spotify_playlist_for_emotion
from utils.logger import get_logger
import re

logger = get_logger(__name__)

PLAY_KEYWORDS = ["play", "put on", "start", "listen", "song",
                 "music", "track", "sing"]

PAUSE_KEYWORDS = ["pause", "stop", "stop music", "stop the music",
                  "turn off", "no music", "quiet", "silence"]


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

    def process_voice_command(self, text: str, emotion: str, posture: str, weather: dict) -> dict:
        """
        Takes transcribed voice text and context, decides the action, and gets LLM response.
        Returns a dict with response text and optionally a suggested action.
        """
        # Store emotion for fallback playlist selection
        self._last_emotion = emotion or "neutral"

        text_lower = text.lower()

        # --- PAUSE/STOP INTENT (check first, higher priority) ---
        pause_intent = any(kw in text_lower for kw in PAUSE_KEYWORDS)

        # --- PLAY INTENT ---
        play_intent = any(kw in text_lower for kw in PLAY_KEYWORDS)

        action = None
        action_msg = ""

        if pause_intent and not play_intent:
            # Pure stop/pause command
            success, msg = self.spotify.pause_music()
            action = "pause"
            action_msg = msg
        elif play_intent:
            # Extract what the user actually wants to play
            search_query = self._extract_search_query(text)
            success, msg = self.spotify.play_music(query=search_query)
            action = "play_music"
            action_msg = msg

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
        # MVP Behavior: Suggest playing music if the user is sad/angry and not currently doing anything.
        if emotion in ["sad", "angry"] and confidence > 0.70:
            playlist_query = get_spotify_playlist_for_emotion(emotion)
            suggestion_text = f"I detected you might be feeling {emotion}. Would you like me to play a {playlist_query} playlist?"
            return {
                "suggested_action": "play_music",
                "query": playlist_query,
                "message": suggestion_text
            }

        return {"suggested_action": None}
