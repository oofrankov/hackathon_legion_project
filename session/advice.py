"""Offline coaching tips for the report: simple rules over the session metrics."""


def get_advice(s):
    """Rule-based coaching tips from the session metrics (fully offline)."""
    tips = []
    if s.get("distracted_screen_min", 0) >= 3:
        tips.append("Block distracting sites during focus time, or close those tabs before you start.")
    total = s.get("total_min", 0)
    if total >= 20 and s.get("best_segment_start_min", 0) <= total * 0.2:
        tips.append("Your best focus was at the start. Take a short break every ~25 minutes.")
    if s.get("away_min", 0) + s.get("looking_away_min", 0) >= 5:
        tips.append("Plan your breaks: stand up on purpose instead of drifting away mid-task.")
    if s.get("longest_focus_streak_min", 0) < 10:
        tips.append("Aim for one unbroken 10-minute stretch next time, then grow it.")
    if len(tips) < 2:
        tips.append("Write down the very next small step before starting - it makes coming back easier.")
    if len(tips) < 2:
        tips.append("Keep the same setup next time: it clearly works for you.")

    pct, gap = s.get("focus_pct", 0), s.get("estimate_gap_pct", 0)
    analysis = f"You were focused {pct}% of the session ({s.get('focused_min', 0)} of {total} minutes). "
    if gap > 0:
        analysis += (f"You expected {s.get('self_estimate_pct', 0)}% - a {gap}-point gap is very normal, "
                     "most people overestimate.")
    else:
        analysis += "You matched or beat your own estimate - great self-awareness!"
    return {"source": "offline", "analysis": analysis, "tips": tips[:3]}
