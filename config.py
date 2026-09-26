"""All thresholds, texts, lists and model names in one place."""
import sys

# --- Camera -------------------------------------------------------------
CAMERA_INDEX = 0
CAMERA_WIDTH, CAMERA_HEIGHT = 640, 480
TARGET_FPS = 8
MODEL_PATH = "models/face_landmarker.task"

# Head-pose sign fixes. After `python app.py --debug`, pitch must grow when
# you lower your head. If it shrinks instead, set PITCH_SIGN = -1.
PITCH_SIGN = 1
YAW_SIGN = 1
ANGLE_SMOOTHING = 0.5            # EMA factor for yaw/pitch (1 = no smoothing)

# --- Calibration / gaze -------------------------------------------------
CALIBRATION_SECONDS = 10
CALIBRATION_POINT_SKIP_SEC = 0.4  # ignore samples right after the dot moves
CALIBRATION_MIN_FACE_RATIO = 0.5
CALIBRATION_MARGIN_DEG = 8       # added around the calibrated yaw/pitch range
DOWN_MARGIN_DEG = 12             # head this far below calibrated max pitch = DOWN
NO_FACE_SEC = 3
EAR_CLOSED_THRESHOLD = 0.2
STATE_HOLD_SEC = 2.5

# --- Input / window -----------------------------------------------------
INPUT_ACTIVE_WINDOW_SEC = 5
WINDOW_POLL_SEC = 1.0

DISTRACTING_KEYWORDS = [
    "youtube", "instagram", "tiktok", "netflix", "reddit", "twitch",
    "facebook", "twitter", "x.com", "discord", "steam", "9gag",
    "prime video", "disney+", "whatsapp", "telegram",
]

# --- Session ------------------------------------------------------------
DEFAULT_SESSION_MIN = 50
DEFAULT_SELF_ESTIMATE_MIN = 40
DISTRACTION_NUDGE_SEC = 90       # configurable in the start window
MIN_NUDGE_SEC = 20
DISTRACTION_MIN_EVENT_SEC = 10   # min length of a distraction to be counted
BEST_SEGMENT_MIN = 10
UI_TICK_MS = 250
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

# --- UI look ------------------------------------------------------------
UI_FONT = "Segoe UI" if sys.platform.startswith("win") else "Helvetica"

# --- UI texts -----------------------------------------------------------
TEXTS = {
    "app_title": "FocusCheck",
    "start_heading": "Start a focus session",
    "task_label": "What are you working on? (optional, stays on this device)",
    "duration_label": "Session length (minutes)",
    "estimate_label": "Honestly: how many of those {n} minutes will you really be focused?",
    "nudge_label": "Remind me after this many seconds of distraction",
    "keywords_label": "Extra distracting sites/apps (comma separated, optional)",
    "start_button": "Start",
    "privacy_note": "Video never leaves this device and is never saved. "
                    "Keys and window titles are not recorded.",
    "err_numbers": "Please enter whole numbers.",
    "err_estimate": "Your estimate must be between 0 and the session length.",
    "err_nudge": "Reminder threshold must be at least {n} seconds.",
    "err_camera": "Could not open the camera. Close other apps using it and try again.",
    "calib_title": "Calibration",
    "calib_hint": "Look at the dot. Keep your usual working posture.",
    "calib_starting": "Starting camera…",
    "calib_fail": "I could not see your face well.\n"
                  "Sit straight in front of the camera and add some light.",
    "calib_retry": "Try again",
    "calib_cancel": "Cancel",
    "widget_rec": "● REC  camera local",
    "widget_cam_off": "○ camera off",
    "widget_pause": "Pause",
    "widget_resume": "Resume",
    "widget_stop": "Stop",
    "widget_paused": "Paused",
    "widget_nudge": "Back to work?",
    "widget_calibrating": "Warming up…",
    "widget_report": "Building report…",
    "meme_caption": "Hey, your task misses you.",
    "privacy_footer": "Video never left your device. Only states and categories were saved.",
}
