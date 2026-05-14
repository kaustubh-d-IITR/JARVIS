import cv2
import numpy as np
from deepface import DeepFace
from utils.logger import get_logger

logger = get_logger(__name__)

class EmotionDetector:
    def __init__(self, skip_frames: int = 5):
        """
        Initializes the Emotion Detector.
        skip_frames: Process every Nth frame to optimize CPU performance.
        """
        self.skip_frames = skip_frames
        self.frame_count = 0
        self.last_emotion = "neutral"
        self.last_confidence = 0.0
        
    def detect_emotion(self, frame: np.ndarray) -> tuple[str, float]:
        """
        Detects emotion from a BGR image frame using DeepFace.
        Uses frame skipping for performance.
        """
        self.frame_count += 1
        
        # Only process every Nth frame
        if self.frame_count % self.skip_frames != 0:
            return self.last_emotion, self.last_confidence
            
        try:
            # DeepFace expects BGR image (OpenCV default)
            result = DeepFace.analyze(
                frame, 
                actions=['emotion'], 
                enforce_detection=False,
                detector_backend='opencv',
                silent=True
            )
            
            # DeepFace can return a list of faces if multiple are found
            if isinstance(result, list):
                result = result[0]
                
            dominant_emotion = result['dominant_emotion']
            # Convert emotion probabilities to confidence score for the dominant one
            confidence = result['emotion'][dominant_emotion] / 100.0
            
            self.last_emotion = dominant_emotion
            self.last_confidence = confidence
            
            return dominant_emotion, confidence
            
        except Exception as e:
            # If detection fails, return last known state
            logger.debug(f"Emotion detection failed this frame: {e}")
            return self.last_emotion, self.last_confidence
