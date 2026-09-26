"""Start screen: one big button. Name and estimate are optional extras."""
import tkinter as tk
from datetime import datetime

import config
from ui.widget import rounded_rect

T, UI = config.TEXTS, config.UI
F = config.UI_FONT
WIDTH = 420


class StartWindow(tk.Toplevel):
    def __init__(self, master, session_number, apps_count, on_start, on_close, on_edit_apps,
                 on_history, wayland=False):
        super().__init__(master, bg=UI["bg"])
        self.on_start, self.on_close, self.on_edit_apps = on_start, on_close, on_edit_apps
        self.default_name = f"Session {session_number} · {datetime.now():%H:%M}"
        self.title(T["app_title"])
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", on_close)

        f = tk.Frame(self, bg=UI["bg"], padx=28, pady=24)
        f.pack(fill="both", expand=True)
        tk.Label(f, text=T["app_title"], bg=UI["bg"], fg=UI["text"], font=(F, 22, "bold")).pack(anchor="w")
        tk.Label(f, text=T["start_subtitle"], bg=UI["bg"], fg=UI["muted"], font=(F, 11)).pack(anchor="w", pady=(0, 18))
        if wayland:
            tk.Label(f, text=T["wayland_warning"], bg="#3b2f12", fg="#fcd34d", font=(F, 9),
                     wraplength=WIDTH - 72, justify="left", padx=8, pady=6).pack(fill="x", pady=(0, 12))

        # optional session name
        self.name = tk.StringVar()
        self._label(f, T["name_label"])
        self._entry(f, self.name).pack(fill="x", ipady=6)
        self._hint(f, T["name_hint"].format(default=self.default_name))

        # self-estimate (the "expected vs. real" moment of the report)
        row = tk.Frame(f, bg=UI["bg"])
        row.pack(fill="x", pady=(14, 0))
        tk.Label(row, text=T["estimate_label"], bg=UI["bg"], fg=UI["text"], font=(F, 10, "bold")).pack(side="left")
        self.estimate = tk.IntVar(value=config.DEFAULT_SELF_ESTIMATE_PCT)
        self.estimate_lbl = tk.Label(row, bg=UI["bg"], fg=UI["text"], font=(F, 14, "bold"))
        self.estimate_lbl.pack(side="right")
        tk.Scale(f, from_=0, to=100, orient="horizontal", variable=self.estimate, showvalue=False,
                 resolution=5, bg=UI["accent"], fg=UI["text"], troughcolor=UI["field"],
                 activebackground=UI["accent_hover"], highlightthickness=0, bd=0, sliderrelief="flat",
                 sliderlength=22, width=10, command=lambda _v: self._update_estimate()).pack(fill="x", pady=(6, 0))
        self._update_estimate()

        # collapsed extra settings
        self.more_open = False
        self.more_btn = tk.Label(f, bg=UI["bg"], fg=UI["muted"], font=(F, 10), cursor="hand2")
        self.more_btn.pack(anchor="w", pady=(14, 0))
        self.more_btn.bind("<Button-1>", lambda _e: self._toggle_more())
        self.more = tk.Frame(f, bg=UI["bg"])
        self.nudge = tk.StringVar(value=str(config.DISTRACTION_NUDGE_SEC))
        self._label(self.more, T["nudge_label"])
        self._entry(self.more, self.nudge, width=8).pack(anchor="w", ipady=4)
        self._render_more()

        self.apps_link = tk.Label(f, bg=UI["bg"], fg="#60a5fa", font=(F, 10), cursor="hand2")
        self.apps_link.pack(anchor="w", pady=(8, 0))
        self.apps_link.bind("<Button-1>", lambda _e: self.on_edit_apps())
        self.set_apps_count(apps_count)

        self.error = tk.Label(f, bg=UI["bg"], fg=UI["danger"], font=(F, 9), wraplength=WIDTH - 56, justify="left")
        self.error.pack(anchor="w", pady=(8, 0))

        # big primary button (canvas for rounded corners)
        self._button(f, T["start_button"], self._submit, primary=True).pack(pady=(6, 8))
        # stats of past sessions are available without starting a new one
        self._button(f, T["history_button"], on_history, primary=False).pack(pady=(0, 14))

        tk.Label(f, text="🔒  " + T["privacy_note"], bg=UI["bg"], fg=UI["muted"], font=(F, 9),
                 wraplength=WIDTH - 56, justify="left").pack(anchor="w")

        self.bind("<Return>", lambda _e: self._submit())
        self.update_idletasks()
        self.geometry(f"{WIDTH}x{self.winfo_reqheight()}+{(self.winfo_screenwidth() - WIDTH) // 2}+"
                      f"{(self.winfo_screenheight() - self.winfo_reqheight()) // 3}")
        self.focus_force()

    # --- helpers ---------------------------------------------------------
    def _button(self, parent, text, command, primary):
        """Rounded canvas button: filled blue (primary) or outlined (secondary)."""
        h = 48 if primary else 42
        fill, hover = (UI["accent"], UI["accent_hover"]) if primary else (UI["bg"], UI["field"])
        c = tk.Canvas(parent, width=WIDTH - 56, height=h, bg=UI["bg"], highlightthickness=0, cursor="hand2")
        bg = rounded_rect(c, 1, 1, WIDTH - 57, h - 1, 12, fill=fill,
                          outline="" if primary else UI["border"], width=1)
        c.create_text((WIDTH - 56) / 2, h / 2, text=text, fill="white" if primary else UI["text"],
                      font=(F, 13 if primary else 11, "bold"))
        c.bind("<Enter>", lambda _e: c.itemconfig(bg, fill=hover))
        c.bind("<Leave>", lambda _e: c.itemconfig(bg, fill=fill))
        c.bind("<ButtonRelease-1>", lambda _e: command())
        return c

    def _label(self, parent, text):
        tk.Label(parent, text=text, bg=UI["bg"], fg=UI["text"], font=(F, 10, "bold"),
                 wraplength=WIDTH - 56, justify="left").pack(anchor="w", pady=(10, 4))

    def _hint(self, parent, text):
        tk.Label(parent, text=text, bg=UI["bg"], fg=UI["muted"], font=(F, 9)).pack(anchor="w", pady=(3, 0))

    def _entry(self, parent, var, width=None):
        e = tk.Entry(parent, textvariable=var, bg=UI["field"], fg=UI["text"], insertbackground=UI["text"],
                     relief="flat", highlightthickness=1, highlightbackground=UI["border"],
                     highlightcolor=UI["accent"], font=(F, 11))
        if width:
            e.config(width=width)
        return e

    def set_apps_count(self, n):
        self.apps_link.config(text=T["apps_link"].format(n=n))

    def _update_estimate(self):
        self.estimate_lbl.config(text=f"{self.estimate.get()}%")

    def _toggle_more(self):
        self.more_open = not self.more_open
        self._render_more()
        self.update_idletasks()
        self.geometry(f"{WIDTH}x{self.winfo_reqheight()}")

    def _render_more(self):
        self.more_btn.config(text=("▾ " if self.more_open else "▸ ") + T["more_settings"])
        if self.more_open:
            self.more.pack(fill="x", after=self.more_btn)
        else:
            self.more.pack_forget()

    def _submit(self):
        try:
            nudge = int(self.nudge.get())
        except ValueError:
            nudge = -1
        if nudge < config.MIN_NUDGE_SEC:
            self.error.config(text=T["err_nudge"].format(n=config.MIN_NUDGE_SEC))
            if not self.more_open:
                self._toggle_more()
            return
        self.on_start({
            "name": self.name.get().strip() or self.default_name,
            "self_estimate_pct": int(self.estimate.get()),
            "nudge_threshold_sec": nudge,
        })
