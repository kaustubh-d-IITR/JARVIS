import cv2
import threading
import time
import numpy as np
from collections import Counter
from vision.emotion_detector import EmotionDetector
from vision.posture_detector import PostureDetector
from utils.logger import get_logger

logger = get_logger(__name__)

EMOTION_LABELS = [
    'angry', 'disgust', 'fear',
    'happy', 'sad', 'surprise', 'neutral'
]


class JarvisVideoProcessor:
    """
    Local OpenCV webcam processor.
    Runs in a background daemon thread.
    Collects emotion votes over 2-3 seconds then
    reports the dominant emotion via majority vote.
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

        # Majority vote buffer — 3 seconds at ~10 detections/sec
        self._emotion_buffer = []
        self._buffer_size = 30

        self._emotion_detector = None
        self._posture_detector = None

    def _init_detectors(self):
        """Initialize detectors inside the thread to avoid issues."""
        try:
            self._emotion_detector = EmotionDetector(
                checkpoint_path='vision/fer_checkpoint.tar'
            )
            self._posture_detector = PostureDetector()
            logger.info("Detectors initialized successfully.")
        except Exception as e:
            logger.error(f"Detector init error: {e}")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop,
            daemon=True
        )
        self._thread.start()
        logger.info("JarvisVideoProcessor started (local OpenCV).")

    def stop(self):
        self._running = False
        logger.info("JarvisVideoProcessor stopped.")

    def _capture_loop(self):
        self._init_detectors()

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error(
                "Could not open webcam at index 0. "
                "Check camera connection."
            )
            self._running = False
            return

        # Set reasonable resolution for performance
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        logger.info("Webcam opened successfully.")

        while self._running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            self._frame_count += 1
            annotated = frame.copy()

            # Run detection every 3rd frame for performance
            if self._frame_count % 3 == 0:
                try:
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

                        # Add to majority vote buffer
                        self._emotion_buffer.append(emotion)
                        if len(self._emotion_buffer) > self._buffer_size:
                            self._emotion_buffer.pop(0)

                        # Compute majority vote emotion
                        if self._emotion_buffer:
                            vote_counts = Counter(self._emotion_buffer)
                            dominant_emotion = vote_counts.most_common(1)[0][0]
                            dominant_count = vote_counts.most_common(1)[0][1]
                            majority_conf = (
                                dominant_count / len(self._emotion_buffer)
                            )

                            with self._lock:
                                self.latest_emotion = dominant_emotion
                                self.latest_emotion_conf = majority_conf

                        # Draw emotion label on frame
                        cv2.putText(
                            annotated,
                            f"{emotion} ({conf:.0%})",
                            (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 255, 0),
                            2
                        )

                except Exception as e:
                    logger.error(f"Frame processing error: {e}")

            # Convert BGR to RGB for Streamlit display
            frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            with self._lock:
                self.latest_frame = frame_rgb

            # ~30fps cap
            time.sleep(0.033)

        cap.release()
        logger.info("Webcam released.")

    def get_frame(self):
        with self._lock:
            return self.latest_frame

    def get_state(self):
        with self._lock:
            return (
                self.latest_emotion,
                self.latest_emotion_conf,
                self.latest_posture
            )
