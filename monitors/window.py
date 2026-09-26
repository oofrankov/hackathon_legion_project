"""Category of the active window: "work" or "distracting".

Privacy: the title is only matched against keywords inside `categorize()` and
immediately dropped. It is never stored, returned or logged.
"""
import re
import subprocess
import sys

import config

WORK, DISTRACTING = "work", "distracting"


def _active_title_windows():
    import pygetwindow
    w = pygetwindow.getActiveWindow()
    return w.title if w is not None else None


def _active_title_linux():
    # X11 only; on Wayland this returns None and we fall back to "work"
    root = subprocess.run(["xprop", "-root", "_NET_ACTIVE_WINDOW"],
                          capture_output=True, text=True, timeout=0.5).stdout
    m = re.search(r"window id # (0x[0-9a-fA-F]+)", root)
    if not m or int(m.group(1), 16) == 0:
        return None
    out = subprocess.run(["xprop", "-id", m.group(1), "_NET_WM_NAME", "WM_NAME"],
                         capture_output=True, text=True, timeout=0.5).stdout
    return out or None


def _active_title_macos():
    from AppKit import NSWorkspace  # app name only, no tabs
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    return app.localizedName() if app else None


def _active_title():
    try:
        if sys.platform.startswith("win"):
            return _active_title_windows()
        if sys.platform == "darwin":
            return _active_title_macos()
        return _active_title_linux()
    except Exception:
        return None


def compile_keywords(keywords):
    parts = [re.escape(k.strip().lower()) for k in keywords if k.strip()]
    if not parts:
        return None
    # keyword must not be glued to letters/digits ("steam" != "mainstream")
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + r")(?![a-z0-9])")


def categorize(title, pattern):
    if not title or pattern is None:
        return WORK   # unknown window: don't punish the user
    return DISTRACTING if pattern.search(title.lower()) else WORK


class WindowMonitor:
    def __init__(self, extra_keywords=()):
        self.pattern = compile_keywords(list(config.DISTRACTING_KEYWORDS) + list(extra_keywords))

    def category(self):
        return categorize(_active_title(), self.pattern)
