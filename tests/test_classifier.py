"""Classifier, summary and privacy-related tests on synthetic data (no camera)."""
import config
from monitors.app_settings import default_settings
from monitors.window import Rules, WindowInfo, WindowMonitor, classify, is_own_window
from session.advice import get_advice
from session.summary import compute_summary
from session.demo import fake_events
from tracker.calibration import make_calibration
from tracker.classifier import (AWAY, DOWN, SCREEN, SIDE, StateSmoother,
                                classify_gaze, combine_state)

CALIB = make_calibration(yaws=[-5, 5], pitches=[-3, 4], margin=8, down_margin=12)
# yaw range -13..13, pitch range -11..12, DOWN when pitch > 16


# --- table 5.6 ---------------------------------------------------------
def test_away_wins_everything():
    assert combine_state(AWAY, "distracting", True) == config.AWAY


def test_down_without_input_is_looking_away():
    assert combine_state(DOWN, "work", False) == config.LOOKING_AWAY


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
    assert sm.update(config.AWAY, 0.0) == config.FOCUSED
    assert sm.update(config.AWAY, 1.0) == config.FOCUSED
    assert sm.update(config.FOCUSED, 1.5) == config.FOCUSED
    assert sm.update(config.AWAY, 2.0) == config.FOCUSED
    assert sm.update(config.AWAY, 4.4) == config.FOCUSED
    assert sm.update(config.AWAY, 4.6) == config.AWAY


# --- window category (5.3, X11 rules) --------------------------------
DEFAULT_RULES = Rules.from_settings(default_settings())


def win(title="", wm_class=(), process="", exe="", pid=4242):
    return WindowInfo(title=title, wm_class=list(wm_class), process=process, exe=exe, pid=pid)


def test_facebook_tab_in_firefox_is_distracting():
    w = win("Facebook — Mozilla Firefox", ("Navigator", "firefox"), "firefox", "/usr/lib/firefox/firefox")
    assert classify(w, DEFAULT_RULES) == "distracting"


def test_facebook_tab_in_chrome_is_distracting():
    w = win("(3) Facebook - Google Chrome", ("google-chrome", "Google-chrome"), "chrome")
    assert classify(w, DEFAULT_RULES) == "distracting"


def test_work_tab_in_browser_is_work():
    w = win("Overleaf - thesis.tex - Google Chrome", ("google-chrome", "Google-chrome"), "chrome")
    assert classify(w, DEFAULT_RULES) == "work"


def test_discord_app_is_distracting():
    assert classify(win("#general | Discord", ("discord", "discord"), "Discord"), DEFAULT_RULES) == "distracting"


def test_flatpak_electron_app_matched_by_exe():
    w = win("Chat", (), "electron", "/var/lib/flatpak/app/com.discordapp.Discord/current/discord/Discord")
    assert classify(w, DEFAULT_RULES) == "distracting"


def test_vscode_is_work_even_with_youtube_in_title():
    w = win("youtube_downloader.py - Visual Studio Code", ("code", "Code"), "code", "/usr/share/code/code")
    assert classify(w, DEFAULT_RULES) == "work"   # not a browser: title is not checked


def test_empty_title_and_unknown_window_is_work():
    assert classify(win(""), DEFAULT_RULES) == "work"
    assert classify(win("", ("firefox",), "firefox"), DEFAULT_RULES) == "work"
    assert classify(None, DEFAULT_RULES) == "work"


def test_keywords_do_not_match_inside_words():
    w = win("box.com files - Firefox", ("firefox",), "firefox")
    assert classify(w, DEFAULT_RULES) == "work"      # "x.com" inside "box.com"


def test_messengers_off_by_default_but_can_be_enabled():
    tg = win("Telegram", ("telegram-desktop", "TelegramDesktop"), "telegram-desktop")
    assert classify(tg, DEFAULT_RULES) == "work"
    settings = default_settings()
    settings["enabled"]["telegram"] = True
    assert classify(tg, Rules.from_settings(settings)) == "distracting"


def test_user_exception_and_custom_entry():
    settings = default_settings()
    settings["enabled"]["youtube"] = False          # needed for work
    settings["custom"] = ["chess.com", "minecraft"]
    rules = Rules.from_settings(settings)
    assert classify(win("Lecture - YouTube - Firefox", ("firefox",), "firefox"), rules) == "work"
    assert classify(win("Play chess.com - Firefox", ("firefox",), "firefox"), rules) == "distracting"
    assert classify(win("Minecraft 1.21", ("Minecraft",), "java"), rules) == "distracting"


def test_own_window_is_ignored():
    assert is_own_window(win("FocusCheck", ("tk", config.APP_WM_CLASS), "python"))
    assert not is_own_window(win("Firefox", ("firefox",), "firefox"))


def test_wayland_means_everything_is_work(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    assert WindowMonitor(DEFAULT_RULES).category() == "work"


# --- summary (5.10) ----------------------------------------------------
def test_summary_on_fake_session():
    events = fake_events()
    s = compute_summary(events, self_estimate_pct=90, nudges_count=2)
    assert s["total_min"] == round(len(events) / 60, 1)
    assert s["focused_min"] == round(1270 / 60, 1)
    assert "phone_count" not in s and "phone_min" not in s
    assert s["distraction_count"] == 5
    assert s["longest_focus_streak_min"] == 7.0
    assert s["longest_focus_streak_start_min"] == 0
    assert 0 <= s["focus_pct"] <= 100
    assert s["self_estimate_min"] == 27.0
    assert s["estimate_gap_pct"] == 90 - s["focus_pct"]
    assert s["estimate_gap_min"] == round(27.0 - s["focused_min"], 1)


def test_summary_empty():
    s = compute_summary([], 10)
    assert s["total_min"] == 0 and s["focus_pct"] == 0


# --- offline advice ----------------------------------------------------
def test_offline_advice_has_tips():
    s = compute_summary(fake_events(), 90, 0)
    advice = get_advice(s)
    assert 2 <= len(advice["tips"]) <= 3 and advice["analysis"]


def test_old_sessions_with_phone_state_are_folded_into_looking_away():
    from session.summary import normalize_session
    data = {"events": [{"state": "PHONE"}, {"state": config.FOCUSED}],
            "summary": {"phone_min": 1.5, "looking_away_min": 0.5, "phone_count": 2}}
    normalize_session(data)
    assert [e["state"] for e in data["events"]] == [config.LOOKING_AWAY, config.FOCUSED]
    assert data["summary"] == {"looking_away_min": 2.0}


def test_frozen_camera_frame_is_not_a_face():
    """Old frame (camera unplugged/frozen) must end up AWAY, never stay SCREEN/FOCUSED."""
    from tracker.classifier import GazeTracker
    from tracker.face import FaceSignals
    gaze = GazeTracker(CALIB)
    s = FaceSignals(ts=10.0, last_face_ts=10.0, face_present=True, frame_id=5)
    assert gaze.update(s, 10.5) == SCREEN
    assert gaze.update(s, 3610.0) == AWAY
