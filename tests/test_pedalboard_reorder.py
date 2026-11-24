import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QApplication

from nexus.effects_db import EffectsDB
from nexus.model import FxSlot, Preset
from nexus.ui.main_window import MainWindow
from nexus.ui.pedalboard_view import MIME, PedalboardView, reordered_slots


class PedalboardReorderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.board = PedalboardView()
        self.board.resize(800, 360)
        self.board.show()
        self.db = EffectsDB()

    def tearDown(self):
        self.board.close()

    def rebuild(self, indices):
        slots = {i: FxSlot(i, "amp.57 CHAMP" if i == 3 else "dist.SCREAMER")
                 for i in indices}
        self.board.rebuild(slots, self.db)
        self.app.processEvents()

    def drop_event(self, source, target):
        mime = QMimeData()
        mime.setData(MIME, str(source).encode())
        widget = self.board._slot_widgets[target]
        center = widget.mapTo(self.board.container, widget.rect().center())
        event = Mock()
        event.mimeData.return_value = mime
        event.pos.return_value = self.board.container.mapTo(self.board.viewport(), center)
        return event

    def test_single_amplifier_cannot_start_drag(self):
        self.rebuild([3])
        with patch("nexus.ui.pedalboard_view.QDrag") as drag:
            self.board._start_drag(3, self.board._slot_widgets[3])
        drag.assert_not_called()
        event = self.drop_event(3, 5)
        self.board.dropEvent(event)
        self.assertIsNone(self.board._pending_reorder)

    def test_drop_on_empty_position_without_order_change_is_noop(self):
        self.rebuild([3, 7])
        event = self.drop_event(3, 5)
        self.board.dropEvent(event)
        event.acceptProposedAction.assert_called_once()
        self.assertIsNone(self.board._pending_reorder)

    def test_reorder_emits_after_drag_returns(self):
        self.rebuild([3, 7])
        scrollbar = self.board.horizontalScrollBar()
        self.assertGreater(scrollbar.maximum(), 0)
        scrollbar.setValue(scrollbar.maximum())
        self.app.processEvents()
        received = []
        self.board.reorder_requested.connect(lambda src, target: received.append((src, target)))
        event = self.drop_event(3, 8)
        drag = Mock()

        def finish_drag(_):
            self.board.dropEvent(event)
            self.assertEqual(received, [])

        drag.exec_.side_effect = finish_drag
        with patch("nexus.ui.pedalboard_view.QDrag", return_value=drag):
            self.board._start_drag(3, self.board._slot_widgets[3])
        self.assertEqual(received, [])
        self.app.processEvents()
        self.assertEqual(received, [(3, 8)])
        self.assertEqual(reordered_slots({3, 7}, 3, 8), [7, 3])

    def test_main_window_does_not_send_noop_order(self):
        window = Mock()
        window.preset = Preset(slots={3: FxSlot(3, "amp.57 CHAMP")})
        MainWindow._reorder(window, 3, 8)
        window.dev.reorder_chain.assert_not_called()
        window._reload.assert_not_called()

    def test_invalid_source_is_rejected(self):
        self.rebuild([3, 7])
        event = self.drop_event(2, 8)
        self.board.dropEvent(event)
        event.ignore.assert_called_once()
        self.assertIsNone(self.board._pending_reorder)


if __name__ == "__main__":
    unittest.main()
