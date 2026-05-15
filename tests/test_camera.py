"""
JARVIS — Isolated Camera Test
Verifies webcam works outside Streamlit.
Run: python tests/test_camera.py
Press 'q' to exit.

IMPORTANT: Close Streamlit and any other camera-using app first!
"""
import cv2
import time
import sys


def try_open_camera():
    """Try multiple backends and indices to find a working webcam."""
    # Try default first (most compatible)
    backends = []
    if sys.platform == "win32":
        backends.extend([
            ("DSHOW", cv2.CAP_DSHOW),
            ("default", None),
            ("MSMF", cv2.CAP_MSMF),
        ])
    else:
        backends.append(("default", None))

    for idx in [0, 1, 2]:
        for name, backend in backends:
            try:
                if backend is not None:
                    cap = cv2.VideoCapture(idx, backend)
                else:
                    cap = cv2.VideoCapture(idx)

                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        print(f"[PASS] Camera opened: index={idx}, backend={name}, "
                              f"resolution={frame.shape[1]}x{frame.shape[0]}")
                        return cap, idx, name
                    cap.release()
            except Exception as e:
                print(f"[WARN] index={idx}, backend={name}: {e}")

    return None, -1, "none"


def main():
    print("\n=== JARVIS Camera Test ===\n")
    print(f"[INFO] Platform: {sys.platform}")
    print(f"[INFO] OpenCV version: {cv2.__version__}")
    print(f"[INFO] Searching for working webcam...\n")

    cap, cam_idx, cam_backend = try_open_camera()

    if cap is None:
        print("\n[FAIL] No working webcam found.")
        print("       Possible causes:")
        print("       1. Another app is using the camera (close Streamlit first!)")
        print("       2. Camera drivers not installed")
        print("       3. Camera physically disconnected")
        print("       4. Camera permissions denied")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    fps_counter = 0
    fps_start = time.time()
    fps_display = 0.0
    frame_total = 0

    print("[INFO] Showing live feed. Press 'q' to exit.\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            frame_total += 1
            fps_counter += 1

            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                fps_display = fps_counter / elapsed
                fps_counter = 0
                fps_start = time.time()

            h, w = frame.shape[:2]
            cv2.putText(frame, f"FPS: {fps_display:.1f}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Frame: {frame_total} | {w}x{h}", (10, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            cv2.putText(frame, f"Camera: idx={cam_idx} backend={cam_backend}",
                        (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(frame, "Press 'q' to exit", (10, h - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 255), 1)

            cv2.imshow("JARVIS Camera Test", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted.")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print(f"\n[DONE] Frames: {frame_total}, FPS: {fps_display:.1f}")


if __name__ == "__main__":
    main()
