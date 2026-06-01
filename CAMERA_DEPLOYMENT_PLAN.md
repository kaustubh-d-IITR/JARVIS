# CAMERA DEPLOYMENT PLAN

## Overview
The deployment version of JARVIS transitions completely from backend-controlled OpenCV camera capture (`cv2.VideoCapture()`) to frontend-controlled, browser-native camera capture via Streamlit's `st.camera_input()`.

## Why Browser Camera is Used
1. **Cloud Hardware Limitations**: Cloud servers hosting the deployed application do not have physical webcams attached (`/dev/video0`). Running local camera drivers will immediately fail.
2. **Browser Security Sandboxing**: Modern browsers explicitly block web applications from accessing local cameras unless initiated over HTTPS and approved by the user via the browser's permission prompt. `st.camera_input()` leverages the browser's built-in MediaDevices API to securely ask for permissions, capture the frame, and pass the image buffer back to the Python backend.
3. **Hardware Lock Avoidance**: Traditional backend webcam loops can cause lock contention, where the backend script blocks the frontend from accessing the hardware. Browser-native capture cleanly avoids this.
4. **Device Agnosticism**: Whether a user is on a desktop, tablet, or mobile phone, the browser abstracts the hardware. Streamlit will capture from the device's default camera safely.

## Removed Dependencies
- `tests/test_camera.py` (which attempted to run `cv2.VideoCapture(0)`) has been removed.
- All internal deployment dependence on OpenCV webcam capture has been eliminated.
- The `webrtc_processor.py` only handles static snapshots returned from the browser.

## Action Plan
- The system exclusively listens to `st.camera_input` in `ui/dashboard.py`.
- Images are processed in memory and written temporarily (without bloating storage).
