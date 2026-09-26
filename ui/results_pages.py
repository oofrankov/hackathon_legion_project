"""In-app session report and history (the HTML versions stay available as an export)."""
import tkinter as tk
from datetime import datetime

import config
from report.history import compute_overall, expected_pct, load_sessions
from ui import charts
from ui.theme import F, T, UI, RoundButton, ScrollArea, auto_wrap, card, link, px, section_title

C, L = config.STATE_COLORS, config.STATE_LABELS
STATE_MIN_KEYS = [
    (config.FOCUSED, "focused_min"), (config.DISTRACTED_SCREEN, "distracted_screen_min"),
    (config.PHONE, "phone_min"), (config.LOOKING_AWAY, "looking_away_min"), (config.AWAY, "away_min"),
]


def fmt_min(m):
    m = m or 0
    if m >= 60:
        return f"{int(m // 60)} h {round(m % 60)} min"
    return f"{m:.1f}".rstrip("0").rstrip(".") + " min"


def fmt_date(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%b %d, %H:%M")
    except (TypeError, ValueError):
        return iso or ""


def _header(page, back_text, back_cmd, buttons):
    bar = tk.Frame(page.body, bg=UI["bg"])
    bar.pack(fill="x")
    link(bar, "‹ " + back_text, back_cmd, color=UI["muted"]).pack(side="left")
    for text, cmd in reversed(buttons):
        RoundButton(bar, text, cmd, "ghost", height=32, width=150, font_size=9).pack(side="right", padx=(px(8), 0))


def _title(parent, title, meta):
    tk.Label(parent, text=title, bg=UI["bg"], fg=UI["text"], font=(F, 20, "bold")).pack(anchor="w", pady=(px(14), 0))
    if meta:
        tk.Label(parent, text=meta, bg=UI["bg"], fg=UI["muted"], font=(F, 10)).pack(anchor="w")


def _tiles(parent, items, columns):
    grid = tk.Frame(parent, bg=parent.cget("bg"))
    grid.pack(fill="x")
    for i in range(columns):
        grid.columnconfigure(i, weight=1, uniform="tiles")
    for i, (value, label) in enumerate(items):
        t = tk.Frame(grid, bg=UI["panel"], highlightthickness=1, highlightbackground=UI["border"],
                     padx=px(12), pady=px(10))
        t.grid(row=i // columns, column=i % columns, sticky="nsew", padx=px(4), pady=px(4))
        tk.Label(t, text=str(value), bg=UI["panel"], fg=UI["text"], font=(F, 17, "bold"), anchor="w").pack(fill="x")
        auto_wrap(tk.Label(t, text=label, bg=UI["panel"], fg=UI["muted"], font=(F, 9),
                           justify="left", anchor="w")).pack(fill="x")


def _state_list(parent, minutes_by_state):
    for state, minutes in minutes_by_state:
        row = tk.Frame(parent, bg=parent.cget("bg"))
        row.pack(fill="x", pady=px(2))
        dot = tk.Canvas(row, width=px(10), height=px(10), bg=row.cget("bg"), highlightthickness=0)
        dot.create_oval(0, 0, px(10), px(10), fill=C[state], outline="")
        dot.pack(side="left", padx=(0, px(6)))
        tk.Label(row, text=L[state], bg=row.cget("bg"), fg=UI["text"], font=(F, 10)).pack(side="left")
        tk.Label(row, text=fmt_min(minutes), bg=row.cget("bg"), fg=UI["text"], font=(F, 10, "bold")).pack(side="right")


def _two_columns(parent):
    row = tk.Frame(parent, bg=UI["bg"])
    row.pack(fill="x")
    row.columnconfigure(0, weight=1, uniform="two")
    row.columnconfigure(1, weight=1, uniform="two")
    cols = []
    for i in range(2):
        holder = tk.Frame(row, bg=UI["bg"])
        holder.grid(row=0, column=i, sticky="nsew", padx=(0, px(6)) if i == 0 else (px(6), 0))
        cols.append(holder)
    return cols


class ResultsPage(ScrollArea):
    def __init__(self, win, ctrl, data, report_path=None):
        super().__init__(win)
        self.body.configure(padx=px(28), pady=px(20))
        s = data.get("summary") or {}
        buttons = [(T["all_sessions"], ctrl.show_history)]
        if report_path:
            buttons.append((T["open_browser"], lambda: ctrl.open_in_browser(report_path)))
        _header(self, T["new_session"], ctrl.show_start, buttons)
        _title(self.body, T["results_title"], " · ".join(
            x for x in (data.get("name") or data.get("task"), fmt_date(data.get("started_at"))) if x))

        # hero: score + expected vs. real
        hero = card(self.body)
        hero.columnconfigure(1, weight=1)
        left = tk.Frame(hero, bg=UI["panel"])
        left.grid(row=0, column=0, sticky="nw", padx=(0, px(24)))
        section_title(left, T["focus_score"])
        tk.Label(left, text=f"{s.get('focus_pct', 0)}%", bg=UI["panel"], fg=UI["text"],
                 font=(F, 44, "bold")).pack(anchor="w")
        right = tk.Frame(hero, bg=UI["panel"])
        right.grid(row=0, column=1, sticky="nsew")
        section_title(right, T["expected_vs_real"])
        exp = expected_pct(data, s)
        real = s.get("focus_pct", 0)
        if exp is not None:
            auto_wrap(tk.Label(right, text=T["expected_line"].format(pct=exp, minutes=fmt_min(exp / 100 * s.get("total_min", 0))),
                               bg=UI["panel"], fg=UI["muted"], font=(F, 14, "bold"), justify="left", anchor="w")).pack(fill="x")
        good = exp is None or real >= exp
        auto_wrap(tk.Label(right, text=T["reality_line"].format(pct=real, minutes=fmt_min(s.get("focused_min", 0))),
                           bg=UI["panel"], fg=C[config.FOCUSED] if good else C[config.PHONE],
                           font=(F, 14, "bold"), justify="left", anchor="w")).pack(fill="x")
        rows = ([(T["expected"], exp, UI["muted"])] if exp is not None else []) + [(T["actual"], real, C[config.FOCUSED])]
        charts.compare_bars(right, rows).pack(fill="x", pady=(px(10), 0))

        # timeline
        tl = card(self.body)
        section_title(tl, T["timeline"])
        charts.timeline(tl, data.get("events") or []).pack(fill="x")
        charts.legend(tl).pack(anchor="w", pady=(px(6), 0))

        # breakdown + key facts
        c1, c2 = _two_columns(self.body)
        br = card(c1, fill="both", expand=True)
        section_title(br, T["where_time_went"])
        mins = [(state, s.get(key, 0)) for state, key in STATE_MIN_KEYS]
        charts.donut(br, [(C[st], m) for st, m in mins], size=130).pack(pady=(0, px(8)))
        _state_list(br, mins)
        facts = card(c2, fill="both", expand=True)
        section_title(facts, T["key_facts"])
        _tiles(facts, [
            (s.get("distraction_count", 0), T["fact_distractions"]),
            (s.get("phone_count", 0), T["fact_phone"]),
            (fmt_min(s.get("longest_focus_streak_min", 0)), T["fact_streak"]),
            (f"{s.get('best_segment_focus_pct', 0)}%", T["fact_best"].format(
                a=s.get("best_segment_start_min", 0), b=s.get("best_segment_end_min", 0))),
            (fmt_min(s.get("total_min", 0)), T["fact_total"]),
            (s.get("nudges_count", 0), T["fact_nudges"]),
        ], columns=2)

        # coach tips
        advice = data.get("advice") or {}
        coach = card(self.body)
        section_title(coach, T["coach"])
        if advice.get("analysis"):
            auto_wrap(tk.Label(coach, text=advice["analysis"], bg=UI["panel"], fg=UI["text"], font=(F, 10),
                               justify="left", anchor="w")).pack(fill="x", pady=(0, px(8)))
        for i, tip in enumerate(advice.get("tips", []), 1):
            auto_wrap(tk.Label(coach, text=f"{i}. {tip}", bg=UI["panel"], fg=UI["text"], font=(F, 10),
                               justify="left", anchor="w")).pack(fill="x", pady=px(2))

        auto_wrap(tk.Label(self.body, text=T["privacy_footer"], bg=UI["bg"], fg=UI["muted"], font=(F, 9),
                           justify="center")).pack(fill="x", pady=(px(16), 0))


class HistoryPage(ScrollArea):
    def __init__(self, win, ctrl):
        super().__init__(win)
        self.body.configure(padx=px(28), pady=px(20))
        rows = load_sessions()
        o = compute_overall(rows)
        _header(self, T["back"], ctrl.show_start, [(T["open_browser"], ctrl.open_history_in_browser)])
        _title(self.body, T["history_title"],
               f"{o['sessions']} session{'s' if o['sessions'] != 1 else ''}" if rows else "")
        if not rows:
            empty = card(self.body)
            tk.Label(empty, text=T["history_empty"], bg=UI["panel"], fg=UI["muted"], font=(F, 11)).pack(pady=px(30))
            return

        hero = card(self.body)
        hero.columnconfigure(1, weight=1)
        left = tk.Frame(hero, bg=UI["panel"])
        left.grid(row=0, column=0, sticky="nw", padx=(0, px(24)))
        section_title(left, T["overall_focus"])
        tk.Label(left, text=f"{o['focus_pct']}%", bg=UI["panel"], fg=UI["text"], font=(F, 44, "bold")).pack(anchor="w")
        right = tk.Frame(hero, bg=UI["panel"])
        right.grid(row=0, column=1, sticky="nsew")
        section_title(right, T["big_picture"])
        auto_wrap(tk.Label(right, text=T["history_headline"].format(focused=fmt_min(o["focused_min"]), total=fmt_min(o["total_min"])),
                           bg=UI["panel"], fg=UI["text"], font=(F, 14, "bold"), justify="left", anchor="w")).pack(fill="x")
        if o["avg_gap_pct"] is not None:
            over = o["avg_gap_pct"] > 0
            text = T["gap_over"].format(n=o["avg_gap_pct"]) if over else T["gap_ok"]
            auto_wrap(tk.Label(right, text=text, bg=UI["panel"], fg=C[config.PHONE] if over else C[config.FOCUSED],
                               font=(F, 12, "bold"), justify="left", anchor="w")).pack(fill="x", pady=(px(4), 0))

        totals = card(self.body)
        section_title(totals, T["totals"])
        best = o["best"]
        _tiles(totals, [
            (o["sessions"], T["tile_sessions"].format(days=o["days"], s="s" if o["days"] != 1 else "")),
            (fmt_min(o["total_min"]), T["fact_total"]),
            (fmt_min(o["longest_streak_min"]), T["fact_streak"]),
            (f"{best['focus_pct']}%" if best else "-", T["tile_best"].format(name=best["name"]) if best else ""),
            (o["distractions"], T["fact_distractions"]),
            (o["phone"], T["fact_phone"]),
            (fmt_min(o["state_min"][config.DISTRACTED_SCREEN]), T["tile_distracting"]),
            (fmt_min(o["state_min"][config.PHONE]), T["tile_phone_time"]),
        ], columns=4)

        tr = card(self.body)
        section_title(tr, T["trend_title"])
        charts.trend(tr, rows).pack(fill="x")
        charts.trend_legend(tr, T["real_focus"], T["expected"]).pack(anchor="w", pady=(px(6), 0))

        br = card(self.body)
        section_title(br, T["where_all_time_went"])
        mins = [(state, o["state_min"][state]) for state, _ in STATE_MIN_KEYS]
        charts.stacked_bar(br, [(C[st], m) for st, m in mins]).pack(fill="x", pady=(0, px(8)))
        _state_list(br, mins)

        table = card(self.body)
        section_title(table, T["all_sessions_title"])
        self._table(table, rows, ctrl)

        auto_wrap(tk.Label(self.body, text=T["privacy_footer"], bg=UI["bg"], fg=UI["muted"], font=(F, 9),
                           justify="center")).pack(fill="x", pady=(px(16), 0))

    def _table(self, parent, rows, ctrl):
        grid = tk.Frame(parent, bg=UI["panel"])
        grid.pack(fill="x")
        headers = [T["col_when"], T["col_session"], T["col_length"], T["col_focus"], T["col_expected"],
                   T["col_distr"], T["col_phone"]]
        weights = [2, 3, 1, 1, 1, 1, 1]
        for i, (h, wgt) in enumerate(zip(headers, weights)):
            grid.columnconfigure(i, weight=wgt)
            tk.Label(grid, text=h.upper(), bg=UI["panel"], fg=UI["muted"], font=(F, 8, "bold"),
                     anchor="w").grid(row=0, column=i, sticky="ew", padx=px(4), pady=(0, px(6)))
        for r_i, r in enumerate(reversed(rows), start=1):
            values = [fmt_date(r["started_at"]), r["name"], fmt_min(r["total_min"]), f"{r['focus_pct']}%",
                      f"{r['expected_pct']}%" if r["expected_pct"] is not None else "-",
                      str(r["distraction_count"]), str(r["phone_count"])]
            cells = []
            for c_i, v in enumerate(values):
                fg = charts.pct_color(r["focus_pct"]) if c_i == 3 else UI["text"] if c_i < 2 else UI["muted"]
                cell = tk.Label(grid, text=v, bg=UI["panel"], fg=fg, anchor="w",
                                font=(F, 10, "bold" if c_i == 3 else "normal"))
                cell.grid(row=r_i, column=c_i, sticky="ew", padx=px(4), pady=px(3), ipady=px(3))
                cells.append(cell)
            if r.get("file"):
                for cell in cells:
                    cell.configure(cursor="hand2")
                    cell.bind("<Button-1>", lambda _e, f=r["file"]: ctrl.open_session(f))
                    cell.bind("<Enter>", lambda _e, cs=cells: [c.configure(bg=UI["hover"]) for c in cs])
                    cell.bind("<Leave>", lambda _e, cs=cells: [c.configure(bg=UI["panel"]) for c in cs])
        tk.Label(parent, text=T["table_hint"], bg=UI["panel"], fg=UI["muted"], font=(F, 8)).pack(anchor="w", pady=(px(6), 0))
