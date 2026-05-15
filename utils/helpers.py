from utils.logger import get_logger

logger = get_logger(__name__)

def get_spotify_playlist_for_emotion(emotion: str) -> str:
    """
    Returns a suitable search query based on the detected emotion.
    Tuned for better Spotify search results with genre + mood keywords.
    """
    mapping = {
        "happy":    "top hits upbeat energetic playlist",
        "sad":      "sad emotional hindi songs arijit singh",
        "angry":    "lofi chill calm relaxing playlist",
        "neutral":  "top bollywood hindi songs playlist",
        "fear":     "soothing calm ambient playlist",
        "surprise": "party hits popular songs playlist",
        "disgust":  "chill vibes relaxing music playlist",
    }
    return mapping.get(emotion.lower(), "top hindi songs playlist")
