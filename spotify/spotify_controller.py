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
            return False, "Spotify not authenticated."
        try:
            # Get devices
            devices = sp.devices()
            device_list = devices.get("devices", [])
            if not device_list:
                return False, "No active Spotify device. Open Spotify on your phone or PC first."

            device_id = next(
                (d["id"] for d in device_list if d["is_active"]),
                device_list[0]["id"]
            )

            # ALWAYS pause current playback before switching
            # This prevents 403 errors when switching mid-song
            try:
                current = sp.current_playback()
                if current and current.get("is_playing"):
                    sp.pause_playback(device_id=device_id)
                    import time
                    time.sleep(0.3)  # Brief pause to let Spotify settle
            except Exception:
                pass  # If nothing playing, continue

            search_query = query or "chill focus"

            # Search for track first
            track_results = sp.search(q=search_query, type="track", limit=5)
            tracks = track_results.get("tracks", {}).get("items", [])

            if tracks:
                track = tracks[0]
                track_uri = track["uri"]
                track_name = track["name"]
                artist_name = track["artists"][0]["name"]
                sp.start_playback(
                    device_id=device_id,
                    uris=[track_uri]
                )
                return True, f"Playing '{track_name}' by {artist_name}"

            # Fallback to playlist
            playlist_results = sp.search(q=search_query, type="playlist", limit=1)
            playlists = playlist_results.get("playlists", {}).get("items", [])
            if playlists:
                playlist = playlists[0]
                sp.start_playback(
                    device_id=device_id,
                    context_uri=playlist["uri"]
                )
                return True, f"Playing playlist: {playlist['name']}"

            return False, f"Nothing found for: {search_query}"

        except Exception as e:
            error_str = str(e)
            if "Premium" in error_str:
                return False, "Spotify Premium required for playback control."
            if "No active device" in error_str:
                return False, "No active Spotify device. Open Spotify app first."
            logger.error(f"Spotify play error: {e}")
            return False, f"Spotify error: {error_str}"

    def pause_music(self) -> tuple:
        sp = self._get_client()
        if sp is None:
            return False, "Spotify not authenticated."
        try:
            # Check if actually playing before pausing
            current = sp.current_playback()
            if current and current.get("is_playing"):
                sp.pause_playback()
                return True, "Music paused."
            else:
                return True, "Music is already paused."
        except Exception as e:
            return False, f"Pause error: {str(e)}"


