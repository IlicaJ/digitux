"""Pedal widget — stylized cartoon pedal with rotary knobs + ON/OFF LED."""
from PyQt5.QtWidgets import QWidget, QMenu
from PyQt5.QtCore import Qt, pyqtSignal, QRect
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QFont

from .knob import Knob
from ..runtime import img_path

SRC_W = 220.0
SRC_H = 364.0
DISP_W = 180
DISP_H = 298


class PedalWidget(QWidget):
    """A single effect 'pedal' on the signal chain."""

    param_changed = pyqtSignal(int, str, int)   # slot index, param, value
    enable_toggled = pyqtSignal(int, bool)      # slot index, enabled
    delete_requested = pyqtSignal(int)
    change_requested = pyqtSignal(int)

    def __init__(self, index, slot, db, parent=None):
        super().__init__(parent)
        self.index = index
        self.slot = slot
        self.db = db
        self._pixmap = None
        self._knobs = {}
        self.setFixedSize(DISP_W, DISP_H)
        self._load_pixmap()
        self._build_knobs()

    # -------------------------------------------------------------- setup
    def _load_pixmap(self):
        addr = self.slot.model.split(".")[-1] if "." in self.slot.model else self.slot.model
        effect = self.db.by_address(addr)
        fn = effect["image"] if effect else None
        if not fn:
            return
        base = img_path()
        for sub in ("amps", "pedals", "cabs"):
            fp = base / sub / fn
            if fp.exists():
                pm = QPixmap(str(fp))
                if not pm.isNull():
                    self._pixmap = pm.scaled(
                        DISP_W, DISP_H, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                return

    def _build_knobs(self):
        addr = self.slot.model.split(".")[-1] if "." in self.slot.model else self.slot.model
        effect = self.db.by_address(addr)
        if not effect:
            return
        # parámetros del efecto (excluyendo ENABLE)
        params = [p for p in effect.get("params", []) if p["address"] != "ENABLE"
                  and p.get("type", "Normal") != "Special"]
        if not params:
            return
        # grilla fija de hasta 6 perillas (2 columnas x 3 filas), en coords fuente 220x364
        # dentro de la placa (y 34..172)
        sx = DISP_W / SRC_W
        sy = DISP_H / SRC_H
        kw = 40
        n = len(params[:6])
        if n == 1:
            # una sola perilla (p.ej. Volume) -> centrada
            positions = [(110, 96)]   # centro de la placa, en coords fuente
        else:
            grid = [(60, 60), (160, 60), (60, 130), (160, 130), (60, 200), (160, 200)]
            positions = grid[:n]
        for i, plist in enumerate(params[:6]):
            name = plist["address"]
            kx, ky = positions[i]
            knob = Knob(name, plist.get("min", 0), plist.get("max", 99),
                        int(self.slot.params.get(name, plist.get("default", 0))),
                        plist.get("unit", ""), size=kw,
                        knob_type=plist.get("knobType"), parent=self)
            px = int(kx * sx) - kw // 2
            py = int(ky * sy) - kw // 2
            knob.move(px, py)
            knob.valueChanged.connect(
                lambda v, n=name, i=self.index: self.param_changed.emit(i, n, v)
            )
            self._knobs[name] = knob
            knob.show()

    # ------------------------------------------------------------ painting
    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # press offset: pedal dips down a few px while pressed
        dy = 6 if getattr(self, "_pressed", False) else 0
        r = QRect(0, dy, DISP_W, DISP_H)
        if self._pixmap:
            p.drawPixmap(r, self._pixmap)
        else:
            p.fillRect(r, QColor(50, 50, 50))
            p.setPen(QColor(255, 176, 0))
            p.setFont(QFont("Sans", 12, QFont.Bold))
            p.drawText(r, Qt.AlignCenter, self.slot.model.split(".")[-1])
        # border highlight when enabled
        enabled = bool(self.slot.enable)
        if enabled:
            p.setPen(QPen(QColor(255, 176, 0, 160), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(1 + dy // 2, 1 + dy, DISP_W - 3, DISP_H - 3, 12, 12)
        # ON/OFF LED + footswitch (bottom-right, part of the animated press)
        lx = DISP_W - 30
        ly = DISP_H - 46 + dy
        if enabled:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(110, 220, 80, 120))
            p.drawEllipse(lx - 4, ly - 4, 24, 24)
            p.setBrush(QColor(150, 240, 110))
            p.setPen(QPen(QColor(40, 90, 30), 1))
        else:
            p.setBrush(QColor(56, 56, 56))
            p.setPen(QPen(QColor(28, 28, 28), 1))
        p.drawEllipse(lx, ly, 16, 16)
        # footswitch ring below LED
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(30, 30, 30), 2))
        p.drawEllipse(lx - 6, ly + 22, 28, 28)
        p.end()

    # ------------------------------------------------------------ events
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._pressed = True
            self._drag_start = e.pos()
            self.update()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if getattr(self, "_pressed", False) and getattr(self, "_drag_start", None) is not None:
            if (e.pos() - self._drag_start).manhattanLength() > 12:
                self._pressed = False
                self.update()
                cb = getattr(self, "_on_drag_requested", None)
                if cb:
                    cb(self.index, self)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and getattr(self, "_pressed", False):
            self._pressed = False
            self.update()
            # toggle on/off
            self.slot.enable = not bool(self.slot.enable)
            self.enable_toggled.emit(self.index, bool(self.slot.enable))
        super().mouseReleaseEvent(e)

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        menu.addAction("Cambiar efecto...", lambda: self.change_requested.emit(self.index))
        menu.addAction("Eliminar", lambda: self.delete_requested.emit(self.index))
        menu.exec_(e.globalPos())