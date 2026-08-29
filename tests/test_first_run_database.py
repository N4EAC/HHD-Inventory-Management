import os
import tempfile
import unittest
from unittest import mock

import hhd_inventory_manager as app


class FirstRunDatabaseTests(unittest.TestCase):
    def open_database(self, database_path, legacy_path):
        patches = [
            mock.patch("hhd_inventory_manager.db_path", return_value=database_path),
            mock.patch(
                "hhd_inventory_manager.legacy_db_path",
                return_value=legacy_path,
            ),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        return app.InventoryDB()

    def test_new_database_has_no_seeded_inventory_and_setup_is_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "new.db")
            legacy_path = os.path.join(directory, "missing-legacy.db")
            database = self.open_database(database_path, legacy_path)
            try:
                self.assertTrue(database.is_new_database)
                self.assertEqual([], list(database.items()))
                self.assertEqual(
                    "0",
                    database.get_setting("first_run_setup_complete"),
                )
            finally:
                database.close()

    def test_interrupted_setup_remains_pending_on_next_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "new.db")
            legacy_path = os.path.join(directory, "missing-legacy.db")
            database = self.open_database(database_path, legacy_path)
            database.close()

            reopened = app.InventoryDB()
            try:
                self.assertFalse(reopened.is_new_database)
                self.assertEqual(
                    "0",
                    reopened.get_setting("first_run_setup_complete"),
                )
                self.assertEqual([], list(reopened.items()))
            finally:
                reopened.close()

    def test_existing_database_is_treated_as_upgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "existing.db")
            legacy_path = os.path.join(directory, "missing-legacy.db")
            open(database_path, "wb").close()

            database = self.open_database(database_path, legacy_path)
            try:
                self.assertFalse(database.is_new_database)
                self.assertEqual(
                    "1",
                    database.get_setting("first_run_setup_complete"),
                )
            finally:
                database.close()

    def test_weekly_schedule_validation(self):
        self.assertEqual(4, app.validate_sessions_per_week("4"))
        for invalid in ("", "four", "2.5", "0", "15"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    app.validate_sessions_per_week(invalid)


if __name__ == "__main__":
    unittest.main()
