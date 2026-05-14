import requests
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class WeatherService:
    def __init__(self):
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
        self.cache = None
        
    def get_weather(self) -> dict:
        api_key = settings.OPENWEATHER_API_KEY
        if not api_key:
            return {"temperature": "unknown", "condition": "unknown", "humidity": "unknown"}
            
        # In a real app we'd add timestamp expiration to cache, but for MVP simple cache is ok per session
        if self.cache:
            return self.cache
            
        try:
            params = {
                "q": settings.LOCATION,
                "appid": api_key,
                "units": "metric"
            }
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            self.cache = {
                "temperature": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "condition": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"]
            }
            return self.cache
            
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return {"temperature": "unknown", "condition": "unknown", "humidity": "unknown"}
