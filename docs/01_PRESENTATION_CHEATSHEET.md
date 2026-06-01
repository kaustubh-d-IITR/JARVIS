# PRESENTATION CHEAT SHEET: JARVIS AI
*For presentation to the Company Owner*

## 1. The "Elevator Pitch"
"JARVIS is a real-time, multimodal AI assistant. It doesn't just hear your commands; it actively 'sees' your emotional state and proactively curates your environment by playing contextually appropriate music on Spotify. It's built entirely on a lightweight, serverless cloud architecture using state-of-the-art Vision Language Models."

## 2. The Architectural Evolution (The "Why")

**Q: Why didn't we just use a local CNN/FER model?**
"Initially, we did. But traditional Facial Expression Recognition (FER) is dumb. If you are sitting in a dark room staring at a screen, FER models often panic and output '80% Sadness'. They lack context. By pivoting to the **Nvidia Nemotron Vision LLM via OpenRouter**, we gave JARVIS actual human-like reasoning. It doesn't just spit out probabilities; it tells us *'The user has a relaxed jaw and a slight smile; they are calm, despite the dim lighting.'*"

## 3. The Core Tech Stack (The "How")
- **Perception:** `nvidia/nemotron-nano-12b-v2-vl:free` (OpenRouter API) for high-fidelity facial analysis.
- **Reasoning:** `llama-3.3-70b-versatile` (Groq API) for ultra-low latency conversational synthesis.
- **Hearing:** Deepgram `nova-2` for near-instant speech-to-text.
- **Action:** Spotify Web API (Spotipy) for cross-device playback control.
- **Frontend:** Streamlit for an event-driven, responsive UI.

## 4. Key Technical Innovations
1. **Separation of Concerns:** By decoupling the "Eyes" (VLM) from the "Brain" (Decision Engine), we can swap AI models in seconds without breaking the system.
2. **Music Bleed Rejection:** JARVIS is smart enough to ignore the music it is currently playing. We use Deepgram confidence scores and keyword boosting to reject "lyric bleed" from the microphone.
3. **Graceful Fallbacks:** If the camera breaks, or the room is too dark, JARVIS doesn't crash. It seamlessly falls back to Weather Data (e.g., "It's raining outside, let me put on some acoustic tracks").
4. **Hardware Independence:** Because we offloaded processing to OpenRouter and Groq, this application requires **zero local GPUs**. It can run on a $5/month cloud server while the user interacts via their mobile phone.

## 5. Overcoming the "Spotify 403" Challenge
*If asked about Spotify integration difficulties:*
"Spotify's API is notoriously strict. If you try to force a song to play while another track is buffering, Spotify throws a 403 Forbidden error. I architected a 'Pause-Sync-Play' wrapper in our `spotify_controller.py` that guarantees clean track switching across any active device."

## 6. API Cost and Scalability
**Q: How much will this cost to scale?**
"Virtually nothing right now. We are heavily utilizing the OpenRouter Free Tier for our vision processing and Groq's generous free tier for LLM reasoning. Because we capture event-based snapshots instead of streaming 30 FPS video to the cloud, our payload size and token consumption are minimized."

## 7. Demo Flow Script
*Follow this sequence during your live demo:*

1. **Start Fresh:** Ensure "Enable JARVIS Brain" is OFF. Ensure Spotify is open on your phone or PC.
2. **The "Look":** Click "Take a snapshot". Make a distinct face (e.g., a wide smile).
3. **The Proof:** Point to the **"🧠 Vision LLM"** tab in the Pipeline Monitor. Show the owner the specific *Facial Cues* JARVIS detected (e.g., "squinting eyes, visible smile").
4. **The Voice Override:** Click the Microphone. Say: *"Jarvis, pause the music."*
5. **The Chat:** Show how the transcript appears instantly and Groq replies conversationally.
6. **The Automation:** Toggle "Enable JARVIS Brain". Wait 5 seconds. Show how JARVIS pushes a music suggestion proactively based on your last known mood.

## 8. Future Improvements (Roadmap)
- **Face Identification:** Integrating embeddings to let JARVIS recognize *who* is sitting at the computer to load specific Spotify profiles.
- **WebSockets:** Upgrading the Streamlit UI to a React/FastAPI websocket architecture for sub-second UI updates without page reruns.
- **Home Assistant IoT:** Linking the Decision Engine to smart bulbs (e.g., turning lights blue if JARVIS detects a stressful mood).
