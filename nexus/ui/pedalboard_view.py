"""Horizontal pedalboard view — faithful Nexus clone.

Displays the 10 fixed chain positions in order (0..9), with empty-slot placeholders,
and supports drag-and-drop to reorder the chain.
"""
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QScrollArea, QLabel, QPushButton, QLayout,
)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QTimer
from PyQt5.QtGui import QPainter, QPixmap, QColor, QDrag

from .pedal_widget import PedalWidget
from .pedal_widget import DISP_W, DISP_H
from ..runtime import img_path

MIME = "application/x-nexus-slot"


def reordered_slots(slots, source, target):
    """Return occupied indices in their requested order."""
    if source not in slots or not 0 <= target < 10:
        raise ValueError("Invalid chain position")
    order = list(range(10))
    order.insert(target, order.pop(source))
    return [index for index in order if index in slots]


class AmpPin(QWidget):
    """Compact draggable pin representing the amplifier in the chain."""

    def __init__(self, index, slot):
        super().__init__()
        self.index = index
        self.slot = slot
        self.setFixedSize(60, 258)
        self._icon = None
        fp = img_path("pedalboard", "Amp_Icon_SignalChain.png")
        if fp.exists():
            pm = QPixmap(str(fp))
            if not pm.isNull():
                self._icon = pm

    def paintEvent(self, e):
        p = QPainter(self)
        if self._icon is not None:
            pm = self._icon.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap((60 - pm.width()) // 2, 8, pm)
        else:
            p.setBrush(QColor(0x8e44ad))
            p.drawEllipse(10, 8, 40, 40)
        # label
        p.setPen(QColor(235, 235, 235))
        p.drawText(0, 84, 60, 20, Qt.AlignCenter, "AMP")
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_start = e.pos()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if getattr(self, "_drag_start", None) is not None:
            if (e.pos() - self._drag_start).manhattanLength() > 10:
                self._drag_start = None
                cb = getattr(self, "_on_drag_requested", None)
                if cb:
                    cb(self.index, self)
        super().mouseMoveEvent(e)


class _Carpet(QWidget):
    """Container that paints the Nexus pedalboard carpet behind the pedals."""

    def __init__(self):
        super().__init__()
        self._bg = None
        fp = img_path("pedalboard", "pedalboard_bg.png")
        if fp.exists():
            pm = QPixmap(str(fp))
            if not pm.isNull():
                self._bg = pm

    def paintEvent(self, e):
        p = QPainter(self)
        if self._bg is not None:
            tw = self._bg.width()
            th = self.height()
            x = 0
            while x < self.width():
                p.drawPixmap(x, 0, self._bg.scaled(tw, th, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
                x += tw
        else:
            p.fillRect(self.rect(), QColor(0x1a1a1a))
        p.end()


class _EmptySlot(QLabel):
    """Placeholder for an empty chain position."""

    def __init__(self, index):
        super().__init__()
        self.index = index
        self._bg = None
        fp = img_path("pedals", "Empty-pedal.png")
        if fp.exists():
            pm = QPixmap(str(fp))
            if not pm.isNull():
                self._bg = pm
        self.setFixedSize(DISP_W, DISP_H)

    def paintEvent(self, e):
        p = QPainter(self)
        if self._bg:
            pm = self._bg.scaled(DISP_W, DISP_H, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap((DISP_W - pm.width()) // 2, (DISP_H - pm.height()) // 2, pm)
        else:
            p.setPen(QColor(90, 90, 90))
            p.drawRect(0, 0, DISP_W - 1, DISP_H - 1)
        p.end()


class PedalboardView(QScrollArea):
    """Horizontal chain of pedals in fixed positions 0..9, with drag-drop reorder."""

    param_changed = pyqtSignal(int, str, int)
    enable_toggled = pyqtSignal(int, bool)
    delete_requested = pyqtSignal(int)
    change_requested = pyqtSignal(int)
    reorder_requested = pyqtSignal(int, int)  # source slot index, target slot index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumHeight(340)
        self.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.container = _Carpet()
        self.layout = QHBoxLayout(self.container)
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)
        self.layout.setContentsMargins(16, 20, 16, 10)
        self.layout.setSpacing(6)
        self.setWidget(self.container)
        self.pedals = {}          # slot index -> PedalWidget
        self.empties = []         # _EmptySlot widgets
        self._occupied = set()
        self._pending_reorder = None
        self.setAcceptDrops(True)

    def rebuild(self, slots, db):
        # clear
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.pedals.clear()
        self.empties.clear()
        self._occupied = set(slots)
        self._slot_widgets = {}   # slot index -> widget (for drop calc)

        for idx in range(10):
            slot = slots.get(idx)
            if slot is not None:
                if slot.category == "amp":
                    w = AmpPin(idx, slot)
                    w._on_drag_requested = self._start_drag
                    self.layout.addWidget(w)
                    self._slot_widgets[idx] = w
                else:
                    w = PedalWidget(idx, slot, db)
                    w.param_changed.connect(self.param_changed.emit)
                    w.enable_toggled.connect(self.enable_toggled.emit)
                    w.delete_requested.connect(self.delete_requested.emit)
                    w.change_requested.connect(self.change_requested.emit)
                    w._on_drag_requested = self._start_drag
                    self.layout.addWidget(w)
                    self.pedals[idx] = w
                    self._slot_widgets[idx] = w
            else:
                e = _EmptySlot(idx)
                self.layout.addWidget(e)
                self._slot_widgets[idx] = e
                self.empties.append(e)
        self.layout.addStretch()

    def _start_drag(self, source_index, widget):
        if len(self._occupied) < 2:
            return
        self._pending_reorder = None
        drag = QDrag(widget)
        mime = QMimeData()
        mime.setData(MIME, str(source_index).encode())
        drag.setMimeData(mime)
        drag.setPixmap(widget.grab())
        drag.exec_(Qt.MoveAction)
        if self._pending_reorder is not None:
            src, target = self._pending_reorder
            self._pending_reorder = None
            QTimer.singleShot(0, lambda: self.reorder_requested.emit(src, target))

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if not e.mimeData().hasFormat(MIME):
            e.ignore()
            return
        try:
            src = int(e.mimeData().data(MIME).data().decode())
        except (ValueError, UnicodeDecodeError):
            e.ignore()
            return
        target = self._slot_at_x(self.container.mapFrom(self.viewport(), e.pos()).x())
        if src not in self._occupied or target is None:
            e.ignore()
            return
        order = reordered_slots(self._occupied, src, target)
        if order != sorted(self._occupied):
            self._pending_reorder = (src, target)
        e.acceptProposedAction()

    def _slot_at_x(self, x):
        # find the widget whose horizontal range contains x
        for idx, w in self._slot_widgets.items():
            gx = w.mapTo(self.container, w.rect().topLeft()).x()
            if gx <= x < gx + w.width():
                return idx
        # fallback: nearest
        return None