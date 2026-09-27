#!/usr/bin/env bash
# Wraps the PyInstaller output (dist/FocusCheck) into FocusCheck-x86_64.AppImage.
# Usage: pyinstaller focuscheck.spec && packaging/build_appimage.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPDIR="$ROOT/packaging/AppDir"
TOOLS="$ROOT/packaging/tools"
OUT="$ROOT/FocusCheck-x86_64.AppImage"
# pinned release + checksum (not the mutable "continuous" build)
TOOL_VERSION="1.9.1"
TOOL_URL="https://github.com/AppImage/appimagetool/releases/download/${TOOL_VERSION}/appimagetool-x86_64.AppImage"
TOOL_SHA256="ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"

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
TOOL="$TOOLS/appimagetool-$TOOL_VERSION"
if [ ! -x "$TOOL" ]; then
  curl -fsSL -o "$TOOL.part" "$TOOL_URL"
  echo "$TOOL_SHA256  $TOOL.part" | sha256sum -c - || { rm -f "$TOOL.part"; echo "appimagetool checksum mismatch" >&2; exit 1; }
  mv "$TOOL.part" "$TOOL"
  chmod +x "$TOOL"
fi

# CI runners have no FUSE: let appimagetool extract itself instead of mounting
APPIMAGE_EXTRACT_AND_RUN=1 ARCH=x86_64 "$TOOL" --no-appstream "$APPDIR" "$OUT"
echo "Built $OUT"
