# FocusCheck

**You think you worked for two hours. Let's check.**

FocusCheck is a desktop app that measures how focused you *really* are during a work session. It does not just check whether you look at the screen. It combines **head pose from the webcam**, **which window is on top** and **whether you are typing**. Before the session you guess your focus; after it you see the honest number.

Everything runs **on your device**: no video is stored or sent, no keys are recorded, no window titles are saved, and there is no cloud or AI API.

HACK_002 Vienna · Track **A1 "Applied AI for Consumers"**

---

## For the jury: try it in 5 minutes

Pick one of three ways.

### A. Download the ready-made app (no Python needed)

Latest release: **v2.0.3** on the repository's **Releases** page, `github.com/oofrankov/hackathon_legion_project/releases` (if you have access to the repository).

| System | File | How to start |
|---|---|---|
| Windows 10/11 | `FocusCheck-windows.zip` | Unzip → open the `FocusCheck` folder → `FocusCheck.exe`. If SmartScreen appears: **More info → Run anyway** (the app is not code-signed). |
| macOS (Apple Silicon) | `FocusCheck-macos.zip` | Unzip → move `FocusCheck.app` to Applications → **right-click → Open** the first time. On macOS 15+ use **System Settings → Privacy & Security → Open Anyway**. Allow the camera. For typing detection, allow FocusCheck in **Privacy & Security → Input Monitoring** (or **Accessibility**). |
| Linux (x86_64) | `FocusCheck-x86_64.AppImage` | `chmod +x FocusCheck-x86_64.AppImage && ./FocusCheck-x86_64.AppImage`. Use an **Xorg/X11** session; under Wayland window detection is off. If it does not start: `sudo apt install libfuse2`. |

### B. Run from the source ZIP

You need **Python 3.10–3.12** with tkinter (MediaPipe has no wheels for 3.13 yet). The first install downloads about 300 MB (MediaPipe, OpenCV).

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

- **Ubuntu/Debian**: if tkinter or venv is missing, run `sudo apt install python3-tk python3-venv`.
- **macOS**: use Python from python.org (Homebrew Python often has no tkinter). Allow camera and Input Monitoring for **Terminal**.

### C. No webcam, or just a quick look

```bash
python app.py --demo-report   # opens a full session report built from a synthetic 30-minute session
python app.py --selftest      # checks the install without camera or windows; prints SELFTEST PASSED
python -m pytest -q           # 48 unit tests (needs: pip install -e ".[dev]")
```

---

## 2-minute test script

1. **First launch**: pick which apps and sites count as distracting. The defaults are fine; press **Save**.
2. **Start screen**: optionally type a session name and set *"How focused do you think you'll be?"* (e.g. 80%). Press **Start session**.
3. **Calibration (10 s)**: sit as you normally work and follow the green dot (center + 4 corners) with your eyes.
4. A small **Zoom-style widget** appears on top of all windows. Try these:

| What you do | Widget shows | Why it matters |
|---|---|---|
| Look at the screen, work window open | 🟢 **Focused** | normal work |
| Look at the screen, open **YouTube** (or Instagram, Reddit…) in the browser; on macOS use an app such as Discord or Spotify | 🟡 **Distracting window** | *other trackers would say "focused" here* |
| Lower your head and **type** on the keyboard | 🟢 **Focused** | looking at the keyboard is not a distraction |
| Lower your head and **don't type** (e.g. phone in your lap) | 🟠 **Looking away** | |
| Turn your head to the side | 🟠 **Looking away** | |
| Leave the desk | ⚪ **Away** (after ~2 s) | |
| Someone walks behind you | stays on **you**; widget says "+1 other person in frame · ignored, not identified" | no biometrics, only position/size |
| Stay distracted for 90 s | the widget **flashes red and beeps** | a gentle nudge back |

5. Press the **camera button** in the widget to see the live camera view with the same info; press it again for the compact bar.
6. Press **Stop**. The main window shows your **report**: focus score, *"You expected 80% focus. Reality: 58%"*, a timeline, where the time went, key facts and tips.
7. **All sessions** (or **View stats of past sessions** on the start screen) opens the **history**: overall focus, a trend chart and a table of all sessions (click a row to open its report).

---

## The problem

People spend hours at the computer and *feel* productive, but they switch away constantly (phone, YouTube, social media) without noticing. Research by Gloria Mark (UC Irvine) found that attention on a single screen dropped from about 2.5 minutes (2003) to about 47 seconds (since 2016), and that people are bad at estimating how long they were really focused.

**Target users:** students writing papers or preparing for exams, and remote workers — **for personal use only**. There is deliberately no mode for employers or teachers to watch others.

## Our approach

Existing "focus" extensions only check *looking at the screen or not*. FocusCheck fuses three local signals into one honest state:

1. **Head pose** from the webcam: MediaPipe Face Landmarker, yaw/pitch from the face transformation matrix, calibrated to *your* screen in 10 seconds. This part runs a real ML model locally, on-device.
2. **Active window category**: only the window on top, turned into `work` / `distracting` in memory. Browser tabs are matched by title keywords; apps (Discord, Steam, Telegram…) by window class, process name or exe path.
3. **Input activity**: only *when* the last key or mouse event happened, never *which* key.

| Signals | State |
|---|---|
| no face for > 2 s | ⚪ Away |
| head down + no typing | 🟠 Looking away |
| head down + typing | 🟢 Focused |
| head turned sideways / up | 🟠 Looking away |
| looking at screen + distracting window | 🟡 Distracting window |
| looking at screen + work window | 🟢 Focused |

A new state is accepted only after it lasts 1.5 s, so the widget does not flicker.

**The "wow" moment:** before the session you say *"I'll be 80% focused"*; afterwards you see *58%*, the timeline and exactly when YouTube took over.

## What works now

- The full flow on Windows, macOS and Linux: start → calibration → always-on-top widget (compact and camera mode) → nudges → in-app report → history.
- Distracting app/site detection with a user-editable list. On by default: social networks, YouTube, Discord, Steam and Spotify. Off by default: streaming services and messengers. Works on Linux X11, Windows and macOS (macOS: app names only, no browser tabs).
- **One owner per session without biometrics.** Only the person who calibrated is tracked, by face *position and size* in the frame. Other people are counted and ignored.
- Offline tips based on the session numbers, and HTML export of every report (self-contained, no network).
- Robust against camera loss, UI freezes, failed saves and broken data files (see [Robustness](#robustness)).
- Automatic builds for Windows (`.exe`), macOS (`.app`) and Linux (AppImage) via GitHub Actions, each checked with unit tests and `--selftest`.

## Next steps

- Code signing for Windows and macOS (no more security warnings on first launch).
- Browser-tab detection on macOS (needs a small browser extension or accessibility API).
- Trends across days and weeks, with a compact summary index for fast history loading.
- Fatigue hints (eyes closed, `EAR`) and optional break reminders.
- A user study with students to tune thresholds for glasses, lighting and different webcams.

## What was built during the hackathon

**Everything in this repository was built during HACK_002** (first commit: Saturday 26 September 2026, 15:37; see `git log`). The first prototype (`main.py`, a head-pose demo) was written in the first hours and then replaced by the app.

Third-party components we use, not ours: the **MediaPipe Face Landmarker** model (`models/face_landmarker.task`, Google, Apache 2.0), **Chart.js 4.4.1** for the HTML export (`report/vendor/`, MIT), and the Python libraries in `pyproject.toml` (OpenCV, MediaPipe, NumPy, pynput, psutil, python-xlib, PyInstaller).

---

## Privacy (hard rules)

- Camera frames are processed in memory and **never saved or sent**. The optional camera view in the widget is only drawn on your screen.
- **No biometrics**: no face embeddings, no face recognition. Only face position and size are used, in memory, to follow the session owner. Other people are never analysed.
- **Keys are never recorded**, only the time of the last input event.
- **Window titles, window classes and process names are never stored or logged.** They become `work` / `distracting` in memory and are discarded. No screenshots.
- **Nothing leaves the device**: no accounts, no cloud, no AI API. The tips are computed locally.
- The camera is on only during a session and turns off on Pause.
- Data stays in a local folder. Delete it to erase your history:

| System | Data folder |
|---|---|
| Windows | `%LOCALAPPDATA%\FocusCheck` |
| macOS | `~/Library/Application Support/FocusCheck` |
| Linux | `~/.local/share/FocusCheck` |

Each session is a JSON file with one entry per second: head direction, `work`/`distracting`, typing yes/no and the resulting state. It also holds the summary numbers.

## One owner per session (no biometrics)

- The camera finds up to 3 faces. Calibration needs exactly one person in the frame (otherwise: *"Only you should be in the frame"* and retry). The owner's average face position and size become an in-memory **anchor**, deleted when the session ends.
- On each frame, a face counts as the owner only if it is close to the owner's last position and has a similar size. The position then follows the owner smoothly.
- If the owner is gone for > 2 s, the state is **Away**, even if others are in the frame. The tracker never jumps to another face.
- A returning face is accepted only in the owner's zone and only after 1.5 s there, so people walking past are ignored. After more than 5 minutes away, the app offers a quick recalibration.
- **Known trade-off:** someone who sits exactly in the owner's place at the same distance could be taken for the owner. That is the price of not using face recognition.

## Robustness

- **Camera unplugged or frozen**: an old frame never counts as a face, so the state becomes **Away**, never Focused. The widget shows **"Camera unavailable"**.
- **UI freeze or laptop sleep**: gaps between updates are not invented as session time.
- **Calibration** needs fresh measurements at all 5 dots, and it stops with a clear message if the camera does not start.
- **Saving**: files are written atomically. If saving fails (full disk, permissions), the results are still shown with the error and a **Retry save** button.
- **History** adds up exact seconds; minutes are only rounded for display. Broken or hand-edited files are skipped instead of crashing the app.

## Limitations

- Linux window detection needs an **Xorg/X11** session; under Wayland every window counts as work, and the app shows a warning.
- On **macOS** only app names are detected, not sites inside a browser. The start screen says so.
- The builds are **not code-signed** yet, so there are warnings on first launch.
- The macOS build is Apple Silicon only.
- Builds are large (~170 MB AppImage, ~450 MB unpacked) because of MediaPipe and OpenCV.
- CI checks builds, tests and `--selftest`; camera, window and keyboard detection can only be tested by hand on each system.

---

## Tech stack

Python 3.10–3.12 · MediaPipe Face Landmarker · OpenCV · tkinter (UI) · pynput · psutil · python-xlib · PyInstaller · GitHub Actions. The HTML export uses Chart.js, bundled into each file.

## Project structure

```
app.py               entry point: main window, session loop, --selftest / --history / --demo-report
config.py            all thresholds, texts, app list, paths (resource_path / user_data_dir)
tracker/             face.py (camera + MediaPipe thread), calibration.py, classifier.py, owner_lock.py
monitors/            window.py (top-window category), input_activity.py (pynput), app_settings.py
ui/                  main_window.py (start + apps pages), results_pages.py (report + history),
                     charts.py, theme.py (DPI scaling), calibration_window.py, widget.py
session/             recorder.py (JSON), summary.py (metrics, file validation), advice.py (tips), demo.py
report/              HTML export: report.py, history.py, templates, vendor/ (Chart.js)
models/              face_landmarker.task (MediaPipe)
assets/              icons (+ optional memes/ for the nudge popup)
tests/               48 unit tests on synthetic data (no camera needed)
focuscheck.spec      PyInstaller build
packaging/           AppImage script, .desktop file, icon generator
.github/workflows/   build.yml: Windows / macOS / Linux builds + GitHub Release on v* tags
```

## Development

| Command | What it does |
|---|---|
| `pip install -e ".[dev]"` | installs the app plus pytest and PyInstaller |
| `python app.py --debug` | prints yaw/pitch/eye-openness numbers for tuning |
| `python app.py --history` | opens the app on the history page |
| `python -m pytest -q` | runs the unit tests |
| `pyinstaller focuscheck.spec` | builds `dist/FocusCheck/` (macOS: `dist/FocusCheck.app`) |
| `packaging/build_appimage.sh` | Linux: wraps the build into `FocusCheck-x86_64.AppImage` |
| `git tag vX.Y.Z && git push origin vX.Y.Z` | CI builds all three systems and publishes a Release |

**Tuning** (`config.py`):

- If lowering your head does not turn the widget orange, run `--debug`. Pitch should *increase* when you look down; if it decreases, set `PITCH_SIGN = -1`.
- `DOWN_MARGIN_DEG` / `CALIBRATION_MARGIN_DEG` control how far outside the calibrated range counts as down or sideways.
- `STATE_HOLD_SEC` sets the reaction speed, `DISTRACTION_NUDGE_SEC` the reminder delay, `DISTRACTION_CATALOG` the app/site list.
