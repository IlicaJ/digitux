"""Control assignment panel — Stompbox / Expression / LFO / Wah (like Nexus)."""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTabWidget, QSpinBox, QDoubleSpinBox, QGroupBox, QCheckBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor


class ControlPanel(QTabWidget):
    """Right-side tab widget for r: Stompbox Mode, Expression Link, LFO Link,
    Wah Settings."""

    stomp_assigned = pyqtSignal(str, int)          # ctrl, slot (or -1 to clear)
    expression_assigned = pyqtSignal(str, int, str, int, int)  # ctrl, slot, param, min, max
    lfo_assigned = pyqtSignal(int, str, int, int, int, int)    # slot, param, min, max, speed, waveform
    wah_level = pyqtSignal(int)                    # value
    pedal = pyqtSignal(int)                        # value

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setStyleSheet(
            "QTabWidget::pane{border:1px solid #333; background:#181818;}"
            "QTabBar::tab{background:#222;color:#888;padding:6px 14px;}"
            "QTabBar::tab:selected{background:#181818;color:#ffb000;}"
        )
        self._build_stomp()
        self._build_expression()
        self._build_lfo()
        self._build_wah()

    # ---------------------------------------------------------- stompbox
    def _build_stomp(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.stomp_combo = QComboBox()
        self.stomp_combo.addItems(["ctrlA", "ctrlB", "ctrlC", "ctrlVSw"])
        self.stomp_combo.setStyleSheet(self._combo_style())
        lay.addWidget(QLabel("Footswitch"))
        lay.addWidget(self.stomp_combo)

        self.stomp_slot = QComboBox()
        self.stomp_slot.setStyleSheet(self._combo_style())
        lay.addWidget(QLabel("Asignar a pedal"))
        lay.addWidget(self.stomp_slot)
        for i in range(10):
            self.stomp_slot.addItem(f"Slot {i+1}", i)
        self.stomp_slot.addItem("— Ninguno —", -1)
        self.stomp_slot.currentIndexChanged.connect(self._on_stomp)

        clear = QPushButton("Quitar asignación")
        clear.clicked.connect(self._clear_stomp)
        lay.addWidget(clear)
        lay.addStretch()
        self.addTab(w, "Stompbox")

    def _on_stomp(self):
        idx = self.stomp_slot.currentData()
        ctrl = self.stomp_combo.currentText()
        self.stomp_assigned.emit(ctrl, idx)

    def _clear_stomp(self):
        self.stomp_slot.blockSignals(True)
        self.stomp_slot.setCurrentIndex(self.stomp_slot.count() - 1)
        self.stomp_slot.blockSignals(False)
        self.stomp_assigned.emit(self.stomp_combo.currentText(), -1)

    # -------------------------------------------------------- expression
    def _build_expression(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.expr_ctrl = QComboBox()
        self.expr_ctrl.addItems(["treadle", "altTreadle"])
        self.expr_ctrl.setStyleSheet(self._combo_style())
        lay.addWidget(QLabel("Pedal de expresión"))
        lay.addWidget(self.expr_ctrl)

        self.expr_slot = QComboBox()
        self.expr_slot.setStyleSheet(self._combo_style())
        lay.addWidget(QLabel("Asignar a slot"))
        lay.addWidget(self.expr_slot)

        self.expr_param = QComboBox()
        self.expr_param.setStyleSheet(self._combo_style())
        lay.addWidget(QLabel("Parámetro"))
        lay.addWidget(self.expr_param)

        self.expr_min = QSpinBox(); self.expr_min.setRange(0, 99)
        self.expr_max = QSpinBox(); self.expr_max.setRange(0, 99); self.expr_max.setValue(99)
        row = QHBoxLayout()
        row.addWidget(QLabel("Min")); row.addWidget(self.expr_min)
        row.addWidget(QLabel("Max")); row.addWidget(self.expr_max)
        lay.addLayout(row)

        self.expr_slot.currentIndexChanged.connect(self._populate_params)
        assign = QPushButton("Asignar")
        assign.clicked.connect(self._assign_expression)
        lay.addWidget(assign)
        lay.addStretch()
        self.addTab(w, "Expression")

    def _populate_params(self):
        self.expr_param.clear()

    def _assign_expression(self):
        ctrl = self.expr_ctrl.currentText()
        slot = self.expr_slot.currentData()
        param = self.expr_param.currentText()
        if slot is None or not param:
            return
        self.expression_assigned.emit(ctrl, slot, param, self.expr_min.value(), self.expr_max.value())

    # ------------------------------------------------------------- lfo
    def _build_lfo(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.lfo_slot = QComboBox()
        self.lfo_slot.setStyleSheet(self._combo_style())
        lay.addWidget(QLabel("Asignar a slot"))
        lay.addWidget(self.lfo_slot)

        self.lfo_param = QComboBox()
        self.lfo_param.setStyleSheet(self._combo_style())
        lay.addWidget(QLabel("Parámetro"))
        lay.addWidget(self.lfo_param)

        self.lfo_min = QSpinBox(); self.lfo_min.setRange(0, 99)
        self.lfo_max = QSpinBox(); self.lfo_max.setRange(0, 99); self.lfo_max.setValue(99)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Min")); row1.addWidget(self.lfo_min)
        row1.addWidget(QLabel("Max")); row1.addWidget(self.lfo_max)
        lay.addLayout(row1)

        self.lfo_speed = QSpinBox(); self.lfo_speed.setRange(0, 185); self.lfo_speed.setValue(74)
        self.lfo_wave = QComboBox()
        self.lfo_wave.addItems(["TRIANGLE", "SINE", "SQUARE"])
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Speed")); row2.addWidget(self.lfo_speed)
        row2.addWidget(QLabel("Wave")); row2.addWidget(self.lfo_wave)
        lay.addLayout(row2)

        self.lfo_slot.currentIndexChanged.connect(lambda _: self._populate_params())
        assign = QPushButton("Asignar")
        assign.clicked.connect(self._assign_lfo)
        lay.addWidget(assign)
        lay.addStretch()
        self.addTab(w, "LFO Link")

    def _assign_lfo(self):
        slot = self.lfo_slot.currentData()
        param = self.lfo_param.currentText()
        if slot is None or not param:
            return
        wave = {"TRIANGLE": 0, "SINE": 1, "SQUARE": 2}[self.lfo_wave.currentText()]
        self.lfo_assigned.emit(slot, param, self.lfo_min.value(), self.lfo_max.value(),
                               self.lfo_speed.value(), wave)

    # ------------------------------------------------------------ wah
    def _build_wah(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.wah_level = QSpinBox(); self.wah_level.setRange(0, 12); self.wah_level.setValue(6)
        self.wah_level.valueChanged.connect(self._on_wah_level)
        lay.addWidget(QLabel("WAH LEVL"))
        lay.addWidget(self.wah_level)
        self.pedal = QSpinBox(); self.pedal.setRange(0, 99); self.pedal.setValue(0)
        self.pedal.valueChanged.connect(self._on_pedal)
        lay.addWidget(QLabel("PEDAL"))
        lay.addWidget(self.pedal)
        lay.addStretch()
        self.addTab(w, "Wah Settings")

    def _on_wah_level(self, v):
        self.wah_level_value = v

    def _on_pedal(self, v):
        self.pedal_value = v

    # ----------------------------------------------------------- helpers
    def _combo_style(self):
        return "QComboBox{background:#222;color:#ddd;border:1px solid #444;border-radius:4px;padding:4px;}"

    def set_effect_slots(self, slots):
        """Populate slot combos with the current effects and their params."""
        self._slots = slots
        items = []
        for idx, slot in sorted(slots.items()):
            name = slot.model.split(".")[-1]
            items.append((f"{idx+1}: {name}", idx))
        for combo in (self.expr_slot, self.lfo_slot):
            combo.blockSignals(True)
            combo.clear()
            for label, data in items:
                combo.addItem(label, data)
            combo.blockSignals(False)
        self.expr_slot.currentIndexChanged.connect(self._populate_expr_params)
        self.lfo_slot.currentIndexChanged.connect(self._populate_lfo_params)
        self._populate_expr_params()
        self._populate_lfo_params()

    def _params_for_combo(self, combo):
        idx = combo.currentData()
        if idx is None or not hasattr(self, "_slots"):
            return []
        slot = self._slots.get(idx)
        if slot is None:
            return []
        return [p for p in slot.params.keys()]

    def _populate_expr_params(self):
        self.expr_param.blockSignals(True)
        self.expr_param.clear()
        self.expr_param.addItems(self._params_for_combo(self.expr_slot))
        self.expr_param.blockSignals(False)

    def _populate_lfo_params(self):
        self.lfo_param.blockSignals(True)
        self.lfo_param.clear()
        self.lfo_param.addItems(self._params_for_combo(self.lfo_slot))
        self.lfo_param.blockSignals(False)