"""
JARVIS — Isolated FER Pipeline Test
Verifies face detection + emotion inference + majority vote outside Streamlit.
Run: python tests/test_fer_pipeline.py
Press 'q' to exit.
"""
import cv2
import sys
import time
import torch
import torch.nn.functional as F
import numpy as np
from collections import Counter
from torchvision import transforms

# Add project root to path so we can import vision modules
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.fer_resnet import ResNet18

EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']

CHECKPOINT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "vision", "fer_checkpoint.tar"
)


def load_model():
    print("[INFO] Loading FER ResNet18 model...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Device: {device}")

    model = ResNet18()
    ckpt = torch.load(CHECKPOINT_PATH, map_location=device)

    # Try known key names
    if "model_state_dict" in ckpt:
        model.load_state_dict(ckpt["model_state_dict"])
        print(f"[INFO] Loaded weights from key 'model_state_dict'")
    elif "net" in ckpt:
        model.load_state_dict(ckpt["net"])
    elif "state_dict" in ckpt:
        model.load_state_dict(ckpt["state_dict"])
    else:
        model.load_state_dict(ckpt)

    model.to(device)
    model.eval()

    params = sum(p.numel() for p in model.parameters())
    print(f"[PASS] Model loaded — {params:,} parameters")
    return model, device


def main():
    print("\n=== JARVIS FER Pipeline Test ===\n")

    # Load model
    model, device = load_model()

    # Prepare transforms
    preprocess = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((48, 48)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5], std=[0.5])
    ])

    # Face detector
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    print(f"[PASS] Haar cascade loaded")

    # Open webcam — try multiple methods
    cap = None
    backends = []
    if sys.platform == "win32":
        backends = [(cv2.CAP_DSHOW, "DSHOW"), (None, "default")]
    else:
        backends = [(None, "default")]

    for idx in [0, 1]:
        for backend_val, backend_name in backends:
            if backend_val is not None:
                cap = cv2.VideoCapture(idx, backend_val)
            else:
                cap = cv2.VideoCapture(idx)
                
            if cap.isOpened():
                ret, test_frame = cap.read()
                if ret and test_frame is not None:
                    print(f"[PASS] Webcam opened at index {idx} with backend {backend_name}")
                    break
                cap.release()
                cap = None
            else:
                cap = None
        if cap is not None:
            break

    if cap is None:
        print("[FAIL] Cannot open webcam. Close other camera apps first!")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Majority vote buffer
    emotion_buffer = []
    buffer_size = 30

    # FPS tracking
    fps_counter = 0
    fps_start = time.time()
    fps_display = 0.0
    frame_total = 0

    print("[INFO] Showing live FER feed. Press 'q' to exit.\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            frame_total += 1
            fps_counter += 1
            annotated = frame.copy()

            # FPS
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                fps_display = fps_counter / elapsed
                fps_counter = 0
                fps_start = time.time()

            # Face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )

            emotion_text = "no face"
            conf_text = ""

            if len(faces) > 0:
                # Use largest face
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                face_roi = frame[y:y+h, x:x+w]

                # FER inference
                t0 = time.perf_counter()
                try:
                    input_tensor = preprocess(face_roi).unsqueeze(0).to(device)
                    with torch.no_grad():
                        outputs = model(input_tensor)
                        probs = F.softmax(outputs, dim=1)
                        conf_val, pred_idx = torch.max(probs, 1)

                    emotion_text = EMOTION_LABELS[pred_idx.item()]
                    conf_text = f"{conf_val.item():.0%}"
                    inference_ms = (time.perf_counter() - t0) * 1000

                    # Majority vote
                    emotion_buffer.append(emotion_text)
                    if len(emotion_buffer) > buffer_size:
                        emotion_buffer.pop(0)

                except Exception as e:
                    print(f"[ERROR] FER inference: {e}")
                    inference_ms = 0

                # Draw face bounding box
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Draw emotion label above face
                label = f"{emotion_text} ({conf_text})"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                cv2.rectangle(annotated, (x, y - label_size[1] - 10),
                              (x + label_size[0] + 6, y), (0, 0, 0), -1)
                cv2.putText(annotated, label, (x + 3, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # Log every 30 frames
                if frame_total % 30 == 0:
                    print(f"  Frame {frame_total}: face=({x},{y},{w},{h}) "
                          f"emotion={emotion_text} conf={conf_text} "
                          f"inference={inference_ms:.1f}ms")

            # Majority vote display
            if emotion_buffer:
                vote_counts = Counter(emotion_buffer)
                dominant = vote_counts.most_common(1)[0][0]
                dom_count = vote_counts.most_common(1)[0][1]
                dom_conf = dom_count / len(emotion_buffer)

                cv2.putText(annotated, f"Dominant: {dominant} ({dom_conf:.0%})",
                            (10, annotated.shape[0] - 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)

                # Vote bar
                vote_str = " | ".join(f"{e}:{c}" for e, c in vote_counts.most_common())
                cv2.putText(annotated, vote_str,
                            (10, annotated.shape[0] - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

            # FPS
            cv2.putText(annotated, f"FPS: {fps_display:.1f}",
                        (annotated.shape[1] - 130, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

            cv2.imshow("JARVIS FER Pipeline Test", annotated)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted.")
    finally:
        cap.release()
        cv2.destroyAllWindows()

        if emotion_buffer:
            vote_counts = Counter(emotion_buffer)
            dominant = vote_counts.most_common(1)[0][0]
            print(f"\n[DONE] Frames: {frame_total}, FPS: {fps_display:.1f}")
            print(f"[DONE] Final dominant emotion: {dominant}")
            print(f"[DONE] Vote counts: {dict(vote_counts)}")
        else:
            print(f"\n[DONE] Frames: {frame_total} — no faces detected")


if __name__ == "__main__":
    main()
