# DEBUGGING AND FAILURE HANDLING

JARVIS is built with strict safety locks and fallback mechanisms. This document outlines how the system survives API outages and unexpected inputs.

## 1. Perception Fallbacks (The Safety Lock)

The most fragile component of any multimodal assistant is the VLM endpoint.
- **Model Lock:** In `vision/vlm_emotion_analyzer.py`, dynamic model discovery is disabled. The model is hard-locked to `nvidia/nemotron-nano-12b-v2-vl:free`.
- **Why?** Dynamic switching often selected models that triggered 404 (Not Found) or 402 (Payment Required) errors.
- **Failure Preservation:** If the Nvidia endpoint goes down, the code does NOT try to auto-switch. It purposefully catches the error, logs the exact HTTP status, and passes the error payload back to the UI to be displayed in the Developer Debug Panel.

## 2. Decision Fallbacks (No Face / Environmental)

If the perception pipeline fails or successfully detects an image but cannot find a face, JARVIS relies on contextual fallbacks:
- `DecisionEngine.evaluate_autonomous_state()` actively checks the `face_detected` boolean from the VLM JSON.
- If `False`, it ignores emotional parameters and falls back to **Weather Data**.
- Example: If it's raining outside, JARVIS will suggest "Calm Lo-Fi", acting intelligently even when blind.

## 3. Transcription Failure Handling (Music Bleed)

A common issue in voice AI is the microphone picking up the music that the AI itself is playing.
- `voice/transcriber.py` uses heuristic checks.
- If the confidence score from Deepgram is unusually low (`< 0.55`), or the sentence is very long without explicit command words (like "play" or "jarvis"), it silently throws away the transcript.
- This prevents the "Infinite Feedback Loop" where JARVIS hears a song lyric, interprets it as a command, and changes the music.

## 4. Execution Fallbacks (Spotify 403s)

Spotify's Web API is notoriously strict about playback state transitions.
- **Mid-Track Switching Error:** Attempting to force playback on a device that is already actively buffering can cause a `403 Forbidden` error.
- **The Fix:** `spotify_controller.py` implements a "Pause Before Play" architecture. Before injecting a new track URI, it checks `sp.current_playback()`. If playing, it sends a `pause_playback` command, sleeps for 0.3 seconds to let Spotify's servers sync, and *then* sends the `start_playback` command.

## 5. System Observability (The Debug Panel)

Located in an expander at the bottom of the Streamlit UI, the Developer Debug Panel provides x-ray vision into the pipeline:
- **API Latency:** Explicit MS tracking for VLM, Deepgram, and Groq execution times.
- **State Dumps:** Raw JSON output of `vlm_result`, `api_status`, and Spotify connection statuses.
- **System Logs:** The sidebar houses a `log_container` that intercepts timestamped events tagged with `[VLM]`, `[GROQ]`, and `[SPOTIFY]`. This allows developers to trace an action backward (e.g., seeing exactly what JSON the VLM returned that caused Groq to suggest a specific song).
