# FocusCheck

**You think you worked for two hours. Let's check.**

FocusCheck is a desktop app for honest focus tracking during a work session. It combines three signals:

- **head pose** from the webcam (MediaPipe Face Landmarker): screen, phone, looking away, or away from the desk
- **active window category**: work or distracting (YouTube, Instagram, …)
- **keyboard and mouse activity**: whether you were typing at all

That lets it tell apart cases other trackers mix up. *Looking at the screen* is not the same as *working* (YouTube shows 🟡), and *head down while typing* is not the same as *on the phone* (it stays 🟢).

Before the session you say how many minutes you expect to stay focused. After it you get a report: your focus score, **what you expected vs. what happened**, a timeline, a breakdown, key facts and coaching tips.

HACK_002 Vienna · Track A1 "Applied AI for Consumers".

## Run

Python 3.10–3.12 (MediaPipe has no wheels for 3.13 yet).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python app.py
```

Optional: copy `.env.example` to `.env` and set `OPENAI_API_KEY` to get AI tips. Without a key, or without internet, the report shows rule-based tips and nothing breaks.

Other commands:

| Command | What it does |
|---|---|
| `python app.py --debug` | prints yaw/pitch/EAR to the console (numbers only) for tuning thresholds |
| `python app.py --demo-report` | opens a report built from a fake 30-minute session, no camera needed |
| `python -m pytest -q` | runs the classifier and metrics tests |

The model `models/face_landmarker.task` is included. If it is missing, download it:
`https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task`

## How it works

1. **Start**: enter your task (optional), session length, your honest focus estimate and the reminder threshold.
2. **Calibration** (10 s): look at a dot in the center and in the 4 corners. This records your "looking at the screen" head-pose range.
3. **Widget**: a small always-on-top window shows the current state, the timer and your focus %, with Pause and Stop buttons.
4. **Nudge**: after N seconds of continuous distraction the widget flashes red and beeps. If there are PNG/GIF files in `assets/memes/`, one of them pops up.
5. **Report**: after Stop, or when the time is up, a report opens in your browser. The session is saved to `sessions/`.

| Signals | State |
|---|---|
| no face for > 3 s | ⚪ Away |
| head down, no typing | 🟠 Phone |
| head down, typing | 🟢 Focused |
| head turned away | 🟠 Looking away |
| screen + distracting window | 🟡 Distracting window |
| screen + work window | 🟢 Focused |

A new state is shown only after it has lasted 2.5 s, so the widget does not flicker. All thresholds, keywords and UI texts are in `config.py`.

## Privacy (hard rules)

- Camera frames are processed in memory and **never saved or sent** anywhere.
- **Keys are never recorded.** Only the time of the last input event is kept.
- **Window titles are never stored or logged.** Only `work` / `distracting` is kept.
- OpenAI receives **only numeric metrics**. No video, titles or task text.
- The camera is on only during a session and is turned off on Pause.
- Everything is stored locally in `sessions/`. Delete the files to erase your history.
- There are no accounts, no cloud and no "watch others" mode. It is a tool for yourself only.

## Project structure

```
app.py               entry point, main loop (tkinter main thread)
config.py            thresholds, keywords, texts, OpenAI model
tracker/             face.py (MediaPipe thread), calibration.py, classifier.py
monitors/            window.py (active window category), input_activity.py (pynput)
ui/                  start_window.py, calibration_window.py, widget.py
session/             recorder.py (events → JSON), summary.py (metrics)
report/              report.py + template.html (Chart.js)
ai/advice.py         OpenAI tips with an offline fallback
tests/               unit tests on synthetic data
```

## Tuning

- If looking down does not turn orange, run `python app.py --debug` and lower your head. Pitch should **increase**. If it decreases, set `PITCH_SIGN = -1` in `config.py`.
- `DOWN_MARGIN_DEG` and `CALIBRATION_MARGIN_DEG` control how far outside the calibrated range counts as down or sideways.
- Active window detection works on Windows (`pygetwindow`), on Linux X11 (`xprop`) and on macOS (app name only, via `AppKit`). If the window can't be read, the category is `work`.
