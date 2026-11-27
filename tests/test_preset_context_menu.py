import json
import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QApplication, QInputDialog, QMenu, QMessageBox

from nexus.model import Preset
from nexus.ui.main_window import MainWindow


class PresetContextMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        with patch("nexus.ui.main_window.Device"), patch("nexus.ui.main_window.QTimer.singleShot"):
            self.window = MainWindow()
        self.window.user_names = ["First", "Second", None]
        self.window.factory_names = ["Factory"]
        self.window.dev.get_user_preset.side_effect = lambda index: Preset(name=self.window.user_names[index])
        self.window._on_tab(0)
        self.window.list.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()

    def open_menu(self, row, action):
        item = self.window.list.item(row)
        pos = self.window.list.visualItemRect(item).center()

        def execute(menu, _):
            actions = {entry.text(): entry for entry in menu.actions()}
            self.assertEqual(set(actions), {"Copy", "Delete..."})
            actions[action].trigger()

        with patch.object(QMenu, "exec_", execute):
            self.window._preset_context_menu(pos)

    def test_copy_reads_clicked_saved_preset_not_edit_buffer(self):
        preset = Mock()
        preset.to_json.return_value = {"name": "Second"}
        self.window.dev.get_user_preset.side_effect = None
        self.window.dev.get_user_preset.return_value = preset
        self.window.list.setCurrentRow(0)
        self.open_menu(1, "Copy")
        self.window.dev.get_user_preset.assert_called_once_with(1)
        self.assertEqual(json.loads(self.window._clipboard), {"preset": {"name": "Second"}})
        self.assertEqual(self.window.list.currentRow(), 1)

    def test_delete_requires_confirmation_and_targets_clicked_slot(self):
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            self.open_menu(1, "Delete...")
        self.window.dev.write_user_preset.assert_not_called()

        replacement = self.window.db.build_reset_preset("Preset 2")
        self.window.dev.get_user_preset.side_effect = [replacement]
        self.window.dev.user_preset_names.return_value = ["First", "Preset 2", None]
        self.window.dev.factory_preset_names.return_value = ["Factory"]
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes) as confirm:
            self.open_menu(1, "Delete...")
        self.window.dev.write_user_preset.assert_called_once_with(1, replacement)
        self.assertIn('User 2 ("Second")', confirm.call_args.args[2])
        self.assertIn("Preset 2", confirm.call_args.args[2])
        self.assertIn("no quedará vacía", confirm.call_args.args[2])
        self.assertEqual(self.window.user_names[1], "Preset 2")
        self.assertIn("restablecido", self.window.status.currentMessage())

    def test_empty_slots_and_other_tabs_have_no_menu(self):
        with patch.object(QMenu, "exec_") as execute:
            item = self.window.list.item(2)
            self.window._preset_context_menu(self.window.list.visualItemRect(item).center())
            self.window.tabs.setCurrentIndex(1)
            item = self.window.list.item(0)
            self.window._preset_context_menu(self.window.list.visualItemRect(item).center())
        execute.assert_not_called()

    def test_menu_delete_defaults_to_selected_user_slot(self):
        self.window.list.setCurrentRow(1)
        with patch.object(QInputDialog, "getInt", return_value=(2, False)) as dialog:
            self.window._delete_user_preset()
        self.assertEqual(dialog.call_args.args[3], 2)
        self.window.dev.write_user_preset.assert_not_called()

    def test_delete_reports_when_saved_preset_does_not_match(self):
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            self.open_menu(1, "Delete...")
        self.assertIn("error al verificar", self.window.status.currentMessage())

    def test_device_errors_are_reported(self):
        self.window.dev.get_user_preset.side_effect = RuntimeError("read failed")
        self.open_menu(1, "Copy")
        self.assertIn("read failed", self.window.status.currentMessage())

        self.window.dev.get_user_preset.side_effect = None
        self.window.dev.get_user_preset.return_value = Preset(name="Second")
        self.window.dev.write_user_preset.side_effect = RuntimeError("write failed")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            self.open_menu(1, "Delete...")
        self.assertIn("write failed", self.window.status.currentMessage())
        self.window.dev.user_preset_names.assert_not_called()

    def test_delete_reports_refresh_error_after_command(self):
        replacement = self.window.db.build_reset_preset("Preset 2")
        self.window.dev.get_user_preset.side_effect = [replacement]
        self.window.dev.user_preset_names.side_effect = RuntimeError("refresh failed")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            self.open_menu(1, "Delete...")
        self.window.dev.write_user_preset.assert_called_once_with(1, replacement)
        self.assertIn("restablecido", self.window.status.currentMessage())
        self.assertIn("refresh failed", self.window.status.currentMessage())

    def test_reset_name_uses_one_based_slot_index(self):
        for index in (0, 98):
            with self.subTest(index=index):
                replacement = self.window.db.build_reset_preset(f"Preset {index + 1}")
                self.window.dev.reset_mock()
                self.window.dev.get_user_preset.side_effect = None
                self.window.dev.get_user_preset.return_value = replacement
                self.window.dev.user_preset_names.side_effect = None
                self.window.dev.user_preset_names.return_value = ["Preset"] * 99
                self.window.dev.factory_preset_names.return_value = ["Factory"]
                with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes) as confirm:
                    self.window._delete_user_preset_at(index)
                self.window.dev.write_user_preset.assert_called_once_with(index, replacement)
                self.assertIn(f"Preset {index + 1}", confirm.call_args.args[2])
                self.assertIn("restablecido", self.window.status.currentMessage())


if __name__ == "__main__":
    unittest.main()
