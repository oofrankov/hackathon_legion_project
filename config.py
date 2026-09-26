"""All thresholds, texts, lists and model names in one place."""
import sys

# --- Camera -------------------------------------------------------------
CAMERA_INDEX = 0
CAMERA_WIDTH, CAMERA_HEIGHT = 640, 480
TARGET_FPS = 12
PREVIEW_W, PREVIEW_H = 324, 243   # camera view in the widget (memory only)
PREVIEW_FPS = 12
MODEL_PATH = "models/face_landmarker.task"

# Head-pose sign fixes. After `python app.py --debug`, pitch must grow when
# you lower your head. If it shrinks instead, set PITCH_SIGN = -1.
PITCH_SIGN = 1
YAW_SIGN = 1
ANGLE_SMOOTHING = 0.6            # EMA factor for yaw/pitch (1 = no smoothing)

# --- Calibration / gaze -------------------------------------------------
CALIBRATION_SECONDS = 10
CALIBRATION_POINT_SKIP_SEC = 0.4  # ignore samples right after the dot moves
CALIBRATION_MIN_FACE_RATIO = 0.5
CALIBRATION_MARGIN_DEG = 8       # added around the calibrated yaw/pitch range
DOWN_MARGIN_DEG = 12             # head this far below calibrated max pitch = DOWN
NO_FACE_SEC = 2
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
APP_WM_CLASS = "FocusCheck"                 # our own windows are ignored
USER_SETTINGS_PATH = "user_settings.json"   # local preferences only, no observed data

# --- Session ------------------------------------------------------------
DEFAULT_SELF_ESTIMATE_PCT = 80
DISTRACTION_NUDGE_SEC = 90       # configurable in the start window
MIN_NUDGE_SEC = 20
DISTRACTION_MIN_EVENT_SEC = 10   # min length of a distraction to be counted
BEST_SEGMENT_MIN = 10
UI_TICK_MS = 200
NUDGE_FLASH_TIMES = 6
MEME_POPUP_SEC = 4
SESSIONS_DIR = "sessions"
MEMES_DIR = "assets/memes"

# --- OpenAI -------------------------------------------------------------
OPENAI_MODEL = "gpt-5-nano"      # cheapest text model; change if unavailable
OPENAI_TIMEOUT_SEC = 15

# --- States -------------------------------------------------------------
FOCUSED = "FOCUSED"
DISTRACTED_SCREEN = "DISTRACTED_SCREEN"
PHONE = "PHONE"
LOOKING_AWAY = "LOOKING_AWAY"
AWAY = "AWAY"
STATES = [FOCUSED, DISTRACTED_SCREEN, PHONE, LOOKING_AWAY, AWAY]

STATE_COLORS = {
    FOCUSED: "#22c55e",
    DISTRACTED_SCREEN: "#eab308",
    PHONE: "#f97316",
    LOOKING_AWAY: "#fb923c",
    AWAY: "#9ca3af",
}
NUDGE_COLOR = "#ef4444"
PAUSED_COLOR = "#6b7280"

STATE_LABELS = {
    FOCUSED: "Focused",
    DISTRACTED_SCREEN: "Distracting window",
    PHONE: "Phone?",
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
}

# --- UI texts -----------------------------------------------------------
TEXTS = {
    "app_title": "FocusCheck",
    "start_subtitle": "See how focused you really are.",
    "name_label": "Session name (optional)",
    "name_hint": "Empty = {default}",
    "estimate_label": "How focused do you think you'll be?",
    "more_settings": "More settings",
    "nudge_label": "Remind me after this many seconds of distraction",
    "apps_link": "Distracting apps & sites ({n} on)  ›",
    "history_button": "View stats of past sessions",
    "apps_title": "Distracting apps & sites",
    "apps_subtitle": "FocusCheck only checks which window is on top, never what is inside it. "
                     "Untick anything you need for work.",
    "apps_custom_label": "Add your own (app or site name, e.g. chess.com, minecraft)",
    "apps_add": "Add",
    "apps_save": "Save",
    "wayland_warning": "Wayland session detected: window detection is off (all windows count as work). "
                       "Log in with an Xorg/X11 session for full FocusCheck.",
    "start_button": "Start session",
    "privacy_note": "Video never leaves this device and is never saved. "
                    "Keys and window titles are not recorded.",
    "err_nudge": "Reminder threshold must be a whole number, at least {n} seconds.",
    "err_camera": "Could not open the camera. Close other apps using it and try again.",
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
