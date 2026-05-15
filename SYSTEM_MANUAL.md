# JARVIS — Complete System Manual

> **Last Updated:** 15 May 2026  
> **Version:** Production (Streamlit Cloud)  
> **Author:** Kaustubh (IITR) + AI Pair Programming

---

## 1. What JARVIS Is

JARVIS is a real-time, emotion-aware AI assistant that:
- **Sees** the user's face (emotion) and body (posture) through their browser webcam via WebRTC.
- **Hears** voice commands through the browser microphone, transcribed by Deepgram.
- **Thinks** using Groq LLM (Llama 3.3 70B) with injected emotion/weather context.
- **Acts** by controlling Spotify playback — playing specific songs or mood-based playlists.
- **Feels** the environment via OpenWeather API for contextual reasoning.

---

## 2. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           USER'S BROWSER                                │
│                                                                         │
│   ┌──────────────┐       ┌──────────────────┐       ┌──────────────┐   │
│   │  Webcam Feed │       │  Streamlit UI     │       │  Microphone  │   │
│   │  (WebRTC)    │       │  (dashboard.py)   │       │  (Recorder)  │   │
│   └──────┬───────┘       └────────┬─────────┘       └──────┬───────┘   │
└──────────┼────────────────────────┼─────────────────────────┼──────────┘
           │ video frames           │ renders UI               │ audio WAV
           ▼                        │                          ▼
┌──────────────────┐                │                ┌──────────────────┐
│  WebRTC Processor│                │                │  Deepgram API    │
│  (webrtc_proc.py)│                │                │  (transcriber.py)│
│                  │                │                │                  │
│  EmotionDetector │                │                │  nova-2 model    │
│  PostureDetector │                │                │  keyword boost   │
└────────┬─────────┘                │                │  confidence chk  │
         │ emotion, posture         │                └────────┬─────────┘
         ▼                          │                         │ transcript
┌──────────────────┐                │                         ▼
│  @st.fragment     │                │                ┌──────────────────┐
│  render_metrics() │◄───polls 1s───┤                │  DecisionEngine  │
│  updates session  │                │                │  (decision_eng.) │
└──────────────────┘                │                │                  │
                                    │                │  Intent Matching │
                                    │                │  Query Extraction│
                                    │                └───┬──────────┬───┘
                                    │                    │          │
                                    │           ┌───────▼──┐   ┌──▼──────────┐
                                    │           │ Spotify   │   │ Groq LLM    │
                                    │           │ Controller│   │ (groq_cl.py)│
                                    │           │           │   │             │
                                    │           │ track-first│  │ Llama 3.3   │
                                    │           │ search     │  │ 70B         │
                                    │           └───────────┘   └─────────────┘
                                    │
                          ┌─────────▼──────────┐
                          │  Autonomous         │
                          │  Controller         │
                          │  (background thread)│
                          │  polls emotion every│
                          │  5s, suggests music  │
                          └─────────────────────┘
```

---

## 3. Complete File Map

```
JARVIS/
│
├── app.py                              ← Entry point. Sets asyncio policy, calls render_dashboard().
├── requirements.txt                    ← All Python dependencies.
├── packages.txt                        ← System-level Linux libs (libgl1 for OpenCV on cloud).
├── .env                                ← API keys (never committed).
├── .gitignore
├── SYSTEM_MANUAL.md                    ← This file.
│
├── config/
│   ├── __init__.py
│   └── settings.py                     ← Loads .env, exposes all API keys + constants as properties.
│
├── ui/
│   ├── __init__.py
│   └── dashboard.py                    ← THE MAIN FILE. All UI rendering, state management,
│                                          WebRTC setup, voice recording, Spotify OAuth, chat display.
│
├── vision/
│   ├── __init__.py
│   ├── webrtc_processor.py             ← VideoProcessorBase subclass. Receives browser video frames
│   │                                      via WebRTC, runs emotion + posture detection on every 10th frame.
│   ├── emotion_detector.py             ← DeepFace wrapper. Detects dominant emotion + confidence.
│   └── posture_detector.py             ← MediaPipe Pose wrapper. Detects upright vs slouched.
│
├── voice/
│   ├── __init__.py
│   └── transcriber.py                  ← Sends audio to Deepgram API. Keyword boosting, confidence
│                                          filtering, music-bleed rejection.
│
├── logic/
│   ├── __init__.py
│   ├── decision_engine.py              ← THE BRAIN. Priority-ordered intent matching, regex-based
│   │                                      query extraction, Spotify action dispatch, LLM prompt building.
│   └── autonomous_controller.py        ← Background thread. Polls emotion state, pushes music
│                                          suggestions when user is sad/angry (60s cooldown).
│
├── llm/
│   ├── __init__.py
│   ├── groq_client.py                  ← Sends (system_prompt + user_prompt) to Groq API.
│   └── prompts.py                      ← SYSTEM_PROMPT (rules) + build_contextual_prompt() function.
│
├── spotify/
│   ├── __init__.py
│   └── spotify_controller.py           ← Web-compatible OAuth flow (MemoryCacheHandler), track-first
│                                          search, pause-before-switch, device detection.
│
├── weather/
│   ├── __init__.py
│   └── weather_service.py              ← OpenWeather API. Cached per session. Returns temp/condition.
│
└── utils/
    ├── __init__.py
    ├── helpers.py                      ← get_spotify_playlist_for_emotion() — maps emotion → search query.
    └── logger.py                       ← Dual logger: writes to stdout + pushes to st.session_state.system_logs.
```

---

## 4. Boot Sequence — What Happens When The App Loads

This is the exact order of execution when a user opens the Streamlit app:

### Step 1: `app.py` runs
```
app.py
  └─► Sets asyncio event loop policy (Windows fix)
  └─► Calls render_dashboard()
```

### Step 2: `render_dashboard()` in `ui/dashboard.py`
```
render_dashboard()
  │
  ├─ 1. st.set_page_config()           ← Sets page title, wide layout
  │
  ├─ 2. preload_models()               ← @st.cache_resource — runs ONCE ever
  │     └─ Creates EmotionDetector()
  │     └─ Runs dummy detection on blank 224×224 image
  │     └─ Forces DeepFace to download model weights (~30s first time)
  │     └─ Result is cached — never runs again unless app restarts
  │
  ├─ 3. initialize_session_state()      ← Runs ONCE per session (guarded by 'initialized' flag)
  │     └─ Creates AudioTranscriber()
  │     └─ Creates GroqClient()
  │     └─ Creates SpotifyController()
  │     └─ Creates WeatherService() → immediately calls get_weather() → caches result
  │     └─ Creates DecisionEngine(groq, spotify)
  │     └─ Creates AutonomousController(decision_engine)
  │     └─ Initializes tracking: current_emotion, emotion_confidence, current_posture
  │     └─ Initializes UI state: chat_history=[], system_logs=[], autonomous_mode=False
  │     └─ Sets initialized=True
  │
  ├─ 4. Spotify OAuth Callback Check
  │     └─ Reads st.query_params for "code"
  │     └─ If found → calls spotify.handle_callback(code) → stores token → clears params → reruns
  │
  ├─ 5. Renders Sidebar
  │     └─ Autonomous Mode toggle
  │     └─ Spotify auth status / Connect link
  │     └─ System logs (scrollable)
  │
  ├─ 6. Renders Main Body
  │     └─ Title, API key warnings, weather widget
  │     └─ Autonomous suggestion alerts (Accept/Dismiss)
  │     └─ Two-column layout: [Vision + Voice] | [Chat History]
  │
  ├─ 7. WebRTC Camera (left column)
  │     └─ webrtc_streamer() with STUN + TURN servers
  │     └─ @st.fragment(run_every=1.0) polls ctx.video_processor for emotion/posture
  │
  ├─ 8. Voice Recorder (left column, below camera)
  │     └─ audio_recorder() widget with tuned thresholds
  │     └─ Live transcript display
  │     └─ Processing pipeline (see Section 6)
  │
  └─ 9. Chat History (right column)
        └─ Renders all user (🎙️) and JARVIS messages
```

---

## 5. File-by-File Responsibilities

### `config/settings.py`
- Loads `.env` using `python-dotenv`
- Exposes every API key as a `@property` that re-reads env each time
- Hardcoded constants: `GROQ_MODEL = "llama-3.3-70b-versatile"`, `AUTONOMOUS_COOLDOWN = 60s`, `EMOTION_THRESHOLD = 0.70`
- `DEBUG_INFO` dict tracks if .env was found (used by UI to show debug panel)

### `ui/dashboard.py` — The Orchestrator
This is the central hub. It:
1. Initializes all services into `st.session_state`
2. Handles Spotify OAuth callback (`?code=` in URL)
3. Renders the entire UI (sidebar + main body)
4. Manages the WebRTC camera lifecycle
5. Captures voice recordings, sends to transcriber, feeds to decision engine
6. Displays chat history and live transcript
7. Handles autonomous suggestion Accept/Dismiss buttons

**Session State Keys:**

| Key | Type | Purpose |
|-----|------|---------|
| `initialized` | bool | Guard — prevents re-initialization |
| `transcriber` | AudioTranscriber | Deepgram client |
| `groq` | GroqClient | LLM client |
| `spotify` | SpotifyController | Spotify API client |
| `weather_svc` | WeatherService | Weather API client |
| `decision_engine` | DecisionEngine | The brain |
| `autonomous` | AutonomousController | Background thread |
| `current_emotion` | str | Latest detected emotion |
| `emotion_confidence` | float | Latest emotion confidence (0-1) |
| `current_posture` | str | "upright", "slouched", or "unknown" |
| `weather` | dict | Cached weather data |
| `chat_history` | list[dict] | `[{"role":"user","text":"..."}, {"role":"jarvis","text":"..."}]` |
| `system_logs` | list[str] | Last 20 log messages |
| `autonomous_mode` | bool | Is background brain active? |
| `last_audio_hash` | str | MD5 of last audio — prevents duplicate processing |
| `spotify_token_info` | dict | OAuth token (set by SpotifyController) |
| `processing_voice` | bool | Lock — prevents concurrent transcriptions |
| `last_transcript` | str | Latest Deepgram transcript (displayed in UI) |
| `pending_suggestion` | dict | Autonomous suggestion awaiting user response |

### `vision/webrtc_processor.py` — Browser Camera Handler
- Extends `VideoProcessorBase` from `streamlit-webrtc`
- `recv(frame)` is called automatically by WebRTC for every video frame from the browser
- Converts `av.VideoFrame` → numpy BGR array
- Every 10th frame: runs `EmotionDetector.detect_emotion()` + `PostureDetector.detect_posture()`
- Stores results in `self.latest_emotion`, `self.latest_emotion_conf`, `self.latest_posture`
- Returns annotated frame (with pose skeleton drawn) back to the browser
- These attributes are polled by `render_metrics()` in dashboard.py every 1 second

### `vision/emotion_detector.py`
- Wraps `DeepFace.analyze()` with `detector_backend='opencv'` and `enforce_detection=False`
- Has its own frame-skipping (every 5th call) for CPU optimization
- Returns `(dominant_emotion: str, confidence: float)` — e.g. `("happy", 0.87)`
- Falls back to last known state on detection failure

### `vision/posture_detector.py`
- Uses MediaPipe Pose Landmarker (Tasks API, Python 3.13 compatible)
- Auto-downloads the `.task` model file on first run
- Simple heuristic: if `nose.y < shoulder_y - 0.2` → "upright", else "slouched"
- Draws pose skeleton on the frame and returns `(posture_status, annotated_frame)`

### `voice/transcriber.py` — Speech-to-Text
- Sends audio WAV to `https://api.deepgram.com/v1/listen` via HTTP POST
- Uses `nova-2` model with these key features:
  - **Keyword boosting**: `play:5, pause:5, stop:5, JARVIS:5` — tells Deepgram to prioritize these words
  - **Confidence filter**: If average word confidence < 55%, rejects transcript (likely background music)
  - **Music-bleed filter**: If transcript > 15 words with zero command words, rejects it (likely song lyrics)
- Returns empty string `""` for rejected transcripts — dashboard ignores empty strings
- Runs in a thread via `asyncio.to_thread()` to avoid blocking Streamlit
- Cleans up temp audio file after processing

### `logic/decision_engine.py` — The Brain
**This is the most critical file.** It decides what JARVIS does.

**Intent Matching (Priority Order):**

| Priority | Intent | Keywords | Action |
|----------|--------|----------|--------|
| 1 (highest) | PAUSE/STOP | "pause", "stop", "halt", "quiet", "silence", "mute", "stop music", etc. | `spotify.pause_music()` |
| 2 | PLAY (specific) | "play" + regex extracts song/artist | `spotify.play_music(query=extracted_query)` |
| 2 | PLAY (generic) | "play", "music", "song" but nothing specific | `spotify.play_music(query=emotion_playlist)` |

**Query Extraction (`_extract_search_query`):**
Uses 4 regex patterns in priority order:

```
Pattern 1: "play Blue Eyes by Arijit Singh"  →  "Blue Eyes Arijit Singh"
Pattern 2: "play music by Arijit Singh"      →  "Arijit Singh"
Pattern 3: "play Arijit Singh song"          →  "Arijit Singh"
Pattern 4: "play Tum Hi Ho"                  →  "Tum Hi Ho"
Generic:   "play music"                      →  None (emotion fallback)
```

**After action (or no action), builds LLM prompt:**
```
[CONTEXT: emotion=sad, posture=slouched, weather=cloudy 24°C]
[SYSTEM ACTION RESULT: Playing 'Tum Hi Ho' by Arijit Singh]
User said: play Tum Hi Ho
```

**LLM Response Rules (from SYSTEM_PROMPT):**
- Max 2 sentences. Never asks questions. References real song names from `[SYSTEM ACTION RESULT]`.

### `logic/autonomous_controller.py` — Background Brain
- Runs in a daemon thread (won't block app shutdown)
- Polls emotion state every 5 seconds
- If emotion is "sad" or "angry" with confidence > 70%:
  - Generates a suggestion: `"I detected you might be feeling sad. Would you like me to play a sad emotional hindi songs playlist?"`
  - Stores in `self.latest_suggestion` (thread-safe via Lock)
- 60-second cooldown between suggestions
- Dashboard polls `get_and_clear_suggestion()` on every render
- User sees Accept/Dismiss buttons

### `llm/groq_client.py`
- Creates a `Groq` client per call (stateless)
- Sends `system_prompt` + `user_prompt` to `llama-3.3-70b-versatile`
- `temperature=0.7`, `max_tokens=150`
- Returns the LLM's text response, or a fallback error message

### `llm/prompts.py`
- `SYSTEM_PROMPT`: 7 strict rules (max 2 sentences, never ask questions, reference real song names, etc.)
- `build_contextual_prompt()`: Injects emotion, posture, weather, and action result into the user's message

### `spotify/spotify_controller.py` — Music Playback
**OAuth Flow (web-compatible):**
1. `get_auth_url()` → returns Spotify authorize URL
2. User clicks link → Spotify redirects back with `?code=`
3. `dashboard.py` catches `?code=` → calls `handle_callback(code)` → exchanges for token
4. Token stored in `st.session_state.spotify_token_info`
5. `_get_client()` reads token from session, auto-refreshes if expired
6. Uses `MemoryCacheHandler()` — no filesystem cache (cloud-compatible)

**`play_music(query)`:**
1. Gets device list → picks active device (or first available)
2. **Pauses current playback first** (prevents 403 mid-song errors)
3. Waits 300ms for Spotify to settle
4. Searches **tracks first** (`type="track"`) → returns `"Playing '{name}' by {artist}"`
5. Falls back to **playlist search** if no track found
6. Handles Premium-required and no-device errors specifically

**`pause_music()`:**
1. Checks `current_playback()` — if already paused, returns `"Music is already paused."`
2. Only calls `pause_playback()` if something is actually playing

### `weather/weather_service.py`
- Calls OpenWeather API with `settings.LOCATION` (default: "London, UK")
- Returns `{temperature, humidity, condition, icon}`
- Cached per session — only makes one API call per session

### `utils/helpers.py`
- `get_spotify_playlist_for_emotion()` — maps emotion to Spotify search queries:

| Emotion | Search Query |
|---------|-------------|
| happy | "top hits upbeat energetic playlist" |
| sad | "sad emotional hindi songs arijit singh" |
| angry | "lofi chill calm relaxing playlist" |
| neutral | "top bollywood hindi songs playlist" |
| fear | "soothing calm ambient playlist" |
| surprise | "party hits popular songs playlist" |
| disgust | "chill vibes relaxing music playlist" |

### `utils/logger.py`
- Dual-output logger:
  - **stdout**: Standard Python logging with timestamps
  - **Streamlit**: Pushes formatted messages to `st.session_state.system_logs` (max 50)
- Every module uses `get_logger(__name__)` for consistent logging

---

## 6. Voice Command Pipeline — Complete Data Flow

When a user clicks the mic and speaks, this exact sequence happens:

```
Step 1: RECORD
  └─ audio_recorder() widget captures browser audio
  └─ Returns raw audio bytes (WAV format, 16kHz)

Step 2: VALIDATE
  └─ If len(audio_bytes) < 8000 → REJECTED (too short, ~0.5s = noise)
  └─ Compute MD5 hash of audio
  └─ If hash == last_audio_hash → REJECTED (duplicate)
  └─ Set processing_voice = True (lock)
  └─ Set last_transcript = "⏳ Transcribing..."

Step 3: TRANSCRIBE (voice/transcriber.py)
  └─ POST audio to Deepgram API with keyword boosting
  └─ Check word-level confidence → if avg < 0.55 → return "" (music bleed)
  └─ Check music-bleed heuristic → if >15 words, no commands → return ""
  └─ Return clean transcript string

Step 4: FILTER (ui/dashboard.py)
  └─ Store transcript in session state (for live display)
  └─ If transcript is empty or starts with "Error" → log and skip
  └─ Add to chat_history as user message

Step 5: DECIDE (logic/decision_engine.py)
  └─ Check PAUSE keywords first (highest priority)
  │     └─ If found → spotify.pause_music() → action = "paused"
  └─ Check PLAY keywords
  │     └─ Extract search query via regex patterns
  │     └─ If specific query found → spotify.play_music(query=...)
  │     └─ If generic → emotion fallback → spotify.play_music(query=emotion_playlist)
  └─ If no intent matched → no action taken

Step 6: RESPOND (llm/groq_client.py)
  └─ Build contextual prompt with emotion + posture + weather + action result
  └─ Send to Groq LLM (Llama 3.3 70B)
  └─ LLM responds in ≤2 sentences, referencing real song names
  └─ Add response to chat_history as jarvis message

Step 7: DISPLAY
  └─ Set processing_voice = False (unlock)
  └─ st.rerun() → UI refreshes with new chat messages + transcript display
```

---

## 7. WebRTC Camera Pipeline — Complete Data Flow

```
Step 1: CONNECT
  └─ webrtc_streamer() creates WebRTC connection from browser to server
  └─ Uses STUN servers (Google) for NAT discovery
  └─ Uses TURN servers (openrelay.metered.ca) for firewall relay
  └─ media_stream_constraints: video=True, audio=False

Step 2: RECEIVE (vision/webrtc_processor.py)
  └─ recv() called for every frame from browser
  └─ Increments frame counter

Step 3: ANALYZE (every 10th frame)
  └─ PostureDetector.detect_posture(frame)
  │     └─ MediaPipe Pose → nose/shoulder landmarks
  │     └─ Heuristic: nose above shoulders → "upright", else "slouched"
  │     └─ Draws skeleton on frame
  └─ EmotionDetector.detect_emotion(frame)
        └─ DeepFace.analyze() → dominant emotion + confidence
        └─ Frame-skips internally (every 5th call)

Step 4: STORE
  └─ self.latest_emotion = "happy"
  └─ self.latest_emotion_conf = 0.87
  └─ self.latest_posture = "upright"

Step 5: POLL (ui/dashboard.py @st.fragment every 1 second)
  └─ render_metrics() reads ctx.video_processor.latest_emotion/conf/posture
  └─ Updates st.session_state.current_emotion / emotion_confidence / current_posture
  └─ Updates autonomous controller state
  └─ Displays 3-column metrics: [Emotion] [Confidence] [Posture]

Step 6: RETURN
  └─ recv() returns annotated frame (with pose skeleton)
  └─ Browser displays the annotated video feed
```

---

## 8. Spotify OAuth Flow — Complete Sequence

```
Step 1: User opens app → sidebar shows "Spotify not connected"
Step 2: User clicks "Connect Spotify" link
Step 3: Browser navigates to Spotify authorize URL
Step 4: User grants permission on Spotify's website
Step 5: Spotify redirects back to app with ?code=XXXXX in URL
Step 6: dashboard.py detects ?code= in st.query_params
Step 7: spotify.handle_callback(code) exchanges code for access_token + refresh_token
Step 8: Token stored in st.session_state.spotify_token_info
Step 9: URL params cleared, page reruns
Step 10: Sidebar shows "Spotify connected" ✓
Step 11: All subsequent spotify.play_music() / pause_music() calls use stored token
Step 12: If token expires, _get_client() auto-refreshes using refresh_token
```

---

## 9. Autonomous Mode — Background Brain

```
When user toggles "Enable JARVIS Brain" ON:

  └─ AutonomousController.start()
  └─ Spawns daemon thread running _loop()
  └─ Every 5 seconds:
       └─ Read current emotion, confidence, posture, weather (thread-safe lock)
       └─ If emotion is "sad" or "angry" AND confidence > 70%:
            └─ Generate suggestion with emotion-mapped playlist
            └─ Store in self.latest_suggestion
            └─ Set 60-second cooldown
       └─ Dashboard polls get_and_clear_suggestion() on every render
       └─ If suggestion exists:
            └─ Show green alert: "💡 JARVIS Suggestion: ..."
            └─ Accept button → plays the suggested playlist
            └─ Dismiss button → clears suggestion
```

---

## 10. Anti-Spam and Quality Filters

| Filter | Location | What it does |
|--------|----------|-------------|
| Min audio length | dashboard.py | Rejects recordings < 8000 bytes (~0.5s) |
| Duplicate hash | dashboard.py | MD5 hash comparison prevents same audio processing twice |
| Processing lock | dashboard.py | `processing_voice` flag prevents concurrent transcriptions |
| Keyword boost | transcriber.py | Deepgram prioritizes "play", "pause", "stop" (weight 5) |
| Confidence filter | transcriber.py | Avg word confidence < 55% → rejected (background music) |
| Music-bleed filter | transcriber.py | >15 words with no command words → rejected (song lyrics) |
| Empty transcript | dashboard.py | Empty or error transcripts logged but not sent to engine |
| Pause-before-switch | spotify_controller.py | Pauses + 300ms delay before starting new track |

---

## 11. Environment Variables Required

```env
# Spotify (get from developer.spotify.com/dashboard)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=https://your-app.streamlit.app/

# Deepgram (get from console.deepgram.com)
DEEPGRAM_API_KEY=your_deepgram_api_key

# Groq (get from console.groq.com)
GROQ_API_KEY=your_groq_api_key

# OpenWeather (get from openweathermap.org/api)
OPENWEATHER_API_KEY=your_openweather_api_key

# Optional
LOCATION=London, UK
CAMERA_INDEX=0
```

---

## 12. Dependencies

```
streamlit>=1.30.0           ← UI framework
tornado<6.4                 ← Streamlit compatibility
opencv-python-headless>=4.8 ← Image processing (DeepFace needs it)
deepface>=0.0.79            ← Facial emotion detection
mediapipe>=0.10.9           ← Pose/posture detection
streamlit-webrtc>=0.47.0    ← Browser webcam via WebRTC
av>=10.0.0                  ← Video frame handling for WebRTC
audio-recorder-streamlit    ← Browser microphone recorder
pydub>=0.25.1               ← Audio processing
groq>=0.4.0                 ← Groq LLM API client
spotipy>=2.23.0             ← Spotify Web API client
python-dotenv>=1.0.0        ← .env file loading
requests>=2.31.0            ← HTTP client (Deepgram, Weather)
numpy>=1.26.0               ← Array operations
tf-keras>=2.15.0            ← DeepFace backend dependency
```

---

## 13. How to Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/kaustubh-d-IITR/JARVIS.git
cd JARVIS

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file with your API keys (see Section 11)

# 5. Run
streamlit run app.py
```

---

## 14. Known Constraints

1. **Spotify Premium Required** — Playback control (play/pause) only works with Spotify Premium accounts.
2. **Active Device Required** — Spotify must be open on at least one device (phone, desktop, or web player).
3. **WebRTC on Cloud** — Camera requires TURN servers for NAT traversal on Streamlit Cloud (configured).
4. **DeepFace Cold Start** — First boot downloads ~300MB of model weights. Subsequent boots are cached.
5. **Single User** — Session state is per-browser-tab. Each user gets their own isolated session.
