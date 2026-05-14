import spotipy
from spotipy.oauth2 import SpotifyOAuth
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class SpotifyController:
    def __init__(self):
        self.scope = "user-modify-playback-state user-read-playback-state"
        
    @property
    def auth_manager(self):
        if not all([settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET, settings.SPOTIFY_REDIRECT_URI]):
            return None
        return SpotifyOAuth(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIFY_REDIRECT_URI,
            scope=self.scope,
            open_browser=False
        )
        
    @property
    def sp(self):
        if not self.auth_manager:
            return None
        return spotipy.Spotify(auth_manager=self.auth_manager)
            
    def is_authenticated(self) -> bool:
        return self.sp is not None
        
    def get_auth_url(self) -> str:
        if not self.auth_manager:
            return ""
        return self.auth_manager.get_authorize_url()
        
    def play_music(self, context_uri: str = None, query: str = None):
        """Plays music. If query is provided, searches for a playlist and plays it."""
        if not self.is_authenticated():
            return False, "Spotify not configured."
            
        try:
            devices = self.sp.devices()
            if not devices or not devices['devices']:
                return False, "No active Spotify devices found. Please open Spotify on one of your devices."
                
            active_device = None
            for device in devices['devices']:
                if device['is_active']:
                    active_device = device['id']
                    break
                    
            if not active_device:
                # Fallback to the first available device
                active_device = devices['devices'][0]['id']
                
            if query:
                # Search for playlist
                results = self.sp.search(q=query, type='playlist', limit=1)
                if results['playlists']['items']:
                    context_uri = results['playlists']['items'][0]['uri']
                else:
                    return False, f"Could not find a playlist for: {query}"
                    
            self.sp.start_playback(device_id=active_device, context_uri=context_uri)
            return True, f"Started playing: {query if query else 'music'}"
            
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Spotify API error: {e}")
            return False, f"Spotify error: {e.msg}"
        except Exception as e:
            logger.error(f"Unexpected Spotify error: {e}")
            return False, f"Error: {str(e)}"
            
    def pause_music(self):
        if not self.is_authenticated():
            return False, "Spotify not configured."
        try:
            self.sp.pause_playback()
            return True, "Paused playback."
        except Exception as e:
            return False, f"Error pausing: {str(e)}"
