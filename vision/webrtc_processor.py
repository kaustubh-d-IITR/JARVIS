import cv2
import threading
import time
import sys
import numpy as np
from collections import Counter
from vision.emotion_detector import EmotionDetector, EMOTION_LABELS
from vision.posture_detector import PostureDetector
from utils.logger import get_logger

logger = get_logger(__name__)


class JarvisVideoProcessor:
    """
    Local OpenCV webcam processor.
    Runs in a background daemon thread.
    Collects emotion votes over 2-3 seconds then
    reports the dominant emotion via majority vote.
    Includes face bounding box, emotion overlay, FPS tracking,
    and thread-safe resource management.
    """
    def __init__(self):
        self.latest_emotion = 'neutral'
        self.latest_emotion_conf = 0.0
        self.latest_posture = 'unknown'
        self.latest_frame = None
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._frame_count = 0
        self._start_time = 0

        # Majority vote buffer
        self._emotion_buffer = []
        self._buffer_size = 30

        # FPS tracking
        self._fps = 0.0
        self._fps_frame_count = 0
        self._fps_start_time = 0.0

        # Debug state
        self._vote_counts = {}
        self._last_face_coords = None
        self._inference_time_ms = 0.0
        self._cam_initialized = False
        self._error_msg = ""

        self._emotion_detector = None
        self._posture_detector = None

    def _init_detectors(self):
        """Initialize detectors inside the thread to avoid cross-thread issues."""
        try:
            logger.info("Initializing EmotionDetector...")
            self._emotion_detector = EmotionDetector(
                checkpoint_path='vision/fer_checkpoint.tar'
            )
            logger.info("Initializing PostureDetector...")
            self._posture_detector = PostureDetector()
            logger.info("All detectors initialized successfully.")
        except Exception as e:
            logger.error(f"Detector init error: {e}")
            self._error_msg = f"Detector init failed: {e}"

    def _try_open_camera(self):
        """Try multiple camera indices and backends to find a working webcam."""
        logger.info("Attempting to open webcam...")

        backends = []
        if sys.platform == "win32":
            backends = [(cv2.CAP_DSHOW, "DSHOW"), (None, "default")]
        else:
            backends = [(None, "default")]

        for idx in [0, 1, 2]:
            for backend_val, backend_name in backends:
                try:
                    if backend_val is not None:
                        cap = cv2.VideoCapture(idx, backend_val)
                    else:
                        cap = cv2.VideoCapture(idx)
                        
                    if cap.isOpened():
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            h, w = test_frame.shape[:2]
                            logger.info(f"Webcam opened: index={idx}, backend={backend_name}, resolution={w}x{h}")
                            return cap
                        else:
                            logger.info(f"Index {idx} ({backend_name}): opened but cannot read frames")
                            cap.release()
                    else:
                        logger.info(f"Index {idx} ({backend_name}): cannot open")
                except Exception as e:
                    logger.error(f"Index {idx} ({backend_name}): exception {e}")

        logger.error("No working webcam found on any index.")
        return None

    def start(self):
        """Start the capture thread. Prevents duplicate threads."""
        with self._lock:
            if self._running:
                logger.info("Already running, ignoring start().")
                return

            # Wait for any previous thread to fully terminate
            if self._thread is not None and self._thread.is_alive():
                logger.warning("Previous thread still alive, waiting for termination...")
                self._running = False
                self._thread.join(timeout=5.0)
                if self._thread.is_alive():
                    logger.error("Previous thread did not terminate! Cannot start new thread.")
                    return

            self._running = True
            self._frame_count = 0
            self._emotion_buffer = []
            self._fps_frame_count = 0
            self._fps_start_time = time.time()
            self._start_time = time.time()
            self._cam_initialized = False
            self._error_msg = ""
            self.latest_frame = None

        self._thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name="JARVIS-Camera"
        )
        self._thread.start()
        logger.info("Camera thread started.")

    def stop(self):
        """Stop the capture thread and release resources."""
        logger.info("Stopping camera thread...")
        self._running = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("Camera thread did not terminate in 5s.")
        with self._lock:
            self.latest_frame = None
            self._cam_initialized = False
        logger.info("Camera stopped.")

    def _capture_loop(self):
        """Main capture loop — runs in background thread."""
        logger.info("=== Camera thread _capture_loop START ===")

        # Step 1: Initialize detectors
        self._init_detectors()

        # Step 2: Open camera
        cap = self._try_open_camera()
        if cap is None:
            self._error_msg = "Cannot open webcam. Close other camera apps and try again."
            logger.error(self._error_msg)
            self._running = False
            return

        # Set resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        with self._lock:
            self._cam_initialized = True
        logger.info("Camera initialized. Entering frame loop.")

        consecutive_fails = 0

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    consecutive_fails += 1
                    if consecutive_fails > 50:
                        logger.error(f"50 consecutive read failures. Stopping.")
                        self._error_msg = "Camera stopped responding."
                        break
                    time.sleep(0.02)
                    continue

                consecutive_fails = 0
                self._frame_count += 1
                self._fps_frame_count += 1
                annotated = frame.copy()

                # FPS calculation every second
                now = time.time()
                elapsed = now - self._fps_start_time
                if elapsed >= 1.0:
                    with self._lock:
                        self._fps = self._fps_frame_count / elapsed
                    self._fps_frame_count = 0
                    self._fps_start_time = now

                # Run detection every 3rd frame for performance
                if self._frame_count % 3 == 0:
                    try:
                        t_start = time.perf_counter()

                        # Posture detection
                        if self._posture_detector:
                            posture, annotated = (
                                self._posture_detector.detect_posture(frame)
                            )
                            with self._lock:
                                self.latest_posture = posture

                        # Emotion detection
                        if self._emotion_detector:
                            emotion, conf = (
                                self._emotion_detector.detect_emotion(frame)
                            )

                            # Get face coordinates for bounding box
                            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            faces = self._emotion_detector.face_cascade.detectMultiScale(
                                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                            )

                            if len(faces) > 0:
                                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                                with self._lock:
                                    self._last_face_coords = (int(x), int(y), int(w), int(h))

                                # Draw face bounding box
                                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)

                                # Draw emotion label above face
                                label = f"{emotion} ({conf:.0%})"
                                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                                cv2.rectangle(annotated,
                                              (x, y - label_size[1] - 10),
                                              (x + label_size[0] + 6, y),
                                              (0, 0, 0), -1)
                                cv2.putText(annotated, label, (x + 3, y - 5),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            else:
                                with self._lock:
                                    self._last_face_coords = None

                            # Majority vote buffer
                            self._emotion_buffer.append(emotion)
                            if len(self._emotion_buffer) > self._buffer_size:
                                self._emotion_buffer.pop(0)

                            # Compute majority vote
                            if self._emotion_buffer:
                                vote_counts = Counter(self._emotion_buffer)
                                dominant_emotion = vote_counts.most_common(1)[0][0]
                                dominant_count = vote_counts.most_common(1)[0][1]
                                majority_conf = dominant_count / len(self._emotion_buffer)

                                with self._lock:
                                    self.latest_emotion = dominant_emotion
                                    self.latest_emotion_conf = majority_conf
                                    self._vote_counts = dict(vote_counts)

                        t_end = time.perf_counter()
                        with self._lock:
                            self._inference_time_ms = (t_end - t_start) * 1000

                    except Exception as e:
                        logger.error(f"Frame processing error: {e}")

                # Draw posture label bottom-left
                cv2.putText(annotated, f"Posture: {self.latest_posture}",
                            (10, annotated.shape[0] - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)

                # Draw FPS top-right
                cv2.putText(annotated, f"FPS: {self._fps:.0f}",
                            (annotated.shape[1] - 120, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

                # Convert BGR to RGB for Streamlit display
                frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                with self._lock:
                    self.latest_frame = frame_rgb

                # ~30fps cap
                time.sleep(0.033)

        except Exception as e:
            logger.error(f"Capture loop crashed: {e}")
            self._error_msg = f"Camera loop error: {e}"
        finally:
            cap.release()
            with self._lock:
                self._cam_initialized = False
            self._running = False
            logger.info("=== Camera thread _capture_loop END (resources released) ===")

    def get_frame(self):
        """Thread-safe frame getter for Streamlit display."""
        with self._lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def get_state(self):
        """Thread-safe state getter for metrics display."""
        with self._lock:
            return (
                self.latest_emotion,
                self.latest_emotion_conf,
                self.latest_posture
            )

    def get_debug_state(self):
        """Returns comprehensive debug info for the debug panel."""
        with self._lock:
            return {
                "running": self._running,
                "cam_initialized": self._cam_initialized,
                "error": self._error_msg,
                "fps": round(self._fps, 1),
                "frame_count": self._frame_count,
                "uptime_seconds": round(time.time() - self._start_time, 1) if self._start_time else 0,
                "emotion": self.latest_emotion,
                "emotion_confidence": round(self.latest_emotion_conf, 3),
                "posture": self.latest_posture,
                "vote_counts": dict(self._vote_counts),
                "buffer_size": len(self._emotion_buffer),
                "buffer_max": self._buffer_size,
                "inference_ms": round(self._inference_time_ms, 1),
                "face_detected": self._last_face_coords is not None,
                "face_coords": self._last_face_coords,
                "thread_alive": self._thread.is_alive() if self._thread else False,
            }
