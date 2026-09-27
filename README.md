# FocusCheck

**You think you worked for two hours. Let's check.**

FocusCheck is a desktop app for honest focus tracking during a work session. It combines three signals:

- **head pose** from the webcam (MediaPipe Face Landmarker): screen, looking away (sideways or down), or away from the desk
- **active window category**: work or distracting (YouTube, Instagram, …)
- **keyboard and mouse activity**: whether you were typing at all

That lets it tell apart cases other trackers mix up. *Looking at the screen* is not the same as *working* (YouTube shows 🟡), and *head down while typing* is not the same as *looking away* (it stays 🟢).

Before the session you say how focused you expect to be (in %). After it you get a report: your focus score, **what you expected vs. what happened**, a timeline, a breakdown, key facts and coaching tips.

HACK_002 Vienna · Track A1 "Applied AI for Consumers".

## Install

Download the file for your system from the repository's **Releases** page. You don't need Python.

- **Windows**: download `FocusCheck-windows.zip`, unzip it, and run `FocusCheck\FocusCheck.exe`. If SmartScreen warns you, click **More info → Run anyway** (the app is not signed yet).
- **macOS** (Apple Silicon): download `FocusCheck-macos.zip`, unzip it, and move `FocusCheck.app` to **Applications**. The first time, **right-click → Open** (the app is not signed). Allow camera access when asked. To enable window detection and keyboard activity, allow FocusCheck under **System Settings → Privacy & Security → Accessibility** and, if needed, **Screen Recording**.
- **Linux**: download `FocusCheck-x86_64.AppImage`, then run:
  ```bash
  chmod +x FocusCheck-x86_64.AppImage && ./FocusCheck-x86_64.AppImage
  ```
  Log in with an **Xorg/X11** session (choose "Xorg" on the login screen). Under Wayland, window detection is off. If the AppImage does not start, install `libfuse2` (`sudo apt install libfuse2`) or run it with `--appimage-extract-and-run`.

Your sessions and settings are stored here (never inside the app):

| System | Folder |
|---|---|
| Windows | `%LOCALAPPDATA%\FocusCheck` |
| macOS | `~/Library/Application Support/FocusCheck` |
| Linux | `~/.local/share/FocusCheck` |

Delete this folder to erase all your history.

### For developers: run from source

Use Python 3.10–3.12 (MediaPipe has no wheels for 3.13 yet).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"
python app.py
```

Everything works offline. The coaching tips in the report are simple rules over your session numbers; no AI service is called. Exported HTML reports are self-contained: Chart.js is embedded from `report/vendor/` (a verified copy of the npm package), and a Content-Security-Policy blocks all network requests.

| Command | What it does |
|---|---|
| `python app.py --debug` | prints yaw/pitch/EAR to the console (numbers only) for tuning thresholds |
| `python app.py --history` | opens the app on the history page |
| `python app.py --selftest` | checks the install/build without camera, windows or keyboard (exit code 0 = OK) |
| `python app.py --demo-report` | opens a report built from a fake 30-minute session, no camera needed |
| `python -m pytest -q` | runs the unit tests |

The model `models/face_landmarker.task` is included. If it is missing, download it:
`https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task`

### Building the apps

```bash
pip install -e ".[dev]"
pyinstaller focuscheck.spec              # -> dist/FocusCheck/ (macOS: dist/FocusCheck.app)
dist/FocusCheck/FocusCheck --selftest
packaging/build_appimage.sh              # Linux only -> FocusCheck-x86_64.AppImage
```

GitHub Actions (`.github/workflows/build.yml`) builds all three systems automatically:

- **Push a version tag** to build everything and attach the three files to a GitHub Release:
  ```bash
  git tag v1.0.0 && git push origin v1.0.0
  ```
- **Actions → Build & release → Run workflow** builds only; the files appear in the run's artifacts.

Every build runs the unit tests and `--selftest`. The workflow uses no secrets.

## How it works

0. **First launch**: choose which apps and sites count as distracting (in the same window; later via "Distracting apps & sites" on the start screen). The defaults come from the team's list: social networks and video are on, messengers are off because people need them for work communication. You can untick anything you need for work and add your own apps or sites (e.g. `chess.com`, `minecraft`). The choice is stored locally in `user_settings.json` in your data folder and can be changed from the start screen.
1. **Start**: open the app and press **Start session**. The session name is optional; if it is empty the app uses "Session N · HH:MM". You can set your focus estimate (%) with a slider. "Distracting apps & sites" opens the list of distracting apps. The reminder comes after 90 s of continuous distraction (`DISTRACTION_NUDGE_SEC` in `config.py`).
2. **Calibration** (10 s): look at a dot in the center and in the 4 corners. This records your "looking at the screen" head-pose range.
3. **Widget** (Zoom-style, always on top, draggable): state, timer counting up (no preset length) and focus %, with Pause, camera view and Stop buttons.
   - **Compact mode** (default): a slim bar.
   - **Camera mode** (camera button): adds a small live camera view with the same info. The preview is shown only in this window and is kept in memory only.
4. **Nudge**: after N seconds of continuous distraction the widget flashes red and beeps. If there are PNG/GIF files in `assets/memes/`, one of them pops up.
5. **Report**: after Stop, the main window shows the session report: focus score, expected vs. real, timeline, breakdown, key facts and tips. Use "Open in browser" to get the HTML version, for example to share it. The session is saved to `sessions/` in your data folder (see [Install](#install)).
6. **History**: overall stats and all past sessions, shown inside the app. Click a session to open its report. An HTML version is saved to `sessions/history.html` in the data folder. It shows total and focused time, overall focus %, the average gap between expected and real focus, the best session, distractions, a per-session chart (real vs. expected focus), where all the time went, and a table with a link to each report. Open it from the start screen ("View stats of past sessions", no session needed), from a report ("All sessions"), or with `python app.py --history`. It is rebuilt after every session.

| Signals | State |
|---|---|
| no face for > 2 s | ⚪ Away |
| head down, no typing | 🟠 Looking away |
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

## Robustness

- **Camera stops or freezes**: a frame older than `FRAME_STALE_SEC` never counts as a face, so the state becomes **Away**, never Focused. After `CAMERA_READ_TIMEOUT_SEC` without frames the widget shows **"Camera unavailable"**.
- **UI freeze or laptop sleep**: gaps longer than `MAX_TICK_GAP_SEC` are not counted as session time, so no invented seconds appear.
- **Calibration** needs fresh measurements at every one of the 5 dots, and it gives up with a clear message if the camera does not start or stops midway.
- **Saving**: session files are written atomically. If saving fails (full disk, permissions), the results are still shown from memory with the error and a **Retry save** button.
- **History** adds up exact seconds per session (`total_sec`, `state_sec`); minutes are rounded only for display. Broken or hand-edited session and settings files are skipped or reset to defaults instead of crashing the app.

## Limitations

- **Owner lock without biometrics.** If the owner leaves and someone else sits exactly in their place at the same distance from the camera, that person can be taken for the owner. This is a deliberate trade-off for not using face recognition.
- Window detection needs an Xorg/X11 session on Linux (see above).

- The builds are not code-signed yet, so Windows SmartScreen and macOS Gatekeeper warn on first launch. Signing is planned after the hackathon.
- CI can only check that each build installs, passes the tests and passes `--selftest`. Camera, windows and keyboard have to be tested by hand on each system.
- Builds are large (~170 MB AppImage, ~450 MB unpacked) because of MediaPipe and OpenCV.
- The history page reads every session file when it opens. With hundreds of long sessions it may take a moment; a compact summary index would fix this.
- The macOS build is Apple Silicon only. Intel Macs would need an extra `macos-13` build.

## Privacy (hard rules)

- Camera frames are processed in memory and **never saved or sent** anywhere.
- **No biometrics.** There are no face embeddings and no face recognition. Only face position and size are used, in memory only, to follow the session owner. Other people in the frame are never analysed.
- **Keys are never recorded.** Only the time of the last input event is kept.
- **Window titles, window classes and process names are never stored or logged.** They are turned into `work` / `distracting` in memory and discarded. No screenshots, no reading of window contents.
- **Nothing is sent anywhere.** There is no cloud and no AI API; the tips are computed locally.
- The camera is on only during a session and is turned off on Pause.
- Everything is stored locally in your data folder (see [Install](#install)). Delete it to erase your history.
- There are no accounts, no cloud and no "watch others" mode. It is a tool for yourself only.

## Project structure

```
app.py               entry point, main loop (tkinter main thread), --selftest
config.py            thresholds, keywords, texts, resource_path() / user_data_dir()
tracker/             face.py (MediaPipe thread), calibration.py, classifier.py, owner_lock.py
monitors/            window.py (active window category), input_activity.py (pynput), app_settings.py
ui/                  main_window.py (start + apps pages), results_pages.py (report + history), charts.py, theme.py (DPI scaling), calibration_window.py, widget.py
session/             recorder.py (events → JSON), summary.py (metrics + file validation), advice.py (offline tips), demo.py
report/              report.py, history.py + HTML templates, vendor/ (bundled Chart.js)
assets/              icons (+ optional memes/)
tests/               unit tests on synthetic data
pyproject.toml       dependencies (platform-specific ones with markers)
focuscheck.spec      PyInstaller build (onedir, windowed, macOS .app with camera permission text)
packaging/           build_appimage.sh, focuscheck.desktop, make_icons.py
.github/workflows/   build.yml: Windows / macOS / Linux builds + GitHub Release on tags
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
