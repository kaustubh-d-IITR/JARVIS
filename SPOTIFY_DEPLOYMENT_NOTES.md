# SPOTIFY DEPLOYMENT NOTES

## Overview
The Spotify architecture remains fully developer-owned. Deployment users do NOT need to provide their own Spotify Client ID or Client Secret.

## Configuration Strategy
- **Developer Credentials:** `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are read from the secure deployment environment (`os.getenv`), ensuring they are completely hidden from the end user.
- **Redirect URI:** `SPOTIFY_REDIRECT_URI` is purposefully loaded from environment variables. This prevents hardcoding localhost (`http://127.0.0.1:8501/callback`) in the codebase, ensuring a smooth transition when deploying to Streamlit Cloud. During deployment, the developer will manually configure this environment variable to match the deployed app's URL.

## Authentication Flow
When the deployed user clicks the "Connect Spotify" link, the application constructs an OAuth URL using the developer's Client ID. The user grants access to their Spotify account, and the Spotify service redirects back to the Streamlit app using the configured `SPOTIFY_REDIRECT_URI`.

## Security Guarantee
No developer secrets are ever exposed to the client interface or stored in `st.session_state`.
