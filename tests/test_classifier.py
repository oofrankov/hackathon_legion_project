"""Classifier, summary and privacy-related tests on synthetic data (no camera)."""
import config
from ai.advice import fallback_advice, numeric_only
from monitors.window import categorize, compile_keywords
from session.summary import compute_summary
from tests.fake_session import fake_events
from tracker.calibration import make_calibration
from tracker.classifier import (AWAY, DOWN, SCREEN, SIDE, StateSmoother,
                                classify_gaze, combine_state)

CALIB = make_calibration(yaws=[-5, 5], pitches=[-3, 4], margin=8, down_margin=12)
# yaw range -13..13, pitch range -11..12, DOWN when pitch > 16


# --- table 5.6 ---------------------------------------------------------
def test_away_wins_everything():
    assert combine_state(AWAY, "distracting", True) == config.AWAY


def test_down_without_input_is_phone():
    assert combine_state(DOWN, "work", False) == config.PHONE


def test_down_with_input_is_focused():
    assert combine_state(DOWN, "work", True) == config.FOCUSED
    assert combine_state(DOWN, "distracting", True) == config.FOCUSED


def test_side_is_looking_away():
    assert combine_state(SIDE, "work", True) == config.LOOKING_AWAY


def test_screen_distracting_window():
    assert combine_state(SCREEN, "distracting", False) == config.DISTRACTED_SCREEN
    assert combine_state(SCREEN, "distracting", True) == config.DISTRACTED_SCREEN


def test_screen_work_window():
    assert combine_state(SCREEN, "work", False) == config.FOCUSED


# --- gaze (5.5) --------------------------------------------------------
def test_gaze_screen_inside_range():
    assert classify_gaze(True, 0, 0, CALIB, 0) == SCREEN
    assert classify_gaze(True, 12, 11, CALIB, 0) == SCREEN


def test_gaze_down_below_range():
    assert classify_gaze(True, 0, 30, CALIB, 0) == DOWN
    assert classify_gaze(True, 0, 14, CALIB, 0) == SCREEN   # between range and down margin


def test_gaze_side():
    assert classify_gaze(True, 30, 0, CALIB, 0) == SIDE
    assert classify_gaze(True, -30, 0, CALIB, 0) == SIDE
    assert classify_gaze(True, 0, -25, CALIB, 0) == SIDE    # looking up


def test_gaze_away_only_after_no_face_sec():
    assert classify_gaze(False, 0, 0, CALIB, 1.0, prev_gaze=SCREEN) == SCREEN
    assert classify_gaze(False, 0, 0, CALIB, config.NO_FACE_SEC, prev_gaze=SCREEN) == AWAY


# --- smoothing ---------------------------------------------------------
def test_smoother_ignores_short_flicker():
    sm = StateSmoother(hold_sec=2.5)
    assert sm.update(config.PHONE, 0.0) == config.FOCUSED
    assert sm.update(config.PHONE, 1.0) == config.FOCUSED
    assert sm.update(config.FOCUSED, 1.5) == config.FOCUSED
    assert sm.update(config.PHONE, 2.0) == config.FOCUSED
    assert sm.update(config.PHONE, 4.4) == config.FOCUSED
    assert sm.update(config.PHONE, 4.6) == config.PHONE


# --- window category (5.3) --------------------------------------------
def test_window_categories():
    pat = compile_keywords(config.DISTRACTING_KEYWORDS)
    assert categorize("Funny cats - YouTube - Firefox", pat) == "distracting"
    assert categorize("thesis.docx - Word", pat) == "work"
    assert categorize("git upstream mainstream", pat) == "work"  # no false "steam"
    assert categorize(None, pat) == "work"


# --- summary (5.10) ----------------------------------------------------
def test_summary_on_fake_session():
    events = fake_events()
    s = compute_summary(events, self_estimate_min=26, nudges_count=2)
    assert s["total_min"] == round(len(events) / 60, 1)
    assert s["focused_min"] == round(1270 / 60, 1)
    assert s["phone_count"] == 3
    assert s["distraction_count"] == 5     # 20 s LOOKING_AWAY merges with PHONE episode
    assert s["longest_focus_streak_min"] == 7.0
    assert s["longest_focus_streak_start_min"] == 0
    assert 0 <= s["focus_pct"] <= 100
    assert s["estimate_gap_min"] == round(26 - s["focused_min"], 1)


def test_summary_empty():
    s = compute_summary([], 10)
    assert s["total_min"] == 0 and s["focus_pct"] == 0


# --- advice privacy ----------------------------------------------------
def test_only_numbers_go_to_openai():
    data = numeric_only({"focus_pct": 50, "task": "secret", "flag": True, "x": 1.5})
    assert data == {"focus_pct": 50, "x": 1.5}


def test_fallback_advice_has_tips():
    s = compute_summary(fake_events(), 26, 0)
    advice = fallback_advice(s)
    assert 2 <= len(advice["tips"]) <= 3 and advice["analysis"]
