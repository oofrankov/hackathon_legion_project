# PyInstaller build for FocusCheck:  pyinstaller focuscheck.spec
# onedir (starts faster with MediaPipe than onefile), no console window.
# Version for the macOS bundle comes from FOCUSCHECK_VERSION (set by CI from the git tag).
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

APP = "FocusCheck"
VERSION = os.environ.get("FOCUSCHECK_VERSION", "1.0.0")

datas = [
    ("models/face_landmarker.task", "models"),
    ("report/template.html", "report"),
    ("report/history_template.html", "report"),
    ("report/vendor/chart.umd.js", "report/vendor"),
    ("assets", "assets"),
]
binaries = []
hiddenimports = []

# MediaPipe ships its graphs/modules as package data
mp_datas, mp_binaries, mp_hidden = collect_all("mediapipe")
datas += mp_datas
binaries += mp_binaries
hiddenimports += mp_hidden

# pynput picks its backend at runtime
if sys.platform == "win32":
    hiddenimports += ["pynput.keyboard._win32", "pynput.mouse._win32"]
    icon = "assets/icon.ico"
elif sys.platform == "darwin":
    hiddenimports += ["pynput.keyboard._darwin", "pynput.mouse._darwin", "AppKit"]
    icon = "assets/icon.icns"
else:
    hiddenimports += ["pynput.keyboard._xorg", "pynput.mouse._xorg"]
    hiddenimports += collect_submodules("Xlib")   # python-xlib loads extensions dynamically
    icon = "assets/icon.png"

# heavy MediaPipe extras that the Face Landmarker never uses (saves hundreds of MB)
excludes = ["jax", "jaxlib", "scipy", "sounddevice", "pytest", "tests"]

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP,
    console=False,
    icon=icon,
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name=APP, upx=False)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP}.app",
        icon=icon,
        bundle_identifier="com.focuscheck.app",
        info_plist={
            "CFBundleName": APP,
            "CFBundleDisplayName": APP,
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSCameraUsageDescription": "FocusCheck uses the camera locally to see whether you are "
                                        "looking at the screen. Video never leaves your computer.",
            "NSHighResolutionCapable": True,
        },
    )
