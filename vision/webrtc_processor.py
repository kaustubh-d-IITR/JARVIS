import cv2
import av
import streamlit as st
from streamlit_webrtc import VideoProcessorBase
from vision.emotion_detector import EmotionDetector
from vision.posture_detector import PostureDetector
from utils.logger import get_logger

logger = get_logger(__name__)

class JarvisVideoProcessor(VideoProcessorBase):
    def __init__(self):
        # We initialize detectors here since this runs on the server side
        self.emotion_detector = EmotionDetector(skip_frames=5)
        self.posture_detector = PostureDetector()
        
        # We only process 1 out of every 10 frames to save cloud CPU
        self.frame_counter = 0
        self.process_every_n_frames = 10
        
        self.latest_emotion = "neutral"
        self.latest_emotion_conf = 0.0
        self.latest_posture = "unknown"
        
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        # Convert WebRTC frame to numpy array (BGR for OpenCV)
        img = frame.to_ndarray(format="bgr24")
        self.frame_counter += 1
        
        # Heavy processing only occasionally
        if self.frame_counter % self.process_every_n_frames == 0:
            try:
                posture, annotated_img = self.posture_detector.detect_posture(img)
                emotion, conf = self.emotion_detector.detect_emotion(annotated_img)
                
                self.latest_emotion = emotion
                self.latest_emotion_conf = conf
                self.latest_posture = posture
                img = annotated_img
            except Exception as e:
                logger.error(f"WebRTC Processing Error: {e}")
        else:
            # On skipped frames, we still want to draw the *last* known metrics visually
            # (or we just return the raw image to keep latency low)
            pass
            
        # Write metrics to Streamlit session state dynamically so the UI can read them
        # (Note: webrtc threads run independently, so writing to session_state directly 
        # is safe as long as the main thread reads it safely)
        
        # Return the annotated frame back to the browser
        return av.VideoFrame.from_ndarray(img, format="bgr24")
