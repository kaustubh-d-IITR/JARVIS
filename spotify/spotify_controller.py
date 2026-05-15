import spotipy
from spotipy.oauth2 import SpotifyOAuth
import streamlit as st
from utils.logger import get_logger

logger = get_logger(__name__)


class SpotifyController:
    def __init__(self):
        self.scope = "user-modify-playback-state user-read-playback-state"

    def _get_client(self):
        """Get authenticated Spotify client using token from session state."""
        token_info = st.session_state.get("spotify_token_info")
        if token_info is None:
            return None

        # Refresh token if expired
        auth_manager = self._get_auth_manager()
        if auth_manager.is_token_expired(token_info):
            token_info = auth_manager.refresh_access_token(
                token_info["refresh_token"]
            )
            st.session_state.spotify_token_info = token_info

        return spotipy.Spotify(auth=token_info["access_token"])

    def _get_auth_manager(self):
        from config.settings import settings
        return SpotifyOAuth(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIFY_REDIRECT_URI,
            scope=self.scope,
            cache_handler=spotipy.cache_handler.MemoryCacheHandler(),
            open_browser=False
        )

    def get_auth_url(self):
        """Return the Spotify authorization URL for the user to click."""
        from config.settings import settings
        if not all([settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET]):
            return ""
        return self._get_auth_manager().get_authorize_url()

    def handle_callback(self, code: str) -> bool:
        """Exchange auth code for token. Call this when callback URL has ?code="""
        try:
            auth_manager = self._get_auth_manager()
            token_info = auth_manager.get_access_token(code, as_dict=True)
            st.session_state.spotify_token_info = token_info
            return True
        except Exception as e:
            logger.error(f"Spotify OAuth callback error: {e}")
            return False

    def is_authenticated(self) -> bool:
        return st.session_state.get("spotify_token_info") is not None

    def play_music(self, query: str = None) -> tuple:
        sp = self._get_client()
        if sp is None:
            return False, "Spotify not authenticated. Please connect Spotify first."
        try:
            results = sp.search(q=query or "chill focus", type="playlist", limit=1)
            playlists = results.get("playlists", {}).get("items", [])
            if not playlists:
                return False, f"No playlist found for: {query}"
            playlist_uri = playlists[0]["uri"]
            devices = sp.devices()
            device_list = devices.get("devices", [])
            if not device_list:
                return False, "No active Spotify device found. Open Spotify on your phone or PC first."
            device_id = next(
                (d["id"] for d in device_list if d["is_active"]),
                device_list[0]["id"]
            )
            sp.start_playback(device_id=device_id, context_uri=playlist_uri)
            return True, f"Playing: {playlists[0]['name']}"
        except Exception as e:
            logger.error(f"Spotify play error: {e}")
            return False, f"Spotify error: {str(e)}"

    def pause_music(self) -> tuple:
        sp = self._get_client()
        if sp is None:
            return False, "Spotify not authenticated."
        try:
            sp.pause_playback()
            return True, "Music paused."
        except Exception as e:
            logger.error(f"Spotify pause error: {e}")
            return False, f"Pause error: {str(e)}"
