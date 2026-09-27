"""Zoom-style always-on-top widget.

Compact mode: a slim dark bar (state, timer, focus %) with icon buttons.
Camera mode (camera button): adds a live camera view with the same info.
Everything is drawn on one canvas; the window is draggable.
"""
import sys
import tkinter as tk

import config
from ui.theme import px, rounded_rect

T, UI = config.TEXTS, config.UI
F = config.UI_FONT
IS_WIN = sys.platform.startswith("win")
KEY = "#010203"            # transparent key color for rounded corners (Windows)

# pixel sizes are set from the screen DPI when the first widget is created
PAD = BAR_H = BTN = NOTICE_H = W = 0


def _apply_scale():
    global PAD, BAR_H, BTN, NOTICE_H, W
    PAD, BAR_H, BTN, NOTICE_H = px(8), px(56), px(36), px(22)
    W = config.PREVIEW_W + 2 * PAD


def fmt_time(sec):
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class Widget(tk.Toplevel):
    def __init__(self, master, on_pause, on_stop, on_camera_view):
        super().__init__(master)
        _apply_scale()
        self.on_pause, self.on_stop, self.on_camera_view = on_pause, on_stop, on_camera_view
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        bg = KEY if IS_WIN else UI["panel"]
        if IS_WIN:
            self.attributes("-transparentcolor", KEY)
        self.configure(bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        self.camera_view = False
        self.paused = False
        self.camera_on = True
        self.others = 0                # other people in frame (ignored, not identified)
        self.disabled = False
        self._flash_job = None
        self._photo = None
        self._x = self.winfo_screenwidth() - W - 24
        self._y = 40
        self._build()

    # --- layout ----------------------------------------------------------
    def _height(self):
        h = (PAD + config.PREVIEW_H + BAR_H) if self.camera_view else BAR_H
        return h + (NOTICE_H if self.others else 0)

    def _build(self):
        c = self.canvas
        c.delete("all")
        h = self._height()
        self.geometry(f"{W}x{h}+{self._x}+{self._y}")
        c.config(width=W, height=h)
        self.panel = rounded_rect(c, 1, 1, W - px(1), h - px(1), px(14), fill=UI["panel"],
                                  outline=UI["border"], width=1, tags="drag")

        bar_top = 0
        if self.camera_view:
            vx, vy = PAD, PAD
            vw, vh = config.PREVIEW_W, config.PREVIEW_H
            c.create_rectangle(vx, vy, vx + vw, vy + vh, fill="#111318", outline="", tags="drag")
            self.video = c.create_image(vx, vy, anchor="nw", tags="drag")
            self.cam_off = c.create_text(vx + vw / 2, vy + vh / 2, text=T["widget_cam_off"],
                                         fill=UI["muted"], font=(F, 11), tags="drag")
            self.video_border = c.create_rectangle(vx, vy, vx + vw, vy + vh, outline=UI["border"], width=px(3))
            # "● REC" tag top-left, name-tag style state label bottom-left (like Zoom)
            self.rec_bg = c.create_rectangle(vx + px(6), vy + px(6), vx + px(6), vy + px(26), fill="#1f2329", outline="")
            self.rec_txt = c.create_text(vx + px(12), vy + px(16), anchor="w", text=T["widget_rec"],
                                         fill="#fca5a5", font=(F, 8))
            c.coords(self.rec_bg, vx + px(6), vy + px(6), c.bbox(self.rec_txt)[2] + px(6), vy + px(26))
            self.tag_bg = c.create_rectangle(vx + px(6), vy + vh - px(30), vx + px(6), vy + vh - px(6), fill="#1f2329", outline="")
            self.tag_dot = c.create_oval(vx + px(12), vy + vh - px(23), vx + px(22), vy + vh - px(13), outline="")
            self.tag_txt = c.create_text(vx + px(28), vy + vh - px(18), anchor="w", fill=UI["text"], font=(F, 10, "bold"))
            bar_top = PAD + vh

        cy = bar_top + BAR_H / 2
        self.dot = c.create_oval(PAD + px(6), cy - px(9), PAD + px(24), cy + px(9), fill=UI["muted"], outline="", tags="drag")
        self.title = c.create_text(PAD + px(34), cy - px(9), anchor="w", fill=UI["text"],
                                   font=(F, 11, "bold"), tags="drag")
        self.sub = c.create_text(PAD + px(34), cy + px(10), anchor="w", fill=UI["muted"], font=(F, 9), tags="drag")

        self._btn_centers = {
            "pause": (W - PAD - BTN / 2 - 2 * (BTN + px(4)), cy),
            "camera": (W - PAD - BTN / 2 - (BTN + px(4)), cy),
            "stop": (W - PAD - BTN / 2, cy),
        }
        for name in self._btn_centers:
            self._draw_button(name)

        self.notice = None
        if self.others:
            ny = bar_top + BAR_H + NOTICE_H / 2 - px(4)
            c.create_line(PAD + px(6), bar_top + BAR_H - px(2), W - PAD - px(6), bar_top + BAR_H - px(2), fill=UI["border"])
            self.notice = c.create_text(PAD + px(8), ny, anchor="w", fill=UI["muted"], font=(F, 8), tags="drag",
                                        text=self._others_text())

        c.tag_bind("drag", "<ButtonPress-1>", self._drag_start)
        c.tag_bind("drag", "<B1-Motion>", self._drag_move)

    def _draw_button(self, name):
        c = self.canvas
        tag = f"btn_{name}"
        c.delete(tag)
        x, y = self._btn_centers[name]
        active = name == "camera" and self.camera_view
        rounded_rect(c, x - BTN / 2, y - BTN / 2, x + BTN / 2, y + BTN / 2, px(8),
                     fill=UI["accent"] if active else UI["panel"], outline="", tags=(tag, f"{tag}_bg"))
        ic = UI["text"] if active else UI["icon"]
        if name == "pause":
            if self.paused:   # play triangle
                c.create_polygon(x - px(5), y - px(8), x - px(5), y + px(8), x + px(8), y, fill="", outline=ic, width=px(2), tags=tag)
            else:
                c.create_line(x - px(4), y - px(8), x - px(4), y + px(8), fill=ic, width=px(3), tags=tag)
                c.create_line(x + px(4), y - px(8), x + px(4), y + px(8), fill=ic, width=px(3), tags=tag)
        elif name == "camera":
            rounded_rect(c, x - px(11), y - px(7), x + px(4), y + px(7), px(3), fill="", outline=ic, width=px(2), tags=tag)
            c.create_polygon(x + px(4), y - px(2), x + px(11), y - px(6), x + px(11), y + px(6), x + px(4), y + px(2),
                             fill="", outline=ic, width=px(2), tags=tag)
            if self.camera_on:  # small red "recording locally" dot
                c.create_oval(x + px(8), y - px(14), x + px(14), y - px(8), fill=UI["danger"], outline="", tags=tag)
        elif name == "stop":
            rounded_rect(c, x - px(7), y - px(7), x + px(7), y + px(7), px(3), fill=UI["danger"], outline="", tags=tag)

        c.tag_bind(tag, "<Enter>", lambda _e: self._hover(name, True))
        c.tag_bind(tag, "<Leave>", lambda _e: self._hover(name, False))
        c.tag_bind(tag, "<ButtonRelease-1>", lambda _e: self._click(name))

    def _hover(self, name, on):
        if self.disabled:
            return
        self.canvas.config(cursor="hand2" if on else "")
        if not (name == "camera" and self.camera_view):
            self.canvas.itemconfig(f"btn_{name}_bg", fill=UI["hover"] if on else UI["panel"])

    def _click(self, name):
        if self.disabled:
            return
        if name == "pause":
            self.on_pause()
        elif name == "stop":
            self.on_stop()
        elif name == "camera":
            self.camera_view = not self.camera_view
            self._photo = None
            self._build()
            self.on_camera_view(self.camera_view)

    # --- drag ------------------------------------------------------------
    def _drag_start(self, e):
        self._dx, self._dy = e.x_root - self.winfo_x(), e.y_root - self.winfo_y()

    def _drag_move(self, e):
        self._x, self._y = e.x_root - self._dx, e.y_root - self._dy
        self.geometry(f"+{self._x}+{self._y}")

    # --- updates ---------------------------------------------------------
    def _others_text(self):
        return T["widget_others"].format(n=self.others, people="person" if self.others == 1 else "people")

    def show(self, state, elapsed_sec, focus_pct, paused=False, camera_on=True, others=0, camera_lost=False):
        c = self.canvas
        if bool(others) != bool(self.others):   # the notice row appears/disappears
            self.others = others
            self._build()
        elif others != self.others:
            self.others = others
            c.itemconfig(self.notice, text=self._others_text())
        if paused != self.paused or camera_on != self.camera_on:
            self.paused, self.camera_on = paused, camera_on
            self._draw_button("pause")
            self._draw_button("camera")
        color = config.PAUSED_COLOR if paused else config.STATE_COLORS.get(state, UI["muted"])
        label = (T["widget_paused"] if paused else T["widget_cam_lost"] if camera_lost
                 else config.STATE_LABELS.get(state, state))
        if self._flash_job is None and not self.disabled:
            c.itemconfig(self.dot, fill=color)
            c.itemconfig(self.title, text=label)
        c.itemconfig(self.sub, text=f"{fmt_time(elapsed_sec)}  ·  {focus_pct}% {T['widget_focus']}")

        if self.camera_view:
            c.itemconfig(self.video_border, outline=color)
            c.itemconfig(self.tag_dot, fill=color)
            c.itemconfig(self.tag_txt, text=f"{label} · {focus_pct}%")
            _, y1, _, y2 = c.coords(self.tag_bg)
            c.coords(self.tag_bg, PAD + px(6), y1, c.bbox(self.tag_txt)[2] + px(8), y2)
            c.itemconfig(self.cam_off, state="hidden" if camera_on else "normal")
            for item in (self.rec_bg, self.rec_txt):
                c.itemconfig(item, state="normal" if camera_on else "hidden")
            if not camera_on:
                c.itemconfig(self.video, image="")
                self._photo = None

    def set_frame(self, ppm_bytes):
        """Show a camera preview frame (PPM bytes, memory only)."""
        if not self.camera_view or not ppm_bytes:
            return
        try:
            self._photo = tk.PhotoImage(data=ppm_bytes)
        except tk.TclError:
            return
        self.canvas.itemconfig(self.video, image=self._photo)

    def set_message(self, text):
        self.disabled = True
        self.canvas.itemconfig(self.title, text=text)

    def flash(self, times=config.NUDGE_FLASH_TIMES):
        """Blink red; the regular colors come back with the next show()."""
        c = self.canvas
        c.itemconfig(self.title, text=T["widget_nudge"])

        def step(n):
            if n <= 0:
                self._flash_job = None
                c.itemconfig(self.panel, outline=UI["border"], width=1)
                return
            on = n % 2 == 0
            c.itemconfig(self.dot, fill=UI["danger"] if on else UI["panel"])
            c.itemconfig(self.panel, outline=UI["danger"] if on else UI["border"], width=3 if on else 1)
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
    factor = max(1, img.width() // 320)
    if factor > 1:
        img = img.subsample(factor, factor)
    pop = tk.Toplevel(master, bg=UI["panel"])
    pop.overrideredirect(True)
    pop.attributes("-topmost", True)
    lbl = tk.Label(pop, image=img, bg=UI["panel"])
    lbl.image = img
    lbl.pack(padx=6, pady=(6, 0))
    tk.Label(pop, text=T["meme_caption"], bg=UI["panel"], fg=UI["text"], font=(F, 11, "bold")).pack(pady=6)
    pop.update_idletasks()
    if anchor_widget is not None:
        x = anchor_widget.winfo_x() + anchor_widget.winfo_width() - pop.winfo_width()
        y = anchor_widget.winfo_y() + anchor_widget.winfo_height() + 8
        pop.geometry(f"+{max(0, x)}+{y}")
    return pop
    pop.bind("<Button-1>", lambda _e: pop.destroy())
    lbl.bind("<Button-1>", lambda _e: pop.destroy())
    master.after(config.MEME_POPUP_SEC * 1000, lambda: pop.winfo_exists() and pop.destroy())


def ask_recalibration(master, anchor_widget, on_yes):
    """Owner is back after a long absence: offer a quick recalibration."""
    pop = tk.Toplevel(master, bg=UI["panel"], highlightthickness=1, highlightbackground=UI["border"])
    pop.overrideredirect(True)
    pop.attributes("-topmost", True)
    tk.Label(pop, text=T["recal_text"], bg=UI["panel"], fg=UI["text"], font=(F, 10),
             justify="left").pack(padx=14, pady=(12, 8), anchor="w")
    row = tk.Frame(pop, bg=UI["panel"])
    row.pack(padx=14, pady=(0, 12), anchor="e")
    btn = dict(relief="flat", bd=0, padx=12, pady=4, font=(F, 9, "bold"), cursor="hand2")
    tk.Button(row, text=T["recal_no"], command=pop.destroy, bg=UI["field"], fg=UI["text"],
              activebackground=UI["hover"], activeforeground=UI["text"], **btn).pack(side="left", padx=(0, 6))
    tk.Button(row, text=T["recal_yes"], command=lambda: (pop.destroy(), on_yes()), bg=UI["accent"], fg="white",
              activebackground=UI["accent_hover"], activeforeground="white", **btn).pack(side="left")
    pop.update_idletasks()
    x = anchor_widget.winfo_x() + anchor_widget.winfo_width() - pop.winfo_width()
    y = anchor_widget.winfo_y() + anchor_widget.winfo_height() + 8
    pop.geometry(f"+{max(0, x)}+{y}")
    return pop
