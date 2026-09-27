"""History page: overall stats and a list of all past sessions from sessions/*.json."""
import json
import webbrowser
from datetime import datetime
from pathlib import Path

import config
from report.report import inline_vendor, report_filename
from session.summary import session_seconds, validate_session

TEMPLATE = config.resource_path("report/history_template.html")
HISTORY_FILE = "history.html"


def expected_pct(data, summary):
    for src in (summary, data):
        v = src.get("self_estimate_pct")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return round(v)
    # early format: "N of planned M minutes"
    planned, est = data.get("planned_min"), data.get("self_estimate_min")
    if isinstance(planned, (int, float)) and planned > 0 and isinstance(est, (int, float)):
        return round(est / planned * 100)
    return None


def _minutes(sec):
    return round(sec / 60, 1)


def load_sessions(sessions_dir=config.SESSIONS_DIR):
    """One row per session (oldest first). Bad or hand-edited files are skipped, never fatal."""
    rows = []
    for i, path in enumerate(sorted(Path(sessions_dir).glob("session_*.json")), start=1):
        try:
            data = validate_session(json.loads(path.read_text(encoding="utf-8")))
            if data is None:
                raise ValueError("not a session object")
            sec = session_seconds(data)
            total = sum(sec.values())
            if total <= 0:
                continue
            s = data["summary"]
            started = data.get("started_at", "")
            report = Path(sessions_dir, report_filename(started))
            rows.append({
                "started_at": started,
                "name": data.get("name") or data.get("task") or f"Session {data.get('session_number') or i}",
                "total_sec": total,
                "focused_sec": sec[config.FOCUSED],
                "state_sec": sec,
                "total_min": _minutes(total),
                "focused_min": _minutes(sec[config.FOCUSED]),
                "focus_pct": round(sec[config.FOCUSED] / total * 100),
                "expected_pct": expected_pct(data, s),
                "file": path.name,
                "distraction_count": int(s.get("distraction_count", 0)),
                "longest_focus_streak_min": s.get("longest_focus_streak_min", 0),
                "nudges_count": int(s.get("nudges_count", 0)),
                "state_min": {st: _minutes(n) for st, n in sec.items()},
                "report": report.name if report.exists() else None,
            })
        except Exception as e:
            print(f"[history] skipped {path.name}: {type(e).__name__}")
    return rows


def compute_overall(rows):
    """Aggregates exact seconds; rounding happens only for display."""
    total = sum(r["total_sec"] for r in rows)
    focused = sum(r["focused_sec"] for r in rows)
    gaps = [r["expected_pct"] - r["focus_pct"] for r in rows if r["expected_pct"] is not None]
    # "best" only among sessions long enough to mean something, if there are any
    candidates = [r for r in rows if r["total_sec"] >= 5 * 60] or rows
    best = max(candidates, key=lambda r: r["focus_pct"]) if rows else None
    days = {r["started_at"][:10] for r in rows if r["started_at"]}
    return {
        "sessions": len(rows),
        "days": len(days),
        "total_min": _minutes(total),
        "focused_min": _minutes(focused),
        "focus_pct": round(focused / total * 100) if total else 0,
        "avg_gap_pct": round(sum(gaps) / len(gaps)) if gaps else None,
        "distractions": sum(r["distraction_count"] for r in rows),
        "longest_streak_min": max((r["longest_focus_streak_min"] for r in rows), default=0),
        "best": {"name": best["name"], "focus_pct": best["focus_pct"], "started_at": best["started_at"]} if best else None,
        "state_min": {st: _minutes(sum(r["state_sec"][st] for r in rows)) for st in config.STATES},
    }


def build_history(sessions_dir=config.SESSIONS_DIR, open_browser=True):
    rows = load_sessions(sessions_dir)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sessions": rows,
        "overall": compute_overall(rows),
        "colors": config.STATE_COLORS,
        "labels": config.STATE_LABELS,
        "privacy": config.TEXTS["privacy_footer"],
    }
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = inline_vendor(TEMPLATE.read_text(encoding="utf-8")).replace("/*__HISTORY_DATA__*/null", data)
    Path(sessions_dir).mkdir(parents=True, exist_ok=True)
    path = Path(sessions_dir, HISTORY_FILE).resolve()
    path.write_text(html, encoding="utf-8")
    if open_browser:
        webbrowser.open(path.as_uri())
    return str(path)
