"""Keyboard/mouse activity: only the time of the last event is kept.

Privacy: the listener callbacks ignore their arguments, so which key was
pressed is never read, stored or logged.
"""
import threading
import time

import config


class InputActivity:
    def __init__(self):
        self._lock = threading.Lock()
        self._last_input_ts = 0.0
        self._listeners = []
        self.available = False

    def _touch(self, *_ignored):
        with self._lock:
            self._last_input_ts = time.monotonic()

    def start(self):
        try:
            from pynput import keyboard, mouse
            self._listeners = [
                keyboard.Listener(on_press=self._touch),
                mouse.Listener(on_move=self._touch, on_click=self._touch, on_scroll=self._touch),
            ]
            for listener in self._listeners:
                listener.daemon = True
                listener.start()
            self.available = True
        except Exception as e:
            print(f"[input] activity monitor unavailable: {e}")
            self.available = False

    def stop(self):
        for listener in self._listeners:
            try:
                listener.stop()
            except Exception:
                pass
        self._listeners = []

    def is_active(self, now=None):
        now = time.monotonic() if now is None else now
        with self._lock:
            return (now - self._last_input_ts) < config.INPUT_ACTIVE_WINDOW_SEC
