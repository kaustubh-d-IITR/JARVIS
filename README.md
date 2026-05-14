# JARVIS: Emotion-Aware AI Assistant

JARVIS is a real-time, emotion-aware AI assistant built with Streamlit. It uses computer vision (OpenCV, DeepFace, MediaPipe) to detect user emotions and posture, voice recognition (Deepgram) to understand spoken commands, and Groq LLM to respond intelligently. It can also autonomously suggest and play Spotify music matching your emotional state.

## Final Execution-Ready Setup

This project is now fully configured for local, CPU-friendly execution with robust background tasks and safe hardware handling.

### Zero-to-Hero Execution Steps

1. **Clone or Navigate to the Directory**:
   Open a terminal and navigate to your `JARVIS` folder.

2. **Create a Virtual Environment (Recommended)**:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   You should already have your `.env` file populated based on `.env.example`. Ensure the following keys exist:
   - `SPOTIFY_CLIENT_ID` & `SPOTIFY_CLIENT_SECRET`
   - `SPOTIFY_REDIRECT_URI=http://127.0.0.1:8501/callback`
   - `DEEPGRAM_API_KEY`
   - `GROQ_API_KEY`
   - `OPENWEATHER_API_KEY`

5. **Launch JARVIS**:
   Use the provided startup scripts. These will run hardware and API validation checks before launching the UI.
   
   **Windows**:
   ```cmd
   run_local.bat
   ```
   **Mac/Linux**:
   ```bash
   bash run_local.sh
   ```
   
   *(Alternatively, run `streamlit run app.py` directly).*

### Using JARVIS
- **Vision Panel**: Click "Start Camera". JARVIS processes every 5th frame for emotion detection to keep CPU usage low. Ensure your face is visible and well-lit. Use "Stop Camera" to release the hardware.
- **Voice Panel**: Click "Start Recording", speak your command, and click "Stop Recording". JARVIS will transcribe it in the background and respond.
- **Spotify**: Click "Play/Pause Music" from the sidebar. Note: Ensure Spotify is *open and active* on one of your devices so JARVIS can detect an active playback session.
- **Autonomous Mode**: Toggle "Enable JARVIS Brain" in the sidebar. If JARVIS detects negative emotions continuously, a suggestion box will appear in the UI offering to play mood-specific music.
