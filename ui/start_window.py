"""Start window: task, duration, self-estimate, nudge threshold."""
import tkinter as tk
from tkinter import ttk

import config

T = config.TEXTS


class StartWindow(tk.Toplevel):
    def __init__(self, master, on_start, on_close):
        super().__init__(master)
        self.on_start, self.on_close = on_start, on_close
        self.title(T["app_title"])
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", on_close)

        style = ttk.Style(self)
        style.configure(".", font=(config.UI_FONT, 10))
        f = ttk.Frame(self, padding=24)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=T["start_heading"], font=(config.UI_FONT, 16, "bold")).pack(anchor="w", pady=(0, 14))

        self.task = tk.StringVar()
        self.duration = tk.StringVar(value=str(config.DEFAULT_SESSION_MIN))
        self.estimate = tk.StringVar(value=str(config.DEFAULT_SELF_ESTIMATE_MIN))
        self.nudge = tk.StringVar(value=str(config.DISTRACTION_NUDGE_SEC))
        self.keywords = tk.StringVar()

        self._field(f, T["task_label"], ttk.Entry(f, textvariable=self.task, width=48))
        self._field(f, T["duration_label"], ttk.Spinbox(f, from_=1, to=240, textvariable=self.duration, width=8))
        self.estimate_label = ttk.Label(f, wraplength=420, font=(config.UI_FONT, 10, "bold"))
        self._field(f, None, ttk.Spinbox(f, from_=0, to=240, textvariable=self.estimate, width=8),
                    label_widget=self.estimate_label)
        self._field(f, T["nudge_label"],
                    ttk.Spinbox(f, from_=config.MIN_NUDGE_SEC, to=3600, increment=10, textvariable=self.nudge, width=8))
        self._field(f, T["keywords_label"], ttk.Entry(f, textvariable=self.keywords, width=48))

        self.error = ttk.Label(f, foreground="#dc2626")
        self.error.pack(anchor="w", pady=(4, 0))
        ttk.Button(f, text=T["start_button"], command=self._submit).pack(anchor="e", pady=(10, 8))
        ttk.Label(f, text=T["privacy_note"], wraplength=420, foreground="#6b7280").pack(anchor="w")

        self.duration.trace_add("write", lambda *_: self._update_estimate_label())
        self._update_estimate_label()
        self.bind("<Return>", lambda _e: self._submit())
        self.update_idletasks()
        self.geometry(f"+{(self.winfo_screenwidth() - self.winfo_width()) // 2}+"
                      f"{(self.winfo_screenheight() - self.winfo_height()) // 3}")

    def _field(self, parent, label, widget, label_widget=None):
        (label_widget or ttk.Label(parent, text=label, wraplength=420)).pack(anchor="w", pady=(8, 2))
        widget.pack(anchor="w")

    def _update_estimate_label(self):
        n = self.duration.get().strip() or "N"
        self.estimate_label.config(text=T["estimate_label"].format(n=n))

    def _submit(self):
        try:
            duration = int(self.duration.get())
            estimate = int(self.estimate.get())
            nudge = int(self.nudge.get())
        except ValueError:
            self.error.config(text=T["err_numbers"])
            return
        if duration < 1:
            self.error.config(text=T["err_numbers"])
            return
        if not 0 <= estimate <= duration:
            self.error.config(text=T["err_estimate"])
            return
        if nudge < config.MIN_NUDGE_SEC:
            self.error.config(text=T["err_nudge"].format(n=config.MIN_NUDGE_SEC))
            return
        extra = [k.strip() for k in self.keywords.get().split(",") if k.strip()]
        self.on_start({
            "task": self.task.get().strip(),
            "planned_min": duration,
            "self_estimate_min": estimate,
            "nudge_threshold_sec": nudge,
            "extra_keywords": extra,
        })
