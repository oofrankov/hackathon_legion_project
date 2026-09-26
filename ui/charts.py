"""Small Tk canvas charts for the in-app results and history pages.
Every chart redraws itself when its canvas is resized."""
import tkinter as tk

import config
from ui.theme import F, UI, px

C, L = config.STATE_COLORS, config.STATE_LABELS


def _canvas(parent, height):
    c = tk.Canvas(parent, height=px(height), bg=parent.cget("bg"), highlightthickness=0, bd=0)
    return c


def _on_resize(c, draw):
    c.bind("<Configure>", lambda _e: (c.delete("all"), draw(c.winfo_width(), c.winfo_height())))


def runs(events):
    out = []
    for e in events:
        if out and out[-1][0] == e["state"]:
            out[-1][1] += 1
        else:
            out.append([e["state"], 1])
    return out


def timeline(parent, events):
    """Horizontal bar colored by state, with a minute axis."""
    c = _canvas(parent, 58)
    segs, total = runs(events), max(len(events), 1)

    def draw(w, h):
        bar_h = px(34)
        c.create_rectangle(0, 0, w, bar_h, fill=UI["field"], outline="")
        x = 0.0
        for state, n in segs:
            x2 = x + n / total * w
            c.create_rectangle(x, 0, max(x2, x + 1), bar_h, fill=C.get(state, UI["muted"]), outline="")
            x = x2
        for i in range(6):
            tx, sec = w * i / 5, int(total * i / 5)
            anchor = "w" if i == 0 else "e" if i == 5 else "center"
            c.create_text(tx, bar_h + px(12), text=f"{sec // 60}:{sec % 60:02d}",
                          fill=UI["muted"], font=(F, 8), anchor=anchor)

    _on_resize(c, draw)
    return c


def legend(parent, keys=None):
    row = tk.Frame(parent, bg=parent.cget("bg"))
    for k in keys or config.STATES:
        item = tk.Frame(row, bg=row.cget("bg"))
        item.pack(side="left", padx=(0, px(14)))
        dot = tk.Canvas(item, width=px(10), height=px(10), bg=row.cget("bg"), highlightthickness=0)
        dot.create_oval(0, 0, px(10), px(10), fill=C[k], outline="")
        dot.pack(side="left", padx=(0, px(5)))
        tk.Label(item, text=L[k], bg=row.cget("bg"), fg=UI["text"], font=(F, 9)).pack(side="left")
    return row


def donut(parent, parts, size=150):
    """parts: [(color, value)]"""
    c = tk.Canvas(parent, width=px(size), height=px(size), bg=parent.cget("bg"), highlightthickness=0)
    total = sum(v for _, v in parts) or 1
    s, pad, hole = px(size), px(4), px(size) * 0.32
    start = 90.0
    nonzero = [(col, v) for col, v in parts if v > 0]
    if len(nonzero) == 1:
        c.create_oval(pad, pad, s - pad, s - pad, fill=nonzero[0][0], outline="")
    else:
        for col, v in nonzero:
            extent = -360 * v / total
            c.create_arc(pad, pad, s - pad, s - pad, start=start, extent=extent, fill=col, outline="", style="pieslice")
            start += extent
    if not nonzero:
        c.create_oval(pad, pad, s - pad, s - pad, fill=UI["field"], outline="")
    c.create_oval(s / 2 - hole, s / 2 - hole, s / 2 + hole, s / 2 + hole, fill=parent.cget("bg"), outline="")
    return c


def compare_bars(parent, rows):
    """rows: [(label, pct, color)] -> 0..100% bars."""
    c = _canvas(parent, 26 * len(rows))

    def draw(w, h):
        label_w, value_w, bar_h = px(80), px(50), px(12)
        for i, (label, pct, color) in enumerate(rows):
            y = px(13) + i * px(26)
            c.create_text(0, y, text=label, anchor="w", fill=UI["text"], font=(F, 10))
            x1, x2 = label_w, w - value_w
            c.create_rectangle(x1, y - bar_h / 2, x2, y + bar_h / 2, fill=UI["field"], outline="")
            c.create_rectangle(x1, y - bar_h / 2, x1 + (x2 - x1) * max(0, min(pct, 100)) / 100, y + bar_h / 2,
                               fill=color, outline="")
            c.create_text(w, y, text=f"{pct}%", anchor="e", fill=UI["muted"], font=(F, 10))

    _on_resize(c, draw)
    return c


def stacked_bar(parent, parts, height=16):
    """parts: [(color, value)] in one horizontal bar."""
    c = _canvas(parent, height)
    total = sum(v for _, v in parts) or 1

    def draw(w, h):
        c.create_rectangle(0, 0, w, h, fill=UI["field"], outline="")
        x = 0.0
        for col, v in parts:
            x2 = x + v / total * w
            if v > 0:
                c.create_rectangle(x, 0, x2, h, fill=col, outline="")
            x = x2

    _on_resize(c, draw)
    return c


def pct_color(p):
    return C[config.FOCUSED] if p >= 75 else C[config.DISTRACTED_SCREEN] if p >= 50 else UI["warn"]


def trend(parent, rows, max_bars=30):
    """Bars = real focus % per session, dashed line = expected %. rows oldest first."""
    rows = rows[-max_bars:]
    c = _canvas(parent, 210)
    one_day = len({r["started_at"][:10] for r in rows}) <= 1

    def x_label(iso):
        return iso[11:16] if one_day else iso[5:10].replace("-", ".")

    def draw(w, h):
        left, bottom, top = px(36), h - px(22), px(8)
        ch = bottom - top
        for v in (0, 50, 100):
            y = bottom - ch * v / 100
            c.create_line(left, y, w, y, fill=UI["border"])
            c.create_text(left - px(6), y, text=f"{v}%", anchor="e", fill=UI["muted"], font=(F, 8))
        n = len(rows)
        if not n:
            return
        slot = (w - left) / n
        bw = min(px(34), slot * 0.6)
        pts = []
        for i, r in enumerate(rows):
            cx = left + slot * (i + 0.5)
            y = bottom - ch * r["focus_pct"] / 100
            c.create_rectangle(cx - bw / 2, y, cx + bw / 2, bottom, fill=pct_color(r["focus_pct"]), outline="")
            if r.get("expected_pct") is not None:
                pts.append((cx, bottom - ch * r["expected_pct"] / 100))
            if n <= 12 or i % max(1, n // 8) == 0:
                c.create_text(cx, bottom + px(11), text=x_label(r["started_at"]),
                              fill=UI["muted"], font=(F, 8))
        if len(pts) > 1:
            c.create_line(*[v for p in pts for v in p], fill=UI["muted"], dash=(4, 3), width=px(2))
        for x, y in pts:
            c.create_oval(x - px(3), y - px(3), x + px(3), y + px(3), fill=UI["muted"], outline="")

    _on_resize(c, draw)
    return c


def trend_legend(parent, bars_text, line_text):
    """Legend drawn with shapes (no special glyphs: not every Tk font has them)."""
    row = tk.Frame(parent, bg=parent.cget("bg"))
    sw = tk.Canvas(row, width=px(12), height=px(12), bg=row.cget("bg"), highlightthickness=0)
    sw.create_rectangle(0, 0, px(12), px(12), fill=C[config.FOCUSED], outline="")
    sw.pack(side="left", padx=(0, px(5)))
    tk.Label(row, text=bars_text, bg=row.cget("bg"), fg=UI["text"], font=(F, 9)).pack(side="left", padx=(0, px(14)))
    ln = tk.Canvas(row, width=px(22), height=px(12), bg=row.cget("bg"), highlightthickness=0)
    ln.create_line(0, px(6), px(22), px(6), fill=UI["muted"], dash=(4, 3), width=px(2))
    ln.pack(side="left", padx=(0, px(5)))
    tk.Label(row, text=line_text, bg=row.cget("bg"), fg=UI["text"], font=(F, 9)).pack(side="left")
    return row
