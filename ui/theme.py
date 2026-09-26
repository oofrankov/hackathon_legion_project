"""Shared look: DPI scale, colors, rounded buttons, cards, scrolling.

Tk fonts are in points and grow with the screen DPI, but pixel sizes do not.
Every pixel size goes through px() so layouts stay correct at 125-200% scaling.
"""
import sys
import tkinter as tk

import config

T, UI, F = config.TEXTS, config.UI, config.UI_FONT
SCALE = 1.0


def init(root):
    """Call once after creating the Tk root."""
    global SCALE
    try:
        SCALE = max(1.0, root.winfo_fpixels("1i") / 96.0)
    except tk.TclError:
        SCALE = 1.0
    # camera preview in the widget follows the scale too
    config.PREVIEW_W, config.PREVIEW_H = px(324), px(243)


def px(n):
    return int(round(n * SCALE))


def rounded_rect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class RoundButton(tk.Canvas):
    """Rounded button that stretches with its container (pack fill='x') or has a fixed width."""
    STYLES = {
        "primary": ("accent", "accent_hover", "white", None),
        "secondary": ("bg", "field", "text", "border"),
        "ghost": ("panel", "hover", "text", "border"),
    }

    def __init__(self, parent, text, command, kind="primary", height=44, width=None, font_size=None):
        bg = parent.cget("bg")
        super().__init__(parent, height=px(height), width=px(width) if width else px(120),
                         bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        fill, hover, fg, outline = self.STYLES[kind]
        self.fill, self.hover = UI.get(fill, fill), UI.get(hover, hover)
        self.fg = UI.get(fg, fg)
        self.outline = UI[outline] if outline else ""
        self.text, self.command = text, command
        self.font = (F, font_size or (13 if kind == "primary" else 11), "bold")
        self._bg = None
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Enter>", lambda _e: self._bg and self.itemconfig(self._bg, fill=self.hover))
        self.bind("<Leave>", lambda _e: self._bg and self.itemconfig(self._bg, fill=self.fill))
        self.bind("<ButtonRelease-1>", lambda _e: self.command())

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        self._bg = rounded_rect(self, 1, 1, w - 1, h - 1, px(12), fill=self.fill,
                                outline=self.outline, width=1)
        self.create_text(w / 2, h / 2, text=self.text, fill=self.fg, font=self.font)


def link(parent, text, command, color="#60a5fa", size=10):
    lbl = tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color, font=(F, size), cursor="hand2")
    lbl.bind("<Button-1>", lambda _e: command())
    return lbl


def auto_wrap(label, pad=0):
    """Wrap text to the label's current width (works for any window size)."""
    label.bind("<Configure>", lambda e: label.config(wraplength=max(50, e.width - pad)))
    return label


def card(parent, padding=18, **pack):
    """Panel with a thin border; returns the inner frame."""
    outer = tk.Frame(parent, bg=UI["panel"], highlightthickness=1, highlightbackground=UI["border"])
    outer.pack(**{"fill": "x", "pady": (px(12), 0), **pack})
    inner = tk.Frame(outer, bg=UI["panel"], padx=px(padding), pady=px(padding))
    inner.pack(fill="both", expand=True)
    return inner


def section_title(parent, text):
    tk.Label(parent, text=text.upper(), bg=parent.cget("bg"), fg=UI["muted"],
             font=(F, 8, "bold")).pack(anchor="w", pady=(0, px(8)))


class ScrollArea(tk.Frame):
    """Vertical scrolling container; put content into `.body`."""

    def __init__(self, parent, bg=None):
        bg = bg or UI["bg"]
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.bar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview, width=px(10),
                                bg=UI["panel"], troughcolor=bg, activebackground=UI["hover"],
                                highlightthickness=0, bd=0, relief="flat")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._win, width=e.width))
        # one scroll page is shown at a time: wheel scrolls it while it exists
        # (<Enter>/<Leave> would fire on every child widget)
        self._wheel(True)
        self.bind("<Destroy>", lambda e: e.widget is self and self._wheel(False))

    def _wheel(self, on):
        if on:
            if sys.platform.startswith("linux"):
                self.bind_all("<Button-4>", lambda _e: self.canvas.yview_scroll(-3, "units"))
                self.bind_all("<Button-5>", lambda _e: self.canvas.yview_scroll(3, "units"))
            else:
                step = 1 if sys.platform == "darwin" else 120
                self.bind_all("<MouseWheel>",
                              lambda e: self.canvas.yview_scroll(int(-e.delta / step), "units"))
        else:
            for seq in ("<Button-4>", "<Button-5>", "<MouseWheel>"):
                self.unbind_all(seq)

    def to_top(self):
        self.canvas.yview_moveto(0)
