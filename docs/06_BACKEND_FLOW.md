# BACKEND FLOW & DATA PROCESSING

This document explains the internal data processing pipelines, decision-making logic, and background automation that powers JARVIS.

## 1. The Decision Engine (`logic/decision_engine.py`)

The Decision Engine is the central router of the application. It receives processed inputs from the perception layers and decides what action JARVIS should take.

### A. Voice Command Processing
When a voice command is transcribed, it hits `process_voice_command()`:
1. **Priority 1 (Hard Stop):** The engine parses the string for words like `"pause"`, `"stop"`, or `"quiet"`. If found, it immediately triggers the `spotify.pause_music()` method.
2. **Priority 2 (Play Intent):** The engine uses Regex patterns (`_extract_search_query()`) to extract artist and track names (e.g., `"play Shape of You by Ed Sheeran"` -> `"Shape of You Ed Sheeran"`).
3. **Execution:** It tells the Spotify Controller to search for and play the requested track.
4. **Conversational Wrap:** Finally, it passes the action taken and the user's text to the Groq LLM to generate a natural conversational response (e.g., "I've put on Ed Sheeran for you.").

### B. Autonomous State Evaluation
When the VLM finishes processing an image, `evaluate_autonomous_state()` handles the result:
1. **No Face Detected:** If the VLM reports `face_detected: False`, the engine triggers a **Weather Fallback**. It reads the cached weather data and suggests a playlist based on the environment (e.g., "Rainy Lo-Fi" if it's raining).
2. **Low Confidence:** If the emotion confidence is below the threshold (`0.70`), JARVIS will generate a clarification message ("I'm sensing sadness, but I'm not sure...") instead of taking direct action.
3. **High Confidence:** If the emotion is clearly detected, it utilizes `get_spotify_playlist_for_emotion()` to map the mood to a query (e.g., "Happy" -> "Upbeat Pop Hits") and returns a `play_music` action payload.

## 2. Autonomous Controller (`logic/autonomous_controller.py`)

This module allows JARVIS to act as a proactive assistant rather than a reactive chatbot.

- **Background Threading:** When the user enables "JARVIS Brain", a daemon thread starts running `_loop()`.
- **Polling Loop:** Every 5 seconds, the thread safely reads the current session state (Emotion, Weather, Posture) using thread locks (`self.lock`).
- **Cooldown Gating:** It enforces a cooldown (`AUTONOMOUS_COOLDOWN_SECONDS = 60`) to prevent JARVIS from spamming the user with music suggestions every 5 seconds.
- **State Pushing:** When an actionable decision is reached, it pushes the payload to `latest_suggestion`. The Streamlit UI polls `get_and_clear_suggestion()` to display the recommendation alert on the screen.

## 3. Voice Processing (`voice/transcriber.py`)

The audio pipeline utilizes the **Deepgram Nova-2** model for near-instant transcription.

- **Asynchronous Execution:** Transcription runs via `asyncio.to_thread` to prevent blocking the Streamlit UI.
- **Music Bleed Rejection:** A major challenge with voice-controlled music bots is "music bleed" (the microphone picking up the music the bot is currently playing). 
  - `transcriber.py` implements a heuristic check `_is_likely_music_bleed()`.
  - It heavily boosts keywords (`"pause:5"`, `"play:5"`, `"jarvis:5"`) in the API request. 
  - If the transcript is long, lacks command words, or has low confidence (< 0.55), it is silently rejected to prevent JARVIS from hallucinating commands from song lyrics.

## 4. Weather Context (`weather/weather_service.py`)

Environmental context acts as the ultimate fallback when visual perception fails.
- **Caching:** Weather data is requested from OpenWeatherMap and cached per-session (`self.cache`). This prevents redundant API calls and rate-limiting during the autonomous loop.
- **Data Points:** Captures temperature, humidity, and condition description (e.g., "light rain"), which the `DecisionEngine` uses to theme its fallback music suggestions.
