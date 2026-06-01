# AI MODEL PIPELINE & RESPONSIBILITIES

JARVIS separates its intelligence into highly specialized layers. By decoupling Perception from Reasoning, we achieve much higher stability and flexibility compared to monolithic models.

---

## 1. Perception Layer: Vision Language Model (VLM)
**File:** `vision/vlm_emotion_analyzer.py`  
**Model Locked:** `nvidia/nemotron-nano-12b-v2-vl:free` (via OpenRouter)

### Responsibility
The VLM's sole job is **High-Fidelity Emotional Interpretation**. It acts as JARVIS's "eyes".

### Why Not Local FER?
Early iterations used CNN-based Facial Expression Recognition. These models were heavily biased by room lighting, shadows, and face orientation, resulting in wild probability swings. 

### How The VLM Works
1. **Image Transport:** The Streamlit snapshot is converted from PIL -> JPEG buffer -> Base64 string.
2. **Facial Priority Prompting:** The model is fed a highly engineered prompt that strictly enforces rules:
   - *PRIORITIZE facial muscles, eyes, smile, and jaw tension.*
   - *IGNORE background, room lighting, wall colors.*
   - *DO NOT assume 'sadness' from dim lighting.*
3. **Structured Output:** The VLM is forced to return a JSON schema containing `primary_emotion`, `secondary_emotion`, and `facial_cues` (e.g., "squinting eyes, slight smile"). This provides deterministic data to the Decision Engine.
4. **Safety Lock:** Dynamic discovery is disabled. The system is hard-locked to the Nvidia model to guarantee schema compatibility and 404/402 error avoidance.

---

## 2. Reasoning Layer: Conversational LLM
**File:** `llm/groq_client.py`  
**Model:** `llama-3.3-70b-versatile` (via Groq)

### Responsibility
The Conversational LLM handles **Contextual Synthesis and Personality**. It acts as JARVIS's "voice".

### How It Works
1. **Context Aggregation:** The `DecisionEngine` compiles a massive context string using `prompts.py`. This string includes the User's transcript, the VLM's detected emotion, the current weather, and the action Spotify just took.
2. **Speed Execution:** Groq's LPU architecture is used because voice assistants require near-instantaneous response times. The 70B Llama model processes the context and returns conversational dialogue in under 800ms.
3. **Persona Maintenance:** It ensures JARVIS responds professionally, acknowledging the music being played while validating the user's emotional state.

---

## 3. Hearing Layer: Speech-to-Text
**File:** `voice/transcriber.py`  
**Model:** `nova-2` (via Deepgram)

### Responsibility
Converts raw audio bytes into actionable text.

### How It Works
1. **Keyword Boosting:** The API call is structured to heavily weight command words (`"pause:5"`, `"play:5"`).
2. **Bleed Rejection:** It acts as a filter, rejecting audio that is likely music bleeding from the speakers rather than a human command, ensuring JARVIS doesn't randomly change songs based on song lyrics.

---

## 4. Execution Layer: Spotify API
**File:** `spotify/spotify_controller.py`  

### Responsibility
The mechanical execution of the AI's intent.

### How It Works
- Translates high-level VLM moods ("calm", "sad") into specific curated queries ("lofi chill", "upbeat pop").
- Silently locates the user's active device.
- Handles the state management required to pause active tracks before switching contexts, preventing Spotify API 403 playback errors.
