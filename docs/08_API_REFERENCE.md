# API REFERENCE & EXTERNAL INTEGRATIONS

JARVIS relies entirely on cloud-based APIs to maintain a lightweight footprint. This document details the specific interactions and payload structures for each service.

---

## 1. OpenRouter API (Vision LLM)
**Endpoint:** `POST https://openrouter.ai/api/v1/chat/completions`

- **Authentication:** `Authorization: Bearer OPENROUTER_API_KEY`
- **Headers Required:** `HTTP-Referer`, `X-Title`
- **Locked Model:** `nvidia/nemotron-nano-12b-v2-vl:free`
- **Payload Structure:**
  ```json
  {
    "model": "nvidia/nemotron-nano-12b-v2-vl:free",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "Analyze the person's facial expression... Return ONLY valid JSON."},
          {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQ..."}}
        ]
      }
    ],
    "response_format": {"type": "json_object"}
  }
  ```
- **Response Handling:** Responses are strictly parsed as JSON. Markdown fences (e.g., ` ```json `) are programmatically stripped if the model hallucinates formatting.

---

## 2. Groq API (Conversational LLM)
**Endpoint:** Native Python SDK (`groq.Groq()`)

- **Authentication:** Auto-loads `GROQ_API_KEY` from environment.
- **Model:** `llama-3.3-70b-versatile`
- **Parameters:**
  - `temperature: 0.7` (Balances creativity with logical consistency)
  - `max_tokens: 150` (Ensures concise, fast verbal responses)
- **Usage:** Primarily handles the `build_contextual_prompt` execution in the Decision Engine.

---

## 3. Spotify Web API
**Endpoint:** Native Python SDK (`spotipy`)

- **Authentication:** OAuth2 Flow with PCKE via `SpotifyOAuth`.
- **Required Scopes:** `user-modify-playback-state user-read-playback-state`
- **Key Methods:**
  - `sp.devices()`: Queries all active user devices. Filters for `is_active == True`.
  - `sp.search(q=query, type="track", limit=5)`: Used to resolve "Play X" commands.
  - `sp.start_playback(device_id, uris=[])`: Commits the action.
- **Error Handling:** Explicitly traps "Premium Required" and "No Active Device" `spotipy.SpotifyException` errors to feed friendly UI alerts.

---

## 4. Deepgram API (Speech-to-Text)
**Endpoint:** `POST https://api.deepgram.com/v1/listen`

- **Authentication:** `Authorization: Token DEEPGRAM_API_KEY`
- **Model Parameters:**
  - `model: nova-2`
  - `smart_format: true`
  - `keywords: ["pause:5", "play:5", "JARVIS:5"]`
- **Payload:** Raw `.wav` bytes transmitted via standard HTTP POST.

---

## 5. OpenWeatherMap API
**Endpoint:** `GET http://api.openweathermap.org/data/2.5/weather`

- **Authentication:** `appid=OPENWEATHER_API_KEY`
- **Parameters:**
  - `q`: Location (defined in `settings.py`, default "London, UK")
  - `units: metric`
- **Usage:** Returns a simple JSON containing `temperature` and `condition` description. Cached internally after the first fetch to avoid quota abuse.
