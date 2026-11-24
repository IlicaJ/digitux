import unittest
from unittest.mock import Mock

from nexus.device import Device
from nexus.effects_db import EffectsDB
from nexus.model import Preset


class PresetResetTests(unittest.TestCase):
    def test_reset_template_uses_first_amp_and_cabinet(self):
        db = EffectsDB()
        preset = db.build_reset_preset("Mi preset")
        self.assertEqual(preset.name, "Mi preset")
        self.assertEqual(preset.prs_levl, 75)
        self.assertEqual(list(preset.slots), [3])
        amp = preset.slots[3]
        definition = db.by_category("Amplifier")[0]
        self.assertEqual(amp.model, db.model_id(definition["address"]))
        self.assertTrue(amp.enable)
        self.assertEqual(amp.params["CABINET"], db.cabinet_at(0)["id"])
        for param in definition["params"]:
            if param["address"] != "ENABLE":
                self.assertEqual(amp.params[param["address"]], param["default"])
        self.assertEqual(set(preset.ctrls), set(Preset.CTRL_NAMES))
        self.assertTrue(all(not ctrl.lnk for ctrl in preset.ctrls.values()))
        self.assertEqual(Preset.from_json(preset.to_json()), preset)

    def test_write_only_targets_selected_user_slot(self):
        device = Device.__new__(Device)
        device._protocol = Mock()
        preset = EffectsDB().build_reset_preset("Mi preset")
        device.write_user_preset(98, preset)
        device._protocol.send_command.assert_called_once_with(
            "ssc", path="banks/user", value={"98": preset.to_json()}, timeout=15.0
        )
        for index in (-1, 99):
            with self.assertRaises(ValueError):
                device.write_user_preset(index, preset)
        self.assertEqual(device._protocol.send_command.call_count, 1)

    def test_restore_skips_empty_entries_and_keeps_indices(self):
        device = Device.__new__(Device)
        device._protocol = Mock()
        preset = EffectsDB().build_reset_preset("Mi preset")
        self.assertEqual(device.restore_user_bank([None, preset]), 1)
        device._protocol.send_command.assert_called_once_with(
            "ssc", path="banks/user", value={"1": preset.to_json()}, timeout=15.0
        )


if __name__ == "__main__":
    unittest.main()
