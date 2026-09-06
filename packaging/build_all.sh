#!/usr/bin/env bash
# Build all DigiTux distribution artifacts:
#   - single-file binary (PyInstaller)
#   - AppImage
#   - .deb (stdeb, system deps)
#
# Usage:  bash packaging/build_all.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV="${BUILD_VENV:-/tmp/opencode/buildenv}"
PY="$VENV/bin/python"
PYINST="$VENV/bin/pyinstaller"

# --- 0) ensure build venv deps ---
if [ ! -x "$PYINST" ]; then
    echo "[1/5] Creando venv de build e instalando herramientas..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet pyinstaller stdeb PyQt5 pyserial
fi

echo "[1/5] Ajustando rutas (runtime.py ya integrado)."

# --- 2) single-file binary ---
echo "[2/5] Binario (onefile)..."
"$PYINST" --noconfirm --clean packaging/digitux.spec
mv -f dist/digitux dist/digitux-x86_64

# --- 3) onedir -> AppImage ---
echo "[3/5] AppImage..."
"$PYINST" --noconfirm --clean packaging/digitux_onedir.spec
rm -rf packaging/AppDir/usr/bin
mkdir -p packaging/AppDir/usr/bin
cp -r dist/digitux/_internal packaging/AppDir/usr/bin/_internal
cp dist/digitux/digitux packaging/AppDir/usr/bin/digitux
chmod +x packaging/AppDir/usr/bin/digitux packaging/AppDir/AppRun 2>/dev/null || true
ARCH=x86_64 appimagetool packaging/AppDir dist/DigiTux-x86_64.AppImage

# --- 4) .deb ---
echo "[4/5] .deb (stdeb)..."
if [ -f pyproject.toml ]; then mv pyproject.toml /tmp/pyproject.build.bak; fi
rm -rf deb_dist
"$PY" setup.py --command-packages=stdeb.command bdist_deb
if [ -f /tmp/pyproject.build.bak ]; then mv /tmp/pyproject.build.bak pyproject.toml; fi
cp -f deb_dist/python3-digitux_*.deb dist/digitux_0.2.0-1_all.deb

# --- 5) done ---
echo "[5/5] Artefactos generados en dist/:"
ls -lh dist/digitux-x86_64 dist/DigiTux-x86_64.AppImage dist/digitux_0.2.0-1_all.deb