import pathlib
import unittest

import hhd_inventory_manager as app


ROOT = pathlib.Path(__file__).resolve().parents[1]


class BuildScriptTests(unittest.TestCase):
    def test_platform_build_versions_match_application(self):
        expected = app.APP_VERSION
        self.assertIn(
            f'APP_VERSION="{expected}"',
            (ROOT / "build_macos.sh").read_text(encoding="utf-8"),
        )
        self.assertIn(
            f'APP_VERSION="{expected}"',
            (ROOT / "build.linux.sh").read_text(encoding="utf-8"),
        )
        self.assertIn(
            f'APP_VERSION={expected}',
            (ROOT / "build_exe.bat").read_text(encoding="utf-8"),
        )

    def test_windows_pyinstaller_assets_use_project_root(self):
        script = (ROOT / "build_exe.bat").read_text(encoding="utf-8")
        for filename in (
            "hhd_inventory_manager.ico",
            "hhd_inventory_manager.png",
            "hhd_inventory_manager_about.png",
            "hhd_menu_icon.png",
        ):
            self.assertIn(f'%PROJECT_ROOT%\\{filename};.', script)
        self.assertIn(
            '"%PROJECT_ROOT%\\hhd_inventory_manager.py"',
            script,
        )


if __name__ == "__main__":
    unittest.main()
