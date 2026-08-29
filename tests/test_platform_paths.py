import os
import unittest
from unittest import mock

import hhd_inventory_manager as app


class PlatformPathTests(unittest.TestCase):
    @mock.patch("hhd_inventory_manager.os.makedirs")
    @mock.patch("hhd_inventory_manager.os.path.expanduser", return_value="/Users/test")
    def test_macos_uses_application_support(self, _expanduser, _makedirs):
        with mock.patch.object(app.os, "name", "posix"), mock.patch.object(
            app.sys,
            "platform",
            "darwin",
        ):
            self.assertEqual(
                "/Users/test/Library/Application Support/HHD Inventory Manager",
                app.user_data_dir(),
            )

    @mock.patch("hhd_inventory_manager.os.makedirs")
    @mock.patch("hhd_inventory_manager.os.path.expanduser", return_value="/home/test")
    def test_linux_uses_xdg_data_home(self, _expanduser, _makedirs):
        with mock.patch.object(app.os, "name", "posix"), mock.patch.object(
            app.sys,
            "platform",
            "linux",
        ), mock.patch.dict(
            os.environ,
            {"XDG_DATA_HOME": "/tmp/xdg-data"},
        ):
            self.assertEqual(
                "/tmp/xdg-data/HHD Inventory Manager",
                app.user_data_dir(),
            )


if __name__ == "__main__":
    unittest.main()
