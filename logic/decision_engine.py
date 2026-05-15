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

    def _extract_search_query(self, text: str):
        """
        Extract the actual song/artist search query from user text.
        Returns a search string, or None if nothing specific was found.
        Examples:
          "play Blue Eyes by Arijit Singh" -> "Blue Eyes Arijit Singh"
          "play music by Arijit Singh" -> "Arijit Singh"
          "play Tum Hi Ho" -> "Tum Hi Ho"
          "play music" -> None (triggers emotion fallback)
        """
        text_clean = text.strip()
        text_lower = text_clean.lower()

        # Pattern 1: "play X by Y" or "play X of Y" — extract "X Y"
        match = re.search(
            r'play\s+(?:a\s+|the\s+|some\s+|me\s+)?(?:song\s+|music\s+|track\s+)?'
            r'(?:called\s+|named\s+)?(.+?)\s+(?:by|of|from|sung by)\s+(.+)',
            text_lower
        )
        if match:
            song_part = match.group(1).strip()
            artist_part = match.group(2).strip()
            # Remove trailing filler from artist
            for filler in ["please", "for me", "now", "today"]:
                artist_part = artist_part.replace(filler, "").strip()
            if song_part in ["a", "the", "some", "music", "song", ""]:
                return artist_part  # just artist name
            return f"{song_part} {artist_part}"

        # Pattern 2: "play by Y" or "play music by Y" — just artist
        match = re.search(
            r'(?:play|music|song)\s+(?:by|of|from|sung by)\s+(.+)',
            text_lower
        )
        if match:
            artist = match.group(1).strip()
            for filler in ["please", "for me", "now", "today"]:
                artist = artist.replace(filler, "").strip()
            return artist

        # Pattern 3: "play [artist name] song/music"
        match = re.search(
            r'play\s+(.+?)\s+(?:song|music|track|playlist)',
            text_lower
        )
        if match:
            return match.group(1).strip()

        # Pattern 4: Direct name after play
        # "play Tum Hi Ho" "play Shape of You"
        match = re.search(r'play\s+(.+)', text_lower)
        if match:
            result = match.group(1).strip()
            # Remove generic words that mean "nothing specific"
            generic = ["music", "song", "a song", "the music",
                       "something", "anything", "some music"]
            if result.lower() in generic:
                return None  # signal: use emotion fallback
            return result

        return None  # signal: use emotion fallback

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

        # ── PRIORITY 2: PLAY INTENT ──
        PLAY_WORDS = ["play", "put on", "start", "listen", "music", "song"]
        play_intent = any(word in text_lower for word in PLAY_WORDS)

        # ── EXECUTE IN PRIORITY ORDER ──
        action = None
        action_msg = ""

        if pause_intent:
            # Always pause if stop word detected, regardless of other words
            success, action_msg = self.spotify.pause_music()
            action = "paused"

        elif play_intent:
            search_query = self._extract_search_query(text)

            if search_query:
                # User specified something — search for exactly that
                success, action_msg = self.spotify.play_music(query=search_query)
                action = f"playing: {action_msg}"
            else:
                # Truly generic request — use emotion/weather context
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
