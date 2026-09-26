"""Category of the top (active) window: "work" or "distracting".

Privacy (GDPR data minimisation): the title, WM_CLASS, process name and exe
path live only inside `WindowInfo` for a single classification and are then
dropped. They are never stored, returned, printed or logged. No screenshots,
no reading of window contents.
"""
import os
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional

import config

WORK, DISTRACTING = "work", "distracting"


@dataclass
class WindowInfo:
    """Transient snapshot of the top window. Never leaves this module."""
    title: str = ""
    wm_class: List[str] = field(default_factory=list)
    process: str = ""
    exe: str = ""
    pid: Optional[int] = None


def is_wayland():
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


# --- rules ----------------------------------------------------------------
def _boundary_regex(words):
    parts = [re.escape(w.strip().lower()) for w in words if w.strip()]
    if not parts:
        return None
    # not glued to letters/digits: "x.com" does not match "box.com"
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + r")(?![a-z0-9])")


class Rules:
    def __init__(self, keywords, apps, browsers=None):
        self.title_re = _boundary_regex(keywords)
        self.apps = [a.lower() for a in apps if a.strip()]
        self.browsers = [b.lower() for b in (browsers or config.BROWSERS)]

    @classmethod
    def from_settings(cls, user_settings):
        """Enabled catalogue entries + custom names (used as keyword and app)."""
        enabled = user_settings.get("enabled", {})
        keywords, apps = [], []
        for item in config.DISTRACTION_CATALOG:
            if enabled.get(item["id"], item["default"]):
                keywords += item["keywords"]
                apps += item["apps"]
        custom = [c for c in user_settings.get("custom", []) if c.strip()]
        return cls(keywords + custom, apps + custom)


def _ids(info):
    return [s.lower() for s in (*info.wm_class, info.process, info.exe) if s]


def classify(info: Optional[WindowInfo], rules: Rules):
    """Browser -> check tab title; other app -> check WM_CLASS/process/exe."""
    if info is None:
        return WORK   # nothing readable: don't punish the user
    ids = _ids(info)
    if any(b in i for i in ids for b in rules.browsers):
        title = (info.title or "").lower()
        return DISTRACTING if rules.title_re and title and rules.title_re.search(title) else WORK
    if any(a in i for i in ids for a in rules.apps):
        return DISTRACTING
    return WORK


def is_own_window(info):
    """FocusCheck never reacts to its own windows (Tk sets WM_CLASS, not the PID)."""
    if info is None:
        return False
    own_class = config.APP_WM_CLASS.lower()
    return info.pid == os.getpid() or any(c.lower() == own_class for c in info.wm_class)


# --- platform readers (all failures -> None) ------------------------------
def _process_details(info):
    if not info.pid:
        return
    try:
        import psutil
        p = psutil.Process(info.pid)
        info.process = p.name()
        try:
            info.exe = p.exe()
        except (psutil.AccessDenied, psutil.ZombieProcess, OSError):
            pass
    except Exception:
        pass


class _X11Reader:
    def __init__(self):
        from Xlib import X, display
        self.X = X
        self.d = display.Display()
        self.root = self.d.screen().root
        atom = self.d.intern_atom
        self.NET_ACTIVE = atom("_NET_ACTIVE_WINDOW")
        self.NET_NAME = atom("_NET_WM_NAME")
        self.NET_PID = atom("_NET_WM_PID")
        self.UTF8 = atom("UTF8_STRING")

    def read(self):
        prop = self.root.get_full_property(self.NET_ACTIVE, self.X.AnyPropertyType)
        if not prop or not prop.value or prop.value[0] == 0:
            return None
        win = self.d.create_resource_object("window", prop.value[0])
        info = WindowInfo()
        name = win.get_full_property(self.NET_NAME, self.UTF8)
        if name and name.value:
            v = name.value
            info.title = v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v)
        else:
            info.title = win.get_wm_name() or ""
            if isinstance(info.title, bytes):
                info.title = info.title.decode("latin-1", "replace")
        info.wm_class = list(win.get_wm_class() or [])
        pid = win.get_full_property(self.NET_PID, self.X.AnyPropertyType)
        info.pid = int(pid.value[0]) if pid and pid.value else None
        _process_details(info)
        return info


class _WindowsReader:
    def read(self):
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        info = WindowInfo(title=buf.value, pid=pid.value or None)
        _process_details(info)
        return info


class _MacReader:
    def read(self):
        from AppKit import NSWorkspace  # app name only, no tab titles
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if not app:
            return None
        return WindowInfo(process=str(app.localizedName() or ""), pid=int(app.processIdentifier()))


class WindowMonitor:
    def __init__(self, rules: Rules):
        self.rules = rules
        self.last = WORK
        self.disabled = is_wayland()
        self.reader = None
        if self.disabled:
            return
        try:
            if sys.platform.startswith("win"):
                self.reader = _WindowsReader()
            elif sys.platform == "darwin":
                self.reader = _MacReader()
            else:
                self.reader = _X11Reader()
        except Exception as e:  # no X display, missing lib...
            print(f"[window] detection unavailable ({type(e).__name__}); all windows count as work")

    def category(self):
        if self.disabled or self.reader is None:
            return WORK
        try:
            info = self.reader.read()
        except Exception:
            return WORK
        if is_own_window(info):
            return self.last   # our own widget/window: ignore, keep previous category
        self.last = classify(info, self.rules)
        return self.last
