"""Fullscreen calibration: a dot in the center and 4 corners, 2 s each."""
import time
import tkinter as tk

import config
from tracker.calibration import Calibrator

T = config.TEXTS
BG, FG, DOT = "#0f1115", "#f3f4f6", "#22c55e"


class CalibrationWindow(tk.Toplevel):
    def __init__(self, master, tracker, on_done, on_cancel):
        super().__init__(master, bg=BG)
        self.tracker, self.on_done, self.on_cancel = tracker, on_done, on_cancel
        self.title(T["calib_title"])
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.bind("<Escape>", lambda _e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.update_idletasks()
        self.w, self.h = self.winfo_screenwidth(), self.winfo_screenheight()
        self.msg = self.canvas.create_text(self.w / 2, self.h / 2 + 90, fill=FG,
                                           font=(config.UI_FONT, 18), text=T["calib_starting"])
        self.dot = None
        self.buttons = None
        self._job = None
        self._wait_for_camera()

    def _points(self):
        pad = 60
        return [(self.w / 2, self.h / 2), (pad, pad), (self.w - pad, pad),
                (self.w - pad, self.h - pad), (pad, self.h - pad)]

    def _wait_for_camera(self):
        if not hasattr(self, "_wait_since"):
            self._wait_since = time.monotonic()
        if self.tracker.error:
            self._fail(self.tracker.error)
            return
        s = self.tracker.latest()
        if s.frame_id > 0 and time.monotonic() - s.ts <= config.FRAME_STALE_SEC:
            del self._wait_since
            self._begin()
        elif time.monotonic() - self._wait_since > config.FIRST_FRAME_TIMEOUT_SEC:
            del self._wait_since
            self._fail(T["err_camera"])
        else:
            self._job = self.after(100, self._wait_for_camera)

    def _begin(self):
        if self.buttons:
            self.buttons.destroy()
            self.buttons = None
        self.calib = Calibrator()
        self.t_start = time.monotonic()
        self.canvas.itemconfig(self.msg, text=T["calib_hint"])
        self._tick()

    def _tick(self):
        elapsed = time.monotonic() - self.t_start
        per_point = config.CALIBRATION_SECONDS / 5
        idx = int(elapsed // per_point)
        if idx >= 5:
            self._finish()
            return
        x, y = self._points()[idx]
        r = 16
        if self.dot is None:
            self.dot = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=DOT, outline="")
        else:
            self.canvas.coords(self.dot, x - r, y - r, x + r, y + r)
        in_point = elapsed - idx * per_point
        signals = self.tracker.latest()
        if self.tracker.error or time.monotonic() - signals.ts > config.CAMERA_READ_TIMEOUT_SEC:
            self._fail(self.tracker.error or T["err_camera_lost"])   # camera stopped mid-way
            return
        self.calib.add(signals, collect=in_point >= config.CALIBRATION_POINT_SKIP_SEC, point=idx)
        self._job = self.after(50, self._tick)

    def _finish(self):
        if self.calib.ok():
            result = self.calib.result()
            anchor = self.calib.anchor()   # owner position/size, memory only, never logged
            print(f"[calibration] face {self.calib.face_ratio:.0%}, "
                  f"yaw {result.yaw_min:.1f}..{result.yaw_max:.1f}, "
                  f"pitch {result.pitch_min:.1f}..{result.pitch_max:.1f}, down > {result.down_threshold:.1f}")
            self.destroy()
            self.on_done(result, anchor)
        else:
            self._fail(T["calib_multi"] if self.calib.multi_face else T["calib_fail"])

    def _fail(self, text):
        if self.dot is not None:
            self.canvas.delete(self.dot)
            self.dot = None
        self.canvas.itemconfig(self.msg, text=text)
        self.buttons = tk.Frame(self, bg=BG)
        tk.Button(self.buttons, text=T["calib_retry"], command=self._retry, font=(config.UI_FONT, 14)).pack(side="left", padx=8)
        tk.Button(self.buttons, text=T["calib_cancel"], command=self._cancel, font=(config.UI_FONT, 14)).pack(side="left", padx=8)
        self.canvas.create_window(self.w / 2, self.h / 2 + 170, window=self.buttons)

    def _retry(self):
        stale = time.monotonic() - self.tracker.latest().ts > config.FRAME_STALE_SEC
        if self.tracker.error or not self.tracker.camera_on or stale:  # camera problem: restart it
            self.tracker.stop()
            self.tracker.start()
            if self.buttons:
                self.buttons.destroy()
                self.buttons = None
            self.canvas.itemconfig(self.msg, text=T["calib_starting"])
            self._wait_for_camera()
        else:
            self._begin()

    def _cancel(self):
        if self._job:
            self.after_cancel(self._job)
        self.destroy()
        self.on_cancel()
