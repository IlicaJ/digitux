"""Runtime path resolution.

Handles both source execution and frozen bundles (PyInstaller / AppImage),
where data files live under ``sys._MEIPASS`` instead of next to ``__file__``.

Layout:
  - source:  nexus/assets/...  and  ./data/...
  - frozen:  sys._MEIPASS/nexus/assets/...  and  sys._MEIPASS/data/...
"""
import sys
from pathlib import Path


def _package_root() -> Path:
    """Directory that contains the bundled package tree (has 'nexus' inside)."""
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent  # project root


def img_path(*parts) -> Path:
    """Absolute path into ``nexus/assets/img``."""
    return _package_root() / "nexus" / "assets" / "img" / Path(*parts)


def asset_path(*parts) -> Path:
    """Absolute path into ``nexus/assets``."""
    return _package_root() / "nexus" / "assets" / Path(*parts)


def data_path(*parts) -> Path:
    """Absolute path into ``nexus/data``."""
    return _package_root() / "nexus" / "data" / Path(*parts)