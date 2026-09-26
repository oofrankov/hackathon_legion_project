"""Collects head angles while the user looks at screen points; kept in memory only."""
from dataclasses import dataclass

import config


@dataclass
class CalibrationResult:
    yaw_min: float
    yaw_max: float
    pitch_min: float
    pitch_max: float
    down_threshold: float   # pitch above this = DOWN

    def contains(self, yaw, pitch):
        return self.yaw_min <= yaw <= self.yaw_max and self.pitch_min <= pitch <= self.pitch_max


def make_calibration(yaws, pitches, margin=None, down_margin=None):
    margin = config.CALIBRATION_MARGIN_DEG if margin is None else margin
    down_margin = config.DOWN_MARGIN_DEG if down_margin is None else down_margin
    p_max = max(pitches)
    return CalibrationResult(
        yaw_min=min(yaws) - margin,
        yaw_max=max(yaws) + margin,
        pitch_min=min(pitches) - margin,
        pitch_max=p_max + margin,
        down_threshold=p_max + max(margin, down_margin),
    )


class Calibrator:
    def __init__(self):
        self.yaws, self.pitches = [], []
        self.frames_total = 0
        self.frames_with_face = 0
        self._last_frame_id = -1

    def add(self, signals, collect=True):
        """Feed the latest FaceSignals; each camera frame is counted once."""
        if signals.frame_id == self._last_frame_id or signals.frame_id == 0:
            return
        self._last_frame_id = signals.frame_id
        self.frames_total += 1
        if signals.face_present:
            self.frames_with_face += 1
            if collect:
                self.yaws.append(signals.yaw)
                self.pitches.append(signals.pitch)

    @property
    def face_ratio(self):
        return self.frames_with_face / self.frames_total if self.frames_total else 0.0

    def ok(self):
        return self.face_ratio >= config.CALIBRATION_MIN_FACE_RATIO and len(self.yaws) >= 5

    def result(self) -> CalibrationResult:
        return make_calibration(self.yaws, self.pitches)
