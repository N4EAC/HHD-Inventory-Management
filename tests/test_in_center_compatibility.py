import sqlite3
import unittest
from datetime import datetime

import hhd_inventory_manager as app


class InCenterCompatibilityTests(unittest.TestCase):
    def test_sak_hours_remaining_accepts_up_to_89(self):
        self.assertEqual(89, app.validate_sak_hours_remaining("89"))
        with self.assertRaisesRegex(ValueError, "1 to 89"):
            app.validate_sak_hours_remaining("90")

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
            self.assertIn("inventory_type", item_columns)
            session_columns = {
                row["name"]
                for row in database.conn.execute("PRAGMA table_info(session_log)")
            }
            self.assertIn("warmer_line_lot", session_columns)
            self.assertIn("hanging_bags_used", session_columns)
            self.assertIn("treatment_time", session_columns)
            self.assertIn("sak_hours_remaining", session_columns)
            self.assertIn("sak_timer_started_at", session_columns)
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

    def test_legacy_supply_names_receive_stable_inventory_types(self):
        database = self.make_legacy_database()
        try:
            database.conn.executemany(
                """INSERT INTO items(
                       group_name, item_name, baseline_units, baseline_date
                   ) VALUES(?,?,?,?)""",
                [
                    (app.GROUP_NX, "SAK", 3, "2026-01-01"),
                    (
                        app.GROUP_NX,
                        "Dialysate Hanging Bags (Emergency Bags)",
                        12,
                        "2026-01-01",
                    ),
                    (app.GROUP_NX, "Warmer Lines", 4, "2026-01-01"),
                ],
            )
            database.conn.commit()
            database.init_db()

            classifications = {
                row["item_name"]: row["inventory_type"]
                for row in database.items()
            }
            self.assertEqual(
                app.INVENTORY_TYPE_SAK,
                classifications["SAK"],
            )
            self.assertEqual(
                app.INVENTORY_TYPE_HANGING_BAGS,
                classifications[
                    "Dialysate Hanging Bags (Emergency Bags)"
                ],
            )
            self.assertEqual(
                app.INVENTORY_TYPE_WARMER_LINES,
                classifications["Warmer Lines"],
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

    def test_complete_treatment_uses_selected_supply_path(self):
        database = self.make_legacy_database()
        try:
            database.init_db()
            database.add_item(
                app.GROUP_NX,
                "SAK",
                baseline_units=10,
                baseline_date="2026-01-03",
                units_per_session=1,
                inventory_type=app.INVENTORY_TYPE_SAK,
            )
            database.add_item(
                app.GROUP_NX,
                "Emergency Hanging Bags",
                baseline_units=20,
                baseline_date="2026-01-03",
                auto_session_usage=0,
                inventory_type=app.INVENTORY_TYPE_HANGING_BAGS,
            )
            database.add_item(
                app.GROUP_NX,
                "Warmer Line Sets",
                baseline_units=10,
                baseline_date="2026-01-03",
                auto_session_usage=0,
                inventory_type=app.INVENTORY_TYPE_WARMER_LINES,
            )
            items = {
                row["inventory_type"]: row
                for row in database.items()
                if row["inventory_type"] != app.INVENTORY_TYPE_STANDARD
            }

            no_sak_session = database.add_session(
                "2026-01-03",
                "Regular Treatment",
                1,
                treatment_time="08:00",
            )
            no_sak = database.session_by_id(no_sak_session)
            self.assertEqual(
                0,
                database.item_usage_for_session(
                    items[app.INVENTORY_TYPE_SAK],
                    no_sak,
                ),
            )

            sak_session = database.add_session(
                "2026-01-04",
                "Regular Treatment",
                1,
                sak_lot="SAK-LOT-1",
                treatment_time="08:00",
            )
            sak_treatment = database.session_by_id(sak_session)
            self.assertEqual(
                0.5,
                database.item_usage_for_session(
                    items[app.INVENTORY_TYPE_SAK],
                    sak_treatment,
                ),
            )

            bags_session = database.add_session(
                "2026-01-05",
                "Regular Treatment",
                1,
                warmer_line_lot="WL-LOT-1",
                hanging_bags_used=6,
                treatment_time="08:00",
            )
            bags_treatment = database.session_by_id(bags_session)
            self.assertEqual(
                0,
                database.item_usage_for_session(
                    items[app.INVENTORY_TYPE_SAK],
                    bags_treatment,
                ),
            )
            self.assertEqual(
                6,
                database.item_usage_for_session(
                    items[app.INVENTORY_TYPE_HANGING_BAGS],
                    bags_treatment,
                ),
            )
            self.assertEqual(
                1,
                database.item_usage_for_session(
                    items[app.INVENTORY_TYPE_WARMER_LINES],
                    bags_treatment,
                ),
            )
            self.assertEqual(
                1.0,
                database.item_session_usage_units(
                    items[app.INVENTORY_TYPE_SAK],
                    "2026-01-03",
                    datetime(2026, 1, 5, 8, 0),
                ),
            )
            self.assertEqual(
                9,
                database.current_count(
                    database.item_by_id(items[app.INVENTORY_TYPE_SAK]["id"])
                )[0],
            )
            self.assertEqual(
                14,
                database.current_count(
                    database.item_by_id(
                        items[app.INVENTORY_TYPE_HANGING_BAGS]["id"]
                    )
                )[0],
            )
            self.assertEqual(
                9,
                database.current_count(
                    database.item_by_id(
                        items[app.INVENTORY_TYPE_WARMER_LINES]["id"]
                    )
                )[0],
            )
            with self.assertRaises(ValueError):
                database.add_session(
                    "2026-01-06",
                    "Regular Treatment",
                    1,
                    sak_lot="SAK-LOT-2",
                    hanging_bags_used=6,
                    treatment_time="08:00",
                )
        finally:
            database.conn.close()

    def test_only_one_active_item_can_have_each_special_type(self):
        database = self.make_legacy_database()
        try:
            database.init_db()
            database.add_item(
                app.GROUP_NX,
                "Hanging Bags One",
                inventory_type=app.INVENTORY_TYPE_HANGING_BAGS,
            )
            with self.assertRaises(ValueError):
                database.add_item(
                    app.GROUP_DV,
                    "Hanging Bags Two",
                    inventory_type=app.INVENTORY_TYPE_HANGING_BAGS,
                )
        finally:
            database.conn.close()

    def test_complete_treatment_adds_optional_extra_item_usage(self):
        database = self.make_legacy_database()
        try:
            database.init_db()
            database.add_item(
                app.GROUP_NX,
                "Extra-use supply",
                baseline_units=10,
                baseline_date="2026-01-03",
                units_per_session=1,
            )
            item = next(
                row
                for row in database.items()
                if row["item_name"] == "Extra-use supply"
            )
            item_id = item["id"]
            session_id = database.add_session(
                "2026-01-04",
                "Regular Treatment",
                1,
                treatment_time="08:00",
            )
            database.add_session_item_usage(session_id, item_id, 2.5)
            item = database.item_by_id(item_id)
            session = database.session_by_id(session_id)
            self.assertEqual(
                3.5,
                database.item_usage_for_session(item, session),
            )
            self.assertEqual(6.5, database.current_count(item)[0])

            database.delete_session(session_id)
            self.assertEqual(
                10.0,
                database.current_count(database.item_by_id(item_id))[0],
            )
        finally:
            database.conn.close()

    def test_complete_treatment_adds_extra_usage_to_sak_lifecycle(self):
        database = self.make_legacy_database()
        try:
            database.init_db()
            database.add_item(
                app.GROUP_NX,
                "SAK",
                baseline_units=5,
                baseline_date="2026-02-01",
                inventory_type=app.INVENTORY_TYPE_SAK,
            )
            item = database.item_by_inventory_type(app.INVENTORY_TYPE_SAK)
            session_id = database.add_session(
                "2026-02-02",
                "Regular Treatment",
                1,
                treatment_time="08:00",
                sak_lot="SAK-EXTRA",
                sak_hours_remaining=80,
            )
            database.add_session_item_usage(session_id, item["id"], 0.5)
            self.assertEqual(
                1.0,
                database.item_session_usage_units(
                    item,
                    "2026-02-01",
                    datetime(2026, 2, 2, 8, 1),
                ),
            )
        finally:
            database.conn.close()

    def test_sak_remainder_expires_after_user_entered_hours(self):
        database = self.make_legacy_database()
        try:
            database.init_db()
            database.add_item(
                app.GROUP_NX,
                "SAK",
                baseline_units=5,
                baseline_date="2026-02-01",
                inventory_type=app.INVENTORY_TYPE_SAK,
            )
            item = database.item_by_inventory_type(app.INVENTORY_TYPE_SAK)
            first_id = database.add_session(
                "2026-02-01",
                "Regular Treatment",
                1,
                treatment_time="08:00",
                sak_lot="LOT-A",
                sak_hours_remaining=10,
            )
            self.assertEqual(
                10,
                database.session_by_id(first_id)["sak_hours_remaining"],
            )
            self.assertEqual(
                0.5,
                database.item_session_usage_units(
                    item,
                    "2026-02-01",
                    datetime(2026, 2, 1, 17, 59),
                ),
            )
            self.assertEqual(
                1.0,
                database.item_session_usage_units(
                    item,
                    "2026-02-01",
                    datetime(2026, 2, 1, 18, 0),
                ),
            )
            replacement_id = database.add_session(
                "2026-02-01",
                "Regular Treatment",
                1,
                treatment_time="19:00",
                sak_lot="LOT-B",
                sak_hours_remaining=80,
            )
            self.assertEqual(
                80,
                database.session_by_id(replacement_id)["sak_hours_remaining"],
            )
            self.assertEqual(
                1.5,
                database.item_session_usage_units(
                    item,
                    "2026-02-01",
                    datetime(2026, 2, 1, 19, 0),
                ),
            )
        finally:
            database.conn.close()

    def test_second_sak_treatment_consumes_remaining_half(self):
        database = self.make_legacy_database()
        try:
            database.init_db()
            database.add_item(
                app.GROUP_NX,
                "SAK",
                baseline_units=5,
                baseline_date="2026-02-01",
                inventory_type=app.INVENTORY_TYPE_SAK,
            )
            database.add_item(
                app.GROUP_NX,
                "Hanging Bags",
                baseline_units=20,
                baseline_date="2026-02-01",
                inventory_type=app.INVENTORY_TYPE_HANGING_BAGS,
            )
            database.add_item(
                app.GROUP_NX,
                "Warmer Lines",
                baseline_units=10,
                baseline_date="2026-02-01",
                inventory_type=app.INVENTORY_TYPE_WARMER_LINES,
            )
            item = database.item_by_inventory_type(app.INVENTORY_TYPE_SAK)
            database.add_session(
                "2026-02-01",
                "Regular Treatment",
                1,
                treatment_time="08:00",
                sak_lot="LOT-A",
                sak_hours_remaining=30,
            )
            database.snapshot_item_to_current(
                item["id"],
                "2026-02-01",
                current_value=4.5,
            )
            second_id = database.add_session(
                "2026-02-02",
                "Regular Treatment",
                1,
                treatment_time="08:00",
                sak_lot="LOT-A",
                sak_hours_remaining=30,
            )
            self.assertEqual(
                6,
                database.session_by_id(second_id)["sak_hours_remaining"],
            )
            self.assertEqual(
                1.0,
                database.item_session_usage_units(
                    item,
                    "2026-02-01",
                    datetime(2026, 2, 2, 8, 0),
                ),
            )
            self.assertEqual(
                4.0,
                database.current_count(database.item_by_id(item["id"]))[0],
            )
            with self.assertRaises(ValueError):
                database.add_session(
                    "2026-02-03",
                    "Regular Treatment",
                    1,
                    treatment_time="08:00",
                    hanging_bags_used=6,
                )
            database.add_session(
                "2026-02-03",
                "Regular Treatment",
                1,
                treatment_time="08:00",
                hanging_bags_used=6,
                warmer_line_lot="WL-LOT-1",
            )
            self.assertEqual(
                1.0,
                database.item_session_usage_units(
                    item,
                    "2026-02-01",
                    datetime(2026, 2, 3, 8, 0),
                ),
            )
        finally:
            database.conn.close()

    def test_second_sak_treatment_stores_calculated_clock_hours_left(self):
        database = self.make_legacy_database()
        try:
            database.init_db()
            database.add_item(
                app.GROUP_NX,
                "SAK",
                baseline_units=5,
                baseline_date="2026-09-01",
                inventory_type=app.INVENTORY_TYPE_SAK,
            )
            item = database.item_by_inventory_type(app.INVENTORY_TYPE_SAK)
            database.add_session(
                "2026-09-01",
                "Regular Treatment",
                1,
                treatment_time="08:00",
                sak_lot="LOT-87",
                sak_hours_remaining=87,
                sak_timer_started_at="2026-09-01T12:00:00",
            )
            active_sak = database.active_sak_at(datetime(2026, 9, 4, 12, 0))
            self.assertEqual("LOT-87", active_sak["lot"])
            self.assertEqual(
                15,
                app.active_sak_hours_left(
                    active_sak,
                    datetime(2026, 9, 4, 12, 0),
                ),
            )
            second_id = database.add_session(
                "2026-09-04",
                "Regular Treatment",
                1,
                treatment_time="12:00",
                sak_lot="LOT-87",
                sak_hours_remaining=87,
            )
            self.assertEqual(
                15,
                database.session_by_id(second_id)["sak_hours_remaining"],
            )
            self.assertEqual(
                1.0,
                database.item_session_usage_units(
                    item,
                    "2026-09-01",
                    datetime(2026, 9, 4, 12, 0),
                ),
            )
            self.assertIsNone(
                database.active_sak_at(datetime(2026, 9, 4, 12, 1))
            )
        finally:
            database.conn.close()

    def test_deleting_sak_treatment_restores_previous_timer_state(self):
        database = self.make_legacy_database()
        try:
            database.init_db()
            database.add_item(
                app.GROUP_NX,
                "SAK",
                baseline_units=5,
                baseline_date="2026-09-01",
                inventory_type=app.INVENTORY_TYPE_SAK,
            )
            first_id = database.add_session(
                "2026-09-01",
                "Regular Treatment",
                1,
                treatment_time="08:00",
                sak_lot="LOT-DELETE",
                sak_hours_remaining=87,
                sak_timer_started_at="2026-09-01T12:00:00",
            )
            second_id = database.add_session(
                "2026-09-04",
                "Regular Treatment",
                1,
                treatment_time="12:00",
                sak_lot="LOT-DELETE",
            )
            self.assertIsNone(
                database.active_sak_at(datetime(2026, 9, 4, 12, 1))
            )

            database.delete_session(second_id)
            restored = database.active_sak_at(datetime(2026, 9, 4, 12, 1))
            self.assertEqual("LOT-DELETE", restored["lot"])
            self.assertEqual(
                15,
                app.active_sak_hours_left(
                    restored,
                    datetime(2026, 9, 4, 12, 1),
                ),
            )

            database.delete_session(first_id)
            self.assertIsNone(
                database.active_sak_at(datetime(2026, 9, 4, 12, 1))
            )
        finally:
            database.conn.close()


if __name__ == "__main__":
    unittest.main()
