"""The one main window of FocusCheck. Pages: start, apps list, results, history."""
import copy
import tkinter as tk
from datetime import datetime

import config
from ui.theme import F, T, UI, RoundButton, auto_wrap, link, px

START_W, WIDE_W = 560, 780


class MainWindow(tk.Toplevel):
    def __init__(self, master, ctrl):
        """ctrl: the app (start_session, save_apps, open_session, open_*_in_browser, quit...)."""
        super().__init__(master, bg=UI["bg"])
        self.ctrl = ctrl
        self.title(T["app_title"])
        self.protocol("WM_DELETE_WINDOW", ctrl.quit)
        self.minsize(px(460), px(420))
        self.page = None
        self._placed = False

    # --- navigation ------------------------------------------------------
    def _show(self, page_cls, width, tall, *args):
        if self.page is not None:
            self.page.destroy()
        self.page = page_cls(self, self.ctrl, *args)
        self.page.pack(fill="both", expand=True)
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(px(width), sw - px(40))
        h = min(px(860), sh - px(120)) if tall else min(self.page.winfo_reqheight(), sh - px(120))
        if self._placed:   # keep the window where the user put it, just resize
            self.geometry(f"{w}x{h}")
        else:
            self.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(0, (sh - h) // 3)}")
            self._placed = True
        self.deiconify()
        self.lift()
        self.focus_force()
        if not tall:   # wrapped labels grow after the first layout pass: fit once more
            self.after(80, self._refit)

    def _refit(self):
        if self.page is None:
            return
        self.update_idletasks()
        h = min(self.page.winfo_reqheight(), self.winfo_screenheight() - px(120))
        self.geometry(f"{self.winfo_width()}x{h}")

    def show_start(self):
        self._show(StartPage, START_W, False)

    def show_apps(self, first_run=False):
        self._show(AppsPage, START_W, False, first_run)

    def show_results(self, data, report_path=None):
        from ui.results_pages import ResultsPage
        self._show(ResultsPage, WIDE_W, True, data, report_path)

    def show_history(self):
        from ui.results_pages import HistoryPage
        self._show(HistoryPage, WIDE_W, True)


# --- helpers -----------------------------------------------------------------
def _label(parent, text, bold=True, size=10, color=None, pady=(px(10), px(4))):
    lbl = tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color or UI["text"],
                   font=(F, size, "bold" if bold else "normal"), justify="left", anchor="w")
    lbl.pack(fill="x", pady=pady)
    return auto_wrap(lbl)


def _entry(parent, var, width=None):
    e = tk.Entry(parent, textvariable=var, bg=UI["field"], fg=UI["text"], insertbackground=UI["text"],
                 relief="flat", highlightthickness=1, highlightbackground=UI["border"],
                 highlightcolor=UI["accent"], font=(F, 11))
    if width:
        e.config(width=width)
    return e


class StartPage(tk.Frame):
    def __init__(self, win, ctrl):
        super().__init__(win, bg=UI["bg"], padx=px(32), pady=px(26))
        self.ctrl = ctrl
        self.default_name = f"Session {ctrl.next_session_number()} · {datetime.now():%H:%M}"

        tk.Label(self, text=T["app_title"], bg=UI["bg"], fg=UI["text"], font=(F, 24, "bold")).pack(anchor="w")
        tk.Label(self, text=T["start_subtitle"], bg=UI["bg"], fg=UI["muted"], font=(F, 11)).pack(anchor="w", pady=(0, px(16)))
        if ctrl.wayland:
            auto_wrap(tk.Label(self, text=T["wayland_warning"], bg="#3b2f12", fg="#fcd34d", font=(F, 9),
                               justify="left", anchor="w", padx=px(8), pady=px(6))).pack(fill="x", pady=(0, px(12)))

        self.name = tk.StringVar()
        _label(self, T["name_label"])
        _entry(self, self.name).pack(fill="x", ipady=px(6))
        _label(self, T["name_hint"].format(default=self.default_name), bold=False, size=9,
               color=UI["muted"], pady=(px(3), 0))

        row = tk.Frame(self, bg=UI["bg"])
        row.pack(fill="x", pady=(px(14), 0))
        self.estimate = tk.IntVar(value=config.DEFAULT_SELF_ESTIMATE_PCT)
        self.estimate_lbl = tk.Label(row, bg=UI["bg"], fg=UI["text"], font=(F, 15, "bold"))
        self.estimate_lbl.pack(side="right")
        auto_wrap(tk.Label(row, text=T["estimate_label"], bg=UI["bg"], fg=UI["text"], font=(F, 10, "bold"),
                           justify="left", anchor="w")).pack(side="left", fill="x", expand=True)
        tk.Scale(self, from_=0, to=100, orient="horizontal", variable=self.estimate, showvalue=False,
                 resolution=5, bg=UI["accent"], fg=UI["text"], troughcolor=UI["field"],
                 activebackground=UI["accent_hover"], highlightthickness=0, bd=0, sliderrelief="flat",
                 sliderlength=px(22), width=px(10),
                 command=lambda _v: self._update_estimate()).pack(fill="x", pady=(px(6), 0))
        self._update_estimate()

        # secondary actions first, the main action last (closest to the privacy note)
        RoundButton(self, T["apps_link"].format(n=ctrl.apps_count()), ctrl.edit_apps,
                    "secondary", height=38, font_size=10).pack(fill="x", pady=(px(16), px(8)))
        RoundButton(self, T["history_button"], ctrl.show_history, "secondary", height=38,
                    font_size=10).pack(fill="x", pady=(0, px(14)))
        RoundButton(self, T["start_button"], self._submit, "primary", height=48).pack(fill="x", pady=(0, px(14)))
        auto_wrap(tk.Label(self, text=T["privacy_note"], bg=UI["bg"], fg=UI["muted"], font=(F, 9),
                           justify="left", anchor="w")).pack(fill="x")
        win_bind = self.winfo_toplevel()
        win_bind.bind("<Return>", lambda _e: self._submit())
        self.bind("<Destroy>", lambda _e: win_bind.unbind("<Return>"), add="+")

    def _update_estimate(self):
        self.estimate_lbl.config(text=f"{self.estimate.get()}%")

    def _submit(self):
        self.ctrl.start_session({
            "name": self.name.get().strip() or self.default_name,
            "self_estimate_pct": int(self.estimate.get()),
            "nudge_threshold_sec": config.DISTRACTION_NUDGE_SEC,
        })


class AppsPage(tk.Frame):
    """Which apps/sites count as distracting. Shown on first launch, then from the start page."""

    def __init__(self, win, ctrl, first_run=False):
        super().__init__(win, bg=UI["bg"], padx=px(32), pady=px(22))
        self.ctrl = ctrl
        self.settings = copy.deepcopy(ctrl.user_settings)
        if not first_run:
            link(self, "‹ " + T["back"], ctrl.show_start, color=UI["muted"]).pack(anchor="w", pady=(0, px(8)))
        tk.Label(self, text=T["apps_title"], bg=UI["bg"], fg=UI["text"], font=(F, 19, "bold")).pack(anchor="w")
        _label(self, T["apps_subtitle"], bold=False, color=UI["muted"], pady=(px(4), px(10)))

        grid = tk.Frame(self, bg=UI["bg"])
        grid.pack(fill="x")
        cols = [tk.Frame(grid, bg=UI["bg"]) for _ in range(2)]
        for i, col in enumerate(cols):
            grid.columnconfigure(i, weight=1, uniform="apps")
            col.grid(row=0, column=i, sticky="nw")
        self.vars = {}
        for gi, group in enumerate(config.CATALOG_GROUPS):
            col = cols[gi % 2]
            tk.Label(col, text=group.upper(), bg=UI["bg"], fg=UI["muted"], font=(F, 8, "bold")).pack(anchor="w", pady=(px(8), px(2)))
            for item in (i for i in config.DISTRACTION_CATALOG if i["group"] == group):
                var = tk.BooleanVar(value=self.settings["enabled"].get(item["id"], item["default"]))
                self.vars[item["id"]] = var
                tk.Checkbutton(col, text=item["name"], variable=var, bg=UI["bg"], fg=UI["text"],
                               selectcolor=UI["field"], activebackground=UI["bg"], activeforeground=UI["text"],
                               highlightthickness=0, bd=0, font=(F, 10), anchor="w").pack(anchor="w")

        _label(self, T["apps_custom_label"], pady=(px(16), px(4)))
        row = tk.Frame(self, bg=UI["bg"])
        row.pack(fill="x")
        self.new_item = tk.StringVar()
        entry = _entry(row, self.new_item)
        entry.pack(side="left", fill="x", expand=True, ipady=px(5))
        entry.bind("<Return>", lambda _e: self._add())
        RoundButton(row, T["apps_add"], self._add, "secondary", height=34, width=80, font_size=10).pack(side="left", padx=(px(8), 0))
        self.chips = tk.Frame(self, bg=UI["bg"])
        self.chips.pack(fill="x", pady=(px(8), 0))
        self._render_chips()

        RoundButton(self, T["apps_save"], self._save, "primary", height=44).pack(fill="x", pady=(px(16), 0))

    def _add(self):
        name = self.new_item.get().strip()
        if name and name.lower() not in (c.lower() for c in self.settings["custom"]):
            self.settings["custom"].append(name)
            self._render_chips()
        self.new_item.set("")

    def _remove(self, name):
        self.settings["custom"].remove(name)
        self._render_chips()

    def _render_chips(self):
        for w in self.chips.winfo_children():
            w.destroy()
        for name in self.settings["custom"]:
            chip = tk.Frame(self.chips, bg=UI["field"])
            chip.pack(side="left", padx=(0, px(6)), pady=px(2))
            tk.Label(chip, text=name, bg=UI["field"], fg=UI["text"], font=(F, 9)).pack(side="left", padx=(px(8), px(2)), pady=px(3))
            x = tk.Label(chip, text="×", bg=UI["field"], fg=UI["muted"], font=(F, 10), cursor="hand2")
            x.pack(side="left", padx=(px(2), px(6)))
            x.bind("<Button-1>", lambda _e, n=name: self._remove(n))

    def _save(self):
        self.settings["enabled"] = {k: bool(v.get()) for k, v in self.vars.items()}
        self.ctrl.save_apps(self.settings)
