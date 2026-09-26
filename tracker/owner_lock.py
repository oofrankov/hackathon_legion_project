"""Keeps tracking locked on one person - the session owner - WITHOUT biometrics.

The owner is whoever sat in front of the camera during calibration. They are
recognised only by where their face is in the frame and how big it is, never
by who they are: no face embeddings, no recognition models. Other faces are
counted and otherwise ignored. Everything here lives in memory only.

Known limitation: if the owner leaves and someone else sits exactly in their
place at the same distance, that person can be taken for the owner.
"""
import math
from dataclasses import dataclass
from typing import List, Optional

import config


@dataclass
class FaceBox:
    """Face bounding box in frame fractions; `size` is in frame-width units."""
    cx: float
    cy: float
    size: float


def box_from_landmarks(landmarks, aspect):
    """Bounding box of MediaPipe landmarks. aspect = frame height / width."""
    xs = [p.x for p in landmarks]
    ys = [p.y for p in landmarks]
    w, h = max(xs) - min(xs), (max(ys) - min(ys)) * aspect
    # max(): turning the head narrows the box, nodding flattens it - one of them stays
    return FaceBox((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, max(w, h))


class OwnerLock:
    def __init__(self, aspect=config.CAMERA_HEIGHT / config.CAMERA_WIDTH):
        self.aspect = aspect
        self.clear()

    def clear(self):
        """Forget the owner (end of session / before calibration)."""
        self.anchor: Optional[FaceBox] = None
        self.last: Optional[FaceBox] = None
        self.last_seen: Optional[float] = None
        self._return_since: Optional[float] = None
        self.others_count = 0
        self.recalibration_suggested = False

    @property
    def has_anchor(self):
        return self.anchor is not None

    def set_anchor(self, center, size, now):
        """Owner's average face position/size from calibration."""
        self.clear()
        self.anchor = FaceBox(center[0], center[1], size)
        self.last = FaceBox(center[0], center[1], size)
        self.last_seen = now

    def touch(self, now):
        """After a pause: continue from the last position instead of 'returning'."""
        if self.has_anchor:
            self.last_seen = now

    # --- geometry --------------------------------------------------------
    def _dist(self, a, b):
        return math.hypot(a.cx - b.cx, (a.cy - b.cy) * self.aspect)

    @staticmethod
    def _size_ok(face, ref):
        ratio = face.size / ref.size if ref.size > 0 else 0
        return config.OWNER_SIZE_RATIO_MIN <= ratio <= config.OWNER_SIZE_RATIO_MAX

    def _lost(self, now):
        return self.last_seen is None or now - self.last_seen > config.NO_FACE_SEC

    # --- per frame -------------------------------------------------------
    def select(self, faces: List[FaceBox], now) -> Optional[FaceBox]:
        """Returns the owner's face among `faces`, or None. Others are only counted."""
        owner = None
        if self.has_anchor:
            owner = self._return(faces, now) if self._lost(now) else self._follow(faces, now)
        self.others_count = len(faces) - (1 if owner is not None else 0)
        return owner

    def _follow(self, faces, now):
        allowed = config.OWNER_MAX_SHIFT * max(1.0, now - self.last_seen)
        near = [f for f in faces if self._dist(f, self.last) < allowed and self._size_ok(f, self.last)]
        if not near:
            return None   # keep the last position: never drift towards other faces
        owner = min(near, key=lambda f: self._dist(f, self.last))
        a = config.OWNER_SMOOTHING
        self.last = FaceBox(self.last.cx + a * (owner.cx - self.last.cx),
                            self.last.cy + a * (owner.cy - self.last.cy),
                            self.last.size + a * (owner.size - self.last.size))
        self.last_seen = now
        return owner

    def _return(self, faces, now):
        """Owner was gone: accept a face only in the owner's zone, held for a while."""
        zone = [f for f in faces if self._dist(f, self.anchor) < config.OWNER_RETURN_RADIUS
                and self._size_ok(f, self.anchor)]
        if not zone:
            self._return_since = None
            return None
        if self._return_since is None:
            self._return_since = now
        if now - self._return_since < config.OWNER_RETURN_HOLD_SEC:
            return None
        owner = min(zone, key=lambda f: self._dist(f, self.anchor))
        if self.last_seen is not None and now - self.last_seen > config.OWNER_RECALIBRATE_AFTER_SEC:
            self.recalibration_suggested = True
        self.last = FaceBox(owner.cx, owner.cy, owner.size)
        self.last_seen = now
        self._return_since = None
        return owner
