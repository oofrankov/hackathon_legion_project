"""Records one event per active second in memory and saves the session JSON."""
import json
import os
from datetime import datetime

import config


class SessionRecorder:
    def __init__(self, planned_min, self_estimate_min, nudge_threshold_sec, task=""):
        self.started = datetime.now()
        self.meta = {
            "started_at": self.started.isoformat(timespec="seconds"),
            "planned_min": planned_min,
            "self_estimate_min": self_estimate_min,
            "nudge_threshold_sec": nudge_threshold_sec,
            "task": task,  # local only, never sent to OpenAI
        }
        self.events = []
        self.nudges = []   # active-second of each nudge

    def record(self, t, gaze, window, input_active, state):
        self.events.append({"t": t, "gaze": gaze, "window": window,
                            "input_active": bool(input_active), "state": state})

    def add_nudge(self, t):
        self.nudges.append(t)

    def to_dict(self, summary=None, advice=None):
        data = dict(self.meta)
        data["ended_at"] = datetime.now().isoformat(timespec="seconds")
        data["events"] = self.events
        data["nudges"] = self.nudges
        data["summary"] = summary or {}
        if advice is not None:
            data["advice"] = advice
        return data

    def save(self, data):
        os.makedirs(config.SESSIONS_DIR, exist_ok=True)
        name = f"session_{self.started:%Y%m%d_%H%M%S}.json"
        path = os.path.join(config.SESSIONS_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        return path
