"""Session metrics (section 5.10). One event = one active second."""
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


def compute_summary(events, self_estimate_min, nudges_count=0):
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
    phone_count = sum(1 for s, _, n in runs if s == config.PHONE and n >= min_len)

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
    return {
        "total_min": _minutes(total),
        "focused_min": focused_min,
        "distracted_screen_min": _minutes(counts[config.DISTRACTED_SCREEN]),
        "phone_min": _minutes(counts[config.PHONE]),
        "looking_away_min": _minutes(counts[config.LOOKING_AWAY]),
        "away_min": _minutes(counts[config.AWAY]),
        "focus_pct": round(focused / total * 100) if total else 0,
        "distraction_count": distraction_count,
        "phone_count": phone_count,
        "longest_focus_streak_min": _minutes(streak_len),
        "longest_focus_streak_start_min": _minutes(streak_start),
        "longest_focus_streak_end_min": _minutes(streak_start + streak_len),
        "best_segment_start_min": _minutes(best_start),
        "best_segment_end_min": _minutes(best_start + win),
        "best_segment_focus_pct": round(best_focus / win * 100) if win else 0,
        "self_estimate_min": self_estimate_min,
        "estimate_gap_min": round(self_estimate_min - focused_min, 1),
        "nudges_count": nudges_count,
    }
