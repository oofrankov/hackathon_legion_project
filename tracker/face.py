"""MediaPipe Face Landmarker wrapper running in a background thread.

Privacy: frames are never written to disk and never sent anywhere. Only while
the widget's camera view is on, a small mirrored preview is kept in memory for
local display.
"""
import math
import threading
import time
from dataclasses import dataclass
from typing import Optional

import config
from tracker.owner_lock import OwnerLock, box_from_landmarks

LEFT_EYE = (33, 160, 158, 133, 153, 144)
RIGHT_EYE = (362, 385, 387, 263, 373, 380)


@dataclass
class FaceSignals:
    ts: float = 0.0               # time of the last processed frame
    face_present: bool = False    # the OWNER's face (other faces never count)
    yaw: float = 0.0              # degrees
    pitch: float = 0.0            # degrees, > 0 = head down
    ear: float = 0.0              # eye aspect ratio
    last_face_ts: float = 0.0     # when the owner's face was last seen
    frame_id: int = 0
    faces_count: int = 0          # all faces in the frame
    others_count: int = 0         # faces that are not the owner (ignored)
    calib_box: Optional[tuple] = None  # (cx, cy, size) of the single face, calibration only


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
        self._run_id = 0           # each start() gets its own id + stop event
        self.error: Optional[str] = None
        self.camera_on = False
        self.preview_enabled = False
        self._preview = None      # PPM bytes of the latest preview frame
        self._owner = OwnerLock()  # memory only; cleared at session end

    def start(self):
        """Start a capture thread. A previous thread that is still finishing keeps its
        own (already set) stop event and can no longer touch the shared state."""
        if self._thread and self._thread.is_alive() and not self._stop.is_set():
            return
        self.error = None
        self._stop = threading.Event()
        with self._lock:
            self._run_id += 1
            run_id = self._run_id
            self._signals = FaceSignals(last_face_ts=time.monotonic())
        self._thread = threading.Thread(target=self._run, args=(run_id, self._stop), daemon=True)
        self._thread.start()

    def stop(self):
        """Ask the thread to stop; waits briefly so the camera is usually released at once,
        but never blocks the UI for long (a stuck read finishes on its own later)."""
        self._stop.set()
        with self._lock:
            self._run_id += 1          # the old thread's writes are ignored from now on
            self._signals = FaceSignals(last_face_ts=time.monotonic())
            self._preview = None
        self.camera_on = False
        if self._thread:
            self._thread.join(timeout=0.5)

    # --- owner lock (thread-safe wrappers) -------------------------------
    def set_owner_anchor(self, anchor):
        """anchor = ((cx, cy), size) from calibration, or None to forget the owner."""
        with self._lock:
            if anchor is None:
                self._owner.clear()
            else:
                self._owner.set_anchor(anchor[0], anchor[1], time.monotonic())

    def owner_anchor(self):
        with self._lock:
            a = self._owner.anchor
            return ((a.cx, a.cy), a.size) if a else None

    def owner_touch(self):
        with self._lock:
            self._owner.touch(time.monotonic())

    def consume_recalibration_hint(self):
        with self._lock:
            hint = self._owner.recalibration_suggested
            self._owner.recalibration_suggested = False
            return hint

    def preview(self):
        with self._lock:
            return self._preview if self.camera_on else None

    def latest(self) -> FaceSignals:
        with self._lock:
            s = self._signals
            return FaceSignals(**s.__dict__)

    def _run(self, run_id, stop):
        try:
            self._capture(run_id, stop)
        except Exception as e:   # anything unexpected: report it, never keep a stale face
            with self._lock:
                if run_id == self._run_id:
                    self.error = f"Camera error: {type(e).__name__}"
        finally:
            with self._lock:
                if run_id == self._run_id:
                    self.camera_on = False
                    self._preview = None
                    self._signals.face_present = False
                    self._signals.faces_count = self._signals.others_count = 0

    def _capture(self, run_id, stop):
        import cv2
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision

        try:
            options = vision.FaceLandmarkerOptions(
                # a buffer instead of a path: robust to non-ASCII paths inside app bundles
                base_options=BaseOptions(model_asset_buffer=config.MODEL_PATH.read_bytes()),
                running_mode=vision.RunningMode.VIDEO,
                num_faces=config.MAX_FACES,
                output_facial_transformation_matrixes=True,
            )
            landmarker = vision.FaceLandmarker.create_from_options(options)
        except Exception as e:  # missing model etc.
            self.error = f"Face model error: {type(e).__name__}"
            return

        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # always process the freshest frame
        if not cap.isOpened():
            self.error = config.TEXTS["err_camera"]
            landmarker.close()
            return

        with self._lock:
            if run_id != self._run_id:      # stopped while the camera was opening
                cap.release()
                landmarker.close()
                return
            self.camera_on = True
        period = 1.0 / config.TARGET_FPS
        t0 = time.monotonic()
        last_ok = time.monotonic()
        yaw_s = pitch_s = None
        a = config.ANGLE_SMOOTHING
        try:
            while not stop.is_set():
                started = time.monotonic()
                ok, frame = cap.read()
                if not ok:
                    if time.monotonic() - last_ok > config.CAMERA_READ_TIMEOUT_SEC:
                        with self._lock:
                            if run_id == self._run_id:
                                self.error = config.TEXTS["err_camera_lost"]
                        return   # finally: camera off, face cleared -> AWAY, not FOCUSED
                    time.sleep(0.05)
                    continue
                last_ok = time.monotonic()
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                ts_ms = int((time.monotonic() - t0) * 1000)
                result = landmarker.detect_for_video(image, ts_ms)
                preview = None
                if self.preview_enabled:
                    small = cv2.resize(cv2.flip(frame, 1), (config.PREVIEW_W, config.PREVIEW_H))
                    preview = cv2.imencode(".ppm", small)[1].tobytes()
                aspect = frame.shape[0] / frame.shape[1]
                del frame, rgb, image  # only the small in-memory preview outlives this loop
                boxes = [box_from_landmarks(lms, aspect) for lms in result.face_landmarks]

                now = time.monotonic()
                with self._lock:
                    if run_id != self._run_id:   # this thread was stopped: drop the frame
                        break
                    s = self._signals
                    s.ts = now
                    s.frame_id += 1
                    self._preview = preview
                    s.faces_count = len(boxes)
                    s.calib_box = None
                    idx = None
                    if self._owner.has_anchor:
                        owner = self._owner.select(boxes, now)
                        idx = next((i for i, b in enumerate(boxes) if b is owner), None)
                        s.others_count = self._owner.others_count
                    else:
                        # calibration: only a single face in the frame counts
                        s.others_count = 0
                        if len(boxes) == 1:
                            idx = 0
                            s.calib_box = (boxes[0].cx, boxes[0].cy, boxes[0].size)
                    if idx is not None and idx < len(result.facial_transformation_matrixes):
                        yaw, pitch = angles_from_matrix(result.facial_transformation_matrixes[idx])
                        yaw_s = yaw if yaw_s is None else a * yaw + (1 - a) * yaw_s
                        pitch_s = pitch if pitch_s is None else a * pitch + (1 - a) * pitch_s
                        lms = result.face_landmarks[idx]  # other faces are never analysed
                        s.face_present = True
                        s.yaw, s.pitch = yaw_s, pitch_s
                        s.ear = (eye_aspect_ratio(lms, LEFT_EYE) + eye_aspect_ratio(lms, RIGHT_EYE)) / 2
                        s.last_face_ts = now
                    else:
                        s.face_present = False
                        yaw_s = pitch_s = None
                    if self.debug:
                        print(f"owner={s.face_present} others={s.others_count} "
                              f"yaw={s.yaw:6.1f} pitch={s.pitch:6.1f} ear={s.ear:.2f}")

                time.sleep(max(0.0, period - (time.monotonic() - started)))
        finally:
            cap.release()
            landmarker.close()
