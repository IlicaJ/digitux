"""Main window — faithful Nexus clone for Linux."""
import json
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QLineEdit, QTabBar, QSplitter, QMessageBox, QStatusBar,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QPalette, QFont, QPixmap, QPainter, QLinearGradient

from ..device import Device
from ..effects_db import EffectsDB
from .pedalboard_view import PedalboardView
from .amp_cab_block import AmpCabBlock
from .control_panel import ControlPanel


class _TitleBar(QWidget):
    """Custom title bar with a dark gradient."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(54)

    def paintEvent(self, e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor(0x1e1e1e))
        g.setColorAt(0.5, QColor(0x141414))
        g.setColorAt(1, QColor(0x0d0d0d))
        p.fillRect(self.rect(), g)
        p.setPen(QColor(0x333333))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        p.end()


class Worker(QObject):
    notif = pyqtSignal(list)

    def __init__(self, device):
        super().__init__()
        self.dev = device

    def start(self):
        self.dev.on_notification(lambda m: self.notif.emit(m))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DigiTux — RP360/XP Editor")
        self.resize(1360, 820)
        self.db = EffectsDB()
        self.dev = Device()
        self._setup_ui()
        self._apply_theme()
        QTimer.singleShot(100, self._connect)

    # ---------------------------------------------------------------- UI
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left: preset browser
        self.browser = self._build_browser()
        root.addWidget(self.browser)

        # Right: amp-cab + pedalboard
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(10, 10, 10, 10)
        rl.setSpacing(10)

        self.title_bar = self._build_title_bar()
        rl.addWidget(self.title_bar)

        self.amp_block = AmpCabBlock(self.db)
        self.amp_block.param_changed.connect(self._set_param)
        self.amp_block.cabinet_changed.connect(self._set_cabinet)
        self.amp_block.change_requested.connect(self._change_model)
        self.amp_block.bypass_toggled.connect(self._set_amp_bypass)
        rl.addWidget(self.amp_block)

        self.pedalboard = PedalboardView()
        self.pedalboard.param_changed.connect(self._set_param)
        self.pedalboard.enable_toggled.connect(self._set_enable)
        self.pedalboard.delete_requested.connect(self._delete_slot)
        self.pedalboard.change_requested.connect(self._change_model)
        self.pedalboard.reorder_requested.connect(self._reorder)
        rl.addWidget(self.pedalboard, 1)

        root.addWidget(right, 1)

        # Right: control assignment panel
        self.control_panel = ControlPanel(self.db)
        self.control_panel.setFixedWidth(290)
        self.control_panel.stomp_assigned.connect(self._assign_stomp)
        self.control_panel.expression_assigned.connect(self._assign_expression)
        self.control_panel.lfo_assigned.connect(self._assign_lfo)
        root.addWidget(self.control_panel)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Conectando...")
        self._build_menubar()

    def _build_title_bar(self):
        bar = _TitleBar()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 0, 18, 0)
        lay.setSpacing(12)

        # DigiTux logo
        logo_lbl = QLabel()
        logo_path = Path(__file__).parents[1] / "assets" / "img" / "menu" / "digitux_logo.png"
        if logo_path.exists():
            pm = QPixmap(str(logo_path))
            if not pm.isNull():
                logo_lbl.setPixmap(pm)
        lay.addWidget(logo_lbl)

        sep = QLabel("·")
        sep.setStyleSheet("color:#444; font-size:18px;")
        lay.addWidget(sep)

        self.preset_name = QLabel("—")
        self.preset_name.setStyleSheet("color:#fff; font-size:15px; font-weight:bold;")
        lay.addWidget(self.preset_name)
        lay.addStretch()

        # Preset Level
        from PyQt5.QtWidgets import QSlider
        lvl_lbl = QLabel("Level")
        lvl_lbl.setStyleSheet("color:#bbb; font-size:12px;")
        lay.addWidget(lvl_lbl)
        self.level_slider = QSlider(Qt.Horizontal)
        self.level_slider.setRange(0, 99)
        self.level_slider.setFixedWidth(120)
        self.level_slider.setStyleSheet(
            "QSlider::groove:horizontal{height:4px;background:#333;border-radius:2px;}"
            "QSlider::handle:horizontal{background:#ffb000;width:12px;margin:-4px 0;border-radius:6px;}"
        )
        self.level_slider.valueChanged.connect(self._set_preset_level)
        lay.addWidget(self.level_slider)
        self.level_value = QLabel("65")
        self.level_value.setStyleSheet("color:#ffb000; font-size:12px; font-weight:bold; min-width:24px;")
        lay.addWidget(self.level_value)

        for text, slot, kind in [
            ("Guardar", self._store, "save"),
            ("Recargar", self._reload, "reload"),
            ("+ Pedal", self._add_effect, "add"),
        ]:
            b = QPushButton(text)
            b.setFixedHeight(30)
            color = {"save": "#2d7d3d", "reload": "#2d5d7d", "add": "#8a6d2d"}[kind]
            b.setStyleSheet(
                f"QPushButton{{background:{color};color:#fff;border:none;border-radius:5px;"
                f"padding:0 14px;font-weight:bold;font-size:12px;}}"
                f"QPushButton:hover{{opacity:0.9;}}"
            )
            b.clicked.connect(slot)
            lay.addWidget(b)
        return bar

    def _build_browser(self):
        w = QWidget()
        w.setFixedWidth(300)
        w.setStyleSheet("background:#181818;border-right:1px solid #2a2a2a;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        title = QLabel("MIS TONOS")
        title.setStyleSheet("color:#ffb000; font-weight:bold; font-size:13px;")
        lay.addWidget(title)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar...")
        self.search.setStyleSheet(
            "QLineEdit{background:#222;border:1px solid #333;border-radius:4px;"
            "color:#ddd;padding:4px 8px;}"
        )
        self.search.textChanged.connect(self._filter)
        lay.addWidget(self.search)

        self.tabs = QTabBar()
        for t in ("User", "Factory", "Library"):
            self.tabs.addTab(t)
        self.tabs.currentChanged.connect(self._on_tab)
        lay.addWidget(self.tabs)

        self.list = QListWidget()
        self.list.setStyleSheet(
            "QListWidget{background:transparent;border:none;color:#ddd;}"
            "QListWidget::item{padding:7px;border-radius:4px;}"
            "QListWidget::item:selected{background:#ffb000;color:#111;}"
            "QListWidget::item:hover{background:#333;}"
        )
        self.list.itemDoubleClicked.connect(self._on_select)
        lay.addWidget(self.list, 1)

        self.library_presets = []
        return w

    def _apply_theme(self):
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(0x181818))
        pal.setColor(QPalette.WindowText, QColor(0xdddddd))
        pal.setColor(QPalette.Base, QColor(0x1a1a1a))
        pal.setColor(QPalette.Text, QColor(0xdddddd))
        pal.setColor(QPalette.Button, QColor(0x222222))
        pal.setColor(QPalette.ButtonText, QColor(0xdddddd))
        pal.setColor(QPalette.Highlight, QColor(0xffb000))
        pal.setColor(QPalette.HighlightedText, QColor(0x111111))
        app.setPalette(pal)
        app.setStyle("Fusion")

    # ------------------------------------------------------------- device
    def _connect(self):
        try:
            self.dev.connect()
            self.worker = Worker(self.dev)
            self.worker.notif.connect(self._on_notif)
            self.worker.start()
            self._refresh_names()
            self._reload()
        except Exception as e:
            self.status.showMessage(f"Offline: {e}", 6000)
            self._load_library()

    def _refresh_names(self):
        self.user_names = self.dev.user_preset_names()
        self.factory_names = self.dev.factory_preset_names()
        self._on_tab(self.tabs.currentIndex())

    def _load_library(self):
        path = Path(__file__).parents[2] / "data" / "nexus_factory_presets.json"
        if path.exists():
            self.library_presets = json.loads(path.read_text())
        self._on_tab(2)

    def _on_tab(self, i):
        self.list.clear()
        if i == 0:
            names = getattr(self, "user_names", [])
            for n, name in enumerate(names):
                self.list.addItem(f"{n+1:2d}. {name or '— vacío —'}")
        elif i == 1:
            names = getattr(self, "factory_names", [])
            for n, name in enumerate(names):
                self.list.addItem(f"{n+1:2d}. {name or '— vacío —'}")
        else:
            for p in self.library_presets:
                name = p.get("name") or "—"
                art = p.get("artist") or ""
                self.list.addItem(f"{name}  ·  {art}" if art else name)

    def _on_select(self, item):
        i = self.list.row(item)
        tab = self.tabs.currentIndex()
        try:
            if tab == 0:
                self.dev.load_user_preset(i)
            elif tab == 1:
                self.dev.load_factory_preset(i)
            else:
                if 0 <= i < len(self.library_presets):
                    from ..model import Preset
                    p = Preset.from_json(self.library_presets[i]["data"])
                    self.dev.send_preset(p)
            self._reload()
        except Exception as e:
            self.status.showMessage(f"Error: {e}", 5000)

    def _reload(self):
        try:
            p = self.dev.get_active_preset()
            self.preset = p
            self.preset_name.setText(p.name)
            self.level_slider.blockSignals(True)
            self.level_slider.setValue(p.prs_levl)
            self.level_value.setText(str(p.prs_levl))
            self.level_slider.blockSignals(False)
            # amp
            amp_slot = None
            for s in p.slots.values():
                if s.category == "amp":
                    amp_slot = s
                    break
            self.amp_block.set_amp_slot(amp_slot)
            self.pedalboard.rebuild(p.slots, self.db)
            self.control_panel.set_effect_slots(p.slots)
            self.status.showMessage(f"Preset: {p.name}")
        except Exception as e:
            self.status.showMessage(f"Error reload: {e}", 5000)

    def _filter(self, text):
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    # ------------------------------------------------------------- actions
    def _build_menubar(self):
        mb = self.menuBar()
        mb.setStyleSheet("QMenuBar{background:#121212;color:#ddd;} QMenuBar::item:selected{background:#2a2a2a;}")
        f = mb.addMenu("Archivo")
        f.addAction("Backup...", self._backup)
        f.addAction("Restore...", self._restore)
        f.addSeparator()
        f.addAction("Importar preset...", self._import_preset)
        f.addAction("Exportar preset...", self._export_preset)
        p = mb.addMenu("Preset")
        p.addAction("Store New...", self._store_new)
        p.addAction("Quick Store", self._quick_store)
        p.addAction("Copy", self._copy)

    def _change_model(self, slot):
        from .effect_picker import EffectPicker
        s = self.preset.slots.get(slot)
        if not s:
            return
        cat_map = {"wah": "Wah", "cmpr": "Compressor", "dist": "Distortion", "amp": "Amplifier",
                   "gate": "Gate", "mod": "Mod", "dly": "Delay", "rvb": "Reverb",
                   "eq": "EQ", "vol": "Other"}
        title = "Selección de amplificador" if s.category == "amp" else "Seleccionar efecto"
        picker = EffectPicker(self.db, current_category=cat_map.get(s.category), parent=self, title=title)
        if picker.exec_() and picker.result_effect:
            model = self.db.model_id(picker.result_effect["address"])
            if model:
                try:
                    self.dev.set_model(slot, model)
                    self._reload()
                except Exception as e:
                    self.status.showMessage(f"Error: {e}", 5000)

    # ------------------------------------------------------- controllers
    def _assign_stomp(self, ctrl, slot):
        try:
            if slot < 0:
                self.dev.clear_stomp(ctrl)
                self.status.showMessage(f"{ctrl} sin asignación")
            else:
                self.dev.assign_stomp(ctrl, slot)
                self.status.showMessage(f"{ctrl} → slot {slot+1}")
            self._reload()
        except Exception as e:
            self.status.showMessage(f"Error stomp: {e}", 5000)

    def _assign_expression(self, ctrl, slot, param, minv, maxv):
        try:
            s = self.preset.slots.get(slot)
            flat = s is not None and not getattr(s, "_use_fx_subdict", True)
            self.dev.assign_expression(ctrl, slot, param, minv, maxv, flat=flat)
            self.status.showMessage(f"{ctrl} → slot {slot+1} {param}")
            self._reload()
        except Exception as e:
            self.status.showMessage(f"Error expr: {e}", 5000)

    def _assign_lfo(self, slot, param, minv, maxv, speed, wave):
        try:
            s = self.preset.slots.get(slot)
            flat = s is not None and not getattr(s, "_use_fx_subdict", True)
            self.dev.assign_lfo(slot, param, minv, maxv, speed, wave, flat=flat)
            self.status.showMessage(f"LFO → slot {slot+1} {param}")
            self._reload()
        except Exception as e:
            self.status.showMessage(f"Error lfo: {e}", 5000)

    # ------------------------------------------------------ file operations
    def _backup(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Backup 99 presets", "rp360_backup.json", "JSON (*.json)")
        if not path:
            return
        try:
            presets = self.dev.export_user_bank()
            data = {"user": [p.to_json() if p else None for p in presets]}
            import json as _json
            Path(path).write_text(_json.dumps(data, indent=2))
            self.status.showMessage(f"Backup → {path}")
        except Exception as e:
            self.status.showMessage(f"Error backup: {e}", 5000)

    def _restore(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getOpenFileName(self, "Restaurar 99 presets", "", "JSON (*.json)")
        if not path:
            return
        if QMessageBox.question(self, "Restore",
                                "Los presets del dispositivo serán sobrescritos. ¿Continuar?") != QMessageBox.Yes:
            return
        try:
            import json as _json
            from ..model import Preset
            data = _json.loads(Path(path).read_text())
            presets = [Preset.from_json(d) if d else None for d in data["user"]]
            n = self.dev.restore_user_bank(presets)
            self.status.showMessage(f"Restaurados {n} presets")
        except Exception as e:
            self.status.showMessage(f"Error restore: {e}", 5000)

    def _import_preset(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Importar preset", "", "RP360 Preset (*.rp360p);;JSON (*.json)")
        if not path:
            return
        try:
            import json as _json
            from ..model import Preset
            d = _json.loads(Path(path).read_text())
            preset = Preset.from_json(d.get("preset", d))
            self.dev.send_preset(preset)
            self._reload()
            self.status.showMessage(f"Importado: {preset.name}")
        except Exception as e:
            self.status.showMessage(f"Error import: {e}", 5000)

    def _export_preset(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Exportar preset", f"{self.preset.name}.rp360p", "RP360 Preset (*.rp360p)")
        if not path:
            return
        try:
            import json as _json
            Path(path).write_text(_json.dumps({"preset": self.preset.to_json()}, indent=2))
            self.status.showMessage(f"Exportado → {path}")
        except Exception as e:
            self.status.showMessage(f"Error export: {e}", 5000)

    def _store_new(self):
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Store New", "Nombre del preset:", text=self.preset.name)
        if not ok:
            return
        idx, ok = QInputDialog.getInt(self, "Store New", "Slot (1-99):", 1, 1, 99)
        if not ok:
            return
        try:
            self.dev.save_and_rename(idx - 1, name)
            self._refresh_names()
            self.status.showMessage(f"Guardado en User {idx}")
        except Exception as e:
            self.status.showMessage(f"Error: {e}", 5000)

    def _quick_store(self):
        try:
            i = self.browser.list.currentRow()
            if self.tabs.currentIndex() != 0 or i < 0:
                self.status.showMessage("Selecciona un slot de User", 3000)
                return
            self.dev.save_to_user_slot(i)
            self.status.showMessage(f"Quick store en User {i+1}")
        except Exception as e:
            self.status.showMessage(f"Error: {e}", 5000)

    def _copy(self):
        import json as _json
        self._clipboard = _json.dumps({"preset": self.preset.to_json()})
        self.status.showMessage("Preset copiado al portapapeles interno")

    def _store(self):
        i = self.list.currentRow()
        if self.tabs.currentIndex() == 0 and i >= 0:
            try:
                self.dev.save_and_rename(i, self.preset.name)
                self.status.showMessage(f"Guardado en User {i+1}")
            except Exception as e:
                self.status.showMessage(f"Error: {e}", 5000)

    def _set_param(self, slot, param, value):
        try:
            flat = False
            s = self.preset.slots.get(slot)
            if s is not None and not getattr(s, "_use_fx_subdict", True):
                flat = True
            self.dev.set_param(slot, param, value, flat=flat)
        except Exception as e:
            self.status.showMessage(f"Error: {e}", 3000)

    def _set_enable(self, slot, enabled):
        try:
            self.dev.set_enable(slot, enabled)
            self._reload()
        except Exception as e:
            self.status.showMessage(f"Error: {e}", 3000)

    def _set_amp_bypass(self, slot, bypass):
        try:
            self.dev.set_enable(slot, not bypass)
            self._reload()
        except Exception as e:
            self.status.showMessage(f"Error bypass: {e}", 3000)

    def _set_preset_level(self, value):
        self.level_value.setText(str(value))
        try:
            self.dev.set_preset_level(value)
        except Exception as e:
            self.status.showMessage(f"Error level: {e}", 3000)

    def _set_cabinet(self, slot, cab_idx):
        try:
            self.dev.set_param(slot, "CABINET", cab_idx)
            self._reload()
        except Exception as e:
            self.status.showMessage(f"Error cabinet: {e}", 3000)

    def _delete_slot(self, slot):
        try:
            self.dev.delete_effect(slot)
            self._reload()
        except Exception as e:
            self.status.showMessage(f"Error: {e}", 3000)

    def _reorder(self, src, target):
        """Reorder the chain: move the effect at slot `src` to position `target`."""
        try:
            order = list(range(10))
            item = order.pop(src)
            order.insert(target, item)
            occupied = [i for i in order if i in self.preset.slots]
            self.dev.reorder_chain(occupied)
            self._reload()
        except Exception as e:
            self.status.showMessage(f"Error al reordenar: {e}", 5000)

    def _add_effect(self):
        from .effect_picker import EffectPicker
        from ..effects_db import SLOT_CATEGORY, natural_positions
        if not hasattr(self, "preset"):
            self.status.showMessage("No hay preset cargado", 5000)
            return
        # category already present -> cannot add another of that category
        prefix_to_cat = {"wah": "Wah", "cmpr": "Compressor", "dist": "Distortion",
                         "amp": "Amplifier", "eq": "EQ", "gate": "Gate",
                         "vol": "Other", "mod": "Mod", "dly": "Delay", "rvb": "Reverb"}
        used_categories = {prefix_to_cat.get(s.category, s.category)
                           for s in self.preset.slots.values()}
        allowed = [c for c in SLOT_CATEGORY.values() if c not in used_categories]
        if not allowed:
            self.status.showMessage("Cadena completa: todas las categorías están en uso", 5000)
            return
        picker = EffectPicker(self.db, parent=self, allowed_categories=allowed)
        if not (picker.exec_() and picker.result_effect):
            return
        effect = picker.result_effect
        # place at natural (or flexible) position that is still free
        target = None
        for idx in natural_positions(effect["category"]):
            if idx not in self.preset.slots:
                target = idx
                break
        if target is None:
            target = next((i for i in range(10) if i not in self.preset.slots), None)
        if target is None:
            self.status.showMessage("No hay posición libre en la cadena", 5000)
            return
        try:
            slot_data = self.db.build_slot_data(effect["address"])
            self.dev.add_effect(target, slot_data)
            self._reload()
        except Exception as e:
            self.status.showMessage(f"Error: {e}", 5000)

    def _on_notif(self, msg):
        if msg and msg[0] == "np" and len(msg) >= 4:
            path, val = msg[2], msg[3]
            self.status.showMessage(f"Live: {path} = {val}", 1500)
            if "/fxc/" in path:
                self._reload()

    def closeEvent(self, e):
        try:
            self.dev.disconnect()
        except Exception:
            pass
        e.accept()