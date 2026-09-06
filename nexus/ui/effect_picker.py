"""Graphical effect picker — gallery of pedals/amps by category (like Nexus)."""
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QGridLayout,
    QWidget, QLabel, QScrollArea, QPushButton, QFrame, QButtonGroup,
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon


CATEGORIES = [
    ("Amplifier", "Amplificadores"),
    ("Distortion", "Distorsión"),
    ("Wah", "Wah"),
    ("Compressor", "Compresor"),
    ("Mod", "Modulación"),
    ("Delay", "Delay"),
    ("Reverb", "Reverb"),
    ("Gate", "Gate"),
    ("EQ", "EQ"),
    ("Other", "Volumen"),
]


class EffectPicker(QDialog):
    """Modal gallery to choose an effect. Returns the chosen effect dict.

    If `current_category` is given, the picker is locked to that single category
    (no category list shown). Otherwise all categories are browsable.
    """

    def __init__(self, db, current_category=None, parent=None, allowed_categories=None, title=None):
        super().__init__(parent)
        self.db = db
        self.result_effect = None
        self.setWindowTitle(title or "Seleccionar efecto")
        self.resize(760, 560)
        self.setStyleSheet("QDialog{background:#181818;}")

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # Determine which categories to list:
        #  - current_category -> lock to that single category
        #  - allowed_categories -> show only those (add effect)
        #  - otherwise -> all categories
        if current_category is not None:
            self._cats = [current_category]
            self._locked = True
        elif allowed_categories:
            self._cats = [c for c, _ in CATEGORIES if c in allowed_categories]
            self._locked = False
        else:
            self._cats = [c for c, _ in CATEGORIES if self.db.by_category(c)]
            self._locked = False

        body = QHBoxLayout()

        # category list (left) — only when browsing multiple categories
        self.cat_list = None
        if not self._locked:
            self.cat_list = QListWidget()
            self.cat_list.setFixedWidth(180)
            self.cat_list.setStyleSheet(
                "QListWidget{background:#151515;color:#ddd;border:1px solid #333;border-radius:6px;}"
                "QListWidget::item{padding:10px;font-size:13px;}"
                "QListWidget::item:selected{background:#ffb000;color:#111;}"
            )
            body.addWidget(self.cat_list)

        # gallery (right)
        self.gallery = QScrollArea()
        self.gallery.setWidgetResizable(True)
        self.gallery.setStyleSheet("QScrollArea{background:#151515;border:1px solid #333;border-radius:6px;}")
        self.gal_widget = QWidget()
        self.grid = QGridLayout(self.gal_widget)
        self.grid.setSpacing(10)
        self.grid.setContentsMargins(10, 10, 10, 10)
        self.gallery.setWidget(self.gal_widget)
        body.addWidget(self.gallery, 1)

        root.addLayout(body)

        # buttons
        btns = QHBoxLayout()
        if self._locked:
            title = QLabel(f"{current_category}")
            title.setStyleSheet("color:#ffb000; font-weight:bold; font-size:13px;")
            btns.addWidget(title)
        btns.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        root.addLayout(btns)

        # label mapping
        label_map = dict(CATEGORIES)  # db_cat -> label

        # populate
        if self.cat_list is not None:
            self._cat_to_db = {}
            for db_cat in self._cats:
                row = self.cat_list.count()
                self.cat_list.addItem(label_map.get(db_cat, db_cat))
                self._cat_to_db[row] = db_cat
            self.cat_list.currentRowChanged.connect(self._show_category)
            self.cat_list.setCurrentRow(0)
        else:
            self._cat_to_db = {0: self._cats[0]}
            self._show_category(0)

    def _show_category(self, row):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        db_cat = self._cat_to_db.get(row)
        if db_cat is None:
            return
        effects = self.db.by_category(db_cat)
        cols = 4
        base = Path(__file__).parents[1] / "assets" / "img"
        for i, e in enumerate(effects):
            card = _EffectCard(e, base)
            card.clicked.connect(self._on_pick)
            self.grid.addWidget(card, i // cols, i % cols)

    def _on_pick(self, effect):
        self.result_effect = effect
        self.accept()


class _EffectCard(QFrame):
    clicked = pyqtSignal(object)

    def __init__(self, effect, base, parent=None):
        super().__init__(parent)
        self.effect = effect
        self.setFixedSize(150, 150)
        self.setStyleSheet(
            "QFrame{background:#222;border:1px solid #3a3a3a;border-radius:8px;}"
            "QFrame:hover{border-color:#ffb000;}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)

        img = QLabel()
        img.setFixedSize(120, 100)
        img.setAlignment(Qt.AlignCenter)
        fn = effect.get("image")
        if fn:
            for sub in ("amps", "pedals", "cabs"):
                fp = base / sub / fn
                if fp.exists():
                    pm = QPixmap(str(fp))
                    if not pm.isNull():
                        img.setPixmap(pm.scaled(118, 98, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        img.setStyleSheet("background:#0f0f0f;border-radius:4px;")
                    break
        lay.addWidget(img, alignment=Qt.AlignHCenter)

        name = QLabel(effect.get("displayName", ""))
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("color:#ddd;font-size:10px;font-weight:bold;")
        name.setWordWrap(True)
        lay.addWidget(name)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.effect)
        super().mousePressEvent(e)