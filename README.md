# JARVIS: Multimodal AI Assistant (Gemini-Powered)

JARVIS is a real-time, emotion-aware AI assistant built with Streamlit. It uses **Gemini Vision AI** for multimodal emotional perception, voice recognition (Deepgram) to understand spoken commands, and Groq LLM to respond intelligently. It can also autonomously suggest and play Spotify music matching your emotional state.

## 🚀 Quick Start

This project is now fully configured for high-fidelity multimodal analysis with a lightweight local footprint.

### Zero-to-Hero Execution Steps

1. **Clone or Navigate to the Directory**:
   Open a terminal and navigate to your `JARVIS` folder.

2. **Automated Setup**:
   Run the setup script for your platform. This will create a virtual environment, install dependencies, and validate your core files.
   
   **Windows**: `setup_local.bat`
   **Mac/Linux**: `bash setup_local.sh`

3. **Environment Variables**:
   Create a `.env` file based on `.env.example`. You **MUST** provide:
   - `GEMINI_API_KEY` (Get from [Google AI Studio](https://aistudio.google.com/app/apikey))
   - `GROQ_API_KEY`
   - `DEEPGRAM_API_KEY`
   - `SPOTIFY_CLIENT_ID` & `SPOTIFY_CLIENT_SECRET`
   - `OPENWEATHER_API_KEY`

4. **Launch JARVIS**:
   Use the provided launch scripts. These will run hardware and API validation checks before starting the UI.
   
   **Windows**: `run_jarvis.bat`
   **Mac/Linux**: `bash run_jarvis.sh`

### Using JARVIS
- **Vision Panel**: Click "START Camera" to see the live feed. Click **"Analyze My Mood"** to trigger a Gemini-powered multimodal analysis. The system validates face presence locally before sending frames to the API.
- **Voice Panel**: Click the microphone icon, speak your command, and click again to stop. JARVIS will transcribe and respond in the chat history.
- **Spotify**: Click "Connect Spotify" if not already authenticated. JARVIS will offer music recommendations based on your analyzed mood.
- **Autonomous Mode**: Toggle "Enable JARVIS Brain" in the sidebar. If JARVIS detects strong emotions, it will autonomously suggest music or actions to assist you.
