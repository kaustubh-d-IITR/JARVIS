from utils.logger import get_logger

logger = get_logger(__name__)

def get_spotify_playlist_for_emotion(emotion: str) -> str:
    """
    Returns a suitable search query or genre based on the detected emotion.
    """
    emotion = emotion.lower()
    mapping = {
        "happy": "energetic upbeat playlist",
        "sad": "calm peaceful acoustic",
        "angry": "relaxing chill lofi",
        "neutral": "focus concentration instrumental",
        "fear": "soothing ambient",
        "surprise": "pop hits"
    }
    return mapping.get(emotion, "chill focus")
