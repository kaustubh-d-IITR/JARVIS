# JARVIS — Complete System Architecture & Backend Logic Manual

> **Version**: 1.0  
> **Last Updated**: May 15, 2026  
> **Author**: Auto-generated system documentation

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Project File Map](#2-project-file-map)
3. [Boot Sequence — What Happens When You Run JARVIS](#3-boot-sequence)
4. [Layer-by-Layer Architecture](#4-layer-by-layer-architecture)
5. [Detailed File Responsibilities](#5-detailed-file-responsibilities)
6. [Data Flow Diagrams](#6-data-flow-diagrams)
7. [Interaction Sequences](#7-interaction-sequences)
8. [Decision Engine Logic](#8-decision-engine-logic)
9. [Autonomous Mode Deep Dive](#9-autonomous-mode-deep-dive)
10. [External API Integration Map](#10-external-api-integration-map)
11. [Session State Architecture](#11-session-state-architecture)
12. [Error Handling Strategy](#12-error-handling-strategy)

---

## 1. System Overview

JARVIS is an **emotion-aware AI assistant** built on Streamlit. It combines:

- **Computer Vision** (webcam emotion + posture detection)
- **Voice Recognition** (Deepgram speech-to-text)
- **LLM Intelligence** (Groq/Llama for conversational AI)
- **Music Automation** (Spotify playback based on mood)
- **Weather Context** (OpenWeather API)
- **Autonomous Behavior** (background thread that suggests actions)

The system follows a **Perception → Decision → Action** pipeline:

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│ PERCEPTION  │────▶│    DECISION     │────▶│    ACTION     │
│             │     │                 │     │              │
│ • Webcam    │     │ • DecisionEngine│     │ • Spotify    │
│ • Voice     │     │ • GroqLLM       │     │ • Chat Reply │
│ • Weather   │     │ • Autonomous    │     │ • UI Update  │
└─────────────┘     └─────────────────┘     └──────────────┘
```

---

## 2. Project File Map

```
JARVIS/
│
├── app.py                          ← Entry point. Bootstraps asyncio + calls dashboard.
├── requirements.txt                ← All Python dependencies.
├── README.md                       ← Setup instructions.
├── .env.example                    ← Template for API keys.
├── .gitignore                      ← Git exclusions (.env, __pycache__, etc.)
├── run_local.bat / run_local.sh    ← OS-specific startup scripts.
├── packages.txt                    ← System-level Linux libs (for cloud deploy).
│
├── config/
│   ├── __init__.py
│   └── settings.py                 ← Loads .env, exposes all config as properties.
│
├── vision/
│   ├── __init__.py
│   ├── emotion_detector.py         ← DeepFace emotion analysis with frame skipping.
│   ├── posture_detector.py         ← MediaPipe Pose landmark analysis.
│   ├── webrtc_processor.py         ← WebRTC video frame handler (glues vision together).
│   └── pose_landmarker_lite.task   ← Downloaded MediaPipe model binary.
│
├── voice/
│   ├── __init__.py
│   └── transcriber.py              ← Sends audio to Deepgram REST API, returns text.
│
├── llm/
│   ├── __init__.py
│   ├── groq_client.py              ← Groq API wrapper (sends prompt, gets response).
│   └── prompts.py                  ← JARVIS system prompt + context injection builder.
│
├── spotify/
│   ├── __init__.py
│   └── spotify_controller.py       ← Spotipy OAuth, play/pause/search.
│
├── weather/
│   ├── __init__.py
│   └── weather_service.py          ← OpenWeather API fetch + session cache.
│
├── logic/
│   ├── __init__.py
│   ├── decision_engine.py          ← Central brain: intent matching + LLM call + actions.
│   └── autonomous_controller.py    ← Background thread that polls state & suggests actions.
│
├── ui/
│   ├── __init__.py
│   └── dashboard.py                ← Full Streamlit UI: layout, widgets, event wiring.
│
└── utils/
    ├── __init__.py
    ├── logger.py                   ← Dual logger: stdout + Streamlit session_state.
    └── helpers.py                  ← Emotion-to-playlist mapping utility.
```

---

## 3. Boot Sequence

Here is the **exact order of execution** when you run `streamlit run app.py`:

### Step 1 — `app.py` (Entry Point)

```
app.py
  ├── Sets Windows asyncio policy (WindowsSelectorEventLoopPolicy)
  └── Calls render_dashboard() from ui/dashboard.py
```

- On Windows, Python's default asyncio event loop doesn't support some operations needed by the audio transcriber. The `WindowsSelectorEventLoopPolicy` fix is applied before anything else.

### Step 2 — `ui/dashboard.py → render_dashboard()`

```
render_dashboard()
  ├── st.set_page_config()           ← Sets page title, layout to "wide"
  ├── preload_models()               ← @st.cache_resource — downloads DeepFace weights ONCE
  ├── initialize_session_state()     ← Creates all service objects ONCE per session
  │   ├── AudioTranscriber()         ← voice/transcriber.py
  │   ├── GroqClient()               ← llm/groq_client.py
  │   ├── SpotifyController()        ← spotify/spotify_controller.py
  │   ├── WeatherService()           ← weather/weather_service.py
  │   ├── DecisionEngine(groq, spotify)  ← logic/decision_engine.py
  │   ├── AutonomousController(engine)   ← logic/autonomous_controller.py
  │   └── Sets default state values (emotion="neutral", posture="unknown", etc.)
  │
  └── Renders the UI (sidebar + main body)
```

### Step 3 — Model Preloading

```
preload_models()  [@st.cache_resource — runs ONCE per server lifetime]
  ├── Creates EmotionDetector()
  ├── Runs detect_emotion() on a dummy 224x224 black image
  │   └── This forces DeepFace to download its CNN weights (~30s first time)
  └── Returns True (cached forever after)
```

**Why?** DeepFace downloads model weights on first use. If this happened inside the WebRTC thread, the connection would timeout. Pre-downloading on the main thread prevents that.

### Step 4 — Service Initialization

All service objects are created **once** and stored in `st.session_state`:

| Service | Class | File | What It Does on `__init__` |
|---|---|---|---|
| `transcriber` | `AudioTranscriber` | `voice/transcriber.py` | Nothing (lazy) |
| `groq` | `GroqClient` | `llm/groq_client.py` | Nothing (lazy) |
| `spotify` | `SpotifyController` | `spotify/spotify_controller.py` | Sets OAuth scope string |
| `weather_svc` | `WeatherService` | `weather/weather_service.py` | Sets base URL |
| `decision_engine` | `DecisionEngine` | `logic/decision_engine.py` | Stores refs to groq + spotify |
| `autonomous` | `AutonomousController` | `logic/autonomous_controller.py` | Stores ref to decision_engine |

Weather is also fetched immediately: `st.session_state.weather = weather_svc.get_weather()`

---

## 4. Layer-by-Layer Architecture

The system is organized into **5 layers**:

```
┌──────────────────────────────────────────────────────┐
│                    UI LAYER                          │
│              ui/dashboard.py                         │
│   (Streamlit widgets, layout, event handlers)        │
├──────────────────────────────────────────────────────┤
│                  LOGIC LAYER                         │
│    logic/decision_engine.py                          │
│    logic/autonomous_controller.py                    │
│   (Intent matching, LLM orchestration, suggestions)  │
├──────────────────────────────────────────────────────┤
│                SERVICE LAYER                         │
│  llm/groq_client.py    spotify/spotify_controller.py │
│  voice/transcriber.py  weather/weather_service.py    │
│   (External API wrappers — each talks to one API)    │
├──────────────────────────────────────────────────────┤
│               PERCEPTION LAYER                       │
│  vision/emotion_detector.py                          │
│  vision/posture_detector.py                          │
│  vision/webrtc_processor.py                          │
│   (Computer vision — runs in WebRTC thread)          │
├──────────────────────────────────────────────────────┤
│               INFRASTRUCTURE LAYER                   │
│  config/settings.py   utils/logger.py                │
│  utils/helpers.py     llm/prompts.py                 │
│   (Config, logging, utilities, prompt templates)     │
└──────────────────────────────────────────────────────┘
```

**Key Rule**: Upper layers depend on lower layers, never the reverse. The Perception Layer and Service Layer never call each other directly — the Logic Layer orchestrates them.

---

## 5. Detailed File Responsibilities

### `config/settings.py`
- Loads `.env` using `python-dotenv` with `override=True`
- Exposes all config as **properties** on a `Settings` singleton
- Every property call re-reads env vars (via `reload_env()`) ensuring hot-reload
- Hardcoded defaults: `GROQ_MODEL = "llama-3.3-70b-versatile"`, `AUTONOMOUS_COOLDOWN = 60s`, `EMOTION_CONFIDENCE_THRESHOLD = 0.70`
- Includes `DEBUG_INFO` dict for troubleshooting env loading issues

### `vision/emotion_detector.py`
- Uses **DeepFace** with `opencv` detector backend
- **Frame skipping**: Only processes every 5th frame (`skip_frames=5`)
- Returns `(emotion_string, confidence_float)` — e.g., `("sad", 0.85)`
- On failure, returns last known state (graceful degradation)
- `enforce_detection=False` means it won't crash if no face is found

### `vision/posture_detector.py`
- Uses **MediaPipe Pose Landmarker** (Tasks API, not legacy Solutions API)
- Auto-downloads `pose_landmarker_lite.task` model on first run
- Detects 33 body landmarks, draws skeleton overlay on frame
- **Posture heuristic**: If nose Y-coordinate is more than 0.2 above shoulder midpoint → "upright", else → "slouched"
- Returns `(posture_string, annotated_frame)`

### `vision/webrtc_processor.py`
- Implements `VideoProcessorBase` from `streamlit-webrtc`
- **Runs in a separate thread** (not on Streamlit's main thread)
- Creates its own `EmotionDetector` and `PostureDetector` instances
- Processes only **1 out of every 10 frames** (`process_every_n_frames=10`) to save CPU
- Stores results as instance attributes (`latest_emotion`, `latest_emotion_conf`, `latest_posture`)
- The UI reads these attributes via `ctx.video_processor.latest_emotion`

### `voice/transcriber.py`
- Sends audio file to **Deepgram REST API** (`/v1/listen?model=nova-2`)
- Uses `asyncio.to_thread()` to avoid blocking the event loop
- Cleans up temp audio file after transcription
- Returns transcript string or error message

### `llm/groq_client.py`
- Wraps the **Groq SDK** (`groq` Python package)
- Creates a fresh `Groq()` client on each call (API key checked at call time)
- Uses model `llama-3.3-70b-versatile`, `temperature=0.7`, `max_tokens=150`
- Takes `system_prompt` + `user_prompt`, returns response string

### `llm/prompts.py`
- `SYSTEM_PROMPT`: Defines JARVIS personality (calm, intelligent, concise, emotionally aware)
- `build_contextual_prompt()`: Injects live context (emotion, posture, weather) into the user's message as a `[SYSTEM CONTEXT]` prefix so the LLM can reason about the user's state

### `spotify/spotify_controller.py`
- Uses **Spotipy** with `SpotifyOAuth` (scopes: `user-modify-playback-state`, `user-read-playback-state`)
- `play_music(query=...)`: Searches Spotify for a playlist matching the query, finds an active device, starts playback
- Device fallback: If no device is marked "active", uses the first available device
- `pause_music()`: Pauses current playback
- All methods return `(success_bool, message_string)` tuples

### `weather/weather_service.py`
- Calls **OpenWeather API** (`/data/2.5/weather`) with metric units
- Caches result for the entire session (no TTL — simple MVP cache)
- Returns dict: `{temperature, humidity, condition, icon}`
- On failure, returns `{temperature: "unknown", ...}`

### `logic/decision_engine.py`
- **The brain of JARVIS** — Central orchestrator
- `process_voice_command()`: Takes transcribed text + context →
  1. Runs **local intent matching** (keyword-based) for "play music", "pause", "stop music"
  2. If music intent detected → calls `spotify.play_music()` with emotion-appropriate playlist
  3. Always generates a **Groq LLM response** with full context (emotion, posture, weather)
  4. Returns `{response, action, action_msg}`
- `evaluate_autonomous_state()`: Called by the background thread →
  - If emotion is `sad` or `angry` AND confidence > 70% → suggests playing mood-appropriate music
  - Otherwise returns `{suggested_action: None}`

### `logic/autonomous_controller.py`
- Runs a **daemon thread** that polls every 5 seconds
- Has a **cooldown** of 60 seconds between suggestions (prevents spam)
- Thread-safe state updates via `threading.Lock`
- Flow: `_loop()` → reads state → calls `decision_engine.evaluate_autonomous_state()` → stores suggestion
- UI polls `get_and_clear_suggestion()` — returns suggestion once, then clears it

### `ui/dashboard.py`
- The **entire Streamlit interface** in one file
- **Sidebar**: Autonomous mode toggle, Spotify auth status, system logs
- **Main body**: Weather widget, suggestion alerts, WebRTC video feed, voice recorder, chat history
- Uses `@st.fragment(run_every=1.0)` to poll WebRTC processor for emotion/posture metrics without full page rerun
- Uses `audio_recorder_streamlit` for browser-based mic recording
- Deduplicates audio with MD5 hashing to prevent reprocessing on Streamlit reruns

### `utils/logger.py`
- Creates loggers with **two handlers**:
  1. `StreamHandler` → stdout (for terminal/server logs)
  2. `StreamlitSessionHandler` → pushes log messages into `st.session_state.system_logs` (for UI display)
- Max 50 log entries in session state

### `utils/helpers.py`
- `get_spotify_playlist_for_emotion()`: Maps emotions to Spotify search queries
  - happy → "energetic upbeat playlist"
  - sad → "calm peaceful acoustic"
  - angry → "relaxing chill lofi"
  - neutral → "focus concentration instrumental"
  - fear → "soothing ambient"
  - surprise → "pop hits"

---

## 6. Data Flow Diagrams

### A. Webcam Frame Processing (runs continuously in background thread)

```
Browser Webcam
     │
     ▼
streamlit-webrtc (WebRTC connection)
     │
     ▼
JarvisVideoProcessor.recv(frame)     [vision/webrtc_processor.py]
     │
     ├── Every 10th frame:
     │   ├── PostureDetector.detect_posture(frame)    [vision/posture_detector.py]
     │   │   ├── Convert BGR → RGB
     │   │   ├── MediaPipe PoseLandmarker.detect()
     │   │   ├── Draw skeleton overlay
     │   │   └── Return (posture_status, annotated_frame)
     │   │
     │   └── EmotionDetector.detect_emotion(frame)    [vision/emotion_detector.py]
     │       ├── DeepFace.analyze(actions=['emotion'])
     │       └── Return (emotion, confidence)
     │
     ├── Store results: self.latest_emotion, self.latest_posture
     └── Return annotated frame to browser
```

### B. UI Metrics Polling (runs every 1 second on main thread)

```
@st.fragment(run_every=1.0) render_metrics()     [ui/dashboard.py]
     │
     ├── Read ctx.video_processor.latest_emotion
     ├── Read ctx.video_processor.latest_posture
     ├── Update st.session_state (current_emotion, current_posture)
     ├── Update autonomous_controller state
     └── Render st.metric() widgets
```

### C. Voice Command Flow

```
User clicks mic button in browser
     │
     ▼
audio_recorder_streamlit captures audio bytes
     │
     ▼
dashboard.py receives audio_bytes
     │
     ├── MD5 hash check (skip if same as last audio)
     ├── Write to temp_audio.wav
     │
     ▼
AudioTranscriber.transcribe_audio_async()     [voice/transcriber.py]
     │
     ├── POST audio to Deepgram API (/v1/listen?model=nova-2)
     ├── Parse JSON response → transcript string
     └── Delete temp file
     │
     ▼
DecisionEngine.process_voice_command()     [logic/decision_engine.py]
     │
     ├── Intent Matching (keyword scan):
     │   ├── "play music" → helpers.get_spotify_playlist_for_emotion(emotion)
     │   │                 → spotify.play_music(query=...)
     │   ├── "pause"/"stop" → spotify.pause_music()
     │   └── anything else → no direct action
     │
     ├── LLM Response Generation:
     │   ├── prompts.build_contextual_prompt(text, emotion, posture, weather)
     │   ├── groq_client.get_response(SYSTEM_PROMPT, context_prompt)
     │   └── Returns conversational text
     │
     └── Return {response, action, action_msg}
     │
     ▼
dashboard.py appends to chat_history → st.rerun()
```

### D. Autonomous Suggestion Flow

```
AutonomousController._loop()     [logic/autonomous_controller.py]
     │                            (background daemon thread, polls every 5s)
     │
     ├── Check cooldown (60s since last suggestion)
     ├── Read thread-safe state (emotion, confidence, posture, weather)
     │
     ▼
DecisionEngine.evaluate_autonomous_state()     [logic/decision_engine.py]
     │
     ├── IF emotion in [sad, angry] AND confidence > 0.70:
     │   └── Return {suggested_action: "play_music", query: "...", message: "..."}
     └── ELSE: Return {suggested_action: None}
     │
     ▼
AutonomousController stores suggestion (thread-safe)
     │
     ▼
dashboard.py polls get_and_clear_suggestion() on each rerun
     │
     ├── Renders suggestion alert with Accept/Dismiss buttons
     ├── Accept → spotify.play_music(query=...) → log_system()
     └── Dismiss → clear suggestion → st.rerun()
```

---

## 7. Interaction Sequences

### Sequence 1: User Opens App for the First Time

```
1. Browser loads → Streamlit serves app.py
2. app.py calls render_dashboard()
3. preload_models() runs (cache miss) → downloads DeepFace weights (~30s)
4. initialize_session_state() creates all services
5. WeatherService.get_weather() fetches weather from OpenWeather API
6. UI renders with:
   - Warning if any API keys are missing
   - Weather info bar
   - WebRTC streamer (camera not started yet)
   - Voice recorder button
   - Empty chat history
```

### Sequence 2: User Starts the Camera

```
1. User clicks "START" on the WebRTC streamer widget
2. Browser requests camera permission
3. WebRTC connection established (using STUN/TURN servers for NAT traversal)
4. JarvisVideoProcessor() created on server side
   - EmotionDetector() instantiated (weights already cached)
   - PostureDetector() instantiated (downloads model if needed)
5. recv() called for every incoming frame
6. Every 10th frame: posture + emotion analyzed
7. @st.fragment polls processor attributes every 1s → updates UI metrics
```

### Sequence 3: User Speaks a Voice Command

```
1. User clicks mic → speaks "play some happy music" → stops recording
2. audio_bytes received → MD5 hash computed → different from last → proceed
3. Audio written to temp_audio.wav
4. Deepgram API transcribes → "play some happy music"
5. DecisionEngine.process_voice_command() called:
   a. "play music" detected in text
   b. Current emotion = "happy"
   c. helpers.get_spotify_playlist_for_emotion("happy") → "energetic upbeat playlist"
   d. spotify.play_music(query="energetic upbeat playlist")
   e. Spotify searches → finds playlist → starts playback on active device
   f. LLM generates conversational response with full context
6. Chat history updated with user message + JARVIS response
7. System log updated with action result
8. st.rerun() refreshes the UI
```

### Sequence 4: Autonomous Mode Triggers a Suggestion

```
1. User toggles "Enable JARVIS Brain" → autonomous.start()
2. Background thread starts polling every 5 seconds
3. Webcam detects emotion="sad", confidence=0.85 for sustained period
4. Thread reads state → calls evaluate_autonomous_state()
5. Condition met (sad + conf>0.70) → suggestion created:
   "I detected you might be feeling sad. Would you like me to play a calm peaceful acoustic playlist?"
6. Cooldown timer set (no new suggestions for 60s)
7. Next UI rerun: get_and_clear_suggestion() returns the suggestion
8. Green alert box appears with Accept/Dismiss buttons
9. User clicks Accept → spotify.play_music(query="calm peaceful acoustic")
```

---

## 8. Decision Engine Logic

The `DecisionEngine` is the **central brain**. It has two modes:

### Mode A: Reactive (Voice Command)

```python
process_voice_command(text, emotion, posture, weather)
```

**Step 1 — Local Intent Matching** (fast, no API call):
| Keywords in text | Action Taken |
|---|---|
| "play music", "play some music" | `spotify.play_music(query=emotion_playlist)` |
| "pause", "stop music" | `spotify.pause_music()` |
| anything else | No direct action |

**Step 2 — LLM Response** (always runs):
- Builds contextual prompt with `[SYSTEM CONTEXT: emotion, posture, weather]`
- Calls Groq API with JARVIS system prompt
- Returns natural language response

### Mode B: Proactive (Autonomous Evaluation)

```python
evaluate_autonomous_state(emotion, confidence, posture, weather)
```

| Condition | Result |
|---|---|
| emotion ∈ {sad, angry} AND confidence > 0.70 | Suggest mood-appropriate playlist |
| All other states | No suggestion |

---

## 9. Autonomous Mode Deep Dive

### Threading Model

```
Main Thread (Streamlit)              Background Thread (Daemon)
─────────────────────               ────────────────────────
│                                    │
│ autonomous.start()  ──────────▶   Thread starts
│                                    │
│                                    ├── sleep(5s)
│                                    ├── lock → read state
│                                    ├── decision_engine.evaluate_autonomous_state()
│                                    ├── if suggestion → lock → store suggestion
│                                    └── loop ↑
│
│ render_dashboard() reruns
│ ├── get_and_clear_suggestion() ◀── lock → read & clear
│ └── Render suggestion UI
│
│ autonomous.stop()  ──────────▶    is_running = False → thread exits
```

### Thread Safety

- All shared state is protected by `threading.Lock`
- `update_state()` — called by UI fragment every 1s — acquires lock
- `_loop()` — background thread — acquires lock to read state and write suggestions
- `get_and_clear_suggestion()` — called by UI — acquires lock, reads and clears

### Cooldown Mechanism

- After a suggestion is generated, `last_action_time` is set to `time.time()`
- The loop skips evaluation if `now - last_action_time < 60 seconds`
- This prevents JARVIS from spamming suggestions every 5 seconds

---

## 10. External API Integration Map

| API | File | Endpoint | Auth Method | Data Used |
|---|---|---|---|---|
| **Deepgram** | `voice/transcriber.py` | `POST /v1/listen?model=nova-2` | Bearer Token header | Audio → transcript text |
| **Groq** | `llm/groq_client.py` | Groq SDK (Chat Completions) | API Key in constructor | Prompt → LLM response |
| **Spotify** | `spotify/spotify_controller.py` | Spotipy SDK (OAuth) | OAuth2 PKCE flow | Search playlists, control playback |
| **OpenWeather** | `weather/weather_service.py` | `GET /data/2.5/weather` | `appid` query param | City → temp, humidity, condition |

### API Key Loading Chain

```
.env file
  ↓
config/settings.py → load_dotenv(override=True)
  ↓
os.getenv("KEY_NAME") → property on Settings singleton
  ↓
Each service reads settings.KEY_NAME at call time (lazy)
```

---

## 11. Session State Architecture

All persistent state lives in `st.session_state`. Here's the complete map:

| Key | Type | Set By | Read By | Purpose |
|---|---|---|---|---|
| `initialized` | bool | `initialize_session_state()` | `initialize_session_state()` | Prevent re-initialization |
| `transcriber` | AudioTranscriber | init | dashboard (voice flow) | Speech-to-text service |
| `groq` | GroqClient | init | DecisionEngine | LLM service |
| `spotify` | SpotifyController | init | DecisionEngine, dashboard | Music control |
| `weather_svc` | WeatherService | init | dashboard | Weather fetcher |
| `decision_engine` | DecisionEngine | init | dashboard, autonomous | Central brain |
| `autonomous` | AutonomousController | init | dashboard | Background AI loop |
| `current_emotion` | str | render_metrics fragment | dashboard, autonomous | Latest detected emotion |
| `emotion_confidence` | float | render_metrics fragment | autonomous | Latest confidence score |
| `current_posture` | str | render_metrics fragment | dashboard, autonomous | Latest posture state |
| `weather` | dict | init | dashboard, decision_engine | Cached weather data |
| `chat_history` | list[dict] | voice flow | dashboard chat UI | Conversation log |
| `system_logs` | list[str] | log_system(), logger | sidebar logs panel | Debug/info messages |
| `autonomous_mode` | bool | sidebar toggle | dashboard | Whether brain is active |
| `last_audio_hash` | str | voice flow | voice flow | Dedup audio recordings |
| `pending_suggestion` | dict | autonomous poll | suggestion UI | Queued AI suggestion |

---

## 12. Error Handling Strategy

### Principle: Never Crash, Always Degrade

| Component | Failure Mode | Handling |
|---|---|---|
| DeepFace | No face detected | `enforce_detection=False` → returns neutral |
| DeepFace | Model download fails | `preload_models()` catches → shows spinner |
| MediaPipe | No body detected | Returns `posture="unknown"` |
| Deepgram | API key missing | Returns error message string |
| Deepgram | API call fails | Returns `"Error: {details}"` as transcript |
| Groq | API key missing | Returns `"API key not configured"` |
| Groq | API call fails | Returns `"Sorry, I encountered an error"` |
| Spotify | Not authenticated | Shows auth link in sidebar |
| Spotify | No active device | Returns `"No active devices found"` message |
| Spotify | Playlist not found | Returns `"Could not find playlist"` |
| OpenWeather | API fails | Returns `{temperature: "unknown", ...}` |
| WebRTC | Processing error | Logs error, returns raw frame |
| Audio | Same audio resubmitted | MD5 hash dedup prevents reprocessing |
| Any service | Missing .env keys | Warning banner with list of missing keys |

### Logging Dual-Path

Every error is logged to:
1. **stdout** (terminal) via `logging.StreamHandler`
2. **Streamlit UI** (sidebar logs panel) via custom `StreamlitSessionHandler`

---

## Summary

JARVIS is a **Perception → Decision → Action** system where:

1. **Perception** (vision + voice + weather) feeds raw data
2. **Decision** (DecisionEngine + AutonomousController + Groq LLM) interprets and reasons
3. **Action** (Spotify playback + chat responses + UI suggestions) executes

The UI layer (`dashboard.py`) orchestrates everything through Streamlit's session state, while the WebRTC video processor and autonomous controller run in separate threads for non-blocking real-time processing.
