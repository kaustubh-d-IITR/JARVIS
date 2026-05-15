import cv2
import torch
import torch.nn.functional as F
import numpy as np
from torchvision import transforms
from vision.fer_resnet import ResNet18
from utils.logger import get_logger

logger = get_logger(__name__)

# FER2013 standard emotion labels — exact order matches model output
EMOTION_LABELS = [
    'angry', 'disgust', 'fear',
    'happy', 'sad', 'surprise', 'neutral'
]


class EmotionDetector:
    def __init__(self, checkpoint_path: str = 'vision/fer_checkpoint.tar'):
        self.device = torch.device(
            'cuda' if torch.cuda.is_available() else 'cpu'
        )
        self.model = self._load_model(checkpoint_path)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades +
            'haarcascade_frontalface_default.xml'
        )
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Grayscale(num_output_channels=1),
            transforms.Resize((48, 48)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.5],
                std=[0.5]
            )
        ])
        self._last_emotion = 'neutral'
        self._last_confidence = 0.0
        logger.info(f"EmotionDetector loaded on {self.device}")

    def _load_model(self, checkpoint_path: str):
        try:
            model = ResNet18()
            checkpoint = torch.load(
                checkpoint_path,
                map_location=self.device
            )
            # The checkpoint is saved as a dict with 'net' key
            # Try multiple common key names
            if 'net' in checkpoint:
                state_dict = checkpoint['net']
            elif 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
            elif 'model' in checkpoint:
                state_dict = checkpoint['model']
            else:
                # Checkpoint IS the state dict directly
                state_dict = checkpoint

            model.load_state_dict(state_dict)
            model.to(self.device)
            model.eval()
            logger.info("FER ResNet18 model loaded successfully.")
            return model
        except Exception as e:
            logger.error(f"Failed to load FER model: {e}")
            return None

    def detect_emotion(self, frame: np.ndarray):
        """
        Detect emotion from a single BGR frame.
        Returns (emotion_string, confidence_float)
        On failure returns last known state.
        """
        if self.model is None:
            return self._last_emotion, self._last_confidence

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            if len(faces) == 0:
                return self._last_emotion, self._last_confidence

            # Use the largest face found
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            face_roi = frame[y:y+h, x:x+w]

            # Preprocess for model
            input_tensor = self.transform(face_roi)
            input_tensor = input_tensor.unsqueeze(0).to(self.device)

            with torch.no_grad():
                outputs = self.model(input_tensor)
                probabilities = F.softmax(outputs, dim=1)
                confidence, predicted = torch.max(probabilities, 1)

            emotion = EMOTION_LABELS[predicted.item()]
            conf_value = confidence.item()

            self._last_emotion = emotion
            self._last_confidence = conf_value

            return emotion, conf_value

        except Exception as e:
            logger.error(f"Emotion detection error: {e}")
            return self._last_emotion, self._last_confidence

    def get_all_probabilities(self, frame: np.ndarray) -> dict:
        """
        Returns probability for all 7 emotions.
        Useful for debugging and UI display.
        """
        if self.model is None:
            return {e: 0.0 for e in EMOTION_LABELS}
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1,
                minNeighbors=5, minSize=(30, 30)
            )
            if len(faces) == 0:
                return {e: 0.0 for e in EMOTION_LABELS}

            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            face_roi = frame[y:y+h, x:x+w]
            input_tensor = self.transform(face_roi).unsqueeze(0).to(
                self.device
            )
            with torch.no_grad():
                outputs = self.model(input_tensor)
                probs = F.softmax(outputs, dim=1)[0]
            return {
                EMOTION_LABELS[i]: probs[i].item()
                for i in range(len(EMOTION_LABELS))
            }
        except Exception:
            return {e: 0.0 for e in EMOTION_LABELS}
