"""All thresholds, texts, lists and paths in one place."""
import os
import sys
from pathlib import Path

APP_NAME = "FocusCheck"


# --- Paths: work both from source and inside a PyInstaller build -----------
def resource_path(relative: str) -> Path:
    """Bundled read-only files (model, templates, images)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def user_data_dir() -> Path:
    """Sessions and settings live here, never inside the (possibly read-only) app.
    FOCUSCHECK_DATA_DIR overrides it (used by tests)."""
    override = os.environ.get("FOCUSCHECK_DATA_DIR")
    if override:
        path = Path(override)
    elif sys.platform == "win32":
        path = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        path = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


DATA_DIR = user_data_dir()

# --- Camera -------------------------------------------------------------
CAMERA_INDEX = 0
CAMERA_WIDTH, CAMERA_HEIGHT = 640, 480
TARGET_FPS = 12
PREVIEW_W, PREVIEW_H = 324, 243   # camera view in the widget (memory only)
PREVIEW_FPS = 12
MODEL_PATH = resource_path("models/face_landmarker.task")

# Head-pose sign fixes. After `python app.py --debug`, pitch must grow when
# you lower your head. If it shrinks instead, set PITCH_SIGN = -1.
PITCH_SIGN = 1
YAW_SIGN = 1
ANGLE_SMOOTHING = 0.6            # EMA factor for yaw/pitch (1 = no smoothing)

# --- Calibration / gaze -------------------------------------------------
CALIBRATION_SECONDS = 10
CALIBRATION_POINT_SKIP_SEC = 0.4  # ignore samples right after the dot moves
CALIBRATION_MIN_FACE_RATIO = 0.5
CALIBRATION_MIN_SAMPLES_PER_POINT = 3   # fresh head-pose samples needed at each dot
CALIBRATION_MARGIN_DEG = 8       # added around the calibrated yaw/pitch range
DOWN_MARGIN_DEG = 12             # head this far below calibrated max pitch = DOWN
NO_FACE_SEC = 2
FRAME_STALE_SEC = 1.5            # older camera frame = no face (frozen/unplugged camera)
CAMERA_READ_TIMEOUT_SEC = 3      # no frames this long -> "camera lost" error
FIRST_FRAME_TIMEOUT_SEC = 15     # calibration gives up waiting for the camera
MAX_TICK_GAP_SEC = 5             # bigger gaps between UI ticks are not counted as session time
EAR_CLOSED_THRESHOLD = 0.2
STATE_HOLD_SEC = 1.5            # lower = faster reaction, more flicker

# --- Owner lock (no biometrics: only face position/size in the frame) ----
MAX_FACES = 3
OWNER_MAX_SHIFT = 0.15            # share of frame width the owner may move per 1 s
OWNER_SIZE_RATIO_MIN = 0.7
OWNER_SIZE_RATIO_MAX = 1.4
OWNER_SMOOTHING = 0.2             # EMA factor for the owner's last position/size
OWNER_RETURN_RADIUS = 0.2         # share of frame width around the calibration anchor
OWNER_RETURN_HOLD_SEC = 1.5       # a returning face must stay in the zone this long
OWNER_RECALIBRATE_AFTER_SEC = 300 # suggest recalibration after such a long absence
CALIBRATION_MAX_MULTI_FACE_RATIO = 0.1  # more frames with 2+ faces -> repeat calibration

# --- Input / window -----------------------------------------------------
INPUT_ACTIVE_WINDOW_SEC = 5
WINDOW_POLL_SEC = 1.0

# Distracting apps/sites catalogue. Only the category of the top window is used:
#  - browser window -> tab title is matched against "keywords"
#  - other apps     -> WM_CLASS / process name / exe path are matched against "apps"
# "default" = enabled on first launch; the user can untick or add their own.
# Messengers are off by default: people need them for work communication.
BROWSERS = ["google-chrome", "chrome", "chromium", "firefox", "brave", "opera",
            "microsoft-edge", "msedge", "vivaldi", "librewolf"]

DISTRACTION_CATALOG = [
    # id, name, group, keywords (tab titles), apps (WM_CLASS / process / exe), default
    {"id": "tiktok", "name": "TikTok", "group": "Social", "keywords": ["tiktok"], "apps": ["tiktok"], "default": True},
    {"id": "youtube", "name": "YouTube", "group": "Video", "keywords": ["youtube"], "apps": ["youtube", "freetube"], "default": True},
    {"id": "instagram", "name": "Instagram", "group": "Social", "keywords": ["instagram"], "apps": ["instagram"], "default": True},
    {"id": "facebook", "name": "Facebook", "group": "Social", "keywords": ["facebook"], "apps": ["facebook"], "default": True},
    {"id": "x", "name": "X (Twitter)", "group": "Social", "keywords": ["twitter", "x.com", "/ x"], "apps": ["twitter"], "default": True},
    {"id": "snapchat", "name": "Snapchat", "group": "Social", "keywords": ["snapchat"], "apps": ["snapchat"], "default": True},
    {"id": "reddit", "name": "Reddit", "group": "Social", "keywords": ["reddit"], "apps": ["reddit"], "default": True},
    {"id": "threads", "name": "Threads", "group": "Social", "keywords": ["threads.net", "threads.com", "• threads"], "apps": [], "default": True},
    {"id": "9gag", "name": "9GAG", "group": "Social", "keywords": ["9gag"], "apps": [], "default": True},
    {"id": "netflix", "name": "Netflix", "group": "Video", "keywords": ["netflix"], "apps": ["netflix"], "default": False},
    {"id": "twitch", "name": "Twitch", "group": "Video", "keywords": ["twitch"], "apps": ["twitch"], "default": False},
    {"id": "prime", "name": "Prime Video", "group": "Video", "keywords": ["prime video"], "apps": [], "default": False},
    {"id": "disney", "name": "Disney+", "group": "Video", "keywords": ["disney+"], "apps": [], "default": False},
    {"id": "pinterest", "name": "Pinterest", "group": "Social", "keywords": ["pinterest"], "apps": ["pinterest"], "default": False},
    {"id": "discord", "name": "Discord", "group": "Games & music", "keywords": ["discord"], "apps": ["discord", "vesktop", "webcord"], "default": True},
    {"id": "steam", "name": "Steam & games", "group": "Games & music", "keywords": [], "apps": ["steam"], "default": True},
    {"id": "spotify", "name": "Spotify", "group": "Games & music", "keywords": ["spotify"], "apps": ["spotify"], "default": True},
    {"id": "whatsapp", "name": "WhatsApp", "group": "Messengers", "keywords": ["whatsapp"], "apps": ["whatsapp", "zapzap"], "default": False},
    {"id": "telegram", "name": "Telegram", "group": "Messengers", "keywords": ["telegram"], "apps": ["telegram", "telegramdesktop"], "default": False},
    {"id": "signal", "name": "Signal", "group": "Messengers", "keywords": [], "apps": ["signal"], "default": False},
    {"id": "messenger", "name": "Messenger", "group": "Messengers", "keywords": ["messenger"], "apps": ["messenger", "caprine"], "default": False},
]
CATALOG_GROUPS = ["Social", "Video", "Messengers", "Games & music"]
APP_WM_CLASS = APP_NAME                     # our own windows are ignored
USER_SETTINGS_PATH = DATA_DIR / "user_settings.json"   # local preferences only, no observed data

# --- Session ------------------------------------------------------------
DEFAULT_SELF_ESTIMATE_PCT = 80
DISTRACTION_NUDGE_SEC = 90       # reminder after this many seconds of continuous distraction
DISTRACTION_MIN_EVENT_SEC = 10   # min length of a distraction to be counted
BEST_SEGMENT_MIN = 10
UI_TICK_MS = 200
NUDGE_FLASH_TIMES = 6
MEME_POPUP_SEC = 4
SESSIONS_DIR = DATA_DIR / "sessions"
MEMES_DIR = resource_path("assets/memes")
ICON_PNG = resource_path("assets/icon.png")

# --- States -------------------------------------------------------------
FOCUSED = "FOCUSED"
DISTRACTED_SCREEN = "DISTRACTED_SCREEN"
LOOKING_AWAY = "LOOKING_AWAY"
AWAY = "AWAY"
STATES = [FOCUSED, DISTRACTED_SCREEN, LOOKING_AWAY, AWAY]
# sessions recorded before the phone state was removed: shown as "Looking away"
LEGACY_STATES = {"PHONE": LOOKING_AWAY}

STATE_COLORS = {
    FOCUSED: "#22c55e",
    DISTRACTED_SCREEN: "#eab308",
    LOOKING_AWAY: "#fb923c",
    AWAY: "#9ca3af",
}
NUDGE_COLOR = "#ef4444"
PAUSED_COLOR = "#6b7280"

STATE_LABELS = {
    FOCUSED: "Focused",
    DISTRACTED_SCREEN: "Distracting window",
    LOOKING_AWAY: "Looking away",
    AWAY: "Away",
}

# --- UI look (Zoom-like dark) ---------------------------------------------
UI_FONT = "Segoe UI" if sys.platform.startswith("win") else "Helvetica"
UI = {
    "bg": "#1a1a1a",          # window background
    "panel": "#23272f",       # widget / card
    "border": "#3a3f4a",
    "field": "#2c313a",
    "hover": "#353a45",
    "text": "#f3f4f6",
    "muted": "#9ca3af",
    "icon": "#c9ccd1",
    "accent": "#0e72ed",      # primary button (Zoom blue)
    "accent_hover": "#2b86f5",
    "danger": "#ef4444",
    "warn": "#f97316",        # below-expectation numbers
}

# --- UI texts -----------------------------------------------------------
TEXTS = {
    "app_title": "FocusCheck",
    "start_subtitle": "See how focused you really are.",
    "name_label": "Session name (optional)",
    "name_hint": "Empty = {default}",
    "estimate_label": "How focused do you think you'll be?",
    "apps_link": "Distracting apps & sites ({n} on)",
    "history_button": "View stats of past sessions",
    "back": "Back",
    "new_session": "New session",
    "all_sessions": "All sessions",
    "open_browser": "Open in browser",
    "results_title": "Session report",
    "focus_score": "Focus score",
    "expected_vs_real": "What you expected vs. what happened",
    "expected_line": "You expected {pct}% focus (about {minutes}).",
    "reality_line": "Reality: {pct}% ({minutes}).",
    "expected": "Expected",
    "actual": "Actual",
    "timeline": "Timeline",
    "where_time_went": "Where the time went",
    "key_facts": "Key facts",
    "fact_distractions": "distractions (10 s+)",
    "fact_streak": "longest focus streak",
    "fact_best": "best stretch: min {a}-{b}",
    "fact_total": "tracked (without pauses)",
    "fact_nudges": "reminders",
    "coach": "Coach · based on your numbers",
    "history_title": "Your history",
    "history_empty": "No sessions yet. Finish your first session and it shows up here.",
    "overall_focus": "Overall focus",
    "big_picture": "The big picture",
    "history_headline": "{focused} of real focus in {total} tracked.",
    "gap_over": "On average you expect {n} points more focus than you get.",
    "gap_ok": "On average you match or beat your own estimate.",
    "totals": "Totals",
    "tile_sessions": "sessions over {days} day{s}",
    "tile_best": "best: {name}",
    "tile_distracting": "on distracting sites/apps",
    "trend_title": "Focus per session: expected vs. real",
    "real_focus": "Real focus %",
    "where_all_time_went": "Where all the time went",
    "all_sessions_title": "All sessions",
    "col_when": "When", "col_session": "Session", "col_length": "Length", "col_focus": "Focus",
    "col_expected": "Expected", "col_distr": "Distr.",
    "table_hint": "Click a session to open its report.",
    "apps_title": "Distracting apps & sites",
    "apps_subtitle": "FocusCheck only checks which window is on top, never what is inside it. "
                     "Untick anything you need for work.",
    "apps_custom_label": "Add your own (app or site name, e.g. chess.com, minecraft)",
    "apps_add": "Add",
    "apps_save": "Save",
    "macos_note": "On macOS FocusCheck sees app names only: apps like Discord or Steam are detected, "
                  "but not sites inside a browser (e.g. YouTube in Safari or Chrome).",
    "wayland_warning": "Wayland session detected: window detection is off (all windows count as work). "
                       "Log in with an Xorg/X11 session for full FocusCheck.",
    "start_button": "Start session",
    "privacy_note": "Video never leaves this device and is never saved. "
                    "Keys and window titles are not recorded.",
    "err_camera": "Could not open the camera. Close other apps using it and try again.",
    "err_camera_lost": "The camera stopped sending images. Check the cable or other apps using it.",
    "widget_cam_lost": "Camera unavailable",
    "err_save": "Could not save this session ({err}). The results below are only in memory: "
                "free some disk space or fix the permissions, then press Retry.",
    "retry_save": "Retry save",
    "calib_title": "Calibration",
    "calib_hint": "Look at the dot. Keep your usual working posture.",
    "calib_starting": "Starting camera…",
    "calib_fail": "I could not see your face well.\n"
                  "Sit straight in front of the camera and add some light.",
    "calib_multi": "Only you should be in the frame during calibration.\n"
                   "Ask others to step out of the camera view and try again.",
    "calib_retry": "Try again",
    "calib_cancel": "Cancel",
    "widget_rec": "● REC · stays on this device",
    "widget_cam_off": "Camera off",
    "widget_paused": "Paused",
    "widget_nudge": "Back to work?",
    "widget_report": "Building report…",
    "widget_focus": "focus",
    "widget_others": "+{n} other {people} in frame · ignored, not identified",
    "recal_text": "Welcome back! You were away for a while.\nQuick 10-second recalibration?",
    "recal_yes": "Recalibrate",
    "recal_no": "Skip",
    "meme_caption": "Hey, your task misses you.",
    "privacy_footer": "Video never left your device. Only states and categories were saved.",
}
