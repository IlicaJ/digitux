"""Rotary knob widget: circular body + gold pointer + readable label."""
import math

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont


class Knob(QWidget):
    """A rotary knob drawn with a gold pointer and a label under it.

    `knob_type` is accepted for backwards compatibility but unused (knobs are
    drawn programmatically, not from sprite sheets).
    """

    valueChanged = pyqtSignal(int)

    def __init__(self, name="", min_val=0, max_val=99, value=0, unit="",
                 size=56, knob_type=None, parent=None):
        super().__init__(parent)
        self.name = name
        self.min_val = min_val
        self.max_val = max_val
        self._value = value
        self.unit = unit
        self.setFixedSize(size, size + 20)
        self.setMouseTracking(True)
        self._drag_start = None
        self._drag_value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = max(self.min_val, min(self.max_val, v))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        label_h = 18
        knob_area = self.height() - label_h
        cx = w // 2
        cy = knob_area // 2
        r = knob_area // 2 - 3
        # body
        p.setBrush(QColor(75, 75, 75))
        p.setPen(QColor(20, 20, 20))
        p.drawEllipse(cx - r, cy - r, cx + r, cy + r)
        # tick marks
        p.setPen(QColor(150, 150, 150))
        for i in range(0, 101, 10):
            a = math.radians(-135 + (i / 100) * 270)
            x1 = cx + (r - 2) * math.cos(a)
            y1 = cy + (r - 2) * math.sin(a)
            x2 = cx + (r - 5) * math.cos(a)
            y2 = cy + (r - 5) * math.sin(a)
            p.drawLine(int(x1), int(y1), int(x2), int(y2))
        # pointer
        ratio = (self._value - self.min_val) / (self.max_val - self.min_val)
        a = math.radians(-135 + ratio * 270)
        p.setPen(QColor(255, 176, 0))
        pen = p.pen()
        pen.setWidth(2)
        p.setPen(pen)
        p.drawLine(cx, cy, int(cx + (r - 7) * math.cos(a)), int(cy + (r - 7) * math.sin(a)))
        # label
        p.setPen(QColor(225, 225, 225))
        p.setFont(QFont("Sans", 8, QFont.Bold))
        p.drawText(0, knob_area, w, label_h - 2, Qt.AlignCenter, self.name)
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_start = e.globalPos()
            self._drag_value = self._value
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag_start is not None:
            delta = self._drag_start.y() - e.globalPos().y()
            step = max(1, (self.max_val - self.min_val) // 100)
            self.value = self._drag_value + delta * step
            self.valueChanged.emit(self._value)

    def mouseReleaseEvent(self, e):
        self._drag_start = None
        self.setCursor(Qt.ArrowCursor)

    def wheelEvent(self, e):
        delta = e.angleDelta().y() // 120
        step = max(1, (self.max_val - self.min_val) // 50)
        self.value = self._value + delta * step
        self.valueChanged.emit(self._value)