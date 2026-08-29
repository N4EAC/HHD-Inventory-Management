import sqlite3
import unittest

import hhd_inventory_manager as app


class InCenterCompatibilityTests(unittest.TestCase):
    def make_legacy_database(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.executescript(
            """
            CREATE TABLE settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                item_name TEXT NOT NULL,
                baseline_units REAL NOT NULL DEFAULT 0,
                baseline_date TEXT NOT NULL DEFAULT '',
                min_threshold REAL NOT NULL DEFAULT 0,
                low_threshold REAL NOT NULL DEFAULT 0,
                units_per_session REAL NOT NULL DEFAULT 0,
                units_per_week REAL NOT NULL DEFAULT 0,
                reusable_sessions REAL NOT NULL DEFAULT 1,
                lifespan_days INTEGER NOT NULL DEFAULT 0,
                auto_session_usage INTEGER NOT NULL DEFAULT 1,
                active INTEGER NOT NULL DEFAULT 1,
                UNIQUE(group_name, item_name)
            );
            CREATE TABLE received_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                received_date TEXT NOT NULL,
                units REAL NOT NULL,
                notes TEXT
            );
            CREATE TABLE session_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_date TEXT NOT NULL,
                session_type TEXT NOT NULL,
                session_equivalent REAL NOT NULL DEFAULT 1,
                notes TEXT
            );
            CREATE TABLE session_item_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                units_used REAL NOT NULL
            );
            CREATE TABLE corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                correction_date TEXT NOT NULL,
                units_delta REAL NOT NULL,
                notes TEXT
            );

            INSERT INTO settings(key, value)
            VALUES('created_date', '2026-01-01');
            INSERT INTO items(
                group_name, item_name, baseline_units, baseline_date,
                units_per_session, reusable_sessions
            ) VALUES('NxStage', 'Legacy Cartridge', 10, '2026-01-01', 1, 1);
            INSERT INTO session_log(
                session_date, session_type, session_equivalent, notes
            ) VALUES('2026-01-02', 'Regular Treatment', 1, 'legacy record');
            """
        )
        connection.commit()

        database = app.InventoryDB.__new__(app.InventoryDB)
        database.conn = connection
        return database

    def test_legacy_database_migrates_and_keeps_existing_data(self):
        database = self.make_legacy_database()
        try:
            database.init_db()

            legacy = database.conn.execute(
                "SELECT * FROM session_log WHERE notes='legacy record'"
            ).fetchone()
            self.assertIsNotNone(legacy)
            self.assertEqual("", legacy["pak_lot"])

            item_columns = {
                row["name"]
                for row in database.conn.execute("PRAGMA table_info(items)")
            }
            self.assertIn("baseline_session_cutoff_id", item_columns)
            self.assertIn("full_attempt_usage", item_columns)
        finally:
            database.conn.close()

    def test_in_center_treatment_never_deducts_inventory(self):
        database = self.make_legacy_database()
        try:
            database.init_db()
            item = database.conn.execute(
                "SELECT * FROM items WHERE item_name='Legacy Cartridge'"
            ).fetchone()
            before = database.current_count(item)[0]

            session_id = database.add_session(
                "2026-01-03",
                "In Center Treatment",
                1,
                "clinic treatment",
            )
            session = database.session_by_id(session_id)

            self.assertEqual(0, session["session_equivalent"])
            self.assertEqual(0, database.item_usage_for_session(item, session))
            self.assertEqual(
                before,
                database.current_count(database.item_by_id(item["id"]))[0],
            )
        finally:
            database.conn.close()

    def test_schedule_changes_forecast_not_inventory_count(self):
        database = self.make_legacy_database()
        try:
            database.init_db()
            item = database.conn.execute(
                "SELECT * FROM items WHERE item_name='Legacy Cartridge'"
            ).fetchone()
            current_before = database.current_count(item)[0]

            database.set_setting("sessions_per_week", 4)
            four_session_forecast = database.weeks_remaining(
                item,
                current_before,
            )
            database.set_setting("sessions_per_week", 5)
            five_session_forecast = database.weeks_remaining(
                item,
                current_before,
            )

            self.assertEqual(
                current_before,
                database.current_count(item)[0],
            )
            self.assertLess(five_session_forecast, four_session_forecast)
        finally:
            database.conn.close()


if __name__ == "__main__":
    unittest.main()
