"""Session metrics (section 5.10). One event = one active second."""
import math

import config


def _runs(states):
    """[(state, start_idx, length), ...] for consecutive equal states."""
    runs = []
    for i, s in enumerate(states):
        if runs and runs[-1][0] == s:
            runs[-1][2] += 1
        else:
            runs.append([s, i, 1])
    return [tuple(r) for r in runs]


def _minutes(sec):
    return round(sec / 60, 1)


def compute_summary(events, self_estimate_pct, nudges_count=0):
    states = [e["state"] for e in events]
    total = len(states)
    min_len = config.DISTRACTION_MIN_EVENT_SEC

    counts = {s: states.count(s) for s in config.STATES}
    focused = counts[config.FOCUSED]

    # distraction episode: a stretch of non-FOCUSED seconds right after FOCUSED
    distraction_count = 0
    i = 0
    while i < total:
        if states[i] != config.FOCUSED and i > 0 and states[i - 1] == config.FOCUSED:
            j = i
            while j < total and states[j] != config.FOCUSED:
                j += 1
            if j - i >= min_len:
                distraction_count += 1
            i = j
        else:
            i += 1

    runs = _runs(states)

    focus_runs = [(start, n) for s, start, n in runs if s == config.FOCUSED]
    streak_start, streak_len = max(focus_runs, key=lambda r: r[1]) if focus_runs else (0, 0)

    # best window of BEST_SEGMENT_MIN minutes (or the whole session if shorter)
    win = min(total, config.BEST_SEGMENT_MIN * 60)
    best_start, best_focus = 0, 0
    if win:
        cur = sum(1 for s in states[:win] if s == config.FOCUSED)
        best_focus = cur
        for k in range(1, total - win + 1):
            cur += (states[k + win - 1] == config.FOCUSED) - (states[k - 1] == config.FOCUSED)
            if cur > best_focus:
                best_start, best_focus = k, cur

    focused_min = _minutes(focused)
    focus_pct = round(focused / total * 100) if total else 0
    self_estimate_min = round(self_estimate_pct / 100 * total / 60, 1)
    return {
        "total_min": _minutes(total),
        "focused_min": focused_min,
        "distracted_screen_min": _minutes(counts[config.DISTRACTED_SCREEN]),
        "looking_away_min": _minutes(counts[config.LOOKING_AWAY]),
        "away_min": _minutes(counts[config.AWAY]),
        "focus_pct": focus_pct,
        "distraction_count": distraction_count,
        "longest_focus_streak_min": _minutes(streak_len),
        "longest_focus_streak_start_min": _minutes(streak_start),
        "longest_focus_streak_end_min": _minutes(streak_start + streak_len),
        "best_segment_start_min": _minutes(best_start),
        "best_segment_end_min": _minutes(best_start + win),
        "best_segment_focus_pct": round(best_focus / win * 100) if win else 0,
        # exact integer seconds: history aggregates these, minutes are for display only
        "total_sec": total,
        "focused_sec": focused,
        "state_sec": {st: counts[st] for st in config.STATES},
        "self_estimate_pct": self_estimate_pct,
        "self_estimate_min": self_estimate_min,
        "estimate_gap_pct": self_estimate_pct - focus_pct,
        "estimate_gap_min": round(self_estimate_min - focused_min, 1),
        "nudges_count": nudges_count,
    }


def _num(v):
    """A finite number, else 0 (hand-edited or corrupted files must not crash the app)."""
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else 0


def validate_session(data):
    """Returns a structurally safe copy of a loaded session file, or None if it is unusable."""
    if not isinstance(data, dict):
        return None
    out = dict(data)
    events = data.get("events")
    out["events"] = [e for e in events if isinstance(e, dict) and isinstance(e.get("state"), str)] \
        if isinstance(events, list) else []
    summary = data.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    clean = {}
    for k, v in summary.items():
        if k == "state_sec":
            clean[k] = {st: _num(n) for st, n in v.items()} if isinstance(v, dict) else {}
        else:
            clean[k] = _num(v)
    out["summary"] = clean
    for key in ("name", "task", "started_at"):
        if key in out and not isinstance(out[key], str):
            out[key] = str(out[key]) if out[key] is not None else ""
    advice = data.get("advice")
    if isinstance(advice, dict):
        tips = advice.get("tips")
        out["advice"] = {"analysis": str(advice.get("analysis") or ""),
                         "tips": [str(t) for t in tips] if isinstance(tips, list) else []}
    else:
        out.pop("advice", None)
    return normalize_session(out)


def normalize_session(data):
    """Older sessions have a separate PHONE state: fold it into LOOKING_AWAY (in place)."""
    for e in data.get("events") or []:
        if isinstance(e, dict):
            e["state"] = config.LEGACY_STATES.get(e.get("state"), e.get("state"))
    s = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    if "phone_min" in s:
        s["looking_away_min"] = round(_num(s.get("looking_away_min", 0)) + _num(s.pop("phone_min")), 1)
    s.pop("phone_count", None)
    sec = s.get("state_sec")
    if isinstance(sec, dict) and "PHONE" in sec:
        sec[config.LOOKING_AWAY] = sec.get(config.LOOKING_AWAY, 0) + sec.pop("PHONE")
    return data


def session_seconds(data):
    """Exact seconds per state: from events if present, else stored seconds, else minutes."""
    events = data.get("events") or []
    if events:
        counts = {st: 0 for st in config.STATES}
        for e in events:
            if e["state"] in counts:
                counts[e["state"]] += 1
        return counts
    s = data.get("summary") or {}
    if isinstance(s.get("state_sec"), dict):
        return {st: int(_num(s["state_sec"].get(st, 0))) for st in config.STATES}
    keys = {config.FOCUSED: "focused_min", config.DISTRACTED_SCREEN: "distracted_screen_min",
            config.LOOKING_AWAY: "looking_away_min", config.AWAY: "away_min"}
    return {st: round(_num(s.get(k, 0)) * 60) for st, k in keys.items()}
