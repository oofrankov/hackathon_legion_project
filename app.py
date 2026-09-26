"""FocusCheck entry point: python app.py [--debug] [--history] [--selftest] [--demo-report]"""
import argparse
import faulthandler
import random
import shutil
import sys
import json
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path

import config
from monitors.app_settings import enabled_count, load_settings, save_settings
from monitors.input_activity import InputActivity
from monitors.window import Rules, WindowMonitor, is_wayland
from report.history import build_history
from report.report import build_report
from session.advice import get_advice
from session.recorder import SessionRecorder, next_session_number
from session.summary import compute_summary
from tracker.classifier import GazeTracker, StateSmoother, combine_state
from tracker.face import FaceTracker
from ui.calibration_window import CalibrationWindow
from ui import theme
from ui.main_window import MainWindow
from ui.widget import Widget, ask_recalibration, show_meme


def beep(root):
    try:
        if sys.platform.startswith("win"):
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            return
    except Exception:
        pass
    root.bell()


class FocusCheckApp:
    def __init__(self, debug=False):
        if sys.platform.startswith("win"):
            try:  # crisp UI on high-DPI screens
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass
        self.root = tk.Tk(className=config.APP_WM_CLASS)  # WM_CLASS lets us ignore our own windows
        self.root.withdraw()
        theme.init(self.root)   # pixel sizes follow the screen DPI
        self.root.title(config.TEXTS["app_title"])
        try:
            self.root.iconphoto(True, tk.PhotoImage(file=str(config.ICON_PNG)))
        except tk.TclError:
            pass
        self.debug = debug
        self.tracker = FaceTracker(debug=debug)
        self.input = InputActivity()
        self.settings = None
        self.wayland = is_wayland()
        if self.wayland:
            print("[window] " + config.TEXTS["wayland_warning"])
        self.user_settings, first_run = load_settings()
        self.last_nudge_sec = config.DISTRACTION_NUDGE_SEC
        self.main = MainWindow(self.root, self)
        if first_run:  # let the user pick exceptions before the first session
            self.main.show_apps(first_run=True)
        else:
            self.main.show_start()

    # --- main window pages (called by ui.main_window / ui.results_pages) ---
    next_session_number = staticmethod(next_session_number)

    def apps_count(self):
        return enabled_count(self.user_settings)

    def show_start(self):
        self.main.show_start()

    def show_history(self):
        self.main.show_history()

    def edit_apps(self):
        self.main.show_apps()

    def save_apps(self, settings):
        self.user_settings = settings
        save_settings(settings)
        self.main.show_start()

    def open_session(self, filename):
        """Open a past session's report inside the app."""
        path = Path(config.SESSIONS_DIR, filename)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        from report.report import report_filename
        html = Path(config.SESSIONS_DIR, report_filename(data.get("started_at")))
        self.main.show_results(data, str(html) if html.exists() else None)

    def open_in_browser(self, path):
        webbrowser.open(Path(path).as_uri())

    def open_history_in_browser(self):
        build_history(open_browser=True)

    # --- flow ------------------------------------------------------------
    def start_session(self, settings):
        self.settings = settings
        self.last_nudge_sec = settings["nudge_threshold_sec"]
        self.main.withdraw()
        self.tracker.set_owner_anchor(None)   # calibration mode: exactly one face allowed
        self.tracker.start()
        CalibrationWindow(self.root, self.tracker, self.on_calibrated, self.on_calibration_cancel)

    def on_calibration_cancel(self):
        self.tracker.stop()
        self.main.show_start()

    def on_calibrated(self, calib, anchor):
        s = self.settings
        self.tracker.set_owner_anchor(anchor)  # lock tracking on the owner (position/size only)
        self.gaze = GazeTracker(calib)
        self.smoother = StateSmoother()
        self.windows = WindowMonitor(Rules.from_settings(self.user_settings))
        self.window_cat = "work"
        self.last_window_poll = 0.0
        self.recorder = SessionRecorder(s["self_estimate_pct"], s["nudge_threshold_sec"], s["name"])
        self.input.start()

        self.paused = False
        self.recalibrating = False
        self.stopping = False
        self.camera_error_shown = False
        self.active_sec = 0.0          # session time without pauses
        self.last_tick = time.monotonic()
        self.next_record = 1.0
        self.focused_sec = 0
        self.non_focus_since = None    # active_sec when non-FOCUSED streak began
        self.last_nudge = -1e9
        self.state = config.FOCUSED
        self.memes = sorted(p for p in Path(config.MEMES_DIR).glob("*")
                            if p.suffix.lower() in (".png", ".gif"))

        self.widget = Widget(self.root, self.toggle_pause, self.stop, self.set_camera_view)
        self.tick()

    # --- main loop -------------------------------------------------------
    def tick(self):
        if self.stopping:
            return
        now = time.monotonic()
        dt, self.last_tick = now - self.last_tick, now

        if self.tracker.consume_recalibration_hint() and not (self.paused or self.recalibrating):
            ask_recalibration(self.root, self.widget, self.recalibrate)

        if not (self.paused or self.recalibrating):
            if self.tracker.error and not self.camera_error_shown:
                print(f"[camera] {self.tracker.error}")
                self.camera_error_shown = True
            self.active_sec += dt
            signals = self.tracker.latest()
            gaze = self.gaze.update(signals, now)
            if now - self.last_window_poll >= config.WINDOW_POLL_SEC:
                self.window_cat = self.windows.category()
                self.last_window_poll = now
            input_active = self.input.is_active(now)
            self.state = self.smoother.update(combine_state(gaze, self.window_cat, input_active), now)

            # one event per active second
            while self.active_sec >= self.next_record:
                t = int(self.next_record) - 1
                self.recorder.record(t, gaze, self.window_cat, input_active, self.state)
                self.focused_sec += self.state == config.FOCUSED
                self.next_record += 1

            self.check_nudge()

        n = len(self.recorder.events)
        focus_pct = round(self.focused_sec / n * 100) if n else 100
        others = 0 if self.paused else self.tracker.latest().others_count
        self.widget.show(self.state, self.active_sec, focus_pct, paused=self.paused,
                         camera_on=self.tracker.camera_on, others=others)
        self.root.after(config.UI_TICK_MS, self.tick)

    def check_nudge(self):
        if self.state == config.FOCUSED:
            self.non_focus_since = None
            return
        if self.non_focus_since is None:
            self.non_focus_since = self.active_sec
        threshold = self.settings["nudge_threshold_sec"]
        if (self.active_sec - self.non_focus_since >= threshold
                and self.active_sec - self.last_nudge >= threshold):
            self.last_nudge = self.active_sec
            self.recorder.add_nudge(int(self.active_sec))
            self.widget.flash()
            beep(self.root)
            if self.memes:
                show_meme(self.root, str(random.choice(self.memes)), self.widget)

    def set_camera_view(self, on):
        self.tracker.preview_enabled = on
        if on:
            self.preview_loop()

    def preview_loop(self):
        if self.stopping or not self.widget.camera_view:
            return
        self.widget.set_frame(self.tracker.preview())
        self.root.after(int(1000 / config.PREVIEW_FPS), self.preview_loop)

    # --- recalibration after a long absence ------------------------------
    def recalibrate(self):
        self.recalibrating = True             # session time does not run meanwhile
        self._old_anchor, self._old_calib = self.tracker.owner_anchor(), self.gaze.calib
        self.tracker.set_owner_anchor(None)
        CalibrationWindow(self.root, self.tracker, self.on_recalibrated, self.on_recalibration_cancel)

    def on_recalibrated(self, calib, anchor):
        self.gaze.calib = calib
        self.tracker.set_owner_anchor(anchor)
        self.recalibrating = False
        self.last_tick = time.monotonic()

    def on_recalibration_cancel(self):
        self.gaze.calib = self._old_calib
        self.tracker.set_owner_anchor(self._old_anchor)
        if not self.tracker.camera_on:
            self.tracker.start()
        self.recalibrating = False
        self.last_tick = time.monotonic()

    # --- controls --------------------------------------------------------
    def toggle_pause(self):
        if self.recalibrating:
            return
        self.paused = not self.paused
        if self.paused:
            self.tracker.stop()          # camera is off during pause
            self.non_focus_since = None
        else:
            self.tracker.start()
            self.tracker.owner_touch()   # a pause is not an absence: keep following the owner
            self.smoother = StateSmoother(initial=self.state)
        self.last_tick = time.monotonic()

    def stop(self):
        if self.stopping:
            return
        self.stopping = True
        self.tracker.stop()
        self.tracker.set_owner_anchor(None)   # the owner anchor lives only during the session
        self.input.stop()
        self.widget.set_message(config.TEXTS["widget_report"])
        rec = self.recorder
        result = {}

        def work():  # file writes off the UI thread
            summary = compute_summary(rec.events, rec.meta["self_estimate_pct"], len(rec.nudges))
            advice = get_advice(summary)
            data = rec.to_dict(summary, advice)
            result["data"] = data
            result["json"] = rec.save(data)
            result["html"] = build_report(data, open_browser=False)
            build_history(open_browser=False)  # keep the "All sessions" page up to date

        th = threading.Thread(target=work, daemon=True)
        th.start()
        self._wait_report(th, result)

    def _wait_report(self, th, result):
        if th.is_alive():
            self.root.after(200, self._wait_report, th, result)
            return
        self.widget.destroy()
        if "html" in result:
            print(f"Session saved: {result['json']}")
            self.main.show_results(result["data"], result["html"])   # results inside the app
        else:
            self.main.show_start()

    def quit(self):
        self.tracker.stop()
        self.input.stop()
        self.root.after(300, self.root.destroy)

    def run(self):
        self.root.mainloop()


def demo_report():
    """Builds a report from a synthetic 30-minute session (no camera needed)."""
    from tests.fake_session import fake_events
    events = fake_events()
    rec = SessionRecorder(85, 90, "Demo: thesis chapter 2", session_number=1)
    rec.events = events
    rec.nudges = [600, 1320]
    summary = compute_summary(events, 85, len(rec.nudges))
    data = rec.to_dict(summary, get_advice(summary))
    print("Report:", build_report(data))


def migrate_legacy_data():
    """Before v1.0 sessions/settings lived next to app.py; copy them once to the data dir."""
    if getattr(sys, "frozen", False):
        return
    marker = config.DATA_DIR / ".migrated"
    if marker.exists():
        return
    legacy = Path(__file__).resolve().parent
    try:
        if (legacy / "sessions").is_dir():
            config.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
            for f in (legacy / "sessions").iterdir():
                target = config.SESSIONS_DIR / f.name
                if f.is_file() and not target.exists():
                    shutil.copy2(f, target)
        old_settings = legacy / "user_settings.json"
        if old_settings.exists() and not config.USER_SETTINGS_PATH.exists():
            shutil.copy2(old_settings, config.USER_SETTINGS_PATH)
        marker.touch()
    except OSError as e:
        print(f"[data] could not copy old sessions: {e}")


def selftest():
    """Checks a build without camera, windows or keyboard (used by CI). Exit code 0 = OK."""
    lines, ok = [], True

    def check(name, fn):
        nonlocal ok
        try:
            fn()
            lines.append(f"OK   {name}")
        except Exception as e:
            ok = False
            lines.append(f"FAIL {name}: {type(e).__name__}: {e}")

    def mediapipe_model():
        import mediapipe as mp
        import numpy as np
        from mediapipe.tasks.python import BaseOptions, vision
        options = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=config.MODEL_PATH.read_bytes()),
            running_mode=vision.RunningMode.IMAGE, num_faces=config.MAX_FACES,
            output_facial_transformation_matrixes=True)
        with vision.FaceLandmarker.create_from_options(options) as landmarker:
            blank = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.zeros((480, 640, 3), np.uint8))
            landmarker.detect(blank)

    def templates():
        for rel in ("report/template.html", "report/history_template.html", "assets/icon.png"):
            if not config.resource_path(rel).is_file():
                raise FileNotFoundError(rel)

    def input_backend():
        if sys.platform.startswith("linux") and not __import__("os").environ.get("DISPLAY"):
            return  # pynput's X11 backend needs a display (CI uses xvfb-run)
        import pynput.keyboard  # noqa: F401
        import pynput.mouse  # noqa: F401

    def report_roundtrip():
        import tempfile
        summary = compute_summary([], 80, 0)
        with tempfile.TemporaryDirectory() as tmp:
            build_report({"started_at": "2026-01-01T00:00:00", "events": [], "summary": summary,
                          "advice": get_advice(summary)}, out_dir=tmp, open_browser=False)
            build_history(tmp, open_browser=False)

    check("modules imported", lambda: None)
    check("tkinter", lambda: __import__("_tkinter"))
    check("opencv", lambda: __import__("cv2"))
    check("mediapipe model", mediapipe_model)
    check("bundled files", templates)
    check("input backend", input_backend)
    check("report + history", report_roundtrip)
    check("data dir writable", lambda: (config.DATA_DIR / ".selftest").write_text("ok"))
    lines.append("SELFTEST " + ("PASSED" if ok else "FAILED"))
    text = "\n".join(lines)
    print(text)  # windowed builds have no console: also write a file for CI
    try:
        (config.DATA_DIR / "selftest.log").write_text(text + "\n", encoding="utf-8")
    except OSError:
        pass
    return 0 if ok else 1


def enable_crash_log():
    """On a native crash, dump thread stacks (file/function names only) to crash.log."""
    try:
        log = open(config.DATA_DIR / "crash.log", "w")
        faulthandler.enable(file=log, all_threads=True)
        return log
    except OSError:
        return None


def main():
    crash_log = enable_crash_log()  # noqa: F841 - keep the file open for the whole run
    parser = argparse.ArgumentParser(description="FocusCheck")
    parser.add_argument("--debug", action="store_true", help="print head angles to console")
    parser.add_argument("--demo-report", action="store_true", help="open a report from fake data")
    parser.add_argument("--history", action="store_true", help="open stats of all past sessions")
    parser.add_argument("--selftest", action="store_true", help="check the build without camera and exit")
    args = parser.parse_args()
    if args.selftest:
        sys.exit(selftest())
    migrate_legacy_data()
    if args.history:
        app = FocusCheckApp(debug=args.debug)
        app.main.show_history()
        app.run()
        return
    if args.demo_report:
        demo_report()
        return
    FocusCheckApp(debug=args.debug).run()


if __name__ == "__main__":
    main()
