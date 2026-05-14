from llm.groq_client import GroqClient
from llm.prompts import SYSTEM_PROMPT, build_contextual_prompt
from spotify.spotify_controller import SpotifyController
from utils.helpers import get_spotify_playlist_for_emotion
from utils.logger import get_logger

logger = get_logger(__name__)

class DecisionEngine:
    """
    Central logic that decides what JARVIS should say or do based on context.
    Separates the Decision Layer from Perception and Action.
    """
    def __init__(self, groq_client: GroqClient, spotify_client: SpotifyController):
        self.groq = groq_client
        self.spotify = spotify_client
        
    def process_voice_command(self, text: str, emotion: str, posture: str, weather: dict) -> dict:
        """
        Takes transcribed voice text and context, decides the action, and gets LLM response.
        Returns a dict with response text and optionally a suggested action.
        """
        action = None
        action_msg = ""
        text_lower = text.lower()
        
        # Simple local intent matching for hardcoded commands
        if "play music" in text_lower or "play some music" in text_lower:
            playlist_query = get_spotify_playlist_for_emotion(emotion)
            success, msg = self.spotify.play_music(query=playlist_query)
            action = "played_music"
            action_msg = msg
        elif "pause" in text_lower or "stop music" in text_lower:
            success, msg = self.spotify.pause_music()
            action = "paused_music"
            action_msg = msg
            
        # Generate conversational response
        context_prompt = build_contextual_prompt(text, emotion, posture, weather)
        llm_response = self.groq.get_response(SYSTEM_PROMPT, context_prompt)
        
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
