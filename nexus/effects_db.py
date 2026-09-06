"""Effects database loaded from rp360_effects.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from .runtime import _package_root

log = logging.getLogger(__name__)

_DEFAULT_PATH = _package_root() / "nexus" / "rp360_effects.json"

# Natural (default) signal-chain position for each effect category. The RP360/XP
# chain is: Wah, Compressor, Distortion, Amp, EQ/Gate, Volume/Mod, Delay, Reverb.
# A preset may hold at most ONE effect per category; the exact slot index can vary
# slightly (e.g. Volume and Mod may swap), which is why add_effect uses the device
# to confirm placement rather than assuming a hard index.
SLOT_CATEGORY = {
    0: "Wah",
    1: "Compressor",
    2: "Distortion",
    3: "Amplifier",
    4: "EQ",
    5: "Gate",
    6: "Other",     # Volume
    7: "Mod",       # Chorus/Mod
    8: "Delay",
    9: "Reverb",
}

# Flexible neighbours: categories that may occupy more than one position.
_FLEXIBLE = {"Other": (6, 7), "Mod": (6, 7)}


def natural_positions(category: str) -> list[int]:
    """Return the allowed slot index(es) for a category in the default chain."""
    if category in _FLEXIBLE:
        return list(_FLEXIBLE[category])
    for idx, cat in SLOT_CATEGORY.items():
        if cat == category:
            return [idx]
    return []

# Category → prefix used in the device's model identifier (e.g. "dist.SCREAMER").
# "dist" and "amp" are confirmed from protocol captures; others are educated guesses
# and should be verified by capture if used with set_model.
_CATEGORY_PREFIX: dict[str, str] = {
    "Wah":        "wah",   # confirmed
    "Compressor": "cmpr",  # confirmed
    "Distortion": "dist",  # confirmed
    "Other":      "vol",   # Volume effect — flat slot, confirmed prefix from preset JSON
    "EQ":         "eq",    # confirmed
    "Gate":       "gate",  # confirmed
    "Mod":        "mod",   # confirmed
    "Delay":      "dly",   # confirmed
    "Reverb":     "rvb",   # confirmed
    "Amplifier":  "amp",   # confirmed
}


class EffectsDB:
    def __init__(self, path: Optional[Path] = None):
        p = Path(path) if path else _DEFAULT_PATH
        with p.open() as f:
            raw = json.load(f)
        self._effects: list[dict] = raw["effects"] if isinstance(raw, dict) else raw
        self._cabinets: list[dict] = raw.get("cabinets", []) if isinstance(raw, dict) else []
        # Build lookup indices
        self._by_address: dict[str, dict] = {e["address"]: e for e in self._effects}
        self._by_category: dict[str, list[dict]] = {}
        for e in self._effects:
            self._by_category.setdefault(e["category"], []).append(e)

    def by_address(self, address: str) -> Optional[dict]:
        """Return effect definition by its address (e.g. 'SCREAMER')."""
        return self._by_address.get(address)

    def by_model_name(self, model: str) -> Optional[dict]:
        """Look up by the 'prefix.ADDRESS' string stored in preset JSON."""
        if "." in model:
            _, address = model.split(".", 1)
            return self.by_address(address)
        return self.by_address(model)

    def model_id(self, address: str) -> Optional[str]:
        """Return the full 'prefix.ADDRESS' model identifier for set_model.

        Returns None if the address is unknown.
        The prefix for some categories is unverified — check _CATEGORY_PREFIX.
        """
        effect = self._by_address.get(address)
        if effect is None:
            return None
        prefix = _CATEGORY_PREFIX.get(effect["category"])
        if prefix is None:
            return None
        return f"{prefix}.{address}"

    def find(self, text: str) -> list[dict]:
        """Search effects by address or displayName (case-insensitive substring)."""
        text = text.upper()
        return [
            e for e in self._effects
            if text in e["address"].upper() or text in e["displayName"].upper()
        ]

    def by_category(self, category: str) -> list[dict]:
        """Return all effects in a category (e.g. 'Distortion', 'Amp')."""
        return self._by_category.get(category, [])

    def image_filename(self, address: str) -> Optional[str]:
        """Return the image filename for an effect (from rp360_effects.json), or None."""
        e = self._by_address.get(address)
        if e is None:
            return None
        return e.get("image")

    def cabinet_image(self, cabinet_index: int) -> Optional[str]:
        """Return the cabinet image filename for a cabinet id (device index)."""
        for c in self._cabinets:
            if c.get("id") == cabinet_index:
                return c.get("image")
        return None

    def cabinet_by_address(self, address: str) -> Optional[dict]:
        for c in self._cabinets:
            if c.get("address") == address:
                return c
        return None

    def cabinet_at(self, index: int) -> Optional[dict]:
        """Return cabinet dict at a list position (matches cabinet_names())."""
        by_id = sorted(self._cabinets, key=lambda c: c["id"])
        if 0 <= index < len(by_id):
            return by_id[index]
        return None

    def categories(self) -> list[str]:
        return list(self._by_category.keys())

    def cabinet_names(self) -> list[str]:
        """Return cabinet display names ordered by device index (0-based).

        The list index matches the CABINET param value sent by the device.
        """
        return [c["displayName"] for c in sorted(self._cabinets, key=lambda c: c["id"])]

    def param_range(self, address: str, param: str) -> tuple[int, int]:
        """Return (min, max) for a parameter. Raises KeyError if not found."""
        effect = self._by_address[address]
        for p in effect.get("params", []):
            if p["address"] == param:
                return p.get("min", 0), p.get("max", 99)
        raise KeyError(f"Param {param!r} not found in effect {address!r}")

    def build_slot_data(self, address: str) -> dict:
        """Build a default slot dict for add_effect(), using DB default values.

        For EQ and Volume (flat slots) params are at the root level.
        For all others params are nested under an 'fx' subdict.
        Returns None if address is unknown.
        """
        effect = self._by_address.get(address)
        if effect is None:
            return None
        model_id = self.model_id(address)
        if model_id is None:
            return None

        has_enable = any(p["address"] == "ENABLE" for p in effect.get("params", []))
        params = {
            p["address"]: p.get("default", 0)
            for p in effect.get("params", [])
            if p["address"] != "ENABLE"
        }

        prefix = model_id.split(".")[0]
        if prefix in ("eq", "vol"):
            # flat slot — params at root level, no fx subdict
            slot: dict = {"name": model_id, **params}
            if has_enable:
                slot["ENABLE"] = 0
            return slot
        else:
            slot = {"fx": {"name": model_id, **params}}
            if has_enable:
                slot["ENABLE"] = 0
            return slot
