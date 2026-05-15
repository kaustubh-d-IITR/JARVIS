import os
from dotenv import load_dotenv

DEBUG_INFO = {}

def reload_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    DEBUG_INFO['env_path'] = env_path
    DEBUG_INFO['env_exists'] = os.path.exists(env_path)
    
    # Try multiple paths just in case
    if not os.path.exists(env_path):
        env_path = '.env'
        DEBUG_INFO['fallback_env_exists'] = os.path.exists(env_path)
        
    result = load_dotenv(env_path, override=True)
    DEBUG_INFO['dotenv_loaded'] = result

class Settings:
    def __init__(self):
        reload_env()
        
    @property
    def SPOTIFY_CLIENT_ID(self):
        reload_env()
        return os.getenv("SPOTIFY_CLIENT_ID", "")
        
    @property
    def SPOTIFY_CLIENT_SECRET(self):
        return os.getenv("SPOTIFY_CLIENT_SECRET", "")
        
    @property
    def SPOTIFY_REDIRECT_URI(self):
        return os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8501/callback")
        
    @property
    def DEEPGRAM_API_KEY(self):
        return os.getenv("DEEPGRAM_API_KEY", "")
        
    @property
    def GROQ_API_KEY(self):
        return os.getenv("GROQ_API_KEY", "")
        
    @property
    def OPENWEATHER_API_KEY(self):
        return os.getenv("OPENWEATHER_API_KEY", "")
        
    @property
    def LOCATION(self):
        return os.getenv("LOCATION", "London, UK")
        
    @property
    def CAMERA_INDEX(self):
        return int(os.getenv("CAMERA_INDEX", 0))
        
    @property
    def GROQ_MODEL(self):
        return "llama-3.3-70b-versatile"
        
    @property
    def AUTONOMOUS_COOLDOWN_SECONDS(self):
        return 60
        
    @property
    def EMOTION_CONFIDENCE_THRESHOLD(self):
        return 0.70
        
    @property
    def DEBUG_INFO(self):
        return DEBUG_INFO

    @property
    def FER_CHECKPOINT_PATH(self) -> str:
        return os.getenv("FER_CHECKPOINT_PATH", "vision/fer_checkpoint.tar")

settings = Settings()
