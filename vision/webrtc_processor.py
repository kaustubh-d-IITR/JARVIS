from streamlit_webrtc import VideoProcessorBase
import av
import cv2
from vision.emotion_detector import EmotionDetector
from vision.posture_detector import PostureDetector
from utils.logger import get_logger

logger = get_logger(__name__)

class JarvisVideoProcessor(VideoProcessorBase):
    def __init__(self):
        self.latest_emotion = "neutral"
        self.latest_emotion_conf = 0.0
        self.latest_posture = "unknown"
        self.latest_frame = None
        self._frame_count = 0
        self._emotion_detector = EmotionDetector()
        self._posture_detector = PostureDetector()

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        self._frame_count += 1
        annotated = img.copy()
        if self._frame_count % 10 == 0:
            try:
                posture, annotated = self._posture_detector.detect_posture(img)
                emotion, conf = self._emotion_detector.detect_emotion(img)
                self.latest_emotion = emotion
                self.latest_emotion_conf = conf
                self.latest_posture = posture
            except Exception as e:
                logger.error(f"Detection error: {e}")
        return av.VideoFrame.from_ndarray(annotated, format="bgr24")
