
#!/usr/bin/env python3
"""
HHD Inventory Manager v1.0.0

Changes in v0.1.1:
- Rename inventory items
- Add new inventory items to NxStage or DaVita
- Deactivate/remove inventory items
- Keeps historical received/session/correction records safe because items are deactivated, not physically deleted
"""

import os
import sqlite3
import csv
import ctypes
import ctypes.wintypes
import json
import shutil
import math
from datetime import datetime, date, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_NAME = "HHD Inventory Manager"
APP_VERSION = "1.0.10"
DB_NAME = "hhd_inventory.db"
SETTINGS_FILE = "hhd_inventory_settings.json"
APP_FOLDER_NAME = "HHD Inventory Manager"
BACKUP_FOLDER_NAME = "HHD Inventory Backups"
ROLLING_DB_BACKUP_NAME = "HHD_Inventory_Backup_Current.db"
ROLLING_SETTINGS_BACKUP_NAME = "HHD_Settings_Backup_Current.json"
AUTO_BACKUP_INTERVAL_MS = 10 * 60 * 1000


BLUE_BG = "#062A44"
BLUE_PANEL = "#083B5E"
BLUE_PANEL_2 = "#0B456E"
BLUE_HEADER = "#0A5F92"
CYAN = "#5ED8FF"
TEXT = "#EAF8FF"
MUTED = "#A9D6E8"
GREEN = "#59D65C"
YELLOW = "#FFD52E"
RED = "#FF5A4E"
BORDER = "#2A8CC4"
INPUT_BG = "#0D304D"
BUTTON_BG = "#0D5D8C"
BUTTON_HOVER = "#1479B5"

GROUP_NX = "NxStage Supplies"
GROUP_DV = "DaVita Supplies"

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("eduardo.hhd.inventorymanager")
except Exception:
    pass

DEFAULT_ITEMS = [
    (GROUP_NX, "SAK", 0, 4, 8, 1.0, 0.0, 2.0, 0, 1),
    (GROUP_NX, "PAK", 0, 1, 2, 0.0, 0.0, 1.0, 75, 0),
    (GROUP_NX, "Cartridge", 0, 8, 12, 1.0, 0.0, 1.0, 0, 1),
    (GROUP_NX, "Dialysate Hanging Bags (Emergency Bags)", 0, 24, 48, 6.0, 0.0, 1.0, 0, 0),
    (GROUP_NX, "Warmer Lines", 0, 4, 8, 1.0, 0.0, 1.0, 0, 0),

    (GROUP_DV, "Heparin", 0, 2, 4, 1.0, 0.0, 1.0, 0, 1),
    (GROUP_DV, "10CC Syringe", 0, 20, 40, 5.0, 0.0, 1.0, 0, 1),
    (GROUP_DV, "Medical Gloves", 0, 20, 40, 1.0, 0.0, 1.0, 0, 1),
    (GROUP_DV, "Syringe Needles", 0, 20, 40, 1.0, 0.0, 1.0, 0, 1),
    (GROUP_DV, "15 Gauge Tulip Needles (pair)", 0, 4, 8, 1.0, 0.0, 1.0, 0, 1),
    (GROUP_DV, "15 Gauge Tulip Needles (singles)", 0, 8, 16, 2.0, 0.0, 1.0, 0, 1),
    (GROUP_DV, "Alcohol Pads", 0, 32, 64, 4.0, 0.0, 1.0, 0, 1),
    (GROUP_DV, "Iodine Pads", 0, 16, 32, 2.0, 0.0, 1.0, 0, 1),
    (GROUP_DV, "Saline bags", 0, 4, 8, 1.0, 0.0, 1.0, 0, 1),
    (GROUP_DV, "Male-to-Male connector (Mr. Peanut)", 0, 4, 8, 1.0, 0.0, 1.0, 0, 1),
    (GROUP_DV, "2x2 gauze", 0, 20, 40, 2.0, 0.0, 1.0, 0, 1),
    (GROUP_DV, "4x4 gauze", 0, 20, 40, 2.0, 0.0, 1.0, 0, 1),
    (GROUP_DV, "Paper Towels", 0, 1, 2, 0.0, 1.0, 1.0, 0, 0),
    (GROUP_DV, "Chloramine Test Strips", 0, 8, 16, 1.0, 0.0, 1.0, 0, 1),
]

def app_dir():
    return os.path.dirname(os.path.abspath(__file__))

def user_data_dir():
    """Writable per-user application data folder.

    Program Files is not writable by normal users, so the live database and
    settings must live in AppData, not beside the installed EXE.
    """
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    path = os.path.join(base, APP_FOLDER_NAME)
    os.makedirs(path, exist_ok=True)
    return path

def db_path():
    return os.path.join(user_data_dir(), DB_NAME)

def legacy_db_path():
    return os.path.join(app_dir(), DB_NAME)

def icon_path():
    return os.path.join(app_dir(), "hhd_inventory_manager.ico")

def icon_png_path():
    return os.path.join(app_dir(), "hhd_inventory_manager.png")

def documents_dir():
    try:
        import ctypes.wintypes
        CSIDL_PERSONAL = 5
        SHGFP_TYPE_CURRENT = 0
        buf = ctypes.create_unicode_buffer(260)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
        if buf.value:
            return buf.value
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Documents")

def backup_dir():
    path = os.path.join(documents_dir(), BACKUP_FOLDER_NAME)
    os.makedirs(path, exist_ok=True)
    return path

def settings_file_path():
    return os.path.join(user_data_dir(), SETTINGS_FILE)

def timestamp_for_filename():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def safe_copy(src, dst):
    try:
        if os.path.exists(src):
            shutil.copy2(src, dst)
            return True
    except Exception:
        pass
    return False

def _rgb_to_colorref(hex_color):
    """Windows COLORREF is 0x00bbggrr, not 0x00rrggbb."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r | (g << 8) | (b << 16)

def request_windows_medical_blue_titlebar(hwnd):
    """
    Ask Windows 11 DWM to use the app's medical-blue title bar colors.

    This keeps the normal native Windows title bar, which preserves taskbar icon
    reliability, while requesting colors that match the GUI.
    """
    try:
        # Windows 11 DWM attributes.
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_CAPTION_COLOR = 35
        DWMWA_TEXT_COLOR = 36
        DWMWA_BORDER_COLOR = 34

        dark = ctypes.c_int(1)
        caption = ctypes.c_int(_rgb_to_colorref("#062A44"))
        text = ctypes.c_int(_rgb_to_colorref("#EAF8FF"))
        border = ctypes.c_int(_rgb_to_colorref("#2A8CC4"))

        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.wintypes.HWND(hwnd),
            ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE),
            ctypes.byref(dark),
            ctypes.sizeof(dark)
        )
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.wintypes.HWND(hwnd),
            ctypes.c_int(DWMWA_CAPTION_COLOR),
            ctypes.byref(caption),
            ctypes.sizeof(caption)
        )
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.wintypes.HWND(hwnd),
            ctypes.c_int(DWMWA_TEXT_COLOR),
            ctypes.byref(text),
            ctypes.sizeof(text)
        )
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.wintypes.HWND(hwnd),
            ctypes.c_int(DWMWA_BORDER_COLOR),
            ctypes.byref(border),
            ctypes.sizeof(border)
        )
    except Exception:
        # Older Windows/Tk builds may ignore custom caption color. Leave native title bar.
        pass



def iso_today():
    return date.today().isoformat()

def parse_date(value, fallback=None):
    if not value:
        return fallback or date.today()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except Exception:
            pass
    return fallback or date.today()

class InventoryDB:
    def __init__(self):
        self.migrate_legacy_database_if_needed()
        self.conn = sqlite3.connect(db_path())
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def migrate_legacy_database_if_needed(self):
        """Move/copy an older database from the app folder to AppData if needed."""
        try:
            new_path = db_path()
            old_path = legacy_db_path()
            if os.path.exists(old_path) and not os.path.exists(new_path):
                shutil.copy2(old_path, new_path)
        except Exception:
            pass

    def init_db(self):
        c = self.conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS items (
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
            full_attempt_usage INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            UNIQUE(group_name, item_name)
        );

        CREATE TABLE IF NOT EXISTS received_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            received_date TEXT NOT NULL,
            units REAL NOT NULL,
            notes TEXT,
            FOREIGN KEY(item_id) REFERENCES items(id)
        );

        CREATE TABLE IF NOT EXISTS session_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date TEXT NOT NULL,
            session_type TEXT NOT NULL,
            session_equivalent REAL NOT NULL DEFAULT 1,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            correction_date TEXT NOT NULL,
            units_delta REAL NOT NULL,
            notes TEXT,
            FOREIGN KEY(item_id) REFERENCES items(id)
        );
        """)

        # Database migration for v1.0.6. Items such as SAK can consume one
        # reusable-session slot for every attempted treatment, including an
        # incomplete treatment. Missed treatments never consume a slot.
        item_columns = {
            row["name"] for row in c.execute("PRAGMA table_info(items)").fetchall()
        }
        if "full_attempt_usage" not in item_columns:
            c.execute(
                "ALTER TABLE items ADD COLUMN full_attempt_usage INTEGER NOT NULL DEFAULT 0"
            )

        defaults = {
            "patient_name": "Patient Name",
            "sessions_per_week": "4",
            "first_session_day": "Sunday",
            "group_nx_display_name": "NxStage Supplies",
            "group_dv_display_name": "DaVita Supplies",
            "created_date": iso_today(),
        }
        for k, v in defaults.items():
            c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))

        for row in DEFAULT_ITEMS:
            c.execute("""
                INSERT OR IGNORE INTO items(
                    group_name,item_name,baseline_units,baseline_date,min_threshold,low_threshold,
                    units_per_session,units_per_week,reusable_sessions,lifespan_days,auto_session_usage,active
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,1)
            """, (row[0], row[1], row[2], iso_today(), row[3], row[4], row[5], row[6], row[7], row[8], row[9]))

        # Enable the rule for the default/existing SAK item. Once enabled, the
        # database flag remains with the item even if the user renames it.
        c.execute(
            """UPDATE items
               SET full_attempt_usage=1
               WHERE UPPER(TRIM(item_name))='SAK'"""
        )
        self.conn.commit()

    def get_setting(self, key, default=""):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))
        self.conn.commit()

    def items(self, group=None, include_inactive=False):
        active_sql = "" if include_inactive else "AND active=1"
        if group:
            return self.conn.execute(f"SELECT * FROM items WHERE group_name=? {active_sql} ORDER BY item_name", (group,)).fetchall()
        return self.conn.execute(f"SELECT * FROM items WHERE 1=1 {active_sql} ORDER BY group_name,item_name").fetchall()

    def item_by_id(self, item_id):
        return self.conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()

    def add_item(self, group_name, item_name, baseline_units=0, baseline_date=None,
                 min_threshold=0, low_threshold=0, units_per_session=0,
                 units_per_week=0, reusable_sessions=1, lifespan_days=0,
                 auto_session_usage=1, full_attempt_usage=0):
        item_name = item_name.strip()
        if not item_name:
            raise ValueError("Item name cannot be blank.")
        if group_name not in (GROUP_NX, GROUP_DV):
            raise ValueError("Invalid inventory group.")
        baseline_date = baseline_date or iso_today()
        self.conn.execute("""
            INSERT INTO items(
                group_name,item_name,baseline_units,baseline_date,min_threshold,low_threshold,
                units_per_session,units_per_week,reusable_sessions,lifespan_days,
                auto_session_usage,full_attempt_usage,active
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1)
        """, (
            group_name, item_name, float(baseline_units), baseline_date,
            float(min_threshold), float(low_threshold), float(units_per_session),
            float(units_per_week), max(float(reusable_sessions), 1.0),
            int(lifespan_days), int(auto_session_usage), int(full_attempt_usage)
        ))
        self.conn.commit()

    def update_item(self, item_id, **kwargs):
        allowed = {
            "group_name", "item_name", "baseline_units", "baseline_date", "min_threshold",
            "low_threshold", "units_per_session", "units_per_week", "reusable_sessions",
            "lifespan_days", "auto_session_usage", "full_attempt_usage", "active"
        }
        parts, values = [], []
        for k, v in kwargs.items():
            if k in allowed:
                parts.append(f"{k}=?")
                values.append(v)
        if not parts:
            return
        values.append(item_id)
        self.conn.execute(f"UPDATE items SET {', '.join(parts)} WHERE id=?", values)
        self.conn.commit()

    def deactivate_item(self, item_id):
        self.update_item(item_id, active=0)

    def add_received(self, item_id, received_date, units, notes=""):
        self.conn.execute(
            "INSERT INTO received_inventory(item_id,received_date,units,notes) VALUES(?,?,?,?)",
            (item_id, received_date, units, notes)
        )
        self.conn.commit()

    def add_session(self, session_date, session_type, session_equivalent, notes=""):
        self.conn.execute(
            "INSERT INTO session_log(session_date,session_type,session_equivalent,notes) VALUES(?,?,?,?)",
            (session_date, session_type, session_equivalent, notes)
        )
        self.conn.commit()

    def session_by_id(self, session_id):
        return self.conn.execute(
            "SELECT * FROM session_log WHERE id=?",
            (session_id,)
        ).fetchone()

    def update_session_notes(self, session_id, notes):
        self.conn.execute(
            "UPDATE session_log SET notes=? WHERE id=?",
            (notes, session_id)
        )
        self.conn.commit()

    def received_sum(self, item_id, since_date):
        row = self.conn.execute(
            "SELECT COALESCE(SUM(units),0) AS total FROM received_inventory WHERE item_id=? AND received_date>=?",
            (item_id, since_date)
        ).fetchone()
        return float(row["total"])

    def corrections_sum(self, item_id, since_date):
        row = self.conn.execute(
            "SELECT COALESCE(SUM(units_delta),0) AS total FROM corrections WHERE item_id=? AND correction_date>=?",
            (item_id, since_date)
        ).fetchone()
        return float(row["total"])

    def session_usage_sum(self, item, since_date, through_date=None):
        """
        Return the number of treatment-use slots applicable to an item.

        Normal items use the treatment equivalent. Items configured to count
        every attempted treatment as a full use count Regular, Extra, and
        Incomplete treatments as 1 each. Missed treatments count as 0.
        """
        clauses = ["session_date>=?"]
        params = [since_date]
        if through_date is not None:
            clauses.append("session_date<=?")
            params.append(through_date)
        where_sql = " AND ".join(clauses)

        if int(item["full_attempt_usage"] or 0) == 1:
            expression = """
                CASE
                    WHEN LOWER(TRIM(session_type)) LIKE 'missed%' THEN 0
                    ELSE 1
                END
            """
        else:
            expression = "session_equivalent"

        row = self.conn.execute(
            f"""SELECT COALESCE(SUM({expression}),0) AS total
                FROM session_log
                WHERE {where_sql}""",
            tuple(params),
        ).fetchone()
        return float(row["total"])

    def weeks_since(self, since_date):
        d = parse_date(since_date)
        return max(0, (date.today() - d).days / 7.0)

    def historical_count_as_of(self, item, as_of_date):
        """Reconstruct calculated inventory for an item on a specific date."""
        as_of = parse_date(as_of_date)
        baseline_date = parse_date(
            item["baseline_date"] or self.get_setting("created_date", iso_today())
        )
        if as_of < baseline_date:
            return None

        as_of_iso = as_of.isoformat()
        baseline_iso = baseline_date.isoformat()

        received_row = self.conn.execute(
            """SELECT COALESCE(SUM(units),0) AS total
               FROM received_inventory
               WHERE item_id=? AND received_date>=? AND received_date<=?""",
            (item["id"], baseline_iso, as_of_iso),
        ).fetchone()
        correction_row = self.conn.execute(
            """SELECT COALESCE(SUM(units_delta),0) AS total
               FROM corrections
               WHERE item_id=? AND correction_date>=? AND correction_date<=?""",
            (item["id"], baseline_iso, as_of_iso),
        ).fetchone()
        received = float(received_row["total"])
        corrections = float(correction_row["total"])
        sessions = self.session_usage_sum(item, baseline_iso, as_of_iso)

        session_usage = 0.0
        if int(item["auto_session_usage"]) == 1:
            reusable = max(float(item["reusable_sessions"] or 1), 1.0)
            session_usage = sessions * (
                float(item["units_per_session"]) / reusable
            )

        elapsed_weeks = max(0.0, (as_of - baseline_date).days / 7.0)
        weekly_usage = elapsed_weeks * float(item["units_per_week"])
        current = (
            float(item["baseline_units"])
            + received
            + corrections
            - session_usage
            - weekly_usage
        )
        return max(0.0, current)

    def inventory_history(self, item_id, start_date, end_date, max_points=180):
        item = self.item_by_id(item_id)
        if not item:
            return []

        baseline_date = parse_date(
            item["baseline_date"] or self.get_setting("created_date", iso_today())
        )
        start = max(parse_date(start_date), baseline_date)
        end = parse_date(end_date)
        if end < start:
            return []

        total_days = (end - start).days
        step_days = max(1, math.ceil(max(1, total_days) / max(1, max_points - 1)))

        points = []
        cursor = start
        while cursor <= end:
            value = self.historical_count_as_of(item, cursor)
            if value is not None:
                points.append((cursor, value))
            cursor += timedelta(days=step_days)

        if not points or points[-1][0] != end:
            value = self.historical_count_as_of(item, end)
            if value is not None:
                points.append((end, value))
        return points

    def current_count(self, item):
        baseline = float(item["baseline_units"])
        since = item["baseline_date"] or self.get_setting("created_date", iso_today())
        received = self.received_sum(item["id"], since)
        corrections = self.corrections_sum(item["id"], since)
        sessions = self.session_usage_sum(item, since)

        session_usage = 0.0
        if int(item["auto_session_usage"]) == 1:
            reusable = max(float(item["reusable_sessions"] or 1), 1.0)
            session_usage = sessions * (float(item["units_per_session"]) / reusable)

        weekly_usage = self.weeks_since(since) * float(item["units_per_week"])
        used = session_usage + weekly_usage
        current = baseline + received + corrections - used
        return max(0.0, current), used, received, corrections, sessions

    def status(self, item, current):
        if current <= float(item["min_threshold"]):
            return "RE-ORDER", RED
        if current <= float(item["low_threshold"]):
            return "LOW", YELLOW
        return "OK", GREEN

    def weeks_remaining(self, item, current):
        sessions_per_week = float(self.get_setting("sessions_per_week", "4") or 4)
        per_session = float(item["units_per_session"] or 0) / max(float(item["reusable_sessions"] or 1), 1.0)
        per_week = float(item["units_per_week"] or 0)
        weekly_rate = (per_session * sessions_per_week) + per_week

        if int(item["lifespan_days"] or 0) > 0:
            return (current * int(item["lifespan_days"])) / 7.0

        if weekly_rate <= 0:
            return None
        return current / weekly_rate

    def recent_sessions(self, limit=30):
        return self.conn.execute("SELECT * FROM session_log ORDER BY session_date DESC,id DESC LIMIT ?", (limit,)).fetchall()

    def recent_received(self, limit=30):
        return self.conn.execute("""
            SELECT r.*, i.item_name, i.group_name
            FROM received_inventory r
            JOIN items i ON r.item_id=i.id
            ORDER BY r.received_date DESC,r.id DESC LIMIT ?
        """, (limit,)).fetchall()

    def close(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception:
            pass

    def reopen(self):
        try:
            self.conn.close()
        except Exception:
            pass
        self.conn = sqlite3.connect(db_path())
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def backup_database(self, reason="auto"):
        """
        Keep one rolling database backup file in Documents, overwriting it.

        This intentionally avoids creating a new file every 10 minutes.
        The only exception is the pre-import safety backup, which is also a single
        rolling file named HHD_Inventory_Backup_Before_Import.db.
        """
        self.conn.commit()
        if reason == "before_import":
            name = "HHD_Inventory_Backup_Before_Import.db"
        else:
            name = ROLLING_DB_BACKUP_NAME
        return safe_copy(db_path(), os.path.join(backup_dir(), name))

    def import_database(self, source_path):
        if not source_path or not os.path.exists(source_path):
            raise ValueError("Database file not found.")
        # Validate it opens as SQLite and has the expected items table.
        test = sqlite3.connect(source_path)
        try:
            cur = test.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")
            if cur.fetchone() is None:
                raise ValueError("Selected file does not look like an HHD Inventory database.")
        finally:
            test.close()

        self.backup_database("before_import")
        self.close()
        shutil.copy2(source_path, db_path())
        self.reopen()

    def export_csv(self, filename):
        rows = []
        for item in self.items():
            current, used, rec, corr, sessions = self.current_count(item)
            status, _ = self.status(item, current)
            weeks = self.weeks_remaining(item, current)
            rows.append({
                "Group": item["group_name"],
                "Item": item["item_name"],
                "Current Units": round(current, 2),
                "Status": status,
                "Weeks Remaining": "" if weeks is None else round(weeks, 2),
                "Baseline Units": item["baseline_units"],
                "Baseline Date": item["baseline_date"],
                "Received Since Baseline": round(rec, 2),
                "Calculated Used Since Baseline": round(used, 2),
                "Corrections": round(corr, 2),
            })
        if not rows:
            raise ValueError("No active items to export.")
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

class X11TitleBar(tk.Frame):
    def __init__(self, master, title, on_close):
        super().__init__(master, bg="#031B2D", highlightbackground=BORDER, highlightthickness=1)
        self.master = master
        self.on_close = on_close
        self._drag_x = 0
        self._drag_y = 0
        tk.Label(self, text="✚", fg=CYAN, bg="#031B2D", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(12, 8), pady=6)
        tk.Label(self, text=title, fg=TEXT, bg="#031B2D", font=("Segoe UI", 12, "bold")).pack(side="left", pady=6)
        btns = tk.Frame(self, bg="#031B2D")
        btns.pack(side="right", padx=8)
        min_btn = tk.Label(btns, text="—", fg=CYAN, bg="#031B2D", font=("Segoe UI", 14), width=3, cursor="hand2")
        min_btn.pack(side="left")
        close_btn = tk.Label(btns, text="✕", fg=CYAN, bg="#031B2D", font=("Segoe UI", 13), width=3, cursor="hand2")
        close_btn.pack(side="left")
        min_btn.bind("<Button-1>", lambda e: master.iconify())
        close_btn.bind("<Button-1>", lambda e: on_close())
        for widget in self.winfo_children() + [self]:
            widget.bind("<ButtonPress-1>", self.start_move)
            widget.bind("<B1-Motion>", self.do_move)

    def start_move(self, event):
        self._drag_x = event.x_root - self.master.winfo_x()
        self._drag_y = event.y_root - self.master.winfo_y()

    def do_move(self, event):
        self.master.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

class HHDApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = InventoryDB()
        self.settings_data = self.load_local_settings()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry(self.settings_data.get("window_geometry", "1280x760"))
        self.minsize(1080, 680)
        if self.settings_data.get("window_state") == "zoomed":
            self.after(100, lambda: self.state("zoomed"))
        self.configure(bg=BLUE_BG)
        self.set_app_icon()
        # Use a normal Windows title bar so the taskbar icon appears reliably.
        self.overrideredirect(False)
        self.update_idletasks()
        request_windows_medical_blue_titlebar(self.winfo_id())

        self.inventory_font_default = 12
        self.inventory_font_min = self.inventory_font_default - 5
        self.inventory_font_max = self.inventory_font_default + 5
        try:
            saved_font_size = int(self.settings_data.get("inventory_font_size", self.inventory_font_default))
        except Exception:
            saved_font_size = self.inventory_font_default
        self.inventory_font_size = max(self.inventory_font_min, min(self.inventory_font_max, saved_font_size))
        self._inventory_font_labels = []

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.configure_styles()

        self.container = tk.Frame(self, bg=BLUE_BG)
        self.container.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(self.container, bg=BLUE_PANEL, width=215)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(self.container, bg=BLUE_BG)
        self.content.pack(side="left", fill="both", expand=True)

        self.statusbar = tk.Frame(self, bg="#031B2D", height=24, highlightbackground=BORDER, highlightthickness=1)
        self.statusbar.pack(fill="x", side="bottom")
        tk.Label(self.statusbar, text=f"  Data is stored locally in {DB_NAME}    |    Version {APP_VERSION}",
                 bg="#031B2D", fg=MUTED, anchor="w", font=("Segoe UI", 9)).pack(fill="both")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Configure>", self.remember_window_geometry_event)
        self.create_status_led_images()
        self._status_trees = []
        self._blink_on = True
        self.build_sidebar()
        self.show_dashboard()
        self.schedule_clock_update()
        self.schedule_auto_backup()
        self.after(600, self.blink_status_leds)

    def set_app_icon(self):
        """Set the Windows taskbar/Alt-Tab/window icon as reliably as Tk allows."""
        try:
            self.iconbitmap(icon_path())
        except Exception:
            pass
        try:
            self._app_icon_photo = tk.PhotoImage(file=icon_png_path())
            self.iconphoto(True, self._app_icon_photo)
        except Exception:
            pass

    def load_local_settings(self):
        try:
            with open(settings_file_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_local_settings(self):
        try:
            current_state = self.state()
            self.settings_data["window_state"] = current_state

            # When maximized, keep the last normal geometry for future non-maximized launches.
            # The maximized state itself is stored separately and restored on next launch.
            if current_state != "zoomed":
                self.settings_data["window_geometry"] = self.geometry()
            else:
                self.settings_data.setdefault("window_geometry", "1280x760")

            with open(settings_file_path(), "w", encoding="utf-8") as f:
                json.dump(self.settings_data, f, indent=2)
            self.backup_settings_file()
        except Exception:
            pass

    def backup_settings_file(self):
        """Keep one rolling settings backup file in Documents, overwriting it each time."""
        try:
            if os.path.exists(settings_file_path()):
                safe_copy(settings_file_path(), os.path.join(backup_dir(), ROLLING_SETTINGS_BACKUP_NAME))
        except Exception:
            pass

    def auto_backup_now(self):
        try:
            self.db.backup_database("auto")
            self.save_local_settings()
        except Exception:
            pass

    def schedule_auto_backup(self):
        self.auto_backup_now()
        self.after(AUTO_BACKUP_INTERVAL_MS, self.schedule_auto_backup)

    def on_close(self):
        try:
            self.save_local_settings()
            self.db.backup_database("close")
            self.db.close()
        except Exception:
            pass
        self.destroy()

    def center_child_window(self, win, width=580, height=680):
        self.update_idletasks()
        x = self.winfo_x() + max(20, (self.winfo_width() - width) // 2)
        y = self.winfo_y() + max(20, (self.winfo_height() - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")

    def schedule_clock_update(self):
        if hasattr(self, "datetime_label"):
            self.datetime_label.config(text=datetime.now().strftime("%A, %B %d, %Y   %I:%M %p"))
        self.after(30000, self.schedule_clock_update)

    def show_about(self):
        win = tk.Toplevel(self)
        win.title(f"About {APP_NAME}")
        win.configure(bg=BLUE_BG)
        win.resizable(False, False)
        self.center_child_window(win, 520, 390)
        win.transient(self)
        win.grab_set()

        header = tk.Frame(win, bg=BLUE_HEADER, height=72)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="HHDIM",
            bg=BLUE_HEADER,
            fg=CYAN,
            font=("Segoe UI", 22, "bold"),
        ).pack(side="left", padx=(22, 12), pady=16)

        title_area = tk.Frame(header, bg=BLUE_HEADER)
        title_area.pack(side="left", fill="both", expand=True, pady=12)
        tk.Label(
            title_area,
            text=APP_NAME,
            bg=BLUE_HEADER,
            fg=TEXT,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_area,
            text=f"Version {APP_VERSION}",
            bg=BLUE_HEADER,
            fg=MUTED,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(3, 0))

        body = tk.Frame(
            win,
            bg=BLUE_PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        body.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(
            body,
            text="Home Hemodialysis Inventory Management",
            bg=BLUE_PANEL,
            fg=CYAN,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=18, pady=(18, 10))

        tk.Label(
            body,
            text=(
                "Created by Eduardo A. de Carvalho,\n"
                "husband and caregiver of Joelle."
            ),
            bg=BLUE_PANEL,
            fg=TEXT,
            justify="left",
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=18, pady=(0, 16))

        divider = tk.Frame(body, bg=BORDER, height=1)
        divider.pack(fill="x", padx=18, pady=(0, 16))

        tk.Label(
            body,
            text=(
                "This software is an inventory tracking tool only.\n"
                "Always verify physical inventory before treatment."
            ),
            bg=BLUE_PANEL,
            fg=MUTED,
            justify="left",
            wraplength=440,
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=18)

        self.button(body, "Close", win.destroy).pack(
            side="bottom", anchor="e", padx=18, pady=18
        )

        win.bind("<Escape>", lambda _event: win.destroy())
        win.focus_set()


    def import_database_action(self):
        filename = filedialog.askopenfilename(
            title="Import HHD Inventory Database",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )
        if not filename:
            return
        if not messagebox.askyesno(APP_NAME, "Import the selected inventory database?\n\nYour current database will first be backed up to:\nDocuments\\HHD Inventory Backups\\HHD_Inventory_Backup_Before_Import.db\n\nContinue?"):
            return
        try:
            self.db.import_database(filename)
            self.show_dashboard()
            messagebox.showinfo(APP_NAME, "Database imported successfully.")
        except Exception as ex:
            messagebox.showerror(APP_NAME, f"Database import failed:\\n{ex}")

    def remember_window_geometry_event(self, event=None):
        """Remember current window state during runtime without constantly writing to disk."""
        try:
            if event is not None and event.widget is not self:
                return
            current_state = self.state()
            self.settings_data["window_state"] = current_state
            if current_state != "zoomed":
                self.settings_data["window_geometry"] = self.geometry()
        except Exception:
            pass

    def group_display_name(self, internal_group):
        if internal_group == GROUP_NX:
            return self.db.get_setting("group_nx_display_name", GROUP_NX)
        if internal_group == GROUP_DV:
            return self.db.get_setting("group_dv_display_name", GROUP_DV)
        return internal_group

    def internal_group_from_display(self, display_name):
        if display_name == self.group_display_name(GROUP_NX):
            return GROUP_NX
        if display_name == self.group_display_name(GROUP_DV):
            return GROUP_DV
        return display_name

    def create_status_led_images(self):
        self._led_images = {}
        color_map = {"off": "#18384C", "ok": GREEN, "low": YELLOW, "reorder": RED}
        for name, color in color_map.items():
            image = tk.PhotoImage(width=18, height=18)
            image.put(BLUE_PANEL, to=(0, 0, 18, 18))
            spans = {2:(7,11),3:(5,13),4:(4,14),5:(3,15),6:(2,16),7:(2,16),8:(2,16),9:(2,16),10:(2,16),11:(2,16),12:(3,15),13:(4,14),14:(5,13),15:(7,11)}
            for y, (x1, x2) in spans.items():
                image.put(color, to=(x1, y, x2, y+1))
            self._led_images[name] = image

    def register_status_tree(self, tree, status_by_item):
        self._status_trees.append((tree, status_by_item))

    def blink_status_leds(self):
        self._blink_on = not self._blink_on
        active = []
        for tree, status_by_item in self._status_trees:
            try:
                if not tree.winfo_exists():
                    continue
                active.append((tree, status_by_item))
                for iid, status in status_by_item.items():
                    if not tree.exists(iid):
                        continue
                    if status == "OK":
                        image = self._led_images["ok"]
                    elif status == "LOW":
                        image = self._led_images["low"] if self._blink_on else self._led_images["off"]
                    else:
                        image = self._led_images["reorder"] if self._blink_on else self._led_images["off"]
                    tree.item(iid, image=image)
            except Exception:
                pass
        self._status_trees = active
        self.after(600, self.blink_status_leds)

    def configure_styles(self):
        self.style.configure("Treeview", background=BLUE_PANEL, foreground=TEXT, fieldbackground=BLUE_PANEL, rowheight=28, font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading", background=BLUE_HEADER, foreground=TEXT, font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[("selected", "#126A9F")], foreground=[("selected", "white")])

        self.style.configure(
            "Inventory.Treeview",
            background=BLUE_PANEL,
            foreground=TEXT,
            fieldbackground=BLUE_PANEL,
            rowheight=max(26, self.inventory_font_size + 22),
            font=("Segoe UI", self.inventory_font_size),
        )
        self.style.configure(
            "Inventory.Treeview.Heading",
            background=BLUE_HEADER,
            foreground=TEXT,
            font=("Segoe UI", max(9, self.inventory_font_size - 1), "bold"),
        )
        self.style.map(
            "Inventory.Treeview",
            background=[("selected", "#126A9F")],
            foreground=[("selected", "white")],
        )

        # Dark themed combo boxes. The map() calls are important on Windows,
        # especially for readonly comboboxes, otherwise the field can turn white.
        self.style.configure(
            "TCombobox",
            fieldbackground=INPUT_BG,
            background=INPUT_BG,
            foreground=TEXT,
            selectbackground=BLUE_HEADER,
            selectforeground=TEXT,
            arrowcolor=CYAN,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            insertcolor=TEXT,
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", INPUT_BG), ("disabled", INPUT_BG), ("!disabled", INPUT_BG)],
            background=[("readonly", INPUT_BG), ("disabled", INPUT_BG), ("!disabled", INPUT_BG)],
            foreground=[("readonly", TEXT), ("disabled", MUTED), ("!disabled", TEXT)],
            selectbackground=[("readonly", BLUE_HEADER), ("!disabled", BLUE_HEADER)],
            selectforeground=[("readonly", TEXT), ("!disabled", TEXT)],
            arrowcolor=[("readonly", CYAN), ("!disabled", CYAN)],
        )

        # Dropdown list colors used by Tk's internal Listbox for ttk.Combobox.
        self.option_add("*TCombobox*Listbox.background", INPUT_BG)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", BLUE_HEADER)
        self.option_add("*TCombobox*Listbox.selectForeground", TEXT)
        self.option_add("*TCombobox*Listbox.borderWidth", 1)

    def status_display_text(self, status):
        """Return visibly bold Unicode status text for the Status column."""
        return {
            "OK": "𝗢𝗞",
            "LOW": "𝗟𝗢𝗪",
            "RE-ORDER": "𝗥𝗘-𝗢𝗥𝗗𝗘𝗥",
        }.get(status, status)

    def refresh_inventory_font_style(self):
        self.style.configure(
            "Inventory.Treeview",
            rowheight=max(26, self.inventory_font_size + 22),
            font=("Segoe UI", self.inventory_font_size),
        )
        self.style.configure(
            "Inventory.Treeview.Heading",
            font=("Segoe UI", max(9, self.inventory_font_size - 1), "bold"),
        )
        self.settings_data["inventory_font_size"] = self.inventory_font_size
        self.save_local_settings()

        active_labels = []
        for label in self._inventory_font_labels:
            try:
                if label.winfo_exists():
                    label.config(text=f"{self.inventory_font_size} pt")
                    active_labels.append(label)
            except Exception:
                pass
        self._inventory_font_labels = active_labels

    def adjust_inventory_font(self, delta):
        new_size = max(
            self.inventory_font_min,
            min(self.inventory_font_max, self.inventory_font_size + delta)
        )
        if new_size == self.inventory_font_size:
            return
        self.inventory_font_size = new_size
        self.refresh_inventory_font_style()

    def build_inventory_font_controls(self, parent, compact=False):
        controls = tk.Frame(parent, bg=BLUE_PANEL)
        controls.pack(fill="x", pady=(0, 8))

        tk.Label(
            controls,
            text="Item font:",
            bg=BLUE_PANEL,
            fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")

        tk.Button(
            controls,
            text="−",
            command=lambda: self.adjust_inventory_font(-1),
            bg=BUTTON_BG,
            fg=TEXT,
            activebackground=BUTTON_HOVER,
            activeforeground=TEXT,
            relief="flat",
            width=3,
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=(8, 3))

        tk.Button(
            controls,
            text="+",
            command=lambda: self.adjust_inventory_font(1),
            bg=BUTTON_BG,
            fg=TEXT,
            activebackground=BUTTON_HOVER,
            activeforeground=TEXT,
            relief="flat",
            width=3,
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=3)

        size_label = tk.Label(
            controls,
            text=f"{self.inventory_font_size} pt",
            bg=BLUE_PANEL,
            fg=CYAN,
            font=("Segoe UI", 9, "bold"),
        )
        size_label.pack(side="left", padx=8)
        self._inventory_font_labels.append(size_label)

        if not compact:
            tk.Label(
                controls,
                text=f"Range: {self.inventory_font_min}–{self.inventory_font_max} pt",
                bg=BLUE_PANEL,
                fg=MUTED,
                font=("Segoe UI", 8),
            ).pack(side="left", padx=4)

    def button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=BUTTON_BG, fg=TEXT, activebackground=BUTTON_HOVER,
                         activeforeground=TEXT, relief="flat", padx=14, pady=7, font=("Segoe UI", 10), cursor="hand2")

    def build_sidebar(self):
        bottom = tk.Frame(self.sidebar, bg=BLUE_PANEL)
        bottom.pack(side="bottom", fill="x", padx=8, pady=(8, 14))

        tk.Button(
            bottom,
            text="✓  Submit Treatment",
            command=self.show_log_session,
            anchor="center",
            bg=BLUE_HEADER,
            fg=TEXT,
            activebackground=BUTTON_HOVER,
            activeforeground=TEXT,
            relief="raised",
            bd=1,
            font=("Segoe UI", 12, "bold"),
            padx=10,
            pady=12,
            cursor="hand2",
        ).pack(fill="x")

        menu = tk.Frame(self.sidebar, bg=BLUE_PANEL)
        menu.pack(side="top", fill="both", expand=True)

        tk.Label(
            menu,
            text="HHD MENU",
            bg=BLUE_PANEL,
            fg=CYAN,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=18, pady=(18, 8))

        buttons = [
            ("⌂  Dashboard", self.show_dashboard),
            (f"▣  {self.group_display_name(GROUP_NX)}", lambda: self.show_inventory(GROUP_NX)),
            (f"▣  {self.group_display_name(GROUP_DV)}", lambda: self.show_inventory(GROUP_DV)),
            ("⌁  Inventory History", self.show_inventory_history),
            ("＋  Received Inventory", self.show_received),
            ("⚙  Settings / Items", self.show_settings),
            ("⇧  Import Database", self.import_database_action),
            ("⇩  Export CSV", self.export_csv),
            ("ⓘ  About", self.show_about),
        ]
        for text, cmd in buttons:
            tk.Button(
                menu,
                text=text,
                command=cmd,
                anchor="w",
                bg=BLUE_PANEL,
                fg=TEXT,
                activebackground=BLUE_HEADER,
                activeforeground=TEXT,
                relief="flat",
                bd=0,
                font=("Segoe UI", 12),
                padx=14,
                pady=10,
                cursor="hand2",
            ).pack(fill="x", padx=8, pady=1)

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def make_panel(self, parent, title):
        panel = tk.Frame(parent, bg=BLUE_PANEL, highlightbackground=BORDER, highlightthickness=1)
        tk.Label(panel, text=title, bg="#052239", fg=CYAN, font=("Segoe UI", 12, "bold"), anchor="w", padx=12, pady=8).pack(fill="x")
        body = tk.Frame(panel, bg=BLUE_PANEL)
        body.pack(fill="both", expand=True, padx=12, pady=12)
        return panel, body

    def show_dashboard(self):
        self.clear_content()
        top = tk.Frame(self.content, bg=BLUE_BG)
        top.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(top, text=f"👤  Patient: {self.db.get_setting('patient_name', 'Patient Name')}",
                 bg=BLUE_BG, fg=CYAN, font=("Segoe UI", 14, "bold")).pack(side="left")
        self.datetime_label = tk.Label(top, text=datetime.now().strftime("%A, %B %d, %Y   %I:%M %p"),
                                       bg=BLUE_BG, fg=TEXT, font=("Segoe UI", 12))
        self.datetime_label.pack(side="left", padx=40)
        self.button(top, "Add Received Inventory", self.show_received).pack(side="right", padx=6)
        self.button(top, "Submit Treatment", self.show_log_session).pack(side="right", padx=6)

        row = tk.Frame(self.content, bg=BLUE_BG)
        row.pack(fill="both", expand=True, padx=16, pady=8)
        row.grid_columnconfigure(0, weight=1, uniform="inventory_groups")
        row.grid_columnconfigure(1, weight=1, uniform="inventory_groups")
        row.grid_rowconfigure(0, weight=1)

        p1, b1 = self.make_panel(row, self.group_display_name(GROUP_NX).upper())
        p1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.inventory_tree(b1, GROUP_NX, compact=True)

        p2, b2 = self.make_panel(row, self.group_display_name(GROUP_DV).upper())
        p2.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.inventory_tree(b2, GROUP_DV, compact=True)

        glance, body = self.make_panel(self.content, "AT A GLANCE")
        glance.pack(fill="x", padx=16, pady=(4, 14))
        low = reorder = 0
        items = self.db.items()
        for item in items:
            current, *_ = self.db.current_count(item)
            st, _ = self.db.status(item, current)
            low += 1 if st == "LOW" else 0
            reorder += 1 if st == "RE-ORDER" else 0
        cards = [
            ("Schedule", f"{self.db.get_setting('sessions_per_week','4')} sessions/week\nFirst day: {self.db.get_setting('first_session_day','Sunday')}"),
            ("Total Items", str(len(items))),
            ("Re-order", str(reorder)),
            ("Low", str(low)),
        ]
        for title, value in cards:
            card = tk.Frame(body, bg=BLUE_PANEL_2, highlightbackground=BORDER, highlightthickness=1)
            card.pack(side="left", expand=True, fill="both", padx=6, pady=2)
            tk.Label(card, text=title, bg=BLUE_PANEL_2, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
            tk.Label(card, text=value, bg=BLUE_PANEL_2, fg=TEXT, justify="left", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=12, pady=(0, 10))

    def inventory_tree(self, parent, group, compact=False):
        self.build_inventory_font_controls(parent, compact=compact)

        cols = ("item", "units", "weeks", "status")
        tree = ttk.Treeview(
            parent,
            columns=cols,
            show="tree headings",
            height=8 if compact else 18,
            style="Inventory.Treeview",
        )
        tree.heading("#0", text="Alert")
        if compact:
            tree.column("#0", width=54, minwidth=50, stretch=False, anchor="center")
            column_specs = [
                ("item", "Item", 150, True),
                ("units", "Units", 65, False),
                ("weeks", "Weeks", 68, False),
                ("status", "Status", 76, False),
            ]
        else:
            tree.column("#0", width=66, minwidth=60, stretch=False, anchor="center")
            column_specs = [
                ("item", "Item", 320, True),
                ("units", "Units Left", 100, False),
                ("weeks", "Weeks Left", 100, False),
                ("status", "Status", 140, False),
            ]

        for c, h, w, can_stretch in column_specs:
            tree.heading(c, text=h)
            tree.column(
                c,
                width=w,
                minwidth=55 if c != "item" else 100,
                stretch=can_stretch,
                anchor="w" if c == "item" else "center",
            )
        tree.pack(fill="both", expand=True)

        tree.tag_configure("ok", foreground=GREEN)
        tree.tag_configure("low", foreground=YELLOW)
        tree.tag_configure("reorder", foreground=RED)

        status_by_item = {}
        for item in self.db.items(group):
            current, *_ = self.db.current_count(item)
            status, _ = self.db.status(item, current)
            weeks = self.db.weeks_remaining(item, current)
            weeks_txt = "Manual" if weeks is None else f"{weeks:.1f}"
            units_txt = f"{current:.1f}".rstrip("0").rstrip(".")
            tag = "ok" if status == "OK" else ("low" if status == "LOW" else "reorder")
            image = (
                self._led_images["ok"]
                if status == "OK"
                else self._led_images["low"]
                if status == "LOW"
                else self._led_images["reorder"]
            )
            iid = str(item["id"])
            tree.insert(
                "",
                "end",
                iid=iid,
                image=image,
                values=(
                    item["item_name"],
                    units_txt,
                    weeks_txt,
                    self.status_display_text(status),
                ),
                tags=(tag,),
            )
            status_by_item[iid] = status

        self.register_status_tree(tree, status_by_item)

        if not compact:
            tree.bind(
                "<Double-1>",
                lambda e: self.open_item_editor(int(tree.selection()[0]))
                if tree.selection()
                else None,
            )
        return tree

    def show_inventory(self, group):
        self.clear_content()
        top = tk.Frame(self.content, bg=BLUE_BG)
        top.pack(fill="x", padx=16, pady=12)
        tk.Label(top, text=self.group_display_name(group), bg=BLUE_BG, fg=CYAN, font=("Segoe UI", 17, "bold")).pack(side="left")
        self.button(top, "Add New Item", lambda: self.open_item_editor(None, default_group=group)).pack(side="right", padx=6)
        self.button(top, "Remove Selected Item", lambda: self.remove_selected_item()).pack(side="right", padx=6)
        self.button(top, "Edit / Rename Selected", lambda: self.edit_selected_item()).pack(side="right", padx=6)
        p, b = self.make_panel(self.content, f"{self.group_display_name(group)} Inventory")
        p.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.current_tree = self.inventory_tree(b, group, compact=False)

    def edit_selected_item(self):
        if not hasattr(self, "current_tree"):
            return
        sel = self.current_tree.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "Select an item first.")
            return
        self.open_item_editor(int(sel[0]))

    def remove_selected_item(self):
        if not hasattr(self, "current_tree"):
            return
        sel = self.current_tree.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "Select an item first.")
            return
        item = self.db.item_by_id(int(sel[0]))
        if not item:
            return
        if messagebox.askyesno(APP_NAME, f"Remove '{item['item_name']}' from active inventory?\n\nHistorical records are kept safely."):
            self.db.deactivate_item(item["id"])
            self.db.backup_database("change")
            self.show_inventory(item["group_name"])

    def open_item_editor(self, item_id=None, default_group=GROUP_NX):
        is_new = item_id is None
        item = None if is_new else self.db.item_by_id(item_id)
        if not is_new and not item:
            return

        win = tk.Toplevel(self)
        win.configure(bg=BLUE_BG)
        win.title("Item Settings")
        self.center_child_window(win, 620, 735)
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="Add New Item" if is_new else f"Edit Item: {item['item_name']}",
                 bg=BLUE_BG, fg=CYAN, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=14)

        form = tk.Frame(win, bg=BLUE_PANEL, highlightbackground=BORDER, highlightthickness=1)
        form.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        vars_ = {}

        def val(key, default):
            return str(default if is_new else item[key])

        group_var = tk.StringVar(value=self.group_display_name(default_group if is_new else item["group_name"]))
        name_var = tk.StringVar(value="" if is_new else item["item_name"])
        rows = [
            ("group_name", "Inventory Group", group_var, "combo"),
            ("item_name", "Item Name", name_var, "entry"),
            ("baseline_units", "Current/Baseline Units", tk.StringVar(value=val("baseline_units", 0)), "entry"),
            ("baseline_date", "Inventory Count Date YYYY-MM-DD", tk.StringVar(value=val("baseline_date", iso_today())), "entry"),
            ("units_per_session", "Units Used Per Session", tk.StringVar(value=val("units_per_session", 0)), "entry"),
            ("units_per_week", "Additional Units Used Per Week", tk.StringVar(value=val("units_per_week", 0)), "entry"),
            ("reusable_sessions", "Reusable For # Sessions", tk.StringVar(value=val("reusable_sessions", 1)), "entry"),
            ("lifespan_days", "Lifespan Days Per Unit", tk.StringVar(value=val("lifespan_days", 0)), "entry"),
            ("low_threshold", "Low Threshold", tk.StringVar(value=val("low_threshold", 0)), "entry"),
            ("min_threshold", "Re-order Threshold", tk.StringVar(value=val("min_threshold", 0)), "entry"),
        ]

        for idx, (key, label, var, typ) in enumerate(rows):
            vars_[key] = var
            tk.Label(form, text=label, bg=BLUE_PANEL, fg=TEXT, font=("Segoe UI", 10)).grid(row=idx, column=0, sticky="w", padx=14, pady=7)
            if typ == "combo":
                e = ttk.Combobox(form, textvariable=var, values=[self.group_display_name(GROUP_NX), self.group_display_name(GROUP_DV)], width=34, state="readonly")
            else:
                e = tk.Entry(form, textvariable=var, bg=INPUT_BG, fg=TEXT, insertbackground=TEXT, relief="solid", bd=1, font=("Segoe UI", 10), width=38)
            e.grid(row=idx, column=1, sticky="ew", padx=14, pady=7)

        auto_var = tk.IntVar(value=1 if is_new else int(item["auto_session_usage"]))
        tk.Checkbutton(form, text="Auto-calculate usage from logged dialysis sessions", variable=auto_var,
                       bg=BLUE_PANEL, fg=TEXT, activebackground=BLUE_PANEL, activeforeground=TEXT,
                       selectcolor=INPUT_BG, font=("Segoe UI", 10)).grid(row=len(rows), column=0, columnspan=2, sticky="w", padx=14, pady=(10, 4))

        full_attempt_var = tk.IntVar(
            value=1 if (is_new and name_var.get().strip().upper() == "SAK")
            else (0 if is_new else int(item["full_attempt_usage"] or 0))
        )
        tk.Checkbutton(
            form,
            text="Count incomplete treatments as a full use of this item",
            variable=full_attempt_var,
            bg=BLUE_PANEL,
            fg=TEXT,
            activebackground=BLUE_PANEL,
            activeforeground=TEXT,
            selectcolor=INPUT_BG,
            font=("Segoe UI", 10),
        ).grid(
            row=len(rows)+1,
            column=0,
            columnspan=2,
            sticky="w",
            padx=14,
            pady=(4, 8),
        )

        sessions_per_week = self.db.get_setting("sessions_per_week", "4")
        tk.Label(
            form,
            text=f"Forecast weekly usage = (Units per session ÷ reusable sessions × {sessions_per_week} scheduled sessions/week) + additional weekly usage.",
            bg=BLUE_PANEL,
            fg=MUTED,
            wraplength=500,
            justify="left",
            font=("Segoe UI", 9)
        ).grid(row=len(rows)+2, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 10))

        form.columnconfigure(1, weight=1)

        def save():
            try:
                group = self.internal_group_from_display(vars_["group_name"].get())
                item_name = vars_["item_name"].get().strip()
                data = {
                    "group_name": group,
                    "item_name": item_name,
                    "baseline_units": float(vars_["baseline_units"].get() or 0),
                    "baseline_date": parse_date(vars_["baseline_date"].get()).isoformat(),
                    "units_per_session": float(vars_["units_per_session"].get() or 0),
                    "units_per_week": float(vars_["units_per_week"].get() or 0),
                    "reusable_sessions": max(float(vars_["reusable_sessions"].get() or 1), 1.0),
                    "lifespan_days": int(float(vars_["lifespan_days"].get() or 0)),
                    "low_threshold": float(vars_["low_threshold"].get() or 0),
                    "min_threshold": float(vars_["min_threshold"].get() or 0),
                    "auto_session_usage": int(auto_var.get()),
                    "full_attempt_usage": int(full_attempt_var.get()),
                }
                if not item_name:
                    raise ValueError("Item name cannot be blank.")

                if is_new:
                    self.db.add_item(**data)
                else:
                    self.db.update_item(item["id"], **data)

                self.save_local_settings()
                win.destroy()
                self.show_inventory(group)
            except sqlite3.IntegrityError:
                messagebox.showerror(APP_NAME, "An item with that name already exists in that group.")
            except Exception as ex:
                messagebox.showerror(APP_NAME, f"Could not save item:\n{ex}")

        btnrow = tk.Frame(win, bg=BLUE_BG)
        btnrow.pack(fill="x", padx=18, pady=(0, 18))
        self.button(btnrow, "Save Item", save).pack(side="left")
        self.button(btnrow, "Cancel", win.destroy).pack(side="right")

    def item_dropdown_values(self):
        """
        User-facing dropdown labels.

        Internal database IDs are intentionally hidden from the UI because they are
        confusing to the user. A private dictionary maps the clean label back to
        the SQLite item id.
        """
        self._item_dropdown_map = {}
        labels = []
        items = list(self.db.items())

        # Detect duplicate item names. Only show the group if needed to avoid ambiguity.
        name_counts = {}
        for r in items:
            name_counts[r["item_name"]] = name_counts.get(r["item_name"], 0) + 1

        for r in items:
            if name_counts[r["item_name"]] > 1:
                label = f"{self.group_display_name(r['group_name'])} — {r['item_name']}"
            else:
                label = r["item_name"]
            labels.append(label)
            self._item_dropdown_map[label] = r["id"]

        return labels

    def selected_item_id_from_value(self, value):
        return getattr(self, "_item_dropdown_map", {}).get(value)

    def draw_inventory_history_chart(
        self, canvas, item, points, period_start=None, period_end=None
    ):
        canvas.delete("all")
        width = max(640, canvas.winfo_width())
        height = max(340, canvas.winfo_height())
        left, right, top, bottom = 74, 28, 36, 66
        plot_w = max(100, width - left - right)
        plot_h = max(100, height - top - bottom)

        period_end = period_end or date.today()
        period_start = period_start or (
            points[0][0] if points else period_end - timedelta(days=30)
        )
        if period_end < period_start:
            period_start, period_end = period_end, period_start

        total_seconds = max(
            1.0,
            (
                datetime.combine(period_end, datetime.min.time())
                - datetime.combine(period_start, datetime.min.time())
            ).total_seconds(),
        )

        def x_for(day):
            seconds = (
                datetime.combine(day, datetime.min.time())
                - datetime.combine(period_start, datetime.min.time())
            ).total_seconds()
            ratio = max(0.0, min(1.0, seconds / total_seconds))
            return left + ratio * plot_w

        canvas.create_rectangle(
            left, top, left + plot_w, top + plot_h,
            outline=BORDER, fill="#052A43"
        )

        available_start = points[0][0] if points else None
        if available_start and available_start > period_start:
            unavailable_right = x_for(available_start)
            canvas.create_rectangle(
                left,
                top,
                unavailable_right,
                top + plot_h,
                fill="#082338",
                outline="",
            )
            canvas.create_text(
                left + max(8, (unavailable_right - left) / 2),
                top + 22,
                text="No calculated data before baseline",
                fill=MUTED,
                font=("Segoe UI", 9, "italic"),
                anchor="center",
            )

        values = [value for _day, value in points] if points else [0.0]
        threshold_values = [
            float(item["low_threshold"] or 0),
            float(item["min_threshold"] or 0),
        ]
        y_max = max(values + threshold_values + [1.0])
        y_max = max(1.0, math.ceil(y_max * 1.12))
        y_min = 0.0

        for index in range(6):
            ratio = index / 5
            y = top + plot_h - ratio * plot_h
            value = y_min + ratio * (y_max - y_min)
            canvas.create_line(
                left, y, left + plot_w, y,
                fill="#174E70", dash=(2, 4)
            )
            canvas.create_text(
                left - 10, y,
                text=f"{value:.0f}",
                fill=MUTED,
                anchor="e",
                font=("Segoe UI", 9)
            )

        def y_for(value):
            return top + plot_h - ((value - y_min) / (y_max - y_min)) * plot_h

        threshold_lines = [
            (float(item["low_threshold"] or 0), YELLOW, "LOW"),
            (float(item["min_threshold"] or 0), RED, "RE-ORDER"),
        ]
        for value, color, label in threshold_lines:
            if value <= 0 or value > y_max:
                continue
            y = y_for(value)
            canvas.create_line(
                left, y, left + plot_w, y,
                fill=color, dash=(7, 4), width=1
            )
            canvas.create_text(
                left + plot_w - 4, y - 9,
                text=f"{label}: {value:g}",
                fill=color, anchor="e",
                font=("Segoe UI", 8, "bold")
            )

        if points:
            xy = []
            for day, value in points:
                xy.extend((x_for(day), y_for(value)))

            if len(xy) >= 4:
                canvas.create_line(*xy, fill=CYAN, width=3, smooth=False)
            else:
                x, y = xy
                canvas.create_oval(
                    x - 4, y - 4, x + 4, y + 4,
                    fill=CYAN, outline=CYAN
                )

            marker_indexes = sorted(set([
                0,
                max(0, (len(points) - 1) // 2),
                len(points) - 1,
            ]))
            for index in marker_indexes:
                day, value = points[index]
                x = x_for(day)
                y = y_for(value)
                canvas.create_oval(
                    x - 3, y - 3, x + 3, y + 3,
                    fill=TEXT, outline=CYAN
                )
        else:
            canvas.create_text(
                width / 2,
                height / 2,
                text="No inventory history is available for this period.",
                fill=MUTED,
                font=("Segoe UI", 12),
            )

        # Always label the requested time period, not merely the available points.
        tick_days = []
        span_days = max(1, (period_end - period_start).days)
        for ratio in (0.0, 0.25, 0.5, 0.75, 1.0):
            tick_days.append(period_start + timedelta(days=round(span_days * ratio)))

        for day in tick_days:
            x = x_for(day)
            canvas.create_line(
                x, top + plot_h, x, top + plot_h + 5,
                fill=MUTED
            )
            canvas.create_text(
                x,
                top + plot_h + 17,
                text=day.strftime("%m/%d/%y"),
                fill=MUTED,
                anchor="n",
                font=("Segoe UI", 8),
            )

        canvas.create_text(
            left, 14,
            text=f"{item['item_name']} - inventory units over time",
            fill=TEXT, anchor="w",
            font=("Segoe UI", 12, "bold")
        )

        if points:
            first_value = points[0][1]
            last_value = points[-1][1]
            value_text = f"{first_value:.1f} → {last_value:.1f} units"
        else:
            value_text = "No calculated values"

        canvas.create_text(
            left + plot_w, 14,
            text=value_text,
            fill=CYAN, anchor="e",
            font=("Segoe UI", 10, "bold")
        )
        canvas.create_text(
            20, top + plot_h / 2,
            text="Units",
            fill=MUTED,
            angle=90,
            font=("Segoe UI", 9, "bold")
        )

    def show_inventory_history(self):
        self.clear_content()
        tk.Label(
            self.content,
            text="Inventory History",
            bg=BLUE_BG,
            fg=CYAN,
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w", padx=16, pady=12)

        controls_panel, controls = self.make_panel(
            self.content, "History Selection"
        )
        controls_panel.pack(fill="x", padx=16, pady=(0, 12))

        item_var = tk.StringVar()
        period_var = tk.StringVar(value="1 month")
        labels = []
        item_map = {}
        for item in self.db.items():
            label = f"{self.group_display_name(item['group_name'])} — {item['item_name']}"
            labels.append(label)
            item_map[label] = item["id"]

        tk.Label(
            controls, text="Inventory Item",
            bg=BLUE_PANEL, fg=TEXT,
            font=("Segoe UI", 10, "bold")
        ).grid(row=0, column=0, sticky="w", padx=8, pady=8)
        item_combo = ttk.Combobox(
            controls, textvariable=item_var,
            values=labels, state="readonly", width=56
        )
        item_combo.grid(row=0, column=1, sticky="ew", padx=8, pady=8)

        tk.Label(
            controls, text="Time Period",
            bg=BLUE_PANEL, fg=TEXT,
            font=("Segoe UI", 10, "bold")
        ).grid(row=0, column=2, sticky="w", padx=8, pady=8)
        period_combo = ttk.Combobox(
            controls,
            textvariable=period_var,
            values=["1 week", "1 month", "3 months", "6 months", "1 year", "All time"],
            state="readonly",
            width=14,
        )
        period_combo.grid(row=0, column=3, sticky="w", padx=8, pady=8)
        controls.columnconfigure(1, weight=1)

        chart_panel, chart_body = self.make_panel(
            self.content, "Calculated Inventory Level"
        )
        chart_panel.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        summary_label = tk.Label(
            chart_body, text="",
            bg=BLUE_PANEL, fg=MUTED,
            font=("Segoe UI", 10, "bold"),
            anchor="w"
        )
        summary_label.pack(fill="x", pady=(0, 6))

        canvas = tk.Canvas(
            chart_body,
            bg="#052A43",
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        canvas.pack(fill="both", expand=True)

        chart_state = {"item": None, "points": [], "start": None, "end": None}

        def refresh_chart(*_args):
            item_id = item_map.get(item_var.get())
            if item_id is None:
                canvas.delete("all")
                canvas.create_text(
                    360, 170,
                    text="Select an inventory item.",
                    fill=MUTED,
                    font=("Segoe UI", 12)
                )
                return

            item = self.db.item_by_id(item_id)
            end_date = date.today()
            period_days = {
                "1 week": 7,
                "1 month": 30,
                "3 months": 90,
                "6 months": 183,
                "1 year": 365,
            }
            if period_var.get() == "All time":
                start_date = parse_date(
                    item["baseline_date"]
                    or self.db.get_setting("created_date", iso_today())
                )
            else:
                start_date = end_date - timedelta(
                    days=period_days.get(period_var.get(), 30)
                )

            points = self.db.inventory_history(
                item_id, start_date, end_date
            )
            chart_state["item"] = item
            chart_state["points"] = points
            chart_state["start"] = start_date
            chart_state["end"] = end_date

            requested_period = (
                f"Period: {start_date.strftime('%m/%d/%Y')} - "
                f"{end_date.strftime('%m/%d/%Y')}"
            )

            if points:
                values = [value for _day, value in points]
                available_start = points[0][0]
                availability_note = ""
                if available_start > start_date:
                    availability_note = (
                        f"     Available data begins: "
                        f"{available_start.strftime('%m/%d/%Y')}"
                    )

                summary_label.config(
                    text=(
                        f"{requested_period}     "
                        f"First available: {values[0]:.1f}     "
                        f"Current: {values[-1]:.1f}     "
                        f"Minimum: {min(values):.1f}     "
                        f"Maximum: {max(values):.1f}"
                        f"{availability_note}"
                    )
                )
            else:
                summary_label.config(
                    text=f"{requested_period}     No history is available for this selection."
                )

            self.draw_inventory_history_chart(
                canvas, item, points, start_date, end_date
            )

        self.button(
            controls, "Refresh Graphic", refresh_chart
        ).grid(row=0, column=4, sticky="e", padx=8, pady=8)

        item_combo.bind("<<ComboboxSelected>>", refresh_chart)
        period_combo.bind("<<ComboboxSelected>>", refresh_chart)
        canvas.bind(
            "<Configure>",
            lambda event: self.draw_inventory_history_chart(
                canvas,
                chart_state["item"],
                chart_state["points"],
                chart_state["start"],
                chart_state["end"],
            ) if chart_state["item"] is not None else None
        )

        if labels:
            item_combo.current(0)
            self.after(50, refresh_chart)

    def show_received(self):
        self.clear_content()
        tk.Label(self.content, text="Add Received Inventory", bg=BLUE_BG, fg=CYAN, font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=12)
        panel, body = self.make_panel(self.content, "Received Inventory")
        panel.pack(fill="x", padx=16, pady=(0, 14))
        item_var = tk.StringVar()
        date_var = tk.StringVar(value=iso_today())
        units_var = tk.StringVar(value="0")
        notes_var = tk.StringVar()
        for idx, (lab, var) in enumerate([("Item", item_var), ("Date Received YYYY-MM-DD", date_var), ("Units Received", units_var), ("Notes", notes_var)]):
            tk.Label(body, text=lab, bg=BLUE_PANEL, fg=TEXT).grid(row=idx, column=0, sticky="w", padx=10, pady=8)
            if idx == 0:
                e = ttk.Combobox(body, textvariable=var, values=self.item_dropdown_values(), width=70, state="readonly")
                if e["values"]:
                    e.current(0)
            else:
                e = tk.Entry(body, textvariable=var, bg=INPUT_BG, fg=TEXT, insertbackground=TEXT, relief="solid", bd=1)
            e.grid(row=idx, column=1, sticky="ew", padx=10, pady=8)
        body.columnconfigure(1, weight=1)

        def save_received():
            item_id = self.selected_item_id_from_value(item_var.get())
            if item_id is None:
                messagebox.showerror(APP_NAME, "Select an item.")
                return
            try:
                units = float(units_var.get())
                if units <= 0:
                    raise ValueError("Units received must be greater than zero.")
                self.db.add_received(item_id, parse_date(date_var.get()).isoformat(), units, notes_var.get())
                self.db.backup_database("change")
                units_var.set("0")
                notes_var.set("")
                self.show_received()
            except Exception as ex:
                messagebox.showerror(APP_NAME, f"Could not save received inventory:\n{ex}")

        self.button(body, "Save Received Inventory", save_received).grid(row=4, column=1, sticky="w", padx=10, pady=14)

        p2, b2 = self.make_panel(self.content, "Recent Received Inventory")
        p2.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        cols = ("date", "group", "item", "units", "notes")
        tree = ttk.Treeview(b2, columns=cols, show="headings")
        for c, h, w in [("date","Date",110),("group","Group",170),("item","Item",310),("units","Units",90),("notes","Notes",320)]:
            tree.heading(c, text=h); tree.column(c, width=w, anchor="w")
        tree.pack(fill="both", expand=True)
        for r in self.db.recent_received(50):
            tree.insert("", "end", values=(r["received_date"], self.group_display_name(r["group_name"]), r["item_name"], r["units"], r["notes"] or ""))

    def show_log_session(self):
        self.clear_content()
        tk.Label(
            self.content,
            text="Submit Treatment",
            bg=BLUE_BG,
            fg=CYAN,
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w", padx=16, pady=12)

        panel, body = self.make_panel(self.content, "Treatment Entry")
        panel.pack(fill="x", padx=16, pady=(0, 12))

        date_var = tk.StringVar(value=iso_today())
        type_var = tk.StringVar(value="Regular Treatment")
        equiv_var = tk.StringVar(value="1")

        entry_rows = [
            ("Treatment Date YYYY-MM-DD", date_var, "entry"),
            ("Treatment Type", type_var, "combo"),
            ("Treatment Equivalent", equiv_var, "entry"),
        ]
        for index, (label_text, variable, control_type) in enumerate(entry_rows):
            tk.Label(
                body,
                text=label_text,
                bg=BLUE_PANEL,
                fg=TEXT,
                font=("Segoe UI", 10),
            ).grid(row=index, column=0, sticky="nw", padx=10, pady=7)
            if control_type == "combo":
                control = ttk.Combobox(
                    body,
                    textvariable=variable,
                    values=[
                        "Regular Treatment",
                        "Extra Treatment",
                        "Missed Treatment",
                        "Incomplete Treatment",
                    ],
                    width=30,
                    state="readonly",
                )
            else:
                control = tk.Entry(
                    body,
                    textvariable=variable,
                    bg=INPUT_BG,
                    fg=TEXT,
                    insertbackground=TEXT,
                    relief="solid",
                    bd=1,
                    width=34,
                )
            control.grid(row=index, column=1, sticky="w", padx=10, pady=7)

        tk.Label(
            body,
            text="Treatment Notes:",
            bg=BLUE_PANEL,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=3, column=0, sticky="nw", padx=10, pady=7)

        treatment_notes = tk.Text(
            body,
            height=4,
            width=72,
            wrap="word",
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="solid",
            bd=1,
            font=("Segoe UI", 10),
        )
        treatment_notes.grid(row=3, column=1, sticky="ew", padx=10, pady=7)
        body.columnconfigure(1, weight=1)

        tk.Label(
            body,
            text="Equivalent: Regular/Extra = 1, Missed = 0, Incomplete = 0.5 or another decimal.",
            bg=BLUE_PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))

        def adjust_equivalent(*_args):
            if type_var.get() == "Missed Treatment":
                equiv_var.set("0")
            elif type_var.get() == "Incomplete Treatment":
                equiv_var.set("0.5")
            else:
                equiv_var.set("1")

        type_var.trace_add("write", adjust_equivalent)

        def save_treatment():
            try:
                equivalent = float(equiv_var.get())
                if equivalent < 0:
                    raise ValueError("Treatment equivalent cannot be negative.")
                notes = treatment_notes.get("1.0", "end-1c").strip()
                self.db.add_session(
                    parse_date(date_var.get()).isoformat(),
                    type_var.get(),
                    equivalent,
                    notes,
                )
                self.db.backup_database("change")
                treatment_notes.delete("1.0", "end")
                self.show_log_session()
            except Exception as ex:
                messagebox.showerror(
                    APP_NAME,
                    f"Could not save treatment:\n{ex}",
                )

        self.button(
            body, "Submit Treatment", save_treatment
        ).grid(row=5, column=1, sticky="w", padx=10, pady=12)

        history_panel, history_body = self.make_panel(
            self.content, "Treatment History"
        )
        history_panel.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        tree_frame = tk.Frame(history_body, bg=BLUE_PANEL)
        tree_frame.pack(fill="both", expand=True)

        self.style.configure(
            "TreatmentHistory.Treeview",
            background=BLUE_PANEL,
            foreground=TEXT,
            fieldbackground=BLUE_PANEL,
            rowheight=36,
            font=("Segoe UI", 12),
        )
        self.style.configure(
            "TreatmentHistory.Treeview.Heading",
            background=BLUE_HEADER,
            foreground=TEXT,
            font=("Segoe UI", 12, "bold"),
        )
        self.style.map(
            "TreatmentHistory.Treeview",
            background=[("selected", "#126A9F")],
            foreground=[("selected", "white")],
        )

        treatment_tree = ttk.Treeview(
            tree_frame,
            columns=("date", "type"),
            show="headings",
            height=8,
            style="TreatmentHistory.Treeview",
        )
        for column, heading, width in [
            ("date", "Date", 160),
            ("type", "Treatment Type", 360),
        ]:
            treatment_tree.heading(column, text=heading)
            treatment_tree.column(
                column,
                width=width,
                stretch=True,
                anchor="w",
            )
        treatment_tree.pack(fill="both", expand=True)

        notes_header = tk.Frame(history_body, bg=BLUE_PANEL)
        notes_header.pack(fill="x", pady=(10, 5))
        tk.Label(
            notes_header,
            text="Treatment Notes:",
            bg=BLUE_PANEL,
            fg=CYAN,
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left")

        selected_session_id = {"value": None}

        notes_reader = tk.Text(
            history_body,
            height=6,
            wrap="word",
            bg="#052A43",
            fg=TEXT,
            insertbackground=TEXT,
            relief="solid",
            bd=1,
            font=("Segoe UI", 12),
            state="disabled",
        )
        notes_reader.pack(fill="x")

        edit_button = self.button(notes_header, "Edit", lambda: None)
        save_button = self.button(notes_header, "Save Notes", lambda: None)
        save_button.config(state="disabled")
        save_button.pack(side="right", padx=(6, 0))
        edit_button.pack(side="right")

        def show_selected_notes(_event=None):
            selection = treatment_tree.selection()
            if not selection:
                selected_session_id["value"] = None
                text = ""
            else:
                selected_session_id["value"] = int(selection[0])
                record = self.db.session_by_id(selected_session_id["value"])
                text = (record["notes"] or "") if record else ""

            notes_reader.config(state="normal")
            notes_reader.delete("1.0", "end")
            notes_reader.insert("1.0", text)
            notes_reader.config(state="disabled")
            edit_button.config(state="normal" if selection else "disabled")
            save_button.config(state="disabled")

        def edit_selected_notes():
            if selected_session_id["value"] is None:
                return
            notes_reader.config(state="normal")
            notes_reader.focus_set()
            save_button.config(state="normal")
            edit_button.config(state="disabled")

        def save_selected_notes():
            session_id = selected_session_id["value"]
            if session_id is None:
                return
            notes = notes_reader.get("1.0", "end-1c").strip()
            self.db.update_session_notes(session_id, notes)
            self.db.backup_database("change")
            notes_reader.config(state="disabled")
            save_button.config(state="disabled")
            edit_button.config(state="normal")

        edit_button.config(command=edit_selected_notes, state="disabled")
        save_button.config(command=save_selected_notes)

        treatment_tree.bind("<<TreeviewSelect>>", show_selected_notes)

        for record in self.db.recent_sessions(100):
            treatment_tree.insert(
                "",
                "end",
                iid=str(record["id"]),
                values=(
                    record["session_date"],
                    record["session_type"],
                ),
            )

    def show_settings(self):
        self.clear_content()
        tk.Label(self.content, text="Settings / Items", bg=BLUE_BG, fg=CYAN, font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=12)
        panel, body = self.make_panel(self.content, "General and Schedule Settings")
        panel.pack(fill="x", padx=16, pady=(0, 14))
        patient_var = tk.StringVar(value=self.db.get_setting("patient_name", "Patient Name"))
        sessions_var = tk.StringVar(value=self.db.get_setting("sessions_per_week", "4"))
        first_day_var = tk.StringVar(value=self.db.get_setting("first_session_day", "Sunday"))
        nx_group_var = tk.StringVar(value=self.group_display_name(GROUP_NX))
        dv_group_var = tk.StringVar(value=self.group_display_name(GROUP_DV))
        rows = [
            ("Patient Name", patient_var, "entry"),
            ("Dialysis Sessions Per Week", sessions_var, "entry"),
            ("Week's First Session Day", first_day_var, "combo"),
            ("First Inventory Group Name", nx_group_var, "entry"),
            ("Second Inventory Group Name", dv_group_var, "entry"),
        ]
        for idx, (lab, var, typ) in enumerate(rows):
            tk.Label(body, text=lab, bg=BLUE_PANEL, fg=TEXT).grid(row=idx, column=0, sticky="w", padx=10, pady=8)
            if typ == "combo":
                e = ttk.Combobox(body, textvariable=var, values=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"], width=30, state="readonly")
            else:
                e = tk.Entry(body, textvariable=var, bg=INPUT_BG, fg=TEXT, insertbackground=TEXT, relief="solid", bd=1, width=34)
            e.grid(row=idx, column=1, sticky="w", padx=10, pady=8)

        def save_settings():
            try:
                float(sessions_var.get())
                self.db.set_setting("patient_name", patient_var.get().strip() or "Patient Name")
                self.db.set_setting("sessions_per_week", sessions_var.get().strip() or "4")
                self.db.set_setting("first_session_day", first_day_var.get())
                self.db.set_setting("group_nx_display_name", nx_group_var.get().strip() or GROUP_NX)
                self.db.set_setting("group_dv_display_name", dv_group_var.get().strip() or GROUP_DV)
                self.save_local_settings()
                for widget in self.sidebar.winfo_children():
                    widget.destroy()
                self.build_sidebar()
                self.show_settings()
            except Exception as ex:
                messagebox.showerror(APP_NAME, f"Could not save settings:\n{ex}")
        self.button(body, "Save Settings", save_settings).grid(row=5, column=1, sticky="w", padx=10, pady=14)

        p2, b2 = self.make_panel(self.content, "Item Management")
        p2.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        row = tk.Frame(b2, bg=BLUE_PANEL)
        row.pack(fill="x", pady=(0, 8))
        self.button(row, f"Add {self.group_display_name(GROUP_NX)} Item", lambda: self.open_item_editor(None, GROUP_NX)).pack(side="left", padx=4)
        self.button(row, f"Add {self.group_display_name(GROUP_DV)} Item", lambda: self.open_item_editor(None, GROUP_DV)).pack(side="left", padx=4)
        tk.Label(row, text="Open a supply page to edit, rename, or remove existing items.", bg=BLUE_PANEL, fg=MUTED).pack(side="left", padx=12)

    def export_csv(self):
        filename = filedialog.asksaveasfilename(title="Export inventory CSV", defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not filename:
            return
        try:
            self.db.export_csv(filename)
            messagebox.showinfo(APP_NAME, f"Exported:\n{filename}")
        except Exception as ex:
            messagebox.showerror(APP_NAME, f"Export failed:\n{ex}")

if __name__ == "__main__":
    app = HHDApp()
    app.mainloop()
