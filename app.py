"""FocusCheck entry point: python app.py [--debug] [--demo-report]"""
import argparse
import os
import random
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

# run from any cwd: all relative paths (models/, sessions/) are project-relative
os.chdir(Path(__file__).resolve().parent)

from dotenv import load_dotenv  # noqa: E402

import config  # noqa: E402
from ai.advice import get_advice  # noqa: E402
from monitors.input_activity import InputActivity  # noqa: E402
from monitors.window import WindowMonitor  # noqa: E402
from report.report import build_report  # noqa: E402
from session.recorder import SessionRecorder  # noqa: E402
from session.summary import compute_summary  # noqa: E402
from tracker.classifier import GazeTracker, StateSmoother, combine_state  # noqa: E402
from tracker.face import FaceTracker  # noqa: E402
from ui.calibration_window import CalibrationWindow  # noqa: E402
from ui.start_window import StartWindow  # noqa: E402
from ui.widget import Widget, show_meme  # noqa: E402


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
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(config.TEXTS["app_title"])
        self.debug = debug
        self.tracker = FaceTracker(debug=debug)
        self.input = InputActivity()
        self.settings = None
        self.start_window = StartWindow(self.root, self.on_start, self.quit)

    # --- flow ------------------------------------------------------------
    def on_start(self, settings):
        self.settings = settings
        self.start_window.withdraw()
        self.tracker.start()
        CalibrationWindow(self.root, self.tracker, self.on_calibrated, self.on_calibration_cancel)

    def on_calibration_cancel(self):
        self.tracker.stop()
        self.start_window.deiconify()

    def on_calibrated(self, calib):
        s = self.settings
        self.gaze = GazeTracker(calib)
        self.smoother = StateSmoother()
        self.windows = WindowMonitor(s["extra_keywords"])
        self.window_cat = "work"
        self.last_window_poll = 0.0
        self.recorder = SessionRecorder(s["planned_min"], s["self_estimate_min"],
                                        s["nudge_threshold_sec"], s["task"])
        self.input.start()

        self.paused = False
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

        self.widget = Widget(self.root, self.toggle_pause, self.stop)
        self.tick()

    # --- main loop -------------------------------------------------------
    def tick(self):
        if self.stopping:
            return
        now = time.monotonic()
        dt, self.last_tick = now - self.last_tick, now

        if not self.paused:
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
            if self.active_sec >= self.settings["planned_min"] * 60:
                self.stop()
                return

        n = len(self.recorder.events)
        focus_pct = round(self.focused_sec / n * 100) if n else 100
        self.widget.show(self.state, self.active_sec, self.settings["planned_min"], focus_pct,
                         paused=self.paused, camera_on=self.tracker.camera_on)
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

    # --- controls --------------------------------------------------------
    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.tracker.stop()          # camera is off during pause
            self.non_focus_since = None
        else:
            self.tracker.start()
            self.smoother = StateSmoother(initial=self.state)
        self.last_tick = time.monotonic()

    def stop(self):
        if self.stopping:
            return
        self.stopping = True
        self.tracker.stop()
        self.input.stop()
        self.widget.set_message(config.TEXTS["widget_report"])
        rec = self.recorder
        result = {}

        def work():  # OpenAI call may take up to the timeout: keep UI responsive
            summary = compute_summary(rec.events, rec.meta["self_estimate_min"], len(rec.nudges))
            advice = get_advice(summary)
            data = rec.to_dict(summary, advice)
            result["json"] = rec.save(data)
            result["html"] = build_report(data, open_browser=False)

        th = threading.Thread(target=work, daemon=True)
        th.start()
        self._wait_report(th, result)

    def _wait_report(self, th, result):
        if th.is_alive():
            self.root.after(200, self._wait_report, th, result)
            return
        if "html" in result:
            print(f"Session saved: {result['json']}\nReport: {result['html']}")
            import webbrowser
            webbrowser.open(Path(result["html"]).as_uri())
        self.quit()

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
    rec = SessionRecorder(30, 26, 90, "Demo: thesis chapter 2")
    rec.events = events
    rec.nudges = [600, 1320]
    summary = compute_summary(events, 26, len(rec.nudges))
    data = rec.to_dict(summary, get_advice(summary))
    print("Report:", build_report(data))


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="FocusCheck")
    parser.add_argument("--debug", action="store_true", help="print head angles to console")
    parser.add_argument("--demo-report", action="store_true", help="open a report from fake data")
    args = parser.parse_args()
    if args.demo_report:
        demo_report()
        return
    FocusCheckApp(debug=args.debug).run()


if __name__ == "__main__":
    main()
