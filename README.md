# FocusCheck

**You think you worked for two hours. Let's check.**

FocusCheck is a desktop app for honest focus tracking during a work session. It combines three signals:

- **head pose** from the webcam (MediaPipe Face Landmarker): screen, phone, looking away, or away from the desk
- **active window category**: work or distracting (YouTube, Instagram, …)
- **keyboard and mouse activity**: whether you were typing at all

That lets it tell apart cases other trackers mix up. *Looking at the screen* is not the same as *working* (YouTube shows 🟡), and *head down while typing* is not the same as *on the phone* (it stays 🟢).

Before the session you say how focused you expect to be (in %). After it you get a report: your focus score, **what you expected vs. what happened**, a timeline, a breakdown, key facts and coaching tips.

HACK_002 Vienna · Track A1 "Applied AI for Consumers".

## Run

Python 3.10–3.12 (MediaPipe has no wheels for 3.13 yet). On Linux use an **Xorg/X11** session: under Wayland the app warns you and counts every window as work.

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
| `python app.py --history` | opens stats of all past sessions |
| `python app.py --demo-report` | opens a report built from a fake 30-minute session, no camera needed |
| `python -m pytest -q` | runs the classifier and metrics tests |

The model `models/face_landmarker.task` is included. If it is missing, download it:
`https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task`

## How it works

0. **First launch**: choose which apps and sites count as distracting. The defaults come from the team's list: social networks and video are on, messengers are off because people need them for work communication. You can untick anything you need for work and add your own apps or sites (e.g. `chess.com`, `minecraft`). The choice is stored locally in `user_settings.json` and can be changed from the start screen.
1. **Start**: open the app and press **Start session**. The session name is optional; if it is empty the app uses "Session N · HH:MM". You can set your focus estimate (%) with a slider. The reminder threshold and extra distracting sites are under "More settings".
2. **Calibration** (10 s): look at a dot in the center and in the 4 corners. This records your "looking at the screen" head-pose range.
3. **Widget** (Zoom-style, always on top, draggable): state, timer counting up (no preset length) and focus %, with Pause, camera view and Stop buttons.
   - **Compact mode** (default): a slim bar.
   - **Camera mode** (camera button): adds a small live camera view with the same info. The preview is shown only in this window and is kept in memory only.
4. **Nudge**: after N seconds of continuous distraction the widget flashes red and beeps. If there are PNG/GIF files in `assets/memes/`, one of them pops up.
5. **Report**: after Stop, a report opens in your browser. The session is saved to `sessions/`.
6. **History** (`sessions/history.html`): overall stats and all past sessions. It shows total and focused time, overall focus %, the average gap between expected and real focus, the best session, distractions, a per-session chart (real vs. expected focus), where all the time went, and a table with a link to each report. Open it from the start screen ("View stats of past sessions" button, no session needed), from any report ("All sessions →"), or with `python app.py --history`. It is rebuilt after every session.

| Signals | State |
|---|---|
| no face for > 2 s | ⚪ Away |
| head down, no typing | 🟠 Phone |
| head down, typing | 🟢 Focused |
| head turned away | 🟠 Looking away |
| screen + distracting window | 🟡 Distracting window |
| screen + work window | 🟢 Focused |

A new state is shown only after it has lasted 1.5 s, so the widget does not flicker (`STATE_HOLD_SEC`). All thresholds, keywords and UI texts are in `config.py`.

## One owner per session (no biometrics)

FocusCheck follows only the person who calibrated, the **owner**. It recognises the owner by **where their face is in the frame and how big it is**, never by who they are.

- The camera finds up to 3 faces (`MAX_FACES`). Calibration requires exactly one person in the frame; if there are two, it asks you to repeat. The owner's average face position and size become the **anchor**. The anchor lives in memory only and is deleted when the session ends.
- On every frame, a face counts as the owner only if it is close to the owner's last position (`OWNER_MAX_SHIFT` per second) and has a similar size (`OWNER_SIZE_RATIO_MIN`–`OWNER_SIZE_RATIO_MAX`). The last position then follows the owner smoothly (`OWNER_SMOOTHING`).
- **Other faces are ignored completely.** Their gaze is not analysed, and nothing about them is stored or logged. The widget shows only "+N other person in frame · ignored, not identified".
- If the owner is gone for longer than `NO_FACE_SEC`, the state becomes **Away**, even if other people are still in the frame. The tracker never jumps to another face.
- A returning face is accepted only inside the owner's zone (`OWNER_RETURN_RADIUS` around the anchor) and only after it stays there for `OWNER_RETURN_HOLD_SEC`, so people walking past are not taken for the owner. After an absence longer than `OWNER_RECALIBRATE_AFTER_SEC` (5 min), the app offers a quick recalibration.
- The logic lives in `tracker/owner_lock.py` and has no camera dependency. It is tested on synthetic boxes in `tests/test_owner_lock.py`.

## Limitations

- **Owner lock without biometrics.** If the owner leaves and someone else sits exactly in their place at the same distance from the camera, that person can be taken for the owner. This is a deliberate trade-off for not using face recognition.
- Window detection needs an Xorg/X11 session on Linux (see above).

## Privacy (hard rules)

- Camera frames are processed in memory and **never saved or sent** anywhere.
- **No biometrics.** There are no face embeddings and no face recognition. Only face position and size are used, in memory only, to follow the session owner. Other people in the frame are never analysed.
- **Keys are never recorded.** Only the time of the last input event is kept.
- **Window titles, window classes and process names are never stored or logged.** They are turned into `work` / `distracting` in memory and discarded. No screenshots, no reading of window contents.
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
- Active window detection (only the window on top, never its content):
  - **Linux X11** (`python-xlib` + `psutil`): `_NET_ACTIVE_WINDOW`, then the title (`_NET_WM_NAME` / `WM_NAME`), `WM_CLASS` and `_NET_WM_PID` → process name and exe path.
  - **Browser** (Chrome, Chromium, Firefox, Brave, Opera, Edge, …): the tab title is matched against the site keywords.
  - **Any other app**: `WM_CLASS`, process name and exe path are matched against the app list. The exe path also catches Flatpak, Snap and Electron apps.
  - **Windows**: foreground window title + process via `ctypes` and `psutil`. **macOS**: app name only.
  - If anything can't be read, the category is `work`. FocusCheck ignores its own windows.
- The app list is `DISTRACTION_CATALOG` in `config.py`: site `keywords`, app ids in `apps`, and a `default` flag for each entry.
