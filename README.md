# FocusCheck

**You think you worked for two hours. Let's check.**

FocusCheck is a desktop app that measures how focused you really are during a work session. It does not only check whether you look at the screen. It combines three signals: **head pose from the webcam**, **the category of the window on top** and **keyboard/mouse activity**. Before a session you estimate your focus; afterwards you see the real number next to your guess.

HACK_002 Vienna · Track A1 "Applied AI for Consumers"

## Quick start

Requirements: **Python 3.10–3.12** with tkinter (MediaPipe has no wheels for 3.13 yet) and a webcam. The first install downloads about 300 MB (MediaPipe, OpenCV).

**Linux / macOS**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python app.py
```

**Windows (PowerShell)**
```powershell
py -3.12 -m venv .venv; .venv\Scripts\activate
pip install -e .
python app.py
```

- **Ubuntu/Debian**: if tkinter or venv is missing, run `sudo apt install python3-tk python3-venv`. Window detection needs an **Xorg/X11** session.
- **macOS**: use Python from python.org (Homebrew Python often lacks tkinter). Allow **Camera** and **Input Monitoring** for your terminal.

Without a webcam:

```bash
python app.py --demo-report   # full session report from a synthetic 30-minute session
python app.py --selftest      # checks the install without camera or windows
```

## How to use

1. **First launch**: choose which apps and sites count as distracting, or keep the defaults, and press **Save**.
2. **Start screen**: optionally name the session and set *"How focused do you think you'll be?"*. Press **Start session**.
3. **Calibration (10 s)**: sit as you normally work and follow the green dot (center and 4 corners) with your eyes.
4. **Work.** A small widget stays on top of all windows and shows the current state, the timer and your focus %. The camera button switches between a compact bar and a live camera view. Things to try: open YouTube, type with your head down, look down at your phone, leave the desk, let someone walk behind you. After 90 s of continuous distraction the widget flashes red and beeps.
5. **Stop** opens the report in the main window: focus score, what you expected vs. what happened, a timeline, where the time went, key facts and tips. **Open in browser** exports it as a self-contained HTML file.
6. **All sessions** (or **View stats of past sessions** on the start screen) opens your history: overall focus, a trend chart and all sessions. Click a session to open its report.

## The problem

People spend hours at the computer and feel productive, but they switch away all the time (phone, YouTube, social media) without noticing. Research by Gloria Mark (UC Irvine) found that attention on one screen dropped from about 2.5 minutes (2003) to about 47 seconds (since 2016), and that people misjudge how long they were really focused.

Target users are students and remote workers, **for personal use only**. There is deliberately no mode for employers or teachers to monitor others.

## How it works

1. **Head pose**: the MediaPipe Face Landmarker runs locally. Yaw and pitch come from its face transformation matrix and are compared with the range recorded during calibration.
2. **Window category**: only the window on top is checked, and it becomes `work` or `distracting` in memory. Browser tabs are matched by title keywords; apps (Discord, Steam, Telegram…) by window class, process name or exe path. The list is editable in the app.
3. **Keyboard/mouse activity**: only the time of the last input event is used.

| Signals | State |
|---|---|
| no face for more than 2 s | ⚪ Away |
| head down, no keyboard/mouse activity in the last 5 s | 🟠 Looking away |
| head down, with keyboard/mouse activity | 🟢 Focused (looking at the keyboard) |
| head turned sideways or up | 🟠 Looking away |
| looking at the screen, distracting window | 🟡 Distracting window |
| looking at the screen, work window | 🟢 Focused |

A new state is accepted only after it lasts 1.5 s, so the widget does not flicker. Other "focus" trackers only see *looking at the screen or not*. They count YouTube on screen as focus, and they count looking down at the keyboard as a distraction.

**One owner per session, without biometrics.** Calibration requires exactly one person in the frame. It stores that person's average face position and size, in memory, as the owner's anchor. Afterwards a face counts as the owner only if it stays close to that position with a similar size. Other faces are counted ("+1 other person in frame · ignored, not identified") and never analysed. The tracker never switches to them. A returning owner is accepted only in their own place after 1.5 s. After more than 5 minutes away, the app offers a quick recalibration.

## Privacy

- Camera frames are processed in memory and never saved or sent. The optional camera view is only drawn on your screen.
- No biometrics: no face embeddings or recognition, only face position and size.
- Keys are never recorded, only the time of the last input event.
- Window titles, classes and process names are never stored or logged; only `work`/`distracting` is kept.
- No accounts, no cloud, no AI API. The camera is off when the session is paused.
- All data stays in a local folder. Each session is a JSON file with one entry per second (head direction, window category, input yes/no, state) and the summary. Delete the folder to erase your history.

| System | Data folder |
|---|---|
| Windows | `%LOCALAPPDATA%\FocusCheck` |
| macOS | `~/Library/Application Support/FocusCheck` |
| Linux | `~/.local/share/FocusCheck` |

## Limitations

- On Linux, window detection needs Xorg/X11; under Wayland every window counts as work (the app shows a warning).
- On macOS, sites inside a browser are not detected, only apps (the start screen says so).
- "Keyboard/mouse activity" does not tell typing from mouse use.
- Without biometrics, someone who sits exactly in the owner's place at the same distance could be taken for the owner.
- Camera, window and keyboard detection can only be tested by hand on each system; CI checks builds, unit tests and `--selftest`.

## Project structure

```
app.py               entry point: main window, session loop, command-line flags
config.py            thresholds, texts, app/site list, paths
tracker/             face.py (camera + MediaPipe thread), calibration.py, classifier.py, owner_lock.py
monitors/            window.py (window category), input_activity.py, app_settings.py
ui/                  main_window.py, results_pages.py, charts.py, theme.py, calibration_window.py, widget.py
session/             recorder.py, summary.py, advice.py, demo.py
report/              HTML export (report.py, history.py, templates, vendor/Chart.js)
models/              face_landmarker.task
assets/              icons (+ optional memes/ for the reminder popup)
tests/               unit tests on synthetic data (no camera needed)
focuscheck.spec      PyInstaller build
packaging/           AppImage script, .desktop file, icon generator
.github/workflows/   CI: builds for Windows, macOS and Linux
```

## Development

| Command | What it does |
|---|---|
| `pip install -e ".[dev]"` | installs the app plus pytest and PyInstaller |
| `python -m pytest -q` | runs the unit tests |
| `python app.py --debug` | prints head-pose numbers for tuning |
| `python app.py --history` | opens the app on the history page |
| `pyinstaller focuscheck.spec` | builds a standalone app into `dist/` |
| `packaging/build_appimage.sh` | Linux: packs the build into an AppImage |

All thresholds are in `config.py`. For example, `STATE_HOLD_SEC` sets the reaction speed, `DISTRACTION_NUDGE_SEC` the reminder delay and `DISTRACTION_CATALOG` the app/site list. If looking down does not register, run `--debug`: pitch should increase when you look down. If it decreases, set `PITCH_SIGN = -1`.
