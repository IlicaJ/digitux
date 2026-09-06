"""Amp/Cabinet block — clean, legible layout.

  [ AMP image (wide)          ]   [ LED / Bypass lever ]
  [ GAIN BASS MID TREB LEVEL  ]   [ Cabinet image+combo ]
"""
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, QRect
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont

from .knob import Knob
from ..runtime import img_path

AMP_DISP_W = 760
AMP_DISP_H = 252
CAB_DISP_W = 240
CAB_DISP_H = 210


class AmpView(QWidget):
    """Draws the amp image with overlayed knobs + LED/bypass lever baked into
    the amp's free (colored) area to the right of the plate."""

    change_requested = pyqtSignal(int)
    param_changed = pyqtSignal(int, str, int)
    bypass_toggled = pyqtSignal(int, bool)

    # fixed perilla positions in source-image coords (572x194) — below the plate
    KNOB_SRC = [(98, 125), (158, 125), (218, 125), (278, 125), (338, 125)]

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.slot = None
        self._pixmap = None
        self._knobs = []
        self._led_on = self._led_off = None
        self._sw_on = self._sw_off = None
        self.setFixedSize(AMP_DISP_W, AMP_DISP_H)
        self.setToolTip("Clic en la placa para cambiar amplificador")
        self._load_bits()

    def _load_bits(self):
        base = img_path("amps")
        for name in ("LED-red_ON.png", "LED-red_OFF.png",
                     "ToggleSwitch_Up.png", "ToggleSwitch_Down.png"):
            fp = base / name
            if fp.exists():
                pm = QPixmap(str(fp))
                if not pm.isNull():
                    if name == "LED-red_ON.png":
                        self._led_on = pm
                    elif name == "LED-red_OFF.png":
                        self._led_off = pm
                    elif name == "ToggleSwitch_Up.png":
                        self._sw_on = pm
                    else:
                        self._sw_off = pm

    def set_slot(self, slot):
        self.slot = slot
        self._pixmap = None
        self._clear_knobs()
        if slot is None:
            self.update()
            return
        addr = slot.model.split(".")[-1] if "." in slot.model else slot.model
        effect = self.db.by_address(addr)
        fn = effect.get("image") if effect else None
        if fn:
            fp = img_path("amps", fn)
            if fp.exists():
                pm = QPixmap(str(fp))
                if not pm.isNull():
                    self._pixmap = pm
        self._build_knobs(slot, effect)
        self.update()

    def _clear_knobs(self):
        for k in self._knobs:
            k.deleteLater()
        self._knobs = []

    def _build_knobs(self, slot, effect):
        if not effect:
            return
        params = [p for p in effect.get("params", []) if p["address"] != "ENABLE"
                  and p.get("type", "Normal") != "Special"]
        # escale factors: display-relative-to-source, based on how paint scales
        sx = AMP_DISP_W / 572.0
        sy = AMP_DISP_H / 194.0
        kw = 42
        for i, plist in enumerate(params[:5]):
            name = plist["address"]
            kx, ky = self.KNOB_SRC[i]
            knob = Knob(name, plist.get("min", 0), plist.get("max", 99),
                        int(slot.params.get(name, plist.get("default", 0))),
                        plist.get("unit", ""), size=kw,
                        knob_type=plist.get("knobType"), parent=self)
            # center the knob widget over the source perilla point
            px = int(kx * sx) - kw // 2
            py = int(ky * sy) - kw // 2
            knob.move(px, py)
            knob.valueChanged.connect(
                lambda v, n=name, i=slot.slot: self.param_changed.emit(i, n, v)
            )
            self._knobs.append(knob)
            knob.show()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(22, 22, 22))
        if self._pixmap:
            pm = self._pixmap.scaled(
                AMP_DISP_W, AMP_DISP_H, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x = (AMP_DISP_W - pm.width()) // 2
            y = (AMP_DISP_H - pm.height()) // 2
            p.drawPixmap(x, y, pm)
        else:
            p.setPen(QColor(255, 176, 0))
            p.setFont(QFont("Sans", 14, QFont.Bold))
            p.drawText(self.rect(), Qt.AlignCenter, "Amplificador")

        # LED + lever baked into the amp's colored area (right, over the chassis)
        enabled = self.slot is None or bool(self.slot.enable)
        sx = AMP_DISP_W / 572.0
        sy = AMP_DISP_H / 194.0
        col_x = int(455 * sx)   # free column to the right of the plate
        # LED
        led = self._led_on if enabled else self._led_off
        if led is not None:
            p.drawPixmap(col_x, int(30 * sy),
                         led.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        # ON
        p.setPen(QColor(255, 120, 120) if enabled else QColor(90, 90, 90))
        p.setFont(QFont("Sans", 8, QFont.Bold))
        p.drawText(QRect(col_x - 6, int(72 * sy), 78, 12), Qt.AlignCenter, "ON")
        # lever
        sw = self._sw_on if enabled else self._sw_off
        if sw is not None:
            p.drawPixmap(col_x, int(88 * sy),
                         sw.scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        # Bypass
        p.setPen(QColor(200, 200, 200) if enabled else QColor(255, 120, 120))
        p.drawText(QRect(col_x - 6, int(146 * sy), 78, 14), Qt.AlignCenter, "Bypass")
        p.end()

    def _switch_rect(self):
        sx = AMP_DISP_W / 572.0
        sy = AMP_DISP_H / 194.0
        col_x = int(455 * sx)
        return QRect(col_x, int(70 * sy), 66, int(90 * sy))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.slot is not None:
            if self._switch_rect().contains(e.pos()):
                bypass = bool(self.slot.enable)
                self.bypass_toggled.emit(self.slot.slot, bypass)
            else:
                self.change_requested.emit(self.slot.slot)
        super().mousePressEvent(e)


class AmpCabBlock(QWidget):
    """Amp + knobs (below) + cabinet, with bypass switch to the right."""

    param_changed = pyqtSignal(int, str, int)
    cabinet_changed = pyqtSignal(int, int)
    change_requested = pyqtSignal(int)
    bypass_toggled = pyqtSignal(int, bool)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.amp_slot = None
        self.setFixedHeight(290)
        self.setStyleSheet("background:#1a1a1a; border:1px solid #333; border-radius:8px;")
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(18)

        # ---- left: amp image (with overlayed knobs + LED/bypass) ----
        amp_col = QVBoxLayout()
        amp_col.setSpacing(6)
        self.amp_view = AmpView(self.db)
        self.amp_view.change_requested.connect(self.change_requested.emit)
        self.amp_view.param_changed.connect(self.param_changed.emit)
        self.amp_view.bypass_toggled.connect(self.bypass_toggled.emit)
        amp_col.addWidget(self.amp_view)
        amp_col.addStretch()
        lay.addLayout(amp_col, 1)

        # ---- right: cabinet only ----
        right = QVBoxLayout()
        right.setSpacing(6)
        right.setContentsMargins(0, 30, 20, 0)   # más a la derecha y abajo

        # cabinet: imagen a la izquierda + selector a su derecha
        cab_row = QHBoxLayout()
        cab_row.setSpacing(8)
        self.cab_lbl = QLabel("Cabinet")
        self.cab_lbl.setFixedSize(CAB_DISP_W, CAB_DISP_H)
        self.cab_lbl.setAlignment(Qt.AlignCenter)
        self.cab_lbl.setStyleSheet(
            "background:#0f0f0f; border:1px solid #3a3a3a; border-radius:6px; color:#666; font-size:11px;"
        )
        cab_row.addWidget(self.cab_lbl)
        self.cab_combo = QComboBox()
        self.cab_combo.addItems(self.db.cabinet_names())
        self.cab_combo.setMinimumWidth(150)
        self.cab_combo.setStyleSheet(
            "QComboBox{background:#222;color:#ddd;border:1px solid #444;border-radius:4px;padding:4px;}"
            "QComboBox::drop-down{border:none;}"
        )
        self.cab_combo.currentIndexChanged.connect(self._on_cab_combo)
        cab_row.addWidget(self.cab_combo, alignment=Qt.AlignTop)
        right.addLayout(cab_row)
        right.addStretch()
        lay.addLayout(right, 0)

    def set_amp_slot(self, slot):
        self.amp_slot = slot
        self.amp_view.set_slot(slot)
        if slot is None:
            self.cab_lbl.setText("Cabinet")
            return
        addr = slot.model.split(".")[-1] if "." in slot.model else slot.model
        effect = self.db.by_address(addr)
        # cabinet (CABINET param or cabType)
        cab_index = None
        if "CABINET" in slot.params:
            cab_index = int(slot.params["CABINET"])
        cab = self.db.cabinet_at(cab_index) if cab_index is not None else None
        if cab is None:
            cab_type = effect.get("cabType") if effect else None
            cab = self.db.cabinet_by_address(cab_type) if cab_type else None
            cab_index = cab.get("id") if cab else None
        if cab is not None:
            self._set_cab_image(cab)
            if cab_index is not None:
                self.cab_combo.blockSignals(True)
                self.cab_combo.setCurrentIndex(cab_index)
                self.cab_combo.blockSignals(False)

    def _set_cab_image(self, cab):
        self.cab_lbl.setText("")
        fn = cab.get("image")
        if fn:
            fp = img_path("cabs", fn)
            if fp.exists():
                pm = QPixmap(str(fp))
                if not pm.isNull():
                    self.cab_lbl.setPixmap(pm.scaled(CAB_DISP_W - 4, CAB_DISP_H - 4,
                                                     Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    return
        self.cab_lbl.setText(cab.get("displayName", ""))

    def _on_cab_combo(self, idx):
        if self.amp_slot is None:
            return
        cab = self.db.cabinet_at(idx)
        if cab:
            self._set_cab_image(cab)
        self.cabinet_changed.emit(self.amp_slot.slot, idx)