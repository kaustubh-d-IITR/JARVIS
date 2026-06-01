# PROJECT ARCHITECTURE: JARVIS AI Multimodal Assistant

## 1. Executive Summary
JARVIS is a real-time, multimodal AI assistant designed to interpret a user's emotional state through visual cues and voice commands, and autonomously react by playing contextually appropriate music via Spotify. 

Originally envisioned with a local CNN/FER (Facial Expression Recognition) model, the system underwent a major architectural evolution. It now leverages a state-of-the-art **Vision Language Model (VLM)** via OpenRouter to achieve human-like visual reasoning. By decoupling perception (VLM), reasoning (Conversational LLM), and action (Spotify), JARVIS provides a highly resilient, cloud-powered emotional intelligence layer.

## 2. Core Problem & Solution

### The Problem with Local FER
The initial iteration of JARVIS relied on local HuggingFace inference and OpenCV webcam streaming. This approach proved fragile:
- **Environment Sensitivity:** It incorrectly classified emotions based on room lighting and shadows.
- **Hardware Dependency:** OpenCV looping blocked the Streamlit runtime, causing extreme latency.
- **Context Blindness:** A traditional classifier outputs raw probabilities (e.g., `sad: 0.8`), lacking the nuance to differentiate between "sadness" and a "calm/relaxed" resting face.

### The Multimodal VLM Solution
We replaced the local classifier with **`nvidia/nemotron-nano-12b-v2-vl:free`** (via OpenRouter). This shifted the architecture from simple classification to **multimodal reasoning**. The VLM explicitly analyzes facial muscle tension, eye states, and smiles, providing high-fidelity JSON output that explains *why* it chose a particular emotion.

## 3. High-Level Architecture Diagram

```text
+-------------------------------------------------------------------------+
|                          USER INTERFACE (Streamlit)                     |
|                                                                         |
|  [Webcam Snapshot]  <-->  [Voice Recorder]  <-->  [Pipeline Monitor]    |
+---------+-----------------------+------------------------+--------------+
          |                       |                        |
     (Image Bytes)          (Audio Bytes)            (System State)
          v                       v                        v
+--------------------+  +--------------------+  +-------------------------+
| PERCEPTION LAYER   |  | AUDIO LAYER        |  | CONTEXT LAYER           |
| (vision/vlm_...)   |  | (voice/transcri...)|  | (weather/weather_...)   |
| OpenRouter API     |  | Deepgram API       |  | OpenWeather API         |
| Nvidia Nemotron    |  | Nova-2 Engine      |  | Environmental Data      |
+---------+----------+  +---------+----------+  +---------+---------------+
          |                       |                       |
      (Emotion JSON)        (Transcript)           (Temperature/Condition)
          |                       |                       |
          +-----------------------+-----------------------+
                                  |
                                  v
+-------------------------------------------------------------------------+
|                        REASONING & DECISION LAYER                       |
|                                                                         |
|                       [logic/decision_engine.py]                        |
|                                                                         |
|   1. Gating logic (Confidence Thresholds, Voice overrides)              |
|   2. Groq LLM Client (llama-3.3-70b-versatile) for conversational AI    |
|   3. Playlist mapping (helpers.py)                                      |
+---------------------------------+---------------------------------------+
                                  |
                          (Execution Query)
                                  v
+-------------------------------------------------------------------------+
|                          ACTION LAYER (Spotify)                         |
|                                                                         |
|                    [spotify/spotify_controller.py]                      |
|                                                                         |
|  - OAuth & Session Management                                           |
|  - Active Device Targeting                                              |
|  - Music Playback / Pause Control                                       |
+-------------------------------------------------------------------------+
```

## 4. Component Layers Overview

### 1. Frontend Layer (`app.py`, `ui/dashboard.py`)
Built on Streamlit, this layer handles all user interactions. It uses `st.camera_input` for event-based visual snapshots and `audio_recorder_streamlit` for voice commands. The UI completely avoids blocking `while True` loops by shifting to a snapshot/event-driven model.

### 2. Perception Layer (`vision/vlm_emotion_analyzer.py`)
This module handles all visual understanding. It converts captured snapshots into base64 and securely transmits them to OpenRouter. The VLM is instructed via a strict prompt to prioritize facial features over environmental aesthetics, returning a structured JSON containing primary/secondary emotions and detected facial cues.

### 3. Reasoning Layer (`logic/decision_engine.py`, `llm/groq_client.py`)
The "brain" of JARVIS. It evaluates the JSON payload from the VLM. If confidence is high, it maps the emotion to a music vibe. If confidence is low, or no face is detected, it falls back to contextual data (like weather) to make a safe assumption. It also utilizes Groq's fast Llama 3 models to generate conversational responses to user commands.

### 4. Action Layer (`spotify/spotify_controller.py`)
The execution arm. It seamlessly handles Spotify OAuth flows, automatically locates the user's active listening device (phone/PC), and triggers playback for tracks or playlists based on the Decision Engine's recommendation.

### 5. Automation Layer (`logic/autonomous_controller.py`)
A background thread that periodically polls the application's state. When enabled via the UI, it allows JARVIS to proactively evaluate the user's mood and push music recommendations without explicit prompts.
