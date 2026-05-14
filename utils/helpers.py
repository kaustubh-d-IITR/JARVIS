import pyaudio
from utils.logger import get_logger

logger = get_logger(__name__)

def list_audio_devices():
    """
    Lists all available PyAudio input devices for debugging.
    """
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    devices = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            dev_info = p.get_device_info_by_host_api_device_index(0, i)
            devices.append({
                "index": i,
                "name": dev_info.get('name')
            })
            logger.info(f"Input Device id {i} - {dev_info.get('name')}")
    p.terminate()
    return devices

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
