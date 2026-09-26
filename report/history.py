"""History page: overall stats and a list of all past sessions from sessions/*.json."""
import json
import webbrowser
from datetime import datetime
from pathlib import Path

import config
from report.report import report_filename

TEMPLATE = Path(__file__).with_name("history_template.html")
HISTORY_FILE = "history.html"
STATE_MIN_KEYS = {
    config.FOCUSED: "focused_min",
    config.DISTRACTED_SCREEN: "distracted_screen_min",
    config.PHONE: "phone_min",
    config.LOOKING_AWAY: "looking_away_min",
    config.AWAY: "away_min",
}


def _expected_pct(data, summary):
    if summary.get("self_estimate_pct") is not None:
        return summary["self_estimate_pct"]
    if data.get("self_estimate_pct") is not None:
        return data["self_estimate_pct"]
    # early format: "N of planned M minutes"
    if data.get("planned_min") and data.get("self_estimate_min") is not None:
        return round(data["self_estimate_min"] / data["planned_min"] * 100)
    return None


def load_sessions(sessions_dir=config.SESSIONS_DIR):
    """Compact rows (meta + summary only, no per-second events), oldest first."""
    rows = []
    for i, path in enumerate(sorted(Path(sessions_dir).glob("session_*.json")), start=1):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        s = data.get("summary") or {}
        if not s.get("total_min"):
            continue
        started = data.get("started_at", "")
        report = Path(sessions_dir, report_filename(started))
        rows.append({
            "started_at": started,
            "name": data.get("name") or data.get("task") or f"Session {data.get('session_number') or i}",
            "total_min": s.get("total_min", 0),
            "focused_min": s.get("focused_min", 0),
            "focus_pct": s.get("focus_pct", 0),
            "expected_pct": _expected_pct(data, s),
            "distraction_count": s.get("distraction_count", 0),
            "phone_count": s.get("phone_count", 0),
            "longest_focus_streak_min": s.get("longest_focus_streak_min", 0),
            "nudges_count": s.get("nudges_count", 0),
            "state_min": {state: s.get(key, 0) for state, key in STATE_MIN_KEYS.items()},
            "report": report.name if report.exists() else None,
        })
    return rows


def compute_overall(rows):
    total = sum(r["total_min"] for r in rows)
    focused = sum(r["focused_min"] for r in rows)
    gaps = [r["expected_pct"] - r["focus_pct"] for r in rows if r["expected_pct"] is not None]
    # "best" only among sessions long enough to mean something, if there are any
    candidates = [r for r in rows if r["total_min"] >= 5] or rows
    best = max(candidates, key=lambda r: r["focus_pct"]) if rows else None
    days = {r["started_at"][:10] for r in rows if r["started_at"]}
    return {
        "sessions": len(rows),
        "days": len(days),
        "total_min": round(total, 1),
        "focused_min": round(focused, 1),
        "focus_pct": round(focused / total * 100) if total else 0,
        "avg_gap_pct": round(sum(gaps) / len(gaps)) if gaps else None,
        "distractions": sum(r["distraction_count"] for r in rows),
        "phone": sum(r["phone_count"] for r in rows),
        "longest_streak_min": max((r["longest_focus_streak_min"] for r in rows), default=0),
        "best": {"name": best["name"], "focus_pct": best["focus_pct"], "started_at": best["started_at"]} if best else None,
        "state_min": {state: round(sum(r["state_min"][state] for r in rows), 1) for state in STATE_MIN_KEYS},
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
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__HISTORY_DATA__*/null", data)
    Path(sessions_dir).mkdir(parents=True, exist_ok=True)
    path = Path(sessions_dir, HISTORY_FILE).resolve()
    path.write_text(html, encoding="utf-8")
    if open_browser:
        webbrowser.open(path.as_uri())
    return str(path)
