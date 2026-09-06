# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: build DigiTux as a single-file binary.

Resources are bundled under sys._MEIPASS so runtime.py can find them:
  nexus/assets/..., nexus/rp360_effects.json, data/...
"""
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent if 'SPECPATH' in globals() and SPECPATH else Path('.')

a = Analysis(
    [str(ROOT / 'packaging' / 'launcher.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'nexus' / 'assets'), 'nexus/assets'),
        (str(ROOT / 'nexus' / 'data'), 'nexus/data'),
        (str(ROOT / 'nexus' / 'rp360_effects.json'), 'nexus'),
    ],
    hiddenimports=['PyQt5.QtWidgets', 'PyQt5.QtGui', 'PyQt5.QtCore', 'serial'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='digitux',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / 'packaging' / 'digitux.png'),
)