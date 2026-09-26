"""Small always-on-top, draggable status widget."""
import tkinter as tk

import config

T = config.TEXTS
BG, FG, MUTED = "#181b22", "#f3f4f6", "#9ca3af"


class Widget(tk.Toplevel):
    W, H = 260, 104

    def __init__(self, master, on_pause, on_stop):
        super().__init__(master, bg=BG)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        x = self.winfo_screenwidth() - self.W - 24
        self.geometry(f"{self.W}x{self.H}+{x}+40")

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=10, pady=(8, 0))
        self.canvas = tk.Canvas(top, width=34, height=34, bg=BG, highlightthickness=0)
        self.canvas.pack(side="left")
        self.circle = self.canvas.create_oval(3, 3, 31, 31, fill=MUTED, outline="")
        text = tk.Frame(top, bg=BG)
        text.pack(side="left", padx=8, fill="x", expand=True)
        self.state_lbl = tk.Label(text, text=T["widget_calibrating"], bg=BG, fg=FG,
                                  font=(config.UI_FONT, 12, "bold"), anchor="w")
        self.state_lbl.pack(fill="x")
        self.info_lbl = tk.Label(text, text="00:00", bg=BG, fg=MUTED, font=(config.UI_FONT, 10), anchor="w")
        self.info_lbl.pack(fill="x")

        bottom = tk.Frame(self, bg=BG)
        bottom.pack(fill="x", padx=10, pady=(6, 8))
        self.rec_lbl = tk.Label(bottom, text=T["widget_rec"], bg=BG, fg="#ef4444", font=(config.UI_FONT, 8))
        self.rec_lbl.pack(side="left")
        btn = dict(bg="#2a2f3a", fg=FG, activebackground="#374151", activeforeground=FG,
                   relief="flat", bd=0, padx=8, pady=2, font=(config.UI_FONT, 9))
        self.stop_btn = tk.Button(bottom, text=T["widget_stop"], command=on_stop, **btn)
        self.stop_btn.pack(side="right")
        self.pause_btn = tk.Button(bottom, text=T["widget_pause"], command=on_pause, **btn)
        self.pause_btn.pack(side="right", padx=(0, 6))

        # drag anywhere except buttons
        for w in (self, top, text, self.canvas, self.state_lbl, self.info_lbl, bottom, self.rec_lbl):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)
        self._flash_job = None

    def _drag_start(self, e):
        self._dx, self._dy = e.x_root - self.winfo_x(), e.y_root - self.winfo_y()

    def _drag_move(self, e):
        self.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def show(self, state, elapsed_sec, planned_min, focus_pct, paused=False, camera_on=True):
        if self._flash_job is None:
            color = config.PAUSED_COLOR if paused else config.STATE_COLORS.get(state, MUTED)
            self.canvas.itemconfig(self.circle, fill=color)
            self.state_lbl.config(text=T["widget_paused"] if paused else config.STATE_LABELS.get(state, state))
        m, s = divmod(int(elapsed_sec), 60)
        self.info_lbl.config(text=f"{m:02d}:{s:02d} / {planned_min} min  ·  focus {focus_pct}%")
        self.rec_lbl.config(text=T["widget_rec"] if camera_on else T["widget_cam_off"],
                            fg="#ef4444" if camera_on else MUTED)
        self.pause_btn.config(text=T["widget_resume"] if paused else T["widget_pause"])

    def set_message(self, text):
        self.state_lbl.config(text=text)
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")

    def flash(self, times=config.NUDGE_FLASH_TIMES):
        """Blink red; the regular color is restored by the next show()."""
        self.state_lbl.config(text=T["widget_nudge"])

        def step(n):
            if n <= 0:
                self._flash_job = None
                return
            self.canvas.itemconfig(self.circle, fill=config.NUDGE_COLOR if n % 2 == 0 else BG)
            self.configure(bg=config.NUDGE_COLOR if n % 2 == 0 else BG)
            self._flash_job = self.after(300, step, n - 1)

        if self._flash_job:
            self.after_cancel(self._flash_job)
        step(times * 2)


def show_meme(master, image_path, anchor_widget=None):
    """Small popup with a meme next to the widget; closes itself (stage 5)."""
    try:
        img = tk.PhotoImage(file=image_path)  # PNG/GIF only
    except tk.TclError:
        return
    # shrink big images to roughly 320px wide
    factor = max(1, img.width() // 320)
    if factor > 1:
        img = img.subsample(factor, factor)
    pop = tk.Toplevel(master, bg=BG)
    pop.overrideredirect(True)
    pop.attributes("-topmost", True)
    lbl = tk.Label(pop, image=img, bg=BG)
    lbl.image = img
    lbl.pack(padx=6, pady=(6, 0))
    tk.Label(pop, text=T["meme_caption"], bg=BG, fg=FG, font=(config.UI_FONT, 11, "bold")).pack(pady=6)
    pop.update_idletasks()
    if anchor_widget is not None:
        x = anchor_widget.winfo_x() + anchor_widget.winfo_width() - pop.winfo_width()
        y = anchor_widget.winfo_y() + anchor_widget.winfo_height() + 8
        pop.geometry(f"+{max(0, x)}+{y}")
    pop.bind("<Button-1>", lambda _e: pop.destroy())
    lbl.bind("<Button-1>", lambda _e: pop.destroy())
    master.after(config.MEME_POPUP_SEC * 1000, lambda: pop.winfo_exists() and pop.destroy())
