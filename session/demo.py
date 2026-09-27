"""Synthetic session for `app.py --demo-report` and the tests (no camera)."""
import config

GAZE_FOR_STATE = {
    config.FOCUSED: "SCREEN", config.DISTRACTED_SCREEN: "SCREEN",
    config.LOOKING_AWAY: "SIDE", config.AWAY: "AWAY",
}

# (state, seconds) - roughly a realistic 30-minute session
SCRIPT = [
    (config.FOCUSED, 420), (config.LOOKING_AWAY, 75), (config.FOCUSED, 300),
    (config.DISTRACTED_SCREEN, 150), (config.FOCUSED, 240), (config.LOOKING_AWAY, 60), (config.FOCUSED, 180), (config.AWAY, 120),
    (config.FOCUSED, 90), (config.DISTRACTED_SCREEN, 95), (config.LOOKING_AWAY, 30),
    (config.FOCUSED, 40),
]


def fake_events(script=SCRIPT):
    events, t = [], 0
    for state, n in script:
        for _ in range(n):
            events.append({
                "t": t, "gaze": GAZE_FOR_STATE[state],
                "window": "distracting" if state == config.DISTRACTED_SCREEN else "work",
                "input_active": state == config.FOCUSED and t % 3 == 0, "state": state,
            })
            t += 1
    return events
