"""Coaching advice from OpenAI based on numeric metrics only, with a rule-based fallback."""
import json
import os

import config

SYSTEM_PROMPT = (
    "You are a friendly focus coach. You get numeric metrics of one computer work "
    "session (minutes, counts, percentages). Give a short analysis (2-3 sentences) "
    "and 2-3 concrete, practical tips. Do not make medical diagnoses and do not "
    "mention any conditions (e.g. ADHD). Never shame the user. Be warm and concise. "
    'Reply as JSON: {"analysis": "...", "tips": ["...", "..."]}'
)


def numeric_only(summary):
    """Only numbers go to the API: no titles, no task text, no video."""
    return {k: v for k, v in summary.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)}


def fallback_advice(s):
    tips = []
    if s.get("phone_count", 0) >= 3 or s.get("phone_min", 0) >= 5:
        tips.append("Put your phone in another room (or at least out of reach) for the next session.")
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

    pct, gap = s.get("focus_pct", 0), s.get("estimate_gap_min", 0)
    analysis = f"You were focused {pct}% of the session ({s.get('focused_min', 0)} of {total} minutes). "
    if gap > 0:
        analysis += f"That is {gap} minutes less than you expected - a very normal gap, most people overestimate."
    else:
        analysis += "You matched or beat your own estimate - great self-awareness!"
    return {"source": "fallback", "analysis": analysis, "tips": tips[:3]}


def get_advice(summary):
    metrics = numeric_only(summary)
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return fallback_advice(metrics)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, timeout=config.OPENAI_TIMEOUT_SEC, max_retries=0)
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(metrics)},
            ],
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        tips = [str(t) for t in data.get("tips", []) if str(t).strip()][:3]
        analysis = str(data.get("analysis", "")).strip()
        if not tips or not analysis:
            raise ValueError("incomplete AI answer")
        return {"source": "ai", "analysis": analysis, "tips": tips}
    except Exception as e:
        print(f"[advice] OpenAI unavailable, using fallback: {type(e).__name__}")
        return fallback_advice(metrics)
