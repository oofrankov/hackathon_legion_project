"""Gaze classification, final focus state (table 5.6) and smoothing."""
import config

SCREEN, DOWN, SIDE, AWAY = "SCREEN", "DOWN", "SIDE", "AWAY"
WORK, DISTRACTING = "work", "distracting"


def classify_gaze(face_present, yaw, pitch, calib, seconds_without_face, prev_gaze=SCREEN):
    """Returns SCREEN / DOWN / SIDE / AWAY for a single moment."""
    if not face_present:
        # short dropouts (blink, hand on face) keep the previous gaze
        return AWAY if seconds_without_face >= config.NO_FACE_SEC else prev_gaze
    if pitch > calib.down_threshold:
        return DOWN
    # head turned sideways or above the screen; slightly below still counts as screen
    if not (calib.yaw_min <= yaw <= calib.yaw_max) or pitch < calib.pitch_min:
        return SIDE
    return SCREEN


def combine_state(gaze, window, input_active):
    """Table 5.6, in priority order."""
    if gaze == AWAY:
        return config.AWAY
    if gaze == DOWN:
        return config.FOCUSED if input_active else config.PHONE
    if gaze == SIDE:
        return config.LOOKING_AWAY
    if window == DISTRACTING:
        return config.DISTRACTED_SCREEN
    return config.FOCUSED


class StateSmoother:
    """Accepts a new state only after it held for `hold_sec` seconds."""

    def __init__(self, hold_sec=None, initial=config.FOCUSED):
        self.hold_sec = config.STATE_HOLD_SEC if hold_sec is None else hold_sec
        self.state = initial
        self._candidate = None
        self._candidate_since = 0.0

    def update(self, raw_state, now):
        if raw_state == self.state:
            self._candidate = None
        elif raw_state != self._candidate:
            self._candidate, self._candidate_since = raw_state, now
        elif now - self._candidate_since >= self.hold_sec:
            self.state, self._candidate = raw_state, None
        return self.state


class GazeTracker:
    """Stateful wrapper: keeps previous gaze across short face dropouts."""

    def __init__(self, calib):
        self.calib = calib
        self.gaze = SCREEN

    def update(self, signals, now):
        without_face = 0.0 if signals.face_present else now - signals.last_face_ts
        self.gaze = classify_gaze(signals.face_present, signals.yaw, signals.pitch,
                                  self.calib, without_face, self.gaze)
        return self.gaze
