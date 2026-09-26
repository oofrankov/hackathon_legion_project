#!/usr/bin/env bash
# Wraps the PyInstaller output (dist/FocusCheck) into FocusCheck-x86_64.AppImage.
# Usage: pyinstaller focuscheck.spec && packaging/build_appimage.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPDIR="$ROOT/packaging/AppDir"
TOOLS="$ROOT/packaging/tools"
OUT="$ROOT/FocusCheck-x86_64.AppImage"
TOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"

[ -x "$ROOT/dist/FocusCheck/FocusCheck" ] || { echo "Run 'pyinstaller focuscheck.spec' first" >&2; exit 1; }

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/icons/hicolor/512x512/apps"
cp -a "$ROOT/dist/FocusCheck/." "$APPDIR/usr/bin/"
cp "$ROOT/packaging/focuscheck.desktop" "$APPDIR/focuscheck.desktop"
cp "$ROOT/assets/icon.png" "$APPDIR/focuscheck.png"
cp "$ROOT/assets/icon.png" "$APPDIR/usr/share/icons/hicolor/512x512/apps/focuscheck.png"

cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/FocusCheck" "$@"
RUN
chmod +x "$APPDIR/AppRun"

mkdir -p "$TOOLS"
if [ ! -x "$TOOLS/appimagetool" ]; then
  curl -fsSL -o "$TOOLS/appimagetool" "$TOOL_URL"
  chmod +x "$TOOLS/appimagetool"
fi

# CI runners have no FUSE: let appimagetool extract itself instead of mounting
APPIMAGE_EXTRACT_AND_RUN=1 ARCH=x86_64 "$TOOLS/appimagetool" --no-appstream "$APPDIR" "$OUT"
echo "Built $OUT"
