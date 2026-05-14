import cv2
import numpy as np
import os
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from utils.logger import get_logger

logger = get_logger(__name__)

class PostureDetector:
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), "pose_landmarker_lite.task")
        # Download the new Tasks API model if missing
        if not os.path.exists(self.model_path):
            logger.info("Downloading MediaPipe Pose model (required for Python 3.13+)...")
            url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
            urllib.request.urlretrieve(url, self.model_path)
            
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1)
        self.detector = vision.PoseLandmarker.create_from_options(options)
        
        self.mp_drawing = mp.tasks.vision.drawing_utils
        self.mp_drawing_styles = mp.tasks.vision.drawing_styles
        self.mp_pose = mp.tasks.vision

    def detect_posture(self, frame: np.ndarray) -> tuple[str, np.ndarray]:
        """
        Analyzes posture and returns (posture_status, annotated_frame).
        """
        # Convert BGR to RGB for MediaPipe
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        
        results = self.detector.detect(mp_image)
        
        annotated_frame = frame.copy()
        posture_status = "unknown"
        
        if results.pose_landmarks and len(results.pose_landmarks) > 0:
            pose_landmarks = results.pose_landmarks[0] # Get first person
            
            # Map landmarks to a compatible class for drawing_utils
            from mediapipe.framework.formats import landmark_pb2
            proto_landmarks = landmark_pb2.NormalizedLandmarkList()
            proto_landmarks.landmark.extend([
                landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z)
                for landmark in pose_landmarks
            ])
            
            self.mp_drawing.draw_landmarks(
                annotated_frame,
                proto_landmarks,
                self.mp_pose.PoseLandmarksConnections.POSE_LANDMARKS,
                self.mp_drawing_styles.get_default_pose_landmarks_style()
            )
                
            # Simple heuristic for posture based on shoulders and nose
            # index 0 is nose, 11 is left_shoulder, 12 is right_shoulder
            nose = pose_landmarks[0]
            l_shoulder = pose_landmarks[11]
            r_shoulder = pose_landmarks[12]
            
            shoulder_y = (l_shoulder.y + r_shoulder.y) / 2
            
            if nose.y < shoulder_y - 0.2:
                posture_status = "upright"
            else:
                posture_status = "slouched"
                
        return posture_status, annotated_frame
