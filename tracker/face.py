"""MediaPipe Face Landmarker wrapper running in a background thread.

Privacy: frames live only in local variables of the capture loop. They are
never written to disk, never queued and never sent anywhere.
"""
import math
import threading
import time
from dataclasses import dataclass
from typing import Optional

import config

LEFT_EYE = (33, 160, 158, 133, 153, 144)
RIGHT_EYE = (362, 385, 387, 263, 373, 380)


@dataclass
class FaceSignals:
    ts: float = 0.0               # time of the last processed frame
    face_present: bool = False
    yaw: float = 0.0              # degrees
    pitch: float = 0.0            # degrees, > 0 = head down
    ear: float = 0.0              # eye aspect ratio
    last_face_ts: float = 0.0     # when a face was last seen
    frame_id: int = 0


def angles_from_matrix(m):
    """Yaw/pitch (degrees) from MediaPipe's 4x4 facial transformation matrix.

    Uses the face's forward vector (canonical +Z, towards the camera) mapped
    into camera space (Y up): looking down tilts it to negative Y.
    """
    fx, fy, fz = m[0][2], m[1][2], m[2][2]
    yaw = math.degrees(math.atan2(fx, fz)) * config.YAW_SIGN
    pitch = math.degrees(math.atan2(-fy, math.hypot(fx, fz))) * config.PITCH_SIGN
    return yaw, pitch


def eye_aspect_ratio(lms, idx):
    p1, p2, p3, p4, p5, p6 = (lms[i] for i in idx)

    def d(a, b):
        return math.hypot(a.x - b.x, a.y - b.y)

    horiz = d(p1, p4)
    return (d(p2, p6) + d(p3, p5)) / (2 * horiz) if horiz > 1e-6 else 0.0


class FaceTracker:
    def __init__(self, debug=False):
        self.debug = debug
        self._lock = threading.Lock()
        self._signals = FaceSignals()
        self._thread = None
        self._stop = threading.Event()
        self.error: Optional[str] = None
        self.camera_on = False

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self.error = None
        self._stop.clear()
        with self._lock:
            self._signals = FaceSignals(last_face_ts=time.monotonic())
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._thread = None

    def latest(self) -> FaceSignals:
        with self._lock:
            s = self._signals
            return FaceSignals(**s.__dict__)

    def _run(self):
        import cv2
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision

        try:
            options = vision.FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=config.MODEL_PATH),
                running_mode=vision.RunningMode.VIDEO,
                num_faces=1,
                output_facial_transformation_matrixes=True,
            )
            landmarker = vision.FaceLandmarker.create_from_options(options)
        except Exception as e:  # missing model etc.
            self.error = f"Face model error: {e}"
            return

        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        if not cap.isOpened():
            self.error = config.TEXTS["err_camera"]
            landmarker.close()
            return

        self.camera_on = True
        period = 1.0 / config.TARGET_FPS
        t0 = time.monotonic()
        yaw_s = pitch_s = None
        a = config.ANGLE_SMOOTHING
        try:
            while not self._stop.is_set():
                started = time.monotonic()
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                ts_ms = int((time.monotonic() - t0) * 1000)
                result = landmarker.detect_for_video(image, ts_ms)
                del frame, rgb, image  # nothing from the frame outlives this loop

                now = time.monotonic()
                with self._lock:
                    s = self._signals
                    s.ts = now
                    s.frame_id += 1
                    if result.face_landmarks and result.facial_transformation_matrixes:
                        yaw, pitch = angles_from_matrix(result.facial_transformation_matrixes[0])
                        yaw_s = yaw if yaw_s is None else a * yaw + (1 - a) * yaw_s
                        pitch_s = pitch if pitch_s is None else a * pitch + (1 - a) * pitch_s
                        lms = result.face_landmarks[0]
                        s.face_present = True
                        s.yaw, s.pitch = yaw_s, pitch_s
                        s.ear = (eye_aspect_ratio(lms, LEFT_EYE) + eye_aspect_ratio(lms, RIGHT_EYE)) / 2
                        s.last_face_ts = now
                    else:
                        s.face_present = False
                        yaw_s = pitch_s = None
                    if self.debug:
                        print(f"face={s.face_present} yaw={s.yaw:6.1f} pitch={s.pitch:6.1f} ear={s.ear:.2f}")

                time.sleep(max(0.0, period - (time.monotonic() - started)))
        finally:
            cap.release()
            landmarker.close()
            self.camera_on = False
