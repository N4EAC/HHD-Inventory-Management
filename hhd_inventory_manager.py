
#!/usr/bin/env python3
"""
HHD Inventory Manager v1.5.5

Changes in v0.1.1:
- Rename inventory items
- Add new inventory items to NxStage or DaVita
- Deactivate/remove inventory items
- Keeps historical received/session/correction records safe because items are deactivated, not physically deleted
"""

import os
import sys
import sqlite3
import csv
import ctypes
import ctypes.wintypes
import json
import shutil
import math
import webbrowser
import calendar
import tkinter.font as tkfont
from datetime import datetime, date, timedelta
import tkinter as tk
import time
from tkinter import ttk, messagebox, filedialog

APP_NAME = "HHD Inventory Manager"
APP_VERSION = "1.5.5"
DB_NAME = "hhd_inventory.db"
SETTINGS_FILE = "hhd_inventory_settings.json"
APP_FOLDER_NAME = "HHD Inventory Manager"
BACKUP_FOLDER_NAME = "HHD Inventory Backups"
ROLLING_DB_BACKUP_NAME = "HHD_Inventory_Backup_Current.db"
ROLLING_SETTINGS_BACKUP_NAME = "HHD_Settings_Backup_Current.json"
AUTO_BACKUP_INTERVAL_MS = 10 * 60 * 1000


def treatment_type_key(session_type):
    """Return the stable internal category for a stored treatment label."""
    value = str(session_type or "").strip().lower()
    if "in center" in value or "in-center" in value:
        return "in_center"
    if "missed" in value:
        return "missed"
    if "incomplete" in value:
        return "incomplete"
    return "complete"


def treatment_uses_inventory(session_type):
    return treatment_type_key(session_type) not in {"missed", "in_center"}


THEMES = {
    "Medical Blue": {
        "bg": "#062A44",
        "panel": "#083B5E",
        "panel2": "#0B456E",
        "header": "#0A5F92",
        "accent": "#5ED8FF",
        "text": "#EAF8FF",
        "muted": "#A9D6E8",
        "green": "#59D65C",
        "yellow": "#FFD52E",
        "red": "#FF5A4E",
        "border": "#2A8CC4",
        "input": "#0D304D",
        "button": "#0D5D8C",
        "button_hover": "#1479B5",
        "panel_title": "#052239",
        "status": "#031B2D",
        "chart": "#052A43",
        "select": "#126A9F",
        "calendar_empty": "#0A3553",
        "dark_titlebar": True,
    },
    "Beige": {
        "bg": "#E8DDC7",
        "panel": "#F5EEDC",
        "panel2": "#E1D2B5",
        "header": "#9A6B3F",
        "accent": "#6D3F1F",
        "text": "#2D241C",
        "muted": "#6B5B4B",
        "green": "#2E7D32",
        "yellow": "#B8860B",
        "red": "#B3261E",
        "border": "#B99A72",
        "input": "#FFF9EC",
        "button": "#A87545",
        "button_hover": "#8B5D34",
        "panel_title": "#D2B890",
        "status": "#C9B18C",
        "chart": "#FFF9EC",
        "select": "#8B5D34",
        "calendar_empty": "#F0E4CD",
        "dark_titlebar": False,
    },
    "Dark": {
        "bg": "#121417",
        "panel": "#1D2228",
        "panel2": "#252B32",
        "header": "#343B44",
        "accent": "#7CC7FF",
        "text": "#F2F4F7",
        "muted": "#B2BAC4",
        "green": "#55D66B",
        "yellow": "#FFD54A",
        "red": "#FF6B62",
        "border": "#505A66",
        "input": "#171B20",
        "button": "#3A4652",
        "button_hover": "#4B5B69",
        "panel_title": "#171B20",
        "status": "#0D0F12",
        "chart": "#11161B",
        "select": "#365D78",
        "calendar_empty": "#20262D",
        "dark_titlebar": True,
    },    "Gray 95": {
        "bg": "#C0C0C0",
        "panel": "#D4D0C8",
        "panel2": "#E0E0E0",
        "header": "#000080",
        "accent": "#000080",
        "text": "#000000",
        "muted": "#555555",
        "green": "#008000",
        "yellow": "#A07000",
        "red": "#C00000",
        "border": "#808080",
        "input": "#FFFFFF",
        "button": "#D4D0C8",
        "button_hover": "#B8B8B8",
        "panel_title": "#C0C0C0",
        "status": "#D4D0C8",
        "chart": "#FFFFFF",
        "select": "#000080",
        "calendar_empty": "#E8E8E8",
        "header_text": "#FFFFFF",
        "selected_text": "#FFFFFF",
        "blue_button_text": "#FFFFFF",
        "dark_titlebar": False,
    },
    "Red Shadow": {
        "bg": "#160A0D",
        "panel": "#251014",
        "panel2": "#32151B",
        "header": "#7A101D",
        "accent": "#FF6677",
        "text": "#FFF4F5",
        "muted": "#D7A8AE",
        "green": "#62D985",
        "yellow": "#FFD65A",
        "red": "#FF5266",
        "border": "#A92A3A",
        "input": "#1C0C10",
        "button": "#8C1827",
        "button_hover": "#B3263A",
        "panel_title": "#100609",
        "status": "#0A0305",
        "chart": "#12070A",
        "select": "#A61D31",
        "calendar_empty": "#2A1116",
        "header_text": "#FFFFFF",
        "selected_text": "#FFFFFF",
        "blue_button_text": "#FFFFFF",
        "dark_titlebar": True,
    },
    "Cyberpunk": {
        "bg": "#090B14",
        "panel": "#111526",
        "panel2": "#171D33",
        "header": "#291447",
        "accent": "#00F5FF",
        "text": "#F7F7FF",
        "muted": "#A9B0D0",
        "green": "#39FF88",
        "yellow": "#FFE94A",
        "red": "#FF3B7A",
        "border": "#8A2BE2",
        "input": "#0D1020",
        "button": "#3B1763",
        "button_hover": "#5A218F",
        "panel_title": "#160D2A",
        "status": "#07080F",
        "chart": "#080B18",
        "select": "#00A9B8",
        "calendar_empty": "#12172A",
        "dark_titlebar": True,
    },

}

def set_theme_palette(theme_name):
    """Apply a named palette to the module-level colors used by the UI."""
    global BLUE_BG, BLUE_PANEL, BLUE_PANEL_2, BLUE_HEADER
    global CYAN, TEXT, MUTED, GREEN, YELLOW, RED, BORDER
    global INPUT_BG, BUTTON_BG, BUTTON_HOVER
    global PANEL_TITLE_BG, STATUS_BG, CHART_BG, SELECT_BG, CALENDAR_EMPTY
    global HEADER_TEXT, SELECTED_TEXT, BLUE_BUTTON_TEXT

    theme = THEMES.get(theme_name, THEMES["Medical Blue"])
    BLUE_BG = theme["bg"]
    BLUE_PANEL = theme["panel"]
    BLUE_PANEL_2 = theme["panel2"]
    BLUE_HEADER = theme["header"]
    CYAN = theme["accent"]
    TEXT = theme["text"]
    MUTED = theme["muted"]
    GREEN = theme["green"]
    YELLOW = theme["yellow"]
    RED = theme["red"]
    BORDER = theme["border"]
    INPUT_BG = theme["input"]
    BUTTON_BG = theme["button"]
    BUTTON_HOVER = theme["button_hover"]
    PANEL_TITLE_BG = theme["panel_title"]
    STATUS_BG = theme["status"]
    CHART_BG = theme["chart"]
    SELECT_BG = theme["select"]
    CALENDAR_EMPTY = theme["calendar_empty"]
    HEADER_TEXT = theme.get("header_text", TEXT)
    SELECTED_TEXT = theme.get("selected_text", "#FFFFFF")
    BLUE_BUTTON_TEXT = theme.get("blue_button_text", TEXT)
    return theme

set_theme_palette("Medical Blue")

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
    return getattr(
        sys,
        "_MEIPASS",
        os.path.dirname(os.path.abspath(__file__)),
    )

def user_data_dir():
    """Writable per-user application data folder.

    Keep one database format across platforms while using each operating
    system's normal writable application-data location.
    """
    home = os.path.expanduser("~")
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            home,
            "AppData",
            "Local",
        )
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(
            home,
            ".local",
            "share",
        )
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

def about_icon_png_path():
    return os.path.join(app_dir(), "hhd_inventory_manager_about.png")

def menu_icon_png_path():
    return os.path.join(app_dir(), "hhd_menu_icon.png")

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

def request_windows_titlebar(hwnd, caption_color=None, text_color=None, border_color=None, dark_mode=None):
    """Apply the current Windows 10/11 application title-bar theme."""
    if os.name != "nt":
        return
    try:
        import winreg
        key_path = (
            r"Software\Microsoft\Windows\CurrentVersion"
            r"\Themes\Personalize"
        )
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            apps_use_light, _ = winreg.QueryValueEx(
                key, "AppsUseLightTheme"
            )
        use_dark = ctypes.c_int(0 if apps_use_light else 1)

        # Tk's winfo_id can identify the client window; use its native
        # parent when available so DWM styles the actual title bar.
        native_hwnd = ctypes.windll.user32.GetParent(hwnd) or hwnd
        for attribute in (20, 19):
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.wintypes.HWND(native_hwnd),
                ctypes.c_int(attribute),
                ctypes.byref(use_dark),
                ctypes.sizeof(use_dark),
            )
            if result == 0:
                break

        flags = 0x0020 | 0x0001 | 0x0002 | 0x0004
        ctypes.windll.user32.SetWindowPos(
            native_hwnd, 0, 0, 0, 0, 0, flags
        )
    except Exception:
        pass

def iso_today():
    return date.today().isoformat()

def parse_date(value, fallback=None):
    if not value:
        return fallback or date.today()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except Exception:
            pass
    return fallback or date.today()

def round_half_unit(value):
    """Inventory quantities are represented only as whole or half units."""
    return round(float(value) * 2.0) / 2.0

def validate_half_unit(value, field_name="Value"):
    number = float(value)
    normalized = round_half_unit(number)
    if abs(number - normalized) > 1e-8:
        raise ValueError(f"{field_name} must be a whole number or end in .5.")
    return normalized

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
            allow_half_removal INTEGER NOT NULL DEFAULT 0,
            disallow_half_usage INTEGER NOT NULL DEFAULT 0,
            baseline_received_cutoff_id INTEGER NOT NULL DEFAULT 0,
            baseline_correction_cutoff_id INTEGER NOT NULL DEFAULT 0,
            baseline_session_cutoff_id INTEGER NOT NULL DEFAULT 0,
            last_inventory_update_date TEXT NOT NULL DEFAULT '',
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
            notes TEXT,
            pak_lot TEXT NOT NULL DEFAULT '',
            sak_lot TEXT NOT NULL DEFAULT '',
            cartridge_lot TEXT NOT NULL DEFAULT '',
            cycler_serial TEXT NOT NULL DEFAULT '',
            pureflow_serial TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS session_item_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            units_used REAL NOT NULL,
            FOREIGN KEY(session_id) REFERENCES session_log(id),
            FOREIGN KEY(item_id) REFERENCES items(id)
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
        # incomplete treatment. Missed and in-center treatments never consume
        # a slot.
        item_columns = {
            row["name"] for row in c.execute("PRAGMA table_info(items)").fetchall()
        }
        if "full_attempt_usage" not in item_columns:
            c.execute(
                "ALTER TABLE items ADD COLUMN full_attempt_usage INTEGER NOT NULL DEFAULT 0"
            )
        if "allow_half_removal" not in item_columns:
            c.execute(
                "ALTER TABLE items ADD COLUMN allow_half_removal INTEGER NOT NULL DEFAULT 0"
            )
        if "disallow_half_usage" not in item_columns:
            c.execute(
                "ALTER TABLE items ADD COLUMN disallow_half_usage INTEGER NOT NULL DEFAULT 0"
            )
        for column_name in (
            "baseline_received_cutoff_id",
            "baseline_correction_cutoff_id",
            "baseline_session_cutoff_id",
        ):
            if column_name not in item_columns:
                c.execute(
                    f"ALTER TABLE items ADD COLUMN "
                    f"{column_name} INTEGER NOT NULL DEFAULT 0"
                )
        if "last_inventory_update_date" not in item_columns:
            c.execute(
                "ALTER TABLE items ADD COLUMN "
                "last_inventory_update_date TEXT NOT NULL DEFAULT ''"
            )

        session_columns = {
            row["name"] for row in c.execute(
                "PRAGMA table_info(session_log)"
            ).fetchall()
        }
        treatment_identity_columns = {
            "pak_lot": "TEXT NOT NULL DEFAULT ''",
            "sak_lot": "TEXT NOT NULL DEFAULT ''",
            "cartridge_lot": "TEXT NOT NULL DEFAULT ''",
            "cycler_serial": "TEXT NOT NULL DEFAULT ''",
            "pureflow_serial": "TEXT NOT NULL DEFAULT ''",
        }
        for column_name, column_definition in treatment_identity_columns.items():
            if column_name not in session_columns:
                c.execute(
                    f"ALTER TABLE session_log ADD COLUMN "
                    f"{column_name} {column_definition}"
                )

        defaults = {
            "patient_name": "Patient Name",
            "sessions_per_week": "4",
            "first_session_day": "Sunday",
            "group_nx_display_name": "NxStage Supplies",
            "group_dv_display_name": "DaVita Supplies",
            "created_date": iso_today(),
            "last_pak_lot": "",
            "last_sak_lot": "",
            "last_cartridge_lot": "",
            "last_cycler_serial": "",
            "last_pureflow_serial": "",
            "inventory_reconciliation_v15": "0",
            "inventory_last_verified_at": "",
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
                 auto_session_usage=1, full_attempt_usage=0,
                 allow_half_removal=0, disallow_half_usage=0):
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
                auto_session_usage,full_attempt_usage,allow_half_removal,
                disallow_half_usage,last_inventory_update_date,active
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
        """, (
            group_name, item_name, float(baseline_units), baseline_date,
            float(min_threshold), float(low_threshold), float(units_per_session),
            float(units_per_week), max(float(reusable_sessions), 1.0),
            int(lifespan_days), int(auto_session_usage), int(full_attempt_usage),
            int(allow_half_removal), int(disallow_half_usage), baseline_date
        ))
        self.conn.commit()

    def update_item(self, item_id, **kwargs):
        allowed = {
            "group_name", "item_name", "baseline_units", "baseline_date", "min_threshold",
            "low_threshold", "units_per_session", "units_per_week", "reusable_sessions",
            "lifespan_days", "auto_session_usage", "full_attempt_usage",
            "allow_half_removal", "disallow_half_usage",
            "last_inventory_update_date", "active"
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

    def snapshot_item_to_current(
        self,
        item_id,
        snapshot_date=None,
        current_value=None,
    ):
        """
        Synchronize one item's stored baseline with its calculated current
        inventory quantity.

        Transaction cutoffs make the snapshot mathematically neutral:
        transactions already represented in baseline_units are excluded from
        future current-count calculations, while later same-day transactions
        continue to apply normally.
        """
        item = self.item_by_id(item_id)
        if not item:
            raise ValueError("Inventory item was not found.")

        snapshot_day = parse_date(snapshot_date or iso_today())
        snapshot_iso = snapshot_day.isoformat()

        if current_value is None:
            current_value = self.current_count(item)[0]
        current_value = round_half_unit(current_value)

        received_cutoff = self.conn.execute(
            """SELECT COALESCE(MAX(id),0) AS value
               FROM received_inventory
               WHERE item_id=? AND received_date<=?""",
            (item_id, snapshot_iso),
        ).fetchone()["value"]

        correction_cutoff = self.conn.execute(
            """SELECT COALESCE(MAX(id),0) AS value
               FROM corrections
               WHERE item_id=? AND correction_date<=?""",
            (item_id, snapshot_iso),
        ).fetchone()["value"]

        session_cutoff = self.conn.execute(
            """SELECT COALESCE(MAX(id),0) AS value
               FROM session_log
               WHERE session_date<=?""",
            (snapshot_iso,),
        ).fetchone()["value"]

        self.conn.execute(
            """UPDATE items
               SET baseline_units=?,
                   baseline_date=?,
                   baseline_received_cutoff_id=?,
                   baseline_correction_cutoff_id=?,
                   baseline_session_cutoff_id=?,
                   last_inventory_update_date=?
               WHERE id=?""",
            (
                current_value,
                snapshot_iso,
                int(received_cutoff or 0),
                int(correction_cutoff or 0),
                int(session_cutoff or 0),
                snapshot_iso,
                item_id,
            ),
        )

        return current_value

    def add_received(self, item_id, received_date, units, notes=""):
        """
        Record received inventory and make the resulting quantity the new
        current/baseline inventory count for the item.

        Transaction cutoffs prevent the received stock or any earlier activity
        on the same date from being counted twice. New activity recorded later
        on the same date is still applied normally.
        """
        item = self.item_by_id(item_id)
        if not item:
            raise ValueError("Inventory item was not found.")

        received_day = parse_date(received_date)
        baseline_day = parse_date(
            item["baseline_date"]
            or self.get_setting("created_date", iso_today())
        )
        if received_day < baseline_day:
            raise ValueError(
                "Received inventory date cannot be earlier than the "
                "item's current inventory count date."
            )

        current_before = self.historical_count_as_of(item, received_day)
        if current_before is None:
            current_before = float(item["baseline_units"])

        units = validate_half_unit(units, "Units received")
        new_baseline = round_half_unit(float(current_before) + units)
        received_iso = received_day.isoformat()

        try:
            self.conn.execute("BEGIN")
            self.conn.execute(
                """INSERT INTO received_inventory(
                       item_id,received_date,units,notes
                   ) VALUES(?,?,?,?)""",
                (item_id, received_iso, units, notes),
            )

            received_cutoff = self.conn.execute(
                """SELECT COALESCE(MAX(id),0) AS value
                   FROM received_inventory
                   WHERE item_id=? AND received_date<=?""",
                (item_id, received_iso),
            ).fetchone()["value"]

            correction_cutoff = self.conn.execute(
                """SELECT COALESCE(MAX(id),0) AS value
                   FROM corrections
                   WHERE item_id=? AND correction_date<=?""",
                (item_id, received_iso),
            ).fetchone()["value"]

            session_cutoff = self.conn.execute(
                """SELECT COALESCE(MAX(id),0) AS value
                   FROM session_log
                   WHERE session_date<=?""",
                (received_iso,),
            ).fetchone()["value"]

            self.conn.execute(
                """UPDATE items
                   SET baseline_units=?,
                       baseline_date=?,
                       baseline_received_cutoff_id=?,
                       baseline_correction_cutoff_id=?,
                       baseline_session_cutoff_id=?,
                       last_inventory_update_date=?
                   WHERE id=?""",
                (
                    new_baseline,
                    received_iso,
                    int(received_cutoff or 0),
                    int(correction_cutoff or 0),
                    int(session_cutoff or 0),
                    received_iso,
                    item_id,
                ),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        return new_baseline

    def add_correction(self, item_id, correction_date, units_delta, notes=""):
        delta = validate_half_unit(units_delta, "Correction")
        correction_iso = parse_date(correction_date).isoformat()

        item = self.item_by_id(item_id)
        if not item:
            raise ValueError("Inventory item was not found.")

        try:
            self.conn.execute("BEGIN")
            self.conn.execute(
                """INSERT INTO corrections(
                       item_id,correction_date,units_delta,notes
                   ) VALUES(?,?,?,?)""",
                (item_id, correction_iso, delta, notes),
            )

            refreshed = self.item_by_id(item_id)
            current_after = self.current_count(refreshed)[0]
            self.snapshot_item_to_current(
                item_id,
                correction_iso,
                current_after,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        return current_after

    def remove_existing_half_unit(self, item_id, notes="Half-used item removed"):
        """
        Remove the existing .5 fraction and immediately synchronize the
        item's baseline snapshot to the resulting Dashboard quantity.
        """
        item = self.item_by_id(item_id)
        if not item:
            raise ValueError("Inventory item was not found.")

        before, *_ = self.current_count(item)
        fractional = round(before - math.floor(before), 8)
        if abs(fractional - 0.5) > 1e-8:
            raise ValueError(
                f"The current total is {before:g}. "
                "This action is only available when the total ends in .5."
            )

        baseline_date = parse_date(
            item["baseline_date"]
            or self.get_setting("created_date", iso_today())
        )
        effective_date = max(date.today(), baseline_date)
        target = round_half_unit(before - 0.5)

        after = self.add_correction(
            item_id,
            effective_date.isoformat(),
            -0.5,
            notes,
        )

        refreshed = self.item_by_id(item_id)
        baseline_after = round_half_unit(
            float(refreshed["baseline_units"])
        )
        current_after = round_half_unit(
            self.current_count(refreshed)[0]
        )

        if (
            abs(after - target) > 1e-8
            or abs(current_after - target) > 1e-8
            or abs(baseline_after - target) > 1e-8
        ):
            raise RuntimeError(
                "Half-unit removal failed baseline/current verification: "
                f"expected {target:g}, baseline is {baseline_after:g}, "
                f"current is {current_after:g}."
            )

        return before, current_after


    def add_session(
        self,
        session_date,
        session_type,
        session_equivalent,
        notes="",
        pak_lot="",
        sak_lot="",
        cartridge_lot="",
        cycler_serial="",
        pureflow_serial="",
    ):
        if not treatment_uses_inventory(session_type):
            # Keep imports and future clients (including macOS) inventory-safe.
            session_equivalent = 0

        values = {
            "pak_lot": str(pak_lot).strip(),
            "sak_lot": str(sak_lot).strip(),
            "cartridge_lot": str(cartridge_lot).strip(),
            "cycler_serial": str(cycler_serial).strip(),
            "pureflow_serial": str(pureflow_serial).strip(),
        }
        for label, value in [
            ("PAK lot number", values["pak_lot"]),
            ("SAK lot number", values["sak_lot"]),
            ("Cartridge lot number", values["cartridge_lot"]),
            ("Cycler serial number", values["cycler_serial"]),
            ("PureFlow serial number", values["pureflow_serial"]),
        ]:
            if len(value) > 80:
                raise ValueError(f"{label} must be 80 characters or fewer.")

        cursor = self.conn.execute(
            """INSERT INTO session_log(
                   session_date, session_type, session_equivalent, notes,
                   pak_lot, sak_lot, cartridge_lot,
                   cycler_serial, pureflow_serial
               ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                session_date,
                session_type,
                session_equivalent,
                notes,
                values["pak_lot"],
                values["sak_lot"],
                values["cartridge_lot"],
                values["cycler_serial"],
                values["pureflow_serial"],
            ),
        )

        if treatment_uses_inventory(session_type):
            remembered_values = [
                ("last_pak_lot", values["pak_lot"]),
                ("last_sak_lot", values["sak_lot"]),
                ("last_cartridge_lot", values["cartridge_lot"]),
                ("last_cycler_serial", values["cycler_serial"]),
                ("last_pureflow_serial", values["pureflow_serial"]),
            ]
            self.conn.executemany(
                "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
                remembered_values,
            )

        self.conn.commit()
        return cursor.lastrowid

    def add_session_item_usage(self, session_id, item_id, units_used):
        units = validate_half_unit(units_used, "Incomplete treatment units")
        if units < 0.5 or units > 10:
            raise ValueError("Incomplete treatment usage must be between 0.5 and 10 units.")
        self.conn.execute(
            "INSERT INTO session_item_usage(session_id,item_id,units_used) VALUES(?,?,?)",
            (session_id, item_id, units),
        )
        self.conn.commit()

    def session_item_usages(self, session_id):
        return self.conn.execute(
            """SELECT u.*, i.item_name, i.group_name
               FROM session_item_usage u JOIN items i ON i.id=u.item_id
               WHERE u.session_id=? ORDER BY i.group_name,i.item_name""",
            (session_id,),
        ).fetchall()

    def item_usage_for_session(self, item, session):
        treatment_key = treatment_type_key(session["session_type"])
        if treatment_key in {"missed", "in_center"}:
            return 0.0

        if treatment_key == "incomplete":
            row = self.conn.execute(
                """SELECT COALESCE(SUM(units_used),0) AS total
                   FROM session_item_usage
                   WHERE session_id=? AND item_id=?""",
                (session["id"], item["id"]),
            ).fetchone()
            explicit_usage = float(row["total"] or 0)
            if explicit_usage > 0:
                return explicit_usage

            # Special lifespan/attempt rule (for example SAK):
            # an attempted incomplete treatment still consumes the configured
            # reusable-session slot even when SAK was not manually listed.
            if (
                int(item["full_attempt_usage"] or 0) == 1
                and int(item["auto_session_usage"] or 0) == 1
            ):
                reusable = max(
                    float(item["reusable_sessions"] or 1),
                    1.0,
                )
                amount = float(item["units_per_session"] or 0) / reusable
                if int(item["disallow_half_usage"] or 0) == 1:
                    amount = math.ceil(amount - 1e-9)
                return float(amount)

            return 0.0

        if int(item["auto_session_usage"] or 0) != 1:
            return 0.0

        reusable = max(float(item["reusable_sessions"] or 1), 1.0)
        treatment_equivalent = float(session["session_equivalent"] or 1)
        amount = (
            float(item["units_per_session"] or 0)
            / reusable
            * treatment_equivalent
        )

        if int(item["disallow_half_usage"] or 0) == 1:
            amount = math.ceil(amount - 1e-9)

        return float(amount)

    def item_session_usage_units(self, item, since_date, through_date=None):
        """Calculate actual units used after the item's current baseline."""
        cutoff_id = int(item["baseline_session_cutoff_id"] or 0)
        params = [since_date, since_date, cutoff_id]
        end_clause = ""
        if through_date is not None:
            end_clause = " AND s.session_date<=?"
            params.append(through_date)

        sessions = self.conn.execute(
            f"""SELECT s.* FROM session_log s
                WHERE (
                    s.session_date>?
                    OR (s.session_date=? AND s.id>?)
                )
                {end_clause}
                ORDER BY s.session_date,s.id""",
            tuple(params),
        ).fetchall()

        total = 0.0
        for session in sessions:
            total += self.item_usage_for_session(item, session)
        return total


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

    def delete_session(self, session_id):
        """
        Delete a treatment and restore its inventory usage exactly.

        If a treatment has already been incorporated into an item's later
        baseline snapshot, the baseline is increased by that treatment's exact
        usage before the treatment record is removed.
        """
        record = self.session_by_id(session_id)
        if not record:
            raise ValueError("The selected treatment no longer exists.")

        usages = self.session_item_usages(session_id)
        treatment_day = parse_date(record["session_date"])

        baseline_adjustments = []
        for item in self.items(include_inactive=True):
            baseline_day = parse_date(
                item["baseline_date"]
                or self.get_setting("created_date", iso_today())
            )
            session_cutoff = int(
                item["baseline_session_cutoff_id"] or 0
            )
            baked_into_baseline = (
                treatment_day < baseline_day
                or (
                    treatment_day == baseline_day
                    and int(record["id"]) <= session_cutoff
                )
            )
            if not baked_into_baseline:
                continue

            amount = self.item_usage_for_session(item, record)
            if amount > 0:
                baseline_adjustments.append(
                    (float(amount), int(item["id"]))
                )

        try:
            self.conn.execute("BEGIN")

            for amount, item_id in baseline_adjustments:
                self.conn.execute(
                    """UPDATE items
                       SET baseline_units=baseline_units+?
                       WHERE id=?""",
                    (amount, item_id),
                )

            self.conn.execute(
                "DELETE FROM session_item_usage WHERE session_id=?",
                (session_id,),
            )
            cursor = self.conn.execute(
                "DELETE FROM session_log WHERE id=?",
                (session_id,),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("The treatment could not be deleted.")

            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        self.refresh_last_inventory_update_dates()
        return record, usages


    def received_sum(self, item, since_date):
        cutoff_id = int(item["baseline_received_cutoff_id"] or 0)
        row = self.conn.execute(
            """SELECT COALESCE(SUM(units),0) AS total
               FROM received_inventory
               WHERE item_id=?
                 AND (
                     received_date>?
                     OR (received_date=? AND id>?)
                 )""",
            (item["id"], since_date, since_date, cutoff_id),
        ).fetchone()
        return float(row["total"])

    def corrections_sum(self, item, since_date):
        cutoff_id = int(item["baseline_correction_cutoff_id"] or 0)
        row = self.conn.execute(
            """SELECT COALESCE(SUM(units_delta),0) AS total
               FROM corrections
               WHERE item_id=?
                 AND (
                     correction_date>?
                     OR (correction_date=? AND id>?)
                 )""",
            (item["id"], since_date, since_date, cutoff_id),
        ).fetchone()
        return float(row["total"])

    def session_usage_sum(self, item, since_date, through_date=None):
        """
        Return treatment-equivalent slots after the item's current baseline.
        """
        cutoff_id = int(item["baseline_session_cutoff_id"] or 0)
        params = [since_date, since_date, cutoff_id]
        end_clause = ""
        if through_date is not None:
            end_clause = " AND session_date<=?"
            params.append(through_date)

        if int(item["full_attempt_usage"] or 0) == 1:
            expression = """
                CASE
                    WHEN LOWER(TRIM(session_type)) LIKE '%missed%' THEN 0
                    WHEN LOWER(TRIM(session_type)) LIKE '%in center%' THEN 0
                    WHEN LOWER(TRIM(session_type)) LIKE '%in-center%' THEN 0
                    ELSE 1
                END
            """
        else:
            expression = """
                CASE
                    WHEN LOWER(TRIM(session_type)) LIKE '%missed%' THEN 0
                    WHEN LOWER(TRIM(session_type)) LIKE '%in center%' THEN 0
                    WHEN LOWER(TRIM(session_type)) LIKE '%in-center%' THEN 0
                    ELSE session_equivalent
                END
            """

        row = self.conn.execute(
            f"""SELECT COALESCE(SUM({expression}),0) AS total
                FROM session_log
                WHERE (
                    session_date>?
                    OR (session_date=? AND id>?)
                )
                {end_clause}""",
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

        received_cutoff = int(
            item["baseline_received_cutoff_id"] or 0
        )
        correction_cutoff = int(
            item["baseline_correction_cutoff_id"] or 0
        )

        received_row = self.conn.execute(
            """SELECT COALESCE(SUM(units),0) AS total
               FROM received_inventory
               WHERE item_id=?
                 AND (
                     received_date>?
                     OR (received_date=? AND id>?)
                 )
                 AND received_date<=?""",
            (
                item["id"],
                baseline_iso,
                baseline_iso,
                received_cutoff,
                as_of_iso,
            ),
        ).fetchone()
        correction_row = self.conn.execute(
            """SELECT COALESCE(SUM(units_delta),0) AS total
               FROM corrections
               WHERE item_id=?
                 AND (
                     correction_date>?
                     OR (correction_date=? AND id>?)
                 )
                 AND correction_date<=?""",
            (
                item["id"],
                baseline_iso,
                baseline_iso,
                correction_cutoff,
                as_of_iso,
            ),
        ).fetchone()
        received = float(received_row["total"])
        corrections = float(correction_row["total"])
        sessions = self.session_usage_sum(item, baseline_iso, as_of_iso)
        session_usage = self.item_session_usage_units(item, baseline_iso, as_of_iso)

        elapsed_weeks = max(0.0, (as_of - baseline_date).days / 7.0)
        weekly_usage = elapsed_weeks * float(item["units_per_week"])
        current = (
            float(item["baseline_units"])
            + received
            + corrections
            - session_usage
            - weekly_usage
        )
        return max(0.0, round_half_unit(current))

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

    def latest_item_activity_date(self, item):
        dates = []

        baseline_date = item["baseline_date"] or ""
        if baseline_date:
            dates.append(parse_date(baseline_date))

        row = self.conn.execute(
            """SELECT MAX(received_date) AS value
               FROM received_inventory
               WHERE item_id=?""",
            (item["id"],),
        ).fetchone()
        if row and row["value"]:
            dates.append(parse_date(row["value"]))

        row = self.conn.execute(
            """SELECT MAX(correction_date) AS value
               FROM corrections
               WHERE item_id=?""",
            (item["id"],),
        ).fetchone()
        if row and row["value"]:
            dates.append(parse_date(row["value"]))

        sessions = self.conn.execute(
            """SELECT * FROM session_log
               ORDER BY session_date,id"""
        ).fetchall()
        for session in sessions:
            if self.item_usage_for_session(item, session) > 0:
                dates.append(parse_date(session["session_date"]))

        # Time-based weekly deductions change the current quantity as time
        # advances, so today's date is the latest effective update date.
        if float(item["units_per_week"] or 0) > 0:
            dates.append(date.today())

        return max(dates) if dates else date.today()

    def touch_item_update_date(self, item_id, update_date):
        update_iso = parse_date(update_date).isoformat()
        self.conn.execute(
            """UPDATE items
               SET last_inventory_update_date=?
               WHERE id=?""",
            (update_iso, item_id),
        )

    def refresh_last_inventory_update_dates(self):
        for item in self.items(include_inactive=True):
            latest = self.latest_item_activity_date(item).isoformat()
            self.conn.execute(
                """UPDATE items
                   SET last_inventory_update_date=?
                   WHERE id=?""",
                (latest, item["id"]),
            )
        self.conn.commit()

    def mark_treatment_inventory_update(self, session_id):
        session = self.session_by_id(session_id)
        if not session:
            return

        session_date = session["session_date"]
        for item in self.items(include_inactive=True):
            if self.item_usage_for_session(item, session) > 0:
                self.touch_item_update_date(item["id"], session_date)
        self.conn.commit()

    def verify_and_reconcile_inventory(self, progress_callback=None):
        """
        Verify inventory math on every startup.

        On the first v1.5+ startup, create a synchronized inventory snapshot:
        each item's baseline becomes its currently calculated Dashboard total.
        The snapshot date is today, while last_inventory_update_date preserves
        the actual last inventory activity date. Transaction cutoffs prevent
        historical activity from being counted again after the snapshot.
        """
        items = self.items(include_inactive=True)
        total = max(1, len(items))
        first_reconciliation = (
            self.get_setting("inventory_reconciliation_v15", "0") != "1"
        )

        if first_reconciliation:
            # One rolling safety backup before rewriting baseline snapshots.
            self.backup_database("change")

        snapshot_date = iso_today()
        results = []

        for index, item in enumerate(items, start=1):
            if progress_callback:
                progress_callback(
                    index - 1,
                    total,
                    f"Verifying {item['item_name']}..."
                )

            current, *_ = self.current_count(item)
            current = round_half_unit(current)
            last_update = self.latest_item_activity_date(item).isoformat()

            if first_reconciliation:
                received_cutoff = self.conn.execute(
                    """SELECT COALESCE(MAX(id),0) AS value
                       FROM received_inventory
                       WHERE item_id=? AND received_date<=?""",
                    (item["id"], snapshot_date),
                ).fetchone()["value"]

                correction_cutoff = self.conn.execute(
                    """SELECT COALESCE(MAX(id),0) AS value
                       FROM corrections
                       WHERE item_id=? AND correction_date<=?""",
                    (item["id"], snapshot_date),
                ).fetchone()["value"]

                session_cutoff = self.conn.execute(
                    """SELECT COALESCE(MAX(id),0) AS value
                       FROM session_log
                       WHERE session_date<=?""",
                    (snapshot_date,),
                ).fetchone()["value"]

                self.conn.execute(
                    """UPDATE items
                       SET baseline_units=?,
                           baseline_date=?,
                           baseline_received_cutoff_id=?,
                           baseline_correction_cutoff_id=?,
                           baseline_session_cutoff_id=?,
                           last_inventory_update_date=?
                       WHERE id=?""",
                    (
                        current,
                        snapshot_date,
                        int(received_cutoff or 0),
                        int(correction_cutoff or 0),
                        int(session_cutoff or 0),
                        last_update,
                        item["id"],
                    ),
                )
            else:
                baseline_value = round_half_unit(
                    float(item["baseline_units"])
                )
                if abs(current - baseline_value) > 1e-8:
                    # Repair drift left by older builds/manual corrections.
                    # This creates a neutral snapshot and prevents the same
                    # transactions from being counted twice afterwards.
                    self.snapshot_item_to_current(
                        item["id"],
                        snapshot_date,
                        current,
                    )
                else:
                    self.conn.execute(
                        """UPDATE items
                           SET last_inventory_update_date=?
                           WHERE id=?""",
                        (last_update, item["id"]),
                    )

            results.append((item["id"], current, last_update))

            if progress_callback:
                progress_callback(
                    index,
                    total,
                    f"Verified {item['item_name']}"
                )

        self.conn.execute(
            """INSERT OR REPLACE INTO settings(key,value)
               VALUES('inventory_reconciliation_v15','1')"""
        )
        verified_at = datetime.now().astimezone().isoformat(timespec="seconds")
        self.conn.execute(
            """INSERT OR REPLACE INTO settings(key,value)
               VALUES('inventory_last_verified_at',?)""",
            (verified_at,),
        )
        self.conn.commit()

        return {
            "items_verified": len(items),
            "reconciled": first_reconciliation,
            "verified_at": verified_at,
            "results": results,
        }

    def current_count(self, item):
        baseline = float(item["baseline_units"])
        since = item["baseline_date"] or self.get_setting("created_date", iso_today())
        received = self.received_sum(item, since)
        corrections = self.corrections_sum(item, since)
        sessions = self.session_usage_sum(item, since)
        session_usage = self.item_session_usage_units(item, since)

        weekly_usage = self.weeks_since(since) * float(item["units_per_week"])
        used = session_usage + weekly_usage
        current = round_half_unit(
            baseline + received + corrections - used
        )
        used = round_half_unit(used)
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
        if int(item["disallow_half_usage"] or 0) == 1:
            per_session = math.ceil(per_session - 1e-9)
        per_week = float(item["units_per_week"] or 0)
        weekly_rate = (per_session * sessions_per_week) + per_week

        if int(item["lifespan_days"] or 0) > 0:
            return (current * int(item["lifespan_days"])) / 7.0

        if weekly_rate <= 0:
            return None
        return current / weekly_rate

    def recent_sessions(self, limit=30):
        return self.conn.execute("SELECT * FROM session_log ORDER BY session_date DESC,id DESC LIMIT ?", (limit,)).fetchall()

    def sessions_between(self, start_date, end_date):
        def normalize(value):
            if isinstance(value, datetime):
                return value.date().isoformat()
            if isinstance(value, date):
                return value.isoformat()
            return parse_date(value).isoformat()

        return self.conn.execute(
            """SELECT * FROM session_log
               WHERE session_date>=? AND session_date<=?
               ORDER BY session_date,id""",
            (normalize(start_date), normalize(end_date)),
        ).fetchall()

    def search_treatment_lots(self, search_text):
        term = str(search_text or "").strip()
        if not term:
            return []
        pattern = f"%{term}%"
        return self.conn.execute(
            """SELECT * FROM session_log
               WHERE pak_lot LIKE ? COLLATE NOCASE
                  OR sak_lot LIKE ? COLLATE NOCASE
                  OR cartridge_lot LIKE ? COLLATE NOCASE
               ORDER BY session_date DESC, id DESC""",
            (pattern, pattern, pattern),
        ).fetchall()

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
        super().__init__(master, bg=STATUS_BG, highlightbackground=BORDER, highlightthickness=1)
        self.master = master
        self.on_close = on_close
        self._drag_x = 0
        self._drag_y = 0
        tk.Label(self, text="✚", fg=CYAN, bg=STATUS_BG, font=("Segoe UI", 14, "bold")).pack(side="left", padx=(12, 8), pady=6)
        tk.Label(self, text=title, fg=TEXT, bg=STATUS_BG, font=("Segoe UI", 12, "bold")).pack(side="left", pady=6)
        btns = tk.Frame(self, bg=STATUS_BG)
        btns.pack(side="right", padx=8)
        min_btn = tk.Label(btns, text="—", fg=CYAN, bg=STATUS_BG, font=("Segoe UI", 14), width=3, cursor="hand2")
        min_btn.pack(side="left")
        close_btn = tk.Label(btns, text="✕", fg=CYAN, bg=STATUS_BG, font=("Segoe UI", 13), width=3, cursor="hand2")
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


class ColorButton(tk.Label):
    """Flat button whose colors are honored by Windows, macOS, and Linux."""

    def __init__(
        self,
        master,
        text,
        command,
        bg,
        fg,
        activebackground,
        activeforeground,
        **kwargs,
    ):
        self.command = command
        self.normal_bg = bg
        self.normal_fg = fg
        self.active_bg = activebackground
        self.active_fg = activeforeground
        kwargs.setdefault("disabledforeground", MUTED)
        kwargs.setdefault("takefocus", True)
        super().__init__(master, text=text, bg=bg, fg=fg, **kwargs)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonRelease-1>", self._activate)
        self.bind("<Return>", self._activate)
        self.bind("<space>", self._activate)

    def _enabled(self):
        return str(self.cget("state")) != "disabled"

    def _enter(self, _event=None):
        if self._enabled():
            super().configure(bg=self.active_bg, fg=self.active_fg)

    def _leave(self, _event=None):
        super().configure(bg=self.normal_bg, fg=self.normal_fg)

    def _activate(self, _event=None):
        if self._enabled() and self.command:
            self.command()

class HHDApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = InventoryDB()
        self.settings_data = self.load_local_settings()
        self.current_theme = self.settings_data.get("theme", "Medical Blue")
        self.theme_palette = set_theme_palette(self.current_theme)
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
        request_windows_titlebar(
            self.winfo_id(),
            BLUE_BG,
            TEXT,
            BORDER,
            self.theme_palette.get("dark_titlebar", True),
        )

        self.inventory_font_default = 12
        self.inventory_font_min = self.inventory_font_default - 5
        self.inventory_font_max = self.inventory_font_default + 5
        try:
            saved_font_size = int(self.settings_data.get("inventory_font_size", self.inventory_font_default))
        except Exception:
            saved_font_size = self.inventory_font_default
        self.inventory_font_size = max(self.inventory_font_min, min(self.inventory_font_max, saved_font_size))
        self._inventory_font_labels = []
        self._responsive_trees = []

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.configure_styles()

        self.run_startup_database_verification()

        self.container = tk.Frame(self, bg=BLUE_BG)
        self.container.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(self.container, bg=BLUE_PANEL, width=215)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(self.container, bg=BLUE_BG)
        self.content.pack(side="left", fill="both", expand=True)

        self.statusbar = tk.Frame(self, bg=STATUS_BG, height=24, highlightbackground=BORDER, highlightthickness=1)
        self.statusbar.pack(fill="x", side="bottom")
        self.statusbar_label = tk.Label(
            self.statusbar,
            text=f"  Data is stored locally in {DB_NAME}    |    Version {APP_VERSION}",
            bg=STATUS_BG,
            fg=MUTED,
            anchor="w",
            font=("Segoe UI", 9),
        )
        self.statusbar_label.pack(fill="both")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Configure>", self.remember_window_geometry_event)
        self.create_status_led_images()
        self._status_trees = []
        self._blink_on = True
        self.build_windows_menu()
        self.build_sidebar()
        self.show_dashboard()
        self.schedule_clock_update()
        self.schedule_auto_backup()
        self.after(600, self.blink_status_leds)
        self.after(
            150,
            lambda: request_windows_titlebar(self.winfo_id()),
        )

    def run_startup_database_verification(self):
        # The main window must be realized before positioning a transient
        # frameless popup. Otherwise Windows may briefly place it at 0,0.
        self.update_idletasks()
        try:
            self.state("normal")
        except tk.TclError:
            pass
        self.update_idletasks()

        win = tk.Toplevel(self)
        win.withdraw()
        win.overrideredirect(True)
        win.configure(bg=BORDER)
        win.transient(self)

        outer = tk.Frame(
            win,
            bg=BLUE_PANEL,
            highlightbackground=BORDER,
            highlightthickness=2,
        )
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        tk.Label(
            outer,
            text="DB verification and update in progress",
            bg=BLUE_HEADER,
            fg=HEADER_TEXT,
            font=("Segoe UI", 13, "bold"),
            padx=18,
            pady=12,
        ).pack(fill="x")

        status_var = tk.StringVar(
            value="Preparing database verification..."
        )
        tk.Label(
            outer,
            textvariable=status_var,
            bg=BLUE_PANEL,
            fg=TEXT,
            font=("Segoe UI", 10),
            anchor="w",
            padx=18,
            pady=14,
        ).pack(fill="x")

        progress = ttk.Progressbar(
            outer,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            length=420,
        )
        progress.pack(fill="x", padx=18, pady=(0, 8))

        percent_var = tk.StringVar(value="0%")
        tk.Label(
            outer,
            textvariable=percent_var,
            bg=BLUE_PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
            anchor="e",
            padx=18,
            pady=0,
        ).pack(fill="x", pady=(0, 12))

        width = 520
        height = 190

        # Center relative to the actual application window, not the screen.
        self.update_idletasks()
        root_x = self.winfo_rootx()
        root_y = self.winfo_rooty()
        root_w = max(1, self.winfo_width())
        root_h = max(1, self.winfo_height())

        # During the first geometry pass Tk can still report 1x1. Use the
        # application's requested geometry as a safe fallback.
        if root_w <= 10:
            root_w = max(1080, self.winfo_reqwidth())
        if root_h <= 10:
            root_h = max(680, self.winfo_reqheight())

        x = root_x + max(0, (root_w - width) // 2)
        y = root_y + max(0, (root_h - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")

        win.deiconify()
        win.lift()
        try:
            win.attributes("-topmost", True)
            win.after(150, lambda: win.attributes("-topmost", False))
        except tk.TclError:
            pass
        win.update_idletasks()
        win.update()

        # Keep the popup visible long enough to be readable even when the
        # database is small and verification itself completes almost instantly.
        shown_at = time.monotonic()
        minimum_visible_seconds = 1.8
        last_visual_update = [shown_at]

        def update_progress(done, total, message):
            percent = 100 if total <= 0 else int((done / total) * 100)
            percent = max(0, min(100, percent))
            progress["value"] = percent
            percent_var.set(f"{percent}%")
            status_var.set(message)
            win.update_idletasks()
            win.update()

            # Small pacing interval lets the user actually see progress on
            # fast databases without making startup unnecessarily slow.
            elapsed = time.monotonic() - last_visual_update[0]
            if elapsed < 0.035:
                time.sleep(0.035 - elapsed)
            last_visual_update[0] = time.monotonic()

        try:
            result = self.db.verify_and_reconcile_inventory(
                progress_callback=update_progress
            )
            update_progress(
                max(1, result["items_verified"]),
                max(1, result["items_verified"]),
                "Database verification complete."
            )

            remaining = (
                minimum_visible_seconds
                - (time.monotonic() - shown_at)
            )
            if remaining > 0:
                # Keep processing UI messages while holding the completed
                # verification display on screen.
                finish_at = time.monotonic() + remaining
                while time.monotonic() < finish_at:
                    win.update_idletasks()
                    win.update()
                    time.sleep(0.02)
        finally:
            try:
                win.destroy()
            except tk.TclError:
                pass


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

    def themed_dialog(
        self,
        title,
        message,
        buttons,
        width=520,
        height=250,
    ):
        """Display a modal dialog using the currently selected application theme."""
        result = {"value": None}
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=BLUE_BG)
        win.resizable(False, False)
        self.center_child_window(win, width, height)
        win.transient(self)
        win.grab_set()
        request_windows_titlebar(
            win.winfo_id(),
            BLUE_BG,
            TEXT,
            BORDER,
            self.theme_palette.get("dark_titlebar", True),
        )

        header = tk.Frame(win, bg=BLUE_HEADER)
        header.pack(fill="x")
        tk.Label(
            header,
            text=title,
            bg=BLUE_HEADER,
            fg=HEADER_TEXT,
            font=("Segoe UI", 14, "bold"),
            anchor="w",
            padx=18,
            pady=12,
        ).pack(fill="x")

        body = tk.Frame(
            win,
            bg=BLUE_PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        body.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            body,
            text=message,
            bg=BLUE_PANEL,
            fg=TEXT,
            wraplength=width - 70,
            justify="left",
            font=("Segoe UI", 10),
        ).pack(fill="both", expand=True, anchor="w", padx=14, pady=14)

        button_row = tk.Frame(body, bg=BLUE_PANEL)
        button_row.pack(fill="x", padx=12, pady=(0, 12))

        def choose(value):
            result["value"] = value
            win.destroy()

        for label, value in reversed(buttons):
            dialog_button = self.button(
                button_row,
                label,
                lambda v=value: choose(v),
            )
            # Keep dialog actions readable at Windows display scaling levels.
            dialog_button.configure(width=max(10, len(label) + 2))
            dialog_button.pack(side="right", padx=(10, 0), pady=(4, 2))

        win.protocol("WM_DELETE_WINDOW", lambda: choose(None))
        win.bind("<Escape>", lambda _event: choose(None))
        win.wait_window()
        return result["value"]

    def themed_confirm(self, title, message):
        return self.themed_dialog(
            title,
            message,
            [("Yes", True), ("No", False)],
            width=540,
            height=310,
        ) is True

    def themed_export_complete(self, filename, export_name):
        choice = self.themed_dialog(
            f"{export_name} Complete",
            f"{export_name} was exported successfully:\n\n{filename}",
            [("Open Folder", "open"), ("Close", "close")],
            width=590,
            height=270,
        )
        if choice == "open":
            try:
                folder = os.path.dirname(os.path.abspath(filename))
                if os.name == "nt":
                    os.startfile(folder)
                else:
                    webbrowser.open(f"file://{folder}")
            except Exception as ex:
                self.themed_dialog(
                    APP_NAME,
                    f"Could not open the export folder:\n{ex}",
                    [("Close", None)],
                    width=520,
                    height=230,
                )

    def show_about(self):
        win = tk.Toplevel(self)
        win.title(f"About {APP_NAME}")
        win.configure(bg=BLUE_BG)
        win.resizable(False, False)
        self.center_child_window(win, 560, 465)
        win.transient(self)
        win.grab_set()

        header = tk.Frame(win, bg=BLUE_HEADER, height=72)
        header.pack(fill="x")
        header.pack_propagate(False)

        try:
            self._about_icon_photo = tk.PhotoImage(file=about_icon_png_path())
            tk.Label(
                header,
                image=self._about_icon_photo,
                bg=BLUE_HEADER,
                bd=0,
            ).pack(side="left", padx=(18, 12), pady=12)
        except Exception:
            tk.Label(
                header,
                text="🫘",
                bg=BLUE_HEADER,
                fg=CYAN,
                font=("Segoe UI Emoji", 24),
            ).pack(side="left", padx=(22, 12), pady=14)

        title_area = tk.Frame(header, bg=BLUE_HEADER)
        title_area.pack(side="left", fill="both", expand=True, pady=12)
        tk.Label(
            title_area,
            text=APP_NAME,
            bg=BLUE_HEADER,
            fg=HEADER_TEXT,
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
            wraplength=480,
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=18)

        release_link = tk.Label(
            body,
            text="Open HHD Inventory Manager Releases",
            bg=BLUE_PANEL,
            fg=CYAN,
            cursor="hand2",
            font=("Segoe UI", 10, "underline"),
        )
        release_link.pack(anchor="w", padx=18, pady=(14, 0))
        release_link.bind(
            "<Button-1>",
            lambda _event: webbrowser.open(
                "https://github.com/N4EAC/HHD-Inventory-Management/releases"
            ),
        )

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

    def export_database_action(self):
        filename = filedialog.asksaveasfilename(
            title="Export HHD Inventory Database",
            defaultextension=".db",
            initialfile=f"HHD_Inventory_{date.today().isoformat()}.db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
        )
        if not filename:
            return
        try:
            self.db.conn.commit()
            shutil.copy2(db_path(), filename)
            self.themed_export_complete(filename, "Database Export")
        except Exception as ex:
            self.themed_dialog(
                APP_NAME,
                f"Database export failed:\n{ex}",
                [("Close", None)],
                width=540,
                height=240,
            )

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
        self.style.configure("Treeview.Heading", background=BLUE_HEADER, foreground=HEADER_TEXT, font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[("selected", SELECT_BG)], foreground=[("selected", SELECTED_TEXT)])

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
            foreground=HEADER_TEXT,
            font=("Segoe UI", max(9, self.inventory_font_size - 1), "bold"),
        )
        self.style.map(
            "Inventory.Treeview",
            background=[("selected", SELECT_BG)],
            foreground=[("selected", SELECTED_TEXT)],
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
            selectforeground=[("readonly", HEADER_TEXT), ("!disabled", HEADER_TEXT)],
            arrowcolor=[("readonly", CYAN), ("!disabled", CYAN)],
        )

        # Dropdown list colors used by Tk's internal Listbox for ttk.Combobox.
        self.option_add("*TCombobox*Listbox.background", INPUT_BG)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", BLUE_HEADER)
        self.option_add("*TCombobox*Listbox.selectForeground", HEADER_TEXT)
        self.option_add("*TCombobox*Listbox.borderWidth", 1)

    def apply_theme(self, theme_name, rebuild=True):
        self.current_theme = theme_name if theme_name in THEMES else "Medical Blue"
        self.settings_data["theme"] = self.current_theme
        self.theme_palette = set_theme_palette(self.current_theme)

        self.configure(bg=BLUE_BG)
        if hasattr(self, "container"):
            self.container.configure(bg=BLUE_BG)
        if hasattr(self, "sidebar"):
            self.sidebar.configure(bg=BLUE_PANEL)
        if hasattr(self, "content"):
            self.content.configure(bg=BLUE_BG)
        if hasattr(self, "statusbar"):
            self.statusbar.configure(bg=STATUS_BG, highlightbackground=BORDER)
        if hasattr(self, "statusbar_label"):
            self.statusbar_label.configure(bg=STATUS_BG, fg=MUTED)

        self.configure_styles()
        self.create_status_led_images()
        request_windows_titlebar(
            self.winfo_id(),
            BLUE_BG,
            TEXT,
            BORDER,
            self.theme_palette.get("dark_titlebar", True),
        )
        self.save_local_settings()
        self.after(
            75,
            lambda: request_windows_titlebar(self.winfo_id()),
        )

        if rebuild and hasattr(self, "sidebar"):
            for widget in self.sidebar.winfo_children():
                widget.destroy()
            self.build_sidebar()
            self.show_settings()

    def attach_responsive_tree(
        self,
        tree,
        font_size,
        min_widths=None,
        stretch_columns=None,
        include_tree_column=False,
    ):
        """
        Keep table row height and column widths appropriate for the active font
        while preventing the surrounding panel from being forced wider.
        """
        min_widths = dict(min_widths or {})
        stretch_columns = list(stretch_columns or [])
        record = {
            "tree": tree,
            "font_size": font_size,
            "min_widths": min_widths,
            "stretch_columns": stretch_columns,
            "include_tree_column": include_tree_column,
            "last_width": -1,
            "pending": None,
        }
        self._responsive_trees.append(record)

        def resize(force=False):
            try:
                if not tree.winfo_exists():
                    return
                available = max(180, tree.winfo_width() - 8)
                if not force and available == record["last_width"]:
                    return
                record["last_width"] = available

                size = font_size() if callable(font_size) else int(font_size)
                font = tkfont.Font(family="Segoe UI", size=size)
                heading_font = tkfont.Font(
                    family="Segoe UI",
                    size=max(9, size - 1),
                    weight="bold",
                )
                style_name = tree.cget("style") or "Treeview"
                self.style.configure(
                    style_name,
                    rowheight=max(28, font.metrics("linespace") + 12),
                )

                columns = list(tree["columns"])
                visible_columns = (["#0"] if include_tree_column else []) + columns

                desired = {}
                for column in visible_columns:
                    heading = tree.heading(column).get("text", "")
                    widest = heading_font.measure(str(heading)) + 24
                    for iid in tree.get_children(""):
                        value = (
                            tree.item(iid, "text")
                            if column == "#0"
                            else tree.set(iid, column)
                        )
                        widest = max(widest, font.measure(str(value)) + 24)
                    desired[column] = max(min_widths.get(column, 55), widest)

                total_desired = sum(desired.values())
                if total_desired <= available:
                    extra = available - total_desired
                    targets = stretch_columns or visible_columns
                    share = extra // max(1, len(targets))
                    for column in visible_columns:
                        width = desired[column] + (
                            share if column in targets else 0
                        )
                        tree.column(
                            column,
                            width=width,
                            minwidth=min_widths.get(column, 45),
                        )
                else:
                    minimum_total = sum(
                        min_widths.get(column, 55)
                        for column in visible_columns
                    )
                    flexible = max(1, total_desired - minimum_total)
                    usable_extra = max(0, available - minimum_total)
                    for column in visible_columns:
                        minimum = min_widths.get(column, 55)
                        proportional = int(
                            (desired[column] - minimum)
                            / flexible
                            * usable_extra
                        )
                        tree.column(
                            column,
                            width=max(minimum, minimum + proportional),
                            minwidth=minimum,
                        )
            except Exception:
                pass

        def schedule_resize(_event=None):
            try:
                pending = record.get("pending")
                if pending is not None:
                    self.after_cancel(pending)
                record["pending"] = self.after(80, lambda: resize(False))
            except Exception:
                pass

        record["resize"] = resize
        tree.bind("<Configure>", schedule_resize, add="+")
        self.after(100, lambda: resize(True))
        return resize

    def refresh_responsive_trees(self):
        active = []
        for record in self._responsive_trees:
            tree = record["tree"]
            try:
                if tree.winfo_exists():
                    active.append(record)
                    record["last_width"] = -1
                    resize = record.get("resize")
                    if resize:
                        self.after_idle(lambda func=resize: func(True))
            except Exception:
                pass
        self._responsive_trees = active

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
        self.refresh_responsive_trees()

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
        return ColorButton(
            parent,
            text=text,
            command=command,
            bg=BUTTON_BG,
            fg=TEXT,
            activebackground=BUTTON_HOVER,
            activeforeground=TEXT,
            relief="flat",
            padx=14,
            pady=7,
            font=("Segoe UI", 10),
            cursor="hand2",
        )

    def build_windows_menu(self):
        menubar = tk.Menu(self)

        menubar.add_command(
            label="Settings / Items",
            command=self.show_settings,
        )
        menubar.add_command(
            label="About",
            command=self.show_about,
        )

        self.configure(menu=menubar)

    def build_sidebar(self):
        bottom = tk.Frame(self.sidebar, bg=BLUE_PANEL)
        bottom.pack(side="bottom", fill="x", padx=8, pady=(8, 14))

        ColorButton(
            bottom,
            text="✓  Record Treatment",
            command=self.show_log_session,
            anchor="center",
            bg=BLUE_HEADER,
            fg=BLUE_BUTTON_TEXT,
            activebackground=BUTTON_HOVER,
            activeforeground=BLUE_BUTTON_TEXT,
            relief="raised",
            bd=1,
            font=("Segoe UI", 12, "bold"),
            padx=10,
            pady=12,
            cursor="hand2",
        ).pack(fill="x")

        menu = tk.Frame(self.sidebar, bg=BLUE_PANEL)
        menu.pack(side="top", fill="both", expand=True)

        try:
            self._hhd_menu_icon = tk.PhotoImage(file=menu_icon_png_path())
        except Exception:
            self._hhd_menu_icon = None
        tk.Label(
            menu,
            text="  HHD MENU",
            image=self._hhd_menu_icon,
            compound="left",
            bg=BLUE_PANEL,
            fg=CYAN,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=18, pady=(18, 8))

        buttons = [
            ("⌂  Dashboard", self.show_dashboard),
            (f"▣  {self.group_display_name(GROUP_NX)}", lambda: self.show_inventory(GROUP_NX)),
            (f"▣  {self.group_display_name(GROUP_DV)}", lambda: self.show_inventory(GROUP_DV)),
            None,
            ("▦  Calendar", self.show_treatment_calendar),
            ("▤  Treatment History", self.show_treatment_history),
            ("⌁  Inventory History", self.show_inventory_history),
            None,
            ("＋  Received Inventory", self.show_received),
            ("⌕  Lot Number Search", self.show_lot_number_search),
            None,
            ("⇧  Import DB", self.import_database_action),
            ("⇩  Export DB", self.export_database_action),
            ("⇩  Export Inventory CSV", self.export_csv),
        ]
        for entry in buttons:
            if entry is None:
                tk.Frame(
                    menu,
                    bg=BORDER,
                    height=1,
                ).pack(fill="x", padx=14, pady=6)
                continue

            text, cmd = entry
            ColorButton(
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
        binding_id = getattr(self, "_content_mousewheel_binding", None)
        if binding_id:
            try:
                self.unbind("<MouseWheel>", binding_id)
            except tk.TclError:
                pass
            self._content_mousewheel_binding = None
        for w in self.content.winfo_children():
            w.destroy()

    def make_panel(self, parent, title):
        panel = tk.Frame(parent, bg=BLUE_PANEL, highlightbackground=BORDER, highlightthickness=1)
        tk.Label(panel, text=title, bg=PANEL_TITLE_BG, fg=CYAN, font=("Segoe UI", 12, "bold"), anchor="w", padx=12, pady=8).pack(fill="x")
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
        self.button(top, "Record Treatment", self.show_log_session).pack(side="right", padx=6)

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
        self.attach_responsive_tree(
            tree,
            font_size=lambda: self.inventory_font_size,
            min_widths={
                "#0": 50 if compact else 60,
                "item": 110 if compact else 180,
                "units": 62,
                "weeks": 66,
                "status": 74,
            },
            stretch_columns=["item"],
            include_tree_column=True,
        )

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
        self.center_child_window(win, 660, 820)
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
            ("baseline_date", "Baseline Snapshot Date YYYY-MM-DD", tk.StringVar(value=val("baseline_date", iso_today())), "entry"),
            ("last_inventory_update_date", "Last Inventory Update", tk.StringVar(value=val("last_inventory_update_date", iso_today())), "readonly"),
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
                if typ == "readonly":
                    e.configure(state="readonly", readonlybackground=INPUT_BG)
            e.grid(row=idx, column=1, sticky="ew", padx=14, pady=7)

        auto_var = tk.IntVar(value=1 if is_new else int(item["auto_session_usage"]))
        tk.Checkbutton(form, text="Auto-calculate usage from logged dialysis sessions", variable=auto_var,
                       bg=BLUE_PANEL, fg=TEXT, activebackground=BLUE_PANEL, activeforeground=TEXT,
                       selectcolor=INPUT_BG, font=("Segoe UI", 10)).grid(row=len(rows), column=0, columnspan=2, sticky="w", padx=14, pady=(10, 4))

        no_half_var = tk.IntVar(
            value=0 if is_new else int(item["disallow_half_usage"] or 0)
        )
        tk.Checkbutton(
            form,
            text="Do not allow .5 usage for this item (complete treatments round up to 1)",
            variable=no_half_var,
            bg=BLUE_PANEL, fg=TEXT,
            activebackground=BLUE_PANEL, activeforeground=TEXT,
            selectcolor=INPUT_BG, font=("Segoe UI", 10),
        ).grid(row=len(rows)+1, column=0, columnspan=2, sticky="w", padx=14, pady=(4, 4))

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
            row=len(rows)+2,
            column=0,
            columnspan=2,
            sticky="w",
            padx=14,
            pady=(4, 8),
        )

        remove_half_now_var = tk.IntVar(value=0)
        remove_half_check = tk.Checkbutton(
            form,
            text="Remove the existing .5 fraction from total when saving",
            variable=remove_half_now_var,
            bg=BLUE_PANEL,
            fg=TEXT,
            activebackground=BLUE_PANEL,
            activeforeground=TEXT,
            selectcolor=INPUT_BG,
            font=("Segoe UI", 10, "bold"),
        )
        remove_half_check.grid(
            row=len(rows)+3,
            column=0,
            columnspan=2,
            sticky="w",
            padx=14,
            pady=(4, 2),
        )

        tk.Label(
            form,
            text=(
                "One-time action. Example: 23.5 becomes 23.0. "
                "It only runs when the calculated total currently ends in .5."
            ),
            bg=BLUE_PANEL,
            fg=MUTED,
            wraplength=520,
            justify="left",
            font=("Segoe UI", 9),
        ).grid(
            row=len(rows)+4,
            column=0,
            columnspan=2,
            sticky="w",
            padx=32,
            pady=(0, 8),
        )

        if is_new:
            remove_half_check.config(state="disabled")

        sessions_per_week = self.db.get_setting("sessions_per_week", "4")
        tk.Label(
            form,
            text=f"Forecast weekly usage = (Units per session ÷ reusable sessions × {sessions_per_week} scheduled sessions/week) + additional weekly usage.",
            bg=BLUE_PANEL,
            fg=MUTED,
            wraplength=500,
            justify="left",
            font=("Segoe UI", 9)
        ).grid(row=len(rows)+5, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 10))

        form.columnconfigure(1, weight=1)

        def save():
            try:
                group = self.internal_group_from_display(vars_["group_name"].get())
                item_name = vars_["item_name"].get().strip()
                data = {
                    "group_name": group,
                    "item_name": item_name,
                    "baseline_units": validate_half_unit(
                        vars_["baseline_units"].get() or 0,
                        "Current/Baseline Units",
                    ),
                    "baseline_date": parse_date(vars_["baseline_date"].get()).isoformat(),
                    "units_per_session": validate_half_unit(
                        vars_["units_per_session"].get() or 0,
                        "Units Used Per Session",
                    ),
                    "units_per_week": validate_half_unit(
                        vars_["units_per_week"].get() or 0,
                        "Additional Units Used Per Week",
                    ),
                    "reusable_sessions": max(float(vars_["reusable_sessions"].get() or 1), 1.0),
                    "lifespan_days": int(float(vars_["lifespan_days"].get() or 0)),
                    "low_threshold": float(vars_["low_threshold"].get() or 0),
                    "min_threshold": float(vars_["min_threshold"].get() or 0),
                    "auto_session_usage": int(auto_var.get()),
                    "full_attempt_usage": int(full_attempt_var.get()),
                    "disallow_half_usage": int(no_half_var.get()),
                }
                if not item_name:
                    raise ValueError("Item name cannot be blank.")

                if is_new:
                    self.db.add_item(**data)
                else:
                    self.db.update_item(item["id"], **data)

                    if int(remove_half_now_var.get()) == 1:
                        before_units, after_units = self.db.remove_existing_half_unit(
                            item["id"],
                            "Half-used item removed from Item Settings",
                        )
                        if abs(after_units - (before_units - 0.5)) > 1e-8:
                            raise RuntimeError(
                                "The half-unit removal did not update the total."
                            )
                        self.db.backup_database("change")

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

    def treatment_day_statuses(self, start_date, end_date):
        days = {}
        for record in self.db.sessions_between(start_date, end_date):
            day = parse_date(record["session_date"])
            status = treatment_type_key(record["session_type"])
            usages = [
                dict(row)
                for row in self.db.session_item_usages(record["id"])
            ]
            days.setdefault(day, []).append({
                "id": record["id"],
                "status": status,
                "type": record["session_type"],
                "notes": (record["notes"] or "").strip(),
                "usages": usages,
                "record": dict(record),
            })
        return days

    def show_treatment_detail_dialog(self, day_value, treatments):
        win = tk.Toplevel(self)
        win.overrideredirect(True)
        win.configure(bg=BORDER)
        win.transient(self)

        outer = tk.Frame(
            win,
            bg=BLUE_BG,
            highlightbackground=BORDER,
            highlightthickness=2,
        )
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        tk.Label(
            outer,
            text=day_value.strftime("%A, %B %d, %Y"),
            bg=BLUE_HEADER,
            fg=HEADER_TEXT,
            font=("Segoe UI", 15, "bold"),
            pady=12,
        ).pack(fill="x")

        footer = tk.Frame(outer, bg=BLUE_PANEL)
        footer.pack(side="bottom", fill="x", padx=14, pady=(0, 14))

        content_shell = tk.Frame(outer, bg=BLUE_PANEL)
        content_shell.pack(
            side="top",
            fill="both",
            expand=True,
            padx=14,
            pady=(14, 10),
        )

        canvas = tk.Canvas(
            content_shell,
            bg=BLUE_PANEL,
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(
            content_shell,
            orient="vertical",
            command=canvas.yview,
        )
        body = tk.Frame(canvas, bg=BLUE_PANEL)

        body_window = canvas.create_window(
            (0, 0),
            window=body,
            anchor="nw",
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)

        def update_scroll_region(_event=None):
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)

        def fit_body_width(event):
            canvas.itemconfigure(body_window, width=event.width)

        body.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", fit_body_width)

        colors = {
            "complete": GREEN,
            "incomplete": YELLOW,
            "missed": RED,
            "in_center": CYAN,
        }

        for treatment in treatments:
            color = colors[treatment["status"]]
            card = tk.Frame(
                body,
                bg=BLUE_PANEL_2,
                highlightbackground=color,
                highlightthickness=2,
            )
            card.pack(fill="x", pady=(0, 10))

            card_text_color = "#111111"
            if treatment["status"] == "missed":
                card_text_color = "#FFFFFF"

            tk.Label(
                card,
                text=self.display_treatment_type(treatment["type"]),
                bg=color,
                fg=card_text_color,
                font=("Segoe UI", 11, "bold"),
                padx=10,
                pady=6,
            ).pack(fill="x")

            details = []
            record = treatment.get("record", {})
            identity_lines = [
                (
                    f"PAK lot#: {record.get('pak_lot', '')}"
                    if record.get("pak_lot")
                    else ""
                ),
                (
                    f"SAK lot#: {record.get('sak_lot', '')}"
                    if record.get("sak_lot")
                    else ""
                ),
                (
                    f"Cartridge lot#: {record.get('cartridge_lot', '')}"
                    if record.get("cartridge_lot")
                    else ""
                ),
                (
                    f"Cycler serial#: {record.get('cycler_serial', '')}"
                    if record.get("cycler_serial")
                    else ""
                ),
                (
                    f"PureFlow serial#: {record.get('pureflow_serial', '')}"
                    if record.get("pureflow_serial")
                    else ""
                ),
            ]
            identity_lines = [line for line in identity_lines if line]

            if identity_lines:
                details.append("Lot and equipment information:")
                details.extend(f"• {line}" for line in identity_lines)

            if treatment["usages"]:
                if details:
                    details.append("")
                details.append("Items used:")
                details.extend(
                    f"• {usage['item_name']}: "
                    f"{float(usage['units_used']):g}"
                    for usage in treatment["usages"]
                )

            if treatment["notes"]:
                if details:
                    details.append("")
                details.append("Notes:")
                details.append(treatment["notes"])

            if not details:
                details = [
                    "No notes, item usage, or lot information recorded."
                ]

            tk.Label(
                card,
                text="\n".join(details),
                bg=BLUE_PANEL_2,
                fg=TEXT,
                justify="left",
                anchor="nw",
                wraplength=620,
                padx=12,
                pady=10,
            ).pack(fill="x")

        def close_dialog():
            try:
                win.grab_release()
            except tk.TclError:
                pass
            win.destroy()

        ok_button = self.button(footer, "OK", close_dialog)
        ok_button.configure(width=12)
        ok_button.pack(side="right")

        scrolling_enabled = {"value": False}

        def scroll_dialog(event):
            if not scrolling_enabled["value"]:
                return "break"

            delta = getattr(event, "delta", 0)
            if delta:
                steps = -1 if delta > 0 else 1
                canvas.yview_scroll(steps * 3, "units")
            return "break"

        def scroll_dialog_linux(event):
            if not scrolling_enabled["value"]:
                return "break"
            if getattr(event, "num", None) == 4:
                canvas.yview_scroll(-3, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(3, "units")
            return "break"

        def bind_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>", scroll_dialog, add="+")
            widget.bind("<Button-4>", scroll_dialog_linux, add="+")
            widget.bind("<Button-5>", scroll_dialog_linux, add="+")
            for child in widget.winfo_children():
                bind_mousewheel_recursive(child)

        # Bind every widget inside this floating dialog. Wheel events over
        # note labels, cards, or blank canvas space all scroll the details.
        bind_mousewheel_recursive(win)

        # Build the window fully before applying geometry or acquiring
        # the modal grab. This avoids the previous UI freeze.
        win.update_idletasks()

        screen_width = win.winfo_screenwidth()
        screen_height = win.winfo_screenheight()

        self.update_idletasks()

        main_width = max(620, self.winfo_width())
        main_height = max(420, self.winfo_height())

        # Width stays stable; height follows content but never exceeds
        # the main application window.
        width = min(740, max(620, main_width - 80))
        max_height = max(360, main_height - 80)

        # Reserve the non-scrollable portions first. This guarantees that
        # the title/header and OK footer remain visible at all times.
        title_widgets = [
            child
            for child in outer.winfo_children()
            if child is not content_shell and child is not footer
        ]
        header_height = sum(
            max(0, child.winfo_reqheight())
            for child in title_widgets
        )
        footer_height = max(52, footer.winfo_reqheight())
        outer_padding = 46

        content_needed = max(1, body.winfo_reqheight())
        content_available = max(
            160,
            max_height
            - header_height
            - footer_height
            - outer_padding,
        )

        scrolling_enabled["value"] = content_needed > content_available

        if scrolling_enabled["value"]:
            scrollbar.pack(side="right", fill="y")
            content_height = content_available
            height = max_height
        else:
            # Content fits: no scrollbar and no large empty area.
            content_height = content_needed
            height = min(
                max_height,
                header_height
                + footer_height
                + content_height
                + outer_padding,
            )

        # Force the canvas viewport to the calculated visible content height.
        canvas.configure(height=content_height)

        # Ensure the canvas knows the full scrollable extent after sizing.
        win.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox:
            canvas.configure(scrollregion=bbox)

        x = self.winfo_rootx() + max(
            0,
            (self.winfo_width() - width) // 2,
        )
        y = self.winfo_rooty() + max(
            0,
            (self.winfo_height() - height) // 2,
        )

        main_left = self.winfo_rootx() + 20
        main_top = self.winfo_rooty() + 20
        main_right = self.winfo_rootx() + self.winfo_width() - 20
        main_bottom = self.winfo_rooty() + self.winfo_height() - 20

        max_x = min(
            main_right - width,
            screen_width - width - 20,
        )
        max_y = min(
            main_bottom - height,
            screen_height - height - 40,
        )

        x = min(max(main_left, x), max(main_left, max_x))
        y = min(max(main_top, y), max(main_top, max_y))

        win.geometry(f"{width}x{height}+{x}+{y}")
        win.deiconify()
        win.lift()
        win.focus_force()

        # Delay the grab until the dialog is visible and fully realized.
        def activate_modal():
            if not win.winfo_exists():
                return
            try:
                win.grab_set()
            except tk.TclError:
                pass

        win.after(50, activate_modal)

        win.bind("<Escape>", lambda _event: close_dialog())
        win.protocol("WM_DELETE_WINDOW", close_dialog)

    def show_lot_number_search(self):
        self.clear_content()
        tk.Label(
            self.content,
            text="Lot Number Search",
            bg=BLUE_BG,
            fg=CYAN,
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w", padx=16, pady=12)

        search_panel, search_body = self.make_panel(
            self.content,
            "Search PAK, SAK, or Cartridge Lot Numbers",
        )
        search_panel.pack(fill="x", padx=16, pady=(0, 12))

        query_var = tk.StringVar()
        tk.Label(
            search_body,
            text="Lot number contains:",
            bg=BLUE_PANEL,
            fg=TEXT,
        ).pack(side="left", padx=(0, 8))
        query_entry = tk.Entry(
            search_body,
            textvariable=query_var,
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="solid",
            bd=1,
            width=36,
        )
        query_entry.pack(side="left", padx=(0, 8))

        results_panel, results_body = self.make_panel(
            self.content,
            "Search Results",
        )
        results_panel.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        columns = (
            "date", "type", "pak", "sak", "cartridge", "notes"
        )
        tree = ttk.Treeview(
            results_body,
            columns=columns,
            show="headings",
            height=18,
        )
        specs = [
            ("date", "Treatment Date", 120, False),
            ("type", "Treatment Type", 150, False),
            ("pak", "PAK lot#", 140, False),
            ("sak", "SAK lot#", 140, False),
            ("cartridge", "Cartridge lot#", 150, False),
            ("notes", "Notes", 320, True),
        ]
        for col, title, width, stretch in specs:
            tree.heading(col, text=title)
            tree.column(col, width=width, minwidth=90, stretch=stretch, anchor="w")
        tree.pack(fill="both", expand=True)
        current_results = []

        def normalized_type(raw):
            return {
                "missed": "Missed",
                "incomplete": "Incomplete",
                "in_center": "In Center",
                "complete": "Completed",
            }[treatment_type_key(raw)]

        def run_search(*_):
            nonlocal current_results
            for iid in tree.get_children():
                tree.delete(iid)
            term = query_var.get().strip()
            if not term:
                current_results = []
                return
            current_results = [dict(row) for row in self.db.search_treatment_lots(term)]
            for row in current_results:
                tree.insert(
                    "",
                    "end",
                    values=(
                        row["session_date"],
                        normalized_type(row["session_type"]),
                        row["pak_lot"],
                        row["sak_lot"],
                        row["cartridge_lot"],
                        row["notes"] or "",
                    ),
                )

        def export_results():
            if not current_results:
                self.themed_dialog(
                    APP_NAME,
                    "There are no search results to export.",
                    [("Close", None)],
                    width=450,
                    height=220,
                )
                return
            filename = filedialog.asksaveasfilename(
                title="Export Lot Search Results",
                defaultextension=".csv",
                initialfile=f"HHD_Lot_Search_{date.today().isoformat()}.csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            )
            if not filename:
                return
            try:
                with open(filename, "w", newline="", encoding="utf-8-sig") as handle:
                    writer = csv.writer(handle)
                    writer.writerow([
                        "Treatment Date", "Treatment Type", "PAK lot#",
                        "SAK lot#", "Cartridge lot#", "Notes",
                    ])
                    for row in current_results:
                        writer.writerow([
                            row["session_date"],
                            normalized_type(row["session_type"]),
                            row["pak_lot"], row["sak_lot"],
                            row["cartridge_lot"], row["notes"] or "",
                        ])
                self.themed_export_complete(filename, "Lot Search Export")
            except Exception as ex:
                self.themed_dialog(
                    APP_NAME,
                    f"Could not export search results:\n{ex}",
                    [("Close", None)],
                    width=540,
                    height=240,
                )

        self.button(search_body, "Search", run_search).pack(side="left", padx=(0, 8))
        self.button(search_body, "Export Results", export_results).pack(side="left")
        query_entry.bind("<Return>", run_search)
        query_entry.focus_set()

    def edit_treatment_notes_dialog(self, session_id, return_to_history=False):
        """Open a centered themed editor for an existing treatment note."""
        record = self.db.session_by_id(session_id)
        if not record:
            self.themed_dialog(
                APP_NAME,
                "The selected treatment could not be found.",
                [("Close", None)],
                width=480,
                height=220,
            )
            return

        win = tk.Toplevel(self)
        win.title("Edit Treatment Notes")
        win.configure(bg=BLUE_BG)
        win.resizable(False, False)
        self.center_child_window(win, 620, 420)
        win.transient(self)
        win.grab_set()
        request_windows_titlebar(
            win.winfo_id(),
            BLUE_BG,
            TEXT,
            BORDER,
            self.theme_palette.get("dark_titlebar", True),
        )

        header = tk.Frame(win, bg=BLUE_HEADER)
        header.pack(fill="x")
        tk.Label(
            header,
            text="Edit Treatment Notes",
            bg=BLUE_HEADER,
            fg=HEADER_TEXT,
            font=("Segoe UI", 14, "bold"),
            anchor="w",
            padx=18,
            pady=12,
        ).pack(fill="x")

        body = tk.Frame(
            win,
            bg=BLUE_PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        body.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            body,
            text=f"{record['session_date']} — {self.display_treatment_type(record['session_type'])}",
            bg=BLUE_PANEL,
            fg=CYAN,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(14, 8))

        tk.Label(
            body,
            text="Treatment Notes:",
            bg=BLUE_PANEL,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 6))

        notes_box = tk.Text(
            body,
            height=10,
            wrap="word",
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground=SELECT_BG,
            relief="solid",
            bd=1,
            font=("Segoe UI", 10),
        )
        notes_box.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        notes_box.insert("1.0", record["notes"] or "")

        button_row = tk.Frame(body, bg=BLUE_PANEL)
        button_row.pack(fill="x", padx=14, pady=(0, 14))

        def save_notes():
            try:
                entered_note = notes_box.get(
                    "1.0", "end-1c"
                ).strip()
                original_note = (record["notes"] or "").strip()

                # The editor initially contains the existing note history.
                # Only timestamp newly added or changed text.
                if entered_note == original_note:
                    saved_note = original_note
                elif entered_note.startswith(original_note) and original_note:
                    addition = entered_note[len(original_note):].strip()
                    stamped = self.timestamp_note_entry(addition)
                    saved_note = (
                        original_note
                        + ("\n\n" + stamped if stamped else "")
                    )
                else:
                    stamped = self.timestamp_note_entry(entered_note)
                    saved_note = stamped

                self.db.update_session_notes(
                    session_id,
                    saved_note,
                )
                self.db.backup_database("change")
                win.destroy()
                if return_to_history:
                    self.show_treatment_history()
                else:
                    self.show_log_session()
            except Exception as ex:
                self.themed_dialog(
                    APP_NAME,
                    f"Could not update treatment notes:\n{ex}",
                    [("Close", None)],
                    width=540,
                    height=250,
                )

        self.button(button_row, "Cancel", win.destroy).pack(side="right", padx=(8, 0))
        self.button(button_row, "Save Notes", save_notes).pack(side="right")

        win.bind("<Escape>", lambda _event: win.destroy())
        notes_box.focus_set()

    def show_treatment_calendar(self):
        self.clear_content()
        tk.Label(self.content, text="Calendar", bg=BLUE_BG, fg=CYAN,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=16, pady=12)
        state={"mode":"Month","last_mode":"Month","anchor":date.today().replace(day=1),"fade_step":0,"fade_direction":1,"today_cells":[],"fade_job":None}
        controls_panel, controls=self.make_panel(self.content,"Calendar Controls")
        controls_panel.pack(fill="x",padx=16,pady=(0,12))
        title_var=tk.StringVar(); mode_var=tk.StringVar(value="Month")
        self.button(controls,"◀ Previous",lambda:move_period(-1)).pack(side="left",padx=(0,6))
        self.button(controls,"Today",lambda:go_today()).pack(side="left",padx=6)
        self.button(controls,"Next ▶",lambda:move_period(1)).pack(side="left",padx=6)
        self.button(controls,"Export Calendar CSV",lambda:export_calendar_csv()).pack(side="right",padx=(8,0))
        ttk.Combobox(controls,textvariable=mode_var,values=["Month","Week"],state="readonly",width=10).pack(side="right")
        tk.Label(controls,textvariable=title_var,bg=BLUE_PANEL,fg=TEXT,font=("Segoe UI",14,"bold")).pack(side="left",expand=True)
        legend=tk.Frame(self.content,bg=BLUE_BG); legend.pack(fill="x",padx=18,pady=(0,8))
        tk.Label(legend,text="Legend:",bg=BLUE_BG,fg=TEXT,font=("Segoe UI",10,"bold")).pack(side="left",padx=(0,10))
        for label,color in [("Complete",GREEN),("Incomplete",YELLOW),("Missed",RED),("In Center",CYAN)]:
            tk.Label(legend,text=f"  {label}  ",bg=color,fg="#111111",font=("Segoe UI",10,"bold"),padx=8,pady=4).pack(side="left",padx=(0,10))
        calendar_panel,calendar_body=self.make_panel(self.content,"Calendar")
        calendar_panel.pack(fill="both",expand=True,padx=16,pady=(0,14))

        def clear_calendar():
            state["today_cells"]=[]
            for child in calendar_body.winfo_children(): child.destroy()
        def display_cell(parent,row,column,day_value,current_month=True):
            treatments=state.get("statuses",{}).get(day_value,[])
            cell=tk.Frame(parent,bg=CALENDAR_EMPTY,highlightbackground=BORDER,highlightthickness=2,cursor="hand2" if treatments else "arrow")
            cell.grid(row=row,column=column,sticky="nsew",padx=2,pady=2)
            if day_value==date.today(): state["today_cells"].append(cell)
            fg=TEXT if current_month else MUTED
            tk.Label(cell,text=str(day_value.day),bg=CALENDAR_EMPTY,fg=fg,font=("Segoe UI",12,"bold"),anchor="nw").pack(fill="x",padx=6,pady=(5,2))
            bands=tk.Frame(cell,bg=CALENDAR_EMPTY); bands.pack(fill="both",expand=True,padx=3,pady=(0,3))
            colors={"complete":GREEN,"incomplete":YELLOW,"missed":RED,"in_center":CYAN}
            names={"complete":"Complete","incomplete":"Incomplete","missed":"Missed","in_center":"In Center"}
            for tr in treatments:
                band=tk.Frame(bands,bg=colors[tr["status"]])
                band.pack(fill="both",expand=True,pady=1)
                tk.Label(band,text=names[tr["status"]],bg=colors[tr["status"]],fg="#111111",font=("Segoe UI",8,"bold"),anchor="w",padx=5).pack(fill="both",expand=True)
            if treatments:
                def open_detail(_e=None,d=day_value,t=treatments): self.show_treatment_detail_dialog(d,t)
                for widget in [cell,bands]+list(cell.winfo_children())+list(bands.winfo_children()): widget.bind("<Button-1>",open_detail)
        def render_calendar(*_args):
            clear_calendar(); selected=mode_var.get()
            if selected=="Week" and state["last_mode"]!="Week": state["anchor"]=date.today()
            elif selected=="Month" and state["last_mode"]!="Month": state["anchor"]=date.today().replace(day=1)
            state["mode"]=selected; state["last_mode"]=selected; anchor=state["anchor"]
            for col,weekday in enumerate(["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]):
                calendar_body.grid_columnconfigure(col,weight=1,uniform="calendar_days")
                tk.Label(calendar_body,text=weekday,bg=BLUE_HEADER,fg=HEADER_TEXT,font=("Segoe UI",11,"bold"),pady=7).grid(row=0,column=col,sticky="nsew",padx=2,pady=(0,2))
            if selected=="Week":
                ws=anchor-timedelta(days=(anchor.weekday()+1)%7); we=ws+timedelta(days=6)
                title_var.set(f"{ws.strftime('%B %d, %Y')} – {we.strftime('%B %d, %Y')}")
                state["statuses"]=self.treatment_day_statuses(ws,we); calendar_body.grid_rowconfigure(1,weight=1)
                for col in range(7): display_cell(calendar_body,1,col,ws+timedelta(days=col),True)
            else:
                ms=anchor.replace(day=1); vs=ms-timedelta(days=(ms.weekday()+1)%7); ve=vs+timedelta(days=41)
                title_var.set(ms.strftime("%B %Y")); state["statuses"]=self.treatment_day_statuses(vs,ve)
                for ri in range(1,7):
                    calendar_body.grid_rowconfigure(ri,weight=1,uniform="calendar_weeks")
                    for col in range(7):
                        d=vs+timedelta(days=(ri-1)*7+col); display_cell(calendar_body,ri,col,d,d.month==ms.month)
        def blend_hex(start_color, end_color, ratio):
            ratio = max(0.0, min(1.0, ratio))
            def rgb(value):
                value = value.lstrip("#")
                return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))
            a = rgb(start_color)
            b = rgb(end_color)
            mixed = tuple(round(a[i] + (b[i] - a[i]) * ratio) for i in range(3))
            return "#{:02x}{:02x}{:02x}".format(*mixed)

        def fade_today():
            try:
                state["fade_step"] += state["fade_direction"]
                if state["fade_step"] >= 20:
                    state["fade_step"] = 20
                    state["fade_direction"] = -1
                elif state["fade_step"] <= 0:
                    state["fade_step"] = 0
                    state["fade_direction"] = 1
                ratio = state["fade_step"] / 20.0
                border_color = blend_hex(BORDER, CYAN, ratio)
                thickness = 2 + round(2 * ratio)
                for cell in state["today_cells"]:
                    if cell.winfo_exists():
                        cell.configure(
                            highlightbackground=border_color,
                            highlightthickness=thickness,
                        )
                state["fade_job"] = self.after(90, fade_today)
            except tk.TclError:
                state["fade_job"] = None

        def export_calendar_csv():
            filename = filedialog.asksaveasfilename(
                title="Export Calendar CSV",
                defaultextension=".csv",
                initialfile=f"HHD_Treatment_Calendar_{date.today().isoformat()}.csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            )
            if not filename:
                return
            try:
                rows = self.db.sessions_between(date(1900, 1, 1), date(2999, 12, 31))
                with open(filename, "w", newline="", encoding="utf-8-sig") as handle:
                    writer = csv.writer(handle)
                    writer.writerow([
                        "Treatment Date", "Treatment Type", "PAK lot#",
                        "SAK lot#", "Cartridge lot#", "Notes",
                    ])
                    for record in rows:
                        treatment_type = {
                            "missed": "Missed",
                            "incomplete": "Incomplete",
                            "in_center": "In Center",
                            "complete": "Completed",
                        }[treatment_type_key(record["session_type"])]
                        writer.writerow([
                            record["session_date"], treatment_type,
                            record["pak_lot"], record["sak_lot"],
                            record["cartridge_lot"], record["notes"] or "",
                        ])
                self.themed_export_complete(filename, "Calendar Export")
            except Exception as ex:
                self.themed_dialog(
                    APP_NAME,
                    f"Could not export the treatment calendar:\n{ex}",
                    [("Close", None)],
                    width=550,
                    height=250,
                )

        def move_period(direction):
            if mode_var.get()=="Week": state["anchor"]+=timedelta(days=7*direction)
            else:
                cur=state["anchor"].replace(day=1)
                if direction>0: state["anchor"]=cur.replace(year=cur.year+1,month=1) if cur.month==12 else cur.replace(month=cur.month+1)
                else: state["anchor"]=cur.replace(year=cur.year-1,month=12) if cur.month==1 else cur.replace(month=cur.month-1)
            render_calendar()
        def go_today(): state["anchor"]=date.today(); render_calendar()
        mode_var.trace_add("write",render_calendar); render_calendar(); fade_today()

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
            outline=BORDER, fill=CHART_BG
        )

        available_start = points[0][0] if points else None
        if available_start and available_start > period_start:
            unavailable_right = x_for(available_start)
            canvas.create_rectangle(
                left,
                top,
                unavailable_right,
                top + plot_h,
                fill=BLUE_PANEL_2,
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
            bg=CHART_BG,
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
                units = validate_half_unit(units_var.get(), "Units received")
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
        self.attach_responsive_tree(
            tree,
            font_size=10,
            min_widths={"date": 90, "group": 110, "item": 150, "units": 65, "notes": 140},
            stretch_columns=["item", "notes"],
        )
        for r in self.db.recent_received(50):
            tree.insert("", "end", values=(r["received_date"], self.group_display_name(r["group_name"]), r["item_name"], r["units"], r["notes"] or ""))

    def show_treatment_saved_dialog(self):
        win = tk.Toplevel(self)
        win.title("Treatment Saved")
        win.transient(self)
        win.resizable(False, False)
        win.configure(bg=BLUE_BG)

        outer = tk.Frame(
            win,
            bg=BLUE_PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(
            outer,
            text="Treatment Saved",
            bg=BLUE_HEADER,
            fg=HEADER_TEXT,
            font=("Segoe UI", 14, "bold"),
            padx=20,
            pady=14,
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            outer,
            text="The treatment has been successfully recorded.",
            bg=BLUE_PANEL,
            fg=TEXT,
            font=("Segoe UI", 11),
            padx=26,
            pady=24,
        ).pack(fill="x")

        button_row = tk.Frame(outer, bg=BLUE_PANEL)
        button_row.pack(fill="x", padx=20, pady=(0, 18))

        def close_dialog():
            try:
                win.grab_release()
            except tk.TclError:
                pass
            win.destroy()

        close_button = self.button(button_row, "CLOSE", close_dialog)
        close_button.configure(width=12)
        close_button.pack(anchor="center")

        win.update_idletasks()
        width = 430
        height = max(205, win.winfo_reqheight())

        self.update_idletasks()
        x = self.winfo_rootx() + max(
            0,
            (self.winfo_width() - width) // 2,
        )
        y = self.winfo_rooty() + max(
            0,
            (self.winfo_height() - height) // 2,
        )
        win.geometry(f"{width}x{height}+{x}+{y}")

        win.lift()
        win.focus_force()
        win.after(40, lambda: win.grab_set() if win.winfo_exists() else None)
        win.bind("<Escape>", lambda _event: close_dialog())
        win.protocol("WM_DELETE_WINDOW", close_dialog)


    def display_treatment_type(self, session_type):
        if session_type == "Regular Treatment":
            return "Complete Treatment"
        return session_type

    def timestamp_note_entry(self, text):
        text = (text or "").strip()
        if not text:
            return ""
        local_now = datetime.now().astimezone()
        return (
            "Entry: "
            + local_now.strftime("%Y-%m-%d %I:%M %p %Z")
            + "\n"
            + text
        )

    def show_log_session(self):
        self.clear_content()
        tk.Label(
            self.content,
            text="Treatments",
            bg=BLUE_BG,
            fg=CYAN,
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w", padx=16, pady=12)

        scroll_shell = tk.Frame(self.content, bg=BLUE_BG)
        scroll_shell.pack(fill="both", expand=True)
        treatment_canvas = tk.Canvas(
            scroll_shell,
            bg=BLUE_BG,
            highlightthickness=0,
            borderwidth=0,
        )
        treatment_scrollbar = ttk.Scrollbar(
            scroll_shell,
            orient="vertical",
            command=treatment_canvas.yview,
        )
        treatment_canvas.configure(yscrollcommand=treatment_scrollbar.set)
        treatment_canvas.pack(side="left", fill="both", expand=True)
        treatment_scrollbar.pack(side="right", fill="y")

        scroll_body = tk.Frame(treatment_canvas, bg=BLUE_BG)
        scroll_window = treatment_canvas.create_window(
            (0, 0),
            window=scroll_body,
            anchor="nw",
        )

        def update_treatment_scroll_region(_event=None):
            treatment_canvas.configure(
                scrollregion=treatment_canvas.bbox("all")
            )

        def fit_treatment_width(event):
            treatment_canvas.itemconfigure(
                scroll_window,
                width=event.width,
            )

        def scroll_treatments(event):
            if event.delta:
                direction = -1 if event.delta > 0 else 1
                treatment_canvas.yview_scroll(direction * 3, "units")

        scroll_body.bind("<Configure>", update_treatment_scroll_region)
        treatment_canvas.bind("<Configure>", fit_treatment_width)
        treatment_canvas.bind("<MouseWheel>", scroll_treatments)
        scroll_body.bind("<MouseWheel>", scroll_treatments)
        self._content_mousewheel_binding = self.bind(
            "<MouseWheel>",
            scroll_treatments,
            add="+",
        )

        panel, body = self.make_panel(scroll_body, "Treatment Entry")
        panel.pack(fill="x", padx=16, pady=(0, 12))

        date_var = tk.StringVar(value=iso_today())
        type_var = tk.StringVar(value="Complete Treatment")
        equiv_var = tk.StringVar(value="1")

        basic_fields = [
            ("Treatment Date YYYY-MM-DD", date_var, "entry"),
            ("Treatment Type", type_var, "combo"),
            ("Treatment Equivalent", equiv_var, "entry"),
        ]
        for row_index, (label, variable, control_type) in enumerate(
            basic_fields
        ):
            tk.Label(
                body,
                text=label,
                bg=BLUE_PANEL,
                fg=TEXT,
            ).grid(
                row=row_index,
                column=0,
                sticky="nw",
                padx=10,
                pady=7,
            )

            if control_type == "combo":
                control = ttk.Combobox(
                    body,
                    textvariable=variable,
                    values=[
                        "Complete Treatment",
                        "Extra Treatment",
                        "Missed Treatment",
                        "Incomplete Treatment",
                        "In Center Treatment",
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
            control.grid(
                row=row_index,
                column=1,
                sticky="w",
                padx=10,
                pady=7,
            )

        identity_frame = tk.Frame(
            body,
            bg=BLUE_PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        identity_frame.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=10,
            pady=8,
        )
        tk.Label(
            identity_frame,
            text="Treatment Lot and Equipment Information",
            bg=PANEL_TITLE_BG,
            fg=CYAN,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            padx=10,
            pady=7,
        ).grid(row=0, column=0, columnspan=4, sticky="ew")

        identity_vars = {
            "pak_lot": tk.StringVar(
                value=self.db.get_setting("last_pak_lot", "")
            ),
            "sak_lot": tk.StringVar(
                value=self.db.get_setting("last_sak_lot", "")
            ),
            "cartridge_lot": tk.StringVar(
                value=self.db.get_setting("last_cartridge_lot", "")
            ),
            "cycler_serial": tk.StringVar(
                value=self.db.get_setting("last_cycler_serial", "")
            ),
            "pureflow_serial": tk.StringVar(
                value=self.db.get_setting("last_pureflow_serial", "")
            ),
        }

        identity_specs = [
            ("PAK lot#", "pak_lot", 1, 0),
            ("SAK lot#", "sak_lot", 1, 2),
            ("Cartridge lot#", "cartridge_lot", 2, 0),
            ("Cycler serial#", "cycler_serial", 2, 2),
            ("PureFlow serial#", "pureflow_serial", 3, 0),
        ]
        identity_entries = []
        for label, key, row_index, column_index in identity_specs:
            tk.Label(
                identity_frame,
                text=label,
                bg=BLUE_PANEL,
                fg=TEXT,
                anchor="w",
            ).grid(
                row=row_index,
                column=column_index,
                sticky="w",
                padx=(10, 6),
                pady=6,
            )
            entry = tk.Entry(
                identity_frame,
                textvariable=identity_vars[key],
                bg=INPUT_BG,
                fg=TEXT,
                insertbackground=TEXT,
                relief="solid",
                bd=1,
                width=28,
            )
            entry.grid(
                row=row_index,
                column=column_index + 1,
                sticky="ew",
                padx=(0, 12),
                pady=6,
            )
            identity_entries.append(entry)

        identity_frame.columnconfigure(1, weight=1)
        identity_frame.columnconfigure(3, weight=1)

        custom_frame = tk.Frame(
            body,
            bg=BLUE_PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        custom_frame.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=10,
            pady=8,
        )
        tk.Label(
            custom_frame,
            text="Incomplete Treatment — Actual Items Used",
            bg=PANEL_TITLE_BG,
            fg=CYAN,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            padx=10,
            pady=7,
        ).pack(fill="x")

        controls = tk.Frame(custom_frame, bg=BLUE_PANEL)
        controls.pack(fill="x", padx=10, pady=8)

        item_var = tk.StringVar()
        units_var = tk.StringVar(value="0.5")
        item_map = {
            (
                f"{self.group_display_name(item['group_name'])}"
                f" — {item['item_name']}"
            ): item["id"]
            for item in self.db.items()
        }

        item_combo = ttk.Combobox(
            controls,
            textvariable=item_var,
            values=list(item_map),
            state="readonly",
            width=48,
        )
        item_combo.pack(side="left", padx=(0, 8))

        units_combo = ttk.Combobox(
            controls,
            textvariable=units_var,
            values=[f"{value / 2:g}" for value in range(1, 21)],
            state="readonly",
            width=8,
        )
        units_combo.pack(side="left", padx=(0, 8))

        usage_tree = ttk.Treeview(
            custom_frame,
            columns=("item", "units"),
            show="headings",
            height=4,
        )
        usage_tree.heading("item", text="Item")
        usage_tree.heading("units", text="Units Used")
        usage_tree.column("item", width=450, stretch=True)
        usage_tree.column(
            "units",
            width=100,
            anchor="center",
            stretch=False,
        )
        usage_tree.pack(fill="x", padx=10, pady=(0, 8))
        pending = []

        def add_usage():
            label = item_var.get()
            if not label:
                return
            units = float(units_var.get())
            pending.append((item_map[label], label, units))
            usage_tree.insert(
                "",
                "end",
                values=(label, f"{units:g}"),
            )

        def remove_usage():
            selection = usage_tree.selection()
            if not selection:
                return
            selected_index = usage_tree.index(selection[0])
            usage_tree.delete(selection[0])
            pending.pop(selected_index)

        add_usage_button = self.button(
            controls,
            "Add Item Usage",
            add_usage,
        )
        add_usage_button.pack(side="left", padx=(0, 8))

        remove_usage_button = self.button(
            controls,
            "Remove Selected",
            remove_usage,
        )
        remove_usage_button.pack(side="left")

        tk.Label(
            body,
            text="Treatment Notes:",
            bg=BLUE_PANEL,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=5, column=0, sticky="nw", padx=10, pady=7)

        notes = tk.Text(
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
        notes.grid(
            row=5,
            column=1,
            sticky="ew",
            padx=10,
            pady=7,
        )

        body.columnconfigure(1, weight=1)

        tk.Label(
            body,
            text=(
                "The most recently saved lot and equipment values are "
                "automatically prefilled for the next treatment."
            ),
            bg=BLUE_PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            padx=10,
            pady=(0, 8),
        )

        def adjust(*_):
            treatment_type = type_var.get()
            incomplete = treatment_type == "Incomplete Treatment"
            missed = treatment_type == "Missed Treatment"
            in_center = treatment_type == "In Center Treatment"

            equiv_var.set(
                "0" if incomplete or missed or in_center else "1"
            )

            item_combo.configure(
                state="readonly" if incomplete else "disabled"
            )
            units_combo.configure(
                state="readonly" if incomplete else "disabled"
            )
            add_usage_button.configure(
                state="normal" if incomplete else "disabled"
            )
            remove_usage_button.configure(
                state="normal" if incomplete else "disabled"
            )

            for entry in identity_entries:
                entry.configure(
                    state="disabled" if missed or in_center else "normal"
                )

        type_var.trace_add("write", adjust)
        adjust()

        def save_treatment():
            try:
                session_type = type_var.get()
                stored_session_type = (
                    "Regular Treatment"
                    if session_type == "Complete Treatment"
                    else session_type
                )
                equivalent = float(equiv_var.get())

                if "Incomplete" in session_type and not pending:
                    raise ValueError(
                        "Incomplete treatment cannot be saved until "
                        "at least one used item and its actual units "
                        "(0.5 to 10) have been entered."
                    )

                record_identity = treatment_uses_inventory(session_type)
                session_id = self.db.add_session(
                    parse_date(date_var.get()).isoformat(),
                    stored_session_type,
                    equivalent,
                    self.timestamp_note_entry(
                        notes.get("1.0", "end-1c")
                    ),
                    pak_lot=(
                        identity_vars["pak_lot"].get()
                        if record_identity else ""
                    ),
                    sak_lot=(
                        identity_vars["sak_lot"].get()
                        if record_identity else ""
                    ),
                    cartridge_lot=(
                        identity_vars["cartridge_lot"].get()
                        if record_identity else ""
                    ),
                    cycler_serial=(
                        identity_vars["cycler_serial"].get()
                        if record_identity else ""
                    ),
                    pureflow_serial=(
                        identity_vars["pureflow_serial"].get()
                        if record_identity else ""
                    ),
                )

                if "Incomplete" in session_type:
                    for item_id, _label, units in pending:
                        self.db.add_session_item_usage(
                            session_id,
                            item_id,
                            units,
                        )

                self.db.mark_treatment_inventory_update(session_id)
                self.db.backup_database("change")
                self.show_log_session()
                self.after(50, self.show_treatment_saved_dialog)
            except Exception as ex:
                self.themed_dialog(
                    APP_NAME,
                    f"Could not save treatment:\n{ex}",
                    [("Close", None)],
                    width=540,
                    height=250,
                )

        self.button(
            body,
            "Submit Treatment",
            save_treatment,
        ).grid(row=7, column=1, sticky="w", padx=10, pady=12)


    def show_treatment_history(self):
        self.clear_content()
        tk.Label(
            self.content,
            text="Treatment History",
            bg=BLUE_BG,
            fg=CYAN,
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w", padx=16, pady=12)

        panel, body = self.make_panel(
            self.content,
            "Recorded Treatments",
        )
        panel.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=(0, 16),
        )

        toolbar = tk.Frame(body, bg=BLUE_PANEL)
        toolbar.pack(fill="x", pady=(0, 10))

        tk.Label(
            toolbar,
            text=(
                "Select a treatment to edit its notes or delete it. "
                "Double-click a row to edit notes."
            ),
            bg=BLUE_PANEL,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(side="left")

        table_frame = tk.Frame(body, bg=BLUE_PANEL)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "date",
            "type",
            "pak",
            "sak",
            "cartridge",
            "cycler",
            "pureflow",
            "notes",
        )
        tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=18,
        )

        headings = [
            ("date", "Date", 105),
            ("type", "Treatment Type", 155),
            ("pak", "PAK Lot#", 125),
            ("sak", "SAK Lot#", 125),
            ("cartridge", "Cartridge Lot#", 140),
            ("cycler", "Cycler Serial#", 135),
            ("pureflow", "PureFlow Serial#", 145),
            ("notes", "Notes / Incomplete Item Usage", 360),
        ]
        for column, title, width in headings:
            tree.heading(column, text=title)
            tree.column(
                column,
                width=width,
                minwidth=80,
                stretch=column == "notes",
                anchor="w",
            )

        vertical_scroll = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=tree.yview,
        )
        horizontal_scroll = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=tree.xview,
        )
        tree.configure(
            yscrollcommand=vertical_scroll.set,
            xscrollcommand=horizontal_scroll.set,
        )

        tree.grid(row=0, column=0, sticky="nsew")
        vertical_scroll.grid(row=0, column=1, sticky="ns")
        horizontal_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        for record in self.db.recent_sessions(5000):
            usage = ", ".join(
                f"{item_usage['item_name']}: "
                f"{float(item_usage['units_used']):g}"
                for item_usage in self.db.session_item_usages(
                    record["id"]
                )
            )
            notes_and_usage = "; ".join(
                value
                for value in [
                    (record["notes"] or "").strip(),
                    f"Items used: {usage}" if usage else "",
                ]
                if value
            )
            tree.insert(
                "",
                "end",
                iid=str(record["id"]),
                values=(
                    record["session_date"],
                    self.display_treatment_type(
                        record["session_type"]
                    ),
                    record["pak_lot"] or "",
                    record["sak_lot"] or "",
                    record["cartridge_lot"] or "",
                    record["cycler_serial"] or "",
                    record["pureflow_serial"] or "",
                    notes_and_usage,
                ),
            )

        def edit_selected_notes():
            selection = tree.selection()
            if not selection:
                self.themed_dialog(
                    APP_NAME,
                    "Select a treatment from Treatment History first.",
                    [("Close", None)],
                    width=470,
                    height=220,
                )
                return
            self.edit_treatment_notes_dialog(
                int(selection[0]),
                return_to_history=True,
            )

        def delete_selected_treatment():
            selection = tree.selection()
            if not selection:
                self.themed_dialog(
                    APP_NAME,
                    "Select a treatment from Treatment History first.",
                    [("CLOSE", None)],
                    width=470,
                    height=220,
                )
                return

            session_id = int(selection[0])
            record = self.db.session_by_id(session_id)
            if not record:
                self.themed_dialog(
                    APP_NAME,
                    "The selected treatment no longer exists.",
                    [("CLOSE", None)],
                    width=470,
                    height=220,
                )
                self.show_treatment_history()
                return

            usages = self.db.session_item_usages(session_id)
            treatment_name = self.display_treatment_type(
                record["session_type"]
            )

            if usages:
                restored_lines = [
                    f"• {usage['item_name']}: "
                    f"{float(usage['units_used']):g} unit(s)"
                    for usage in usages
                ]
                restoration_text = (
                    "\n\nRecorded incomplete-treatment usage that "
                    "will be restored exactly:\n"
                    + "\n".join(restored_lines)
                )
            elif treatment_type_key(record["session_type"]) in {
                "missed",
                "in_center",
            }:
                restoration_text = (
                    "\n\nThis treatment did not deduct "
                    "inventory units."
                )
            else:
                restoration_text = (
                    "\n\nThe inventory deductions associated with "
                    "this treatment will be undone automatically."
                )

            message = (
                "Delete this treatment permanently?\n\n"
                f"Date: {record['session_date']}\n"
                f"Type: {treatment_name}"
                f"{restoration_text}\n\n"
                "This action cannot be undone."
            )

            def confirm_delete():
                try:
                    self.db.backup_database("change")
                    self.db.delete_session(session_id)
                    self.db.backup_database("change")
                    self.show_treatment_history()
                    self.themed_dialog(
                        "Treatment Deleted",
                        (
                            "The treatment was deleted. "
                            "Its inventory usage has been restored."
                        ),
                        [("CLOSE", None)],
                        width=500,
                        height=230,
                    )
                except Exception as ex:
                    self.themed_dialog(
                        APP_NAME,
                        f"Could not delete treatment:\n{ex}",
                        [("CLOSE", None)],
                        width=520,
                        height=240,
                    )

            selected_action = self.themed_dialog(
                "Delete Treatment",
                message,
                [
                    ("DELETE TREATMENT", "delete"),
                    ("CANCEL", None),
                ],
                width=610,
                height=390 if usages else 330,
            )

            if selected_action == "delete":
                confirm_delete()

        self.button(
            toolbar,
            "Delete Treatment",
            delete_selected_treatment,
        ).pack(side="right", padx=(10, 0))

        self.button(
            toolbar,
            "Edit Selected Treatment Notes",
            edit_selected_notes,
        ).pack(side="right", padx=(0, 10))

        tree.bind(
            "<Double-1>",
            lambda _event: edit_selected_notes(),
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
        theme_var = tk.StringVar(value=self.current_theme)
        rows = [
            ("Patient Name", patient_var, "entry"),
            ("Dialysis Sessions Per Week", sessions_var, "entry"),
            ("Week's First Session Day", first_day_var, "combo"),
            ("First Inventory Group Name", nx_group_var, "entry"),
            ("Second Inventory Group Name", dv_group_var, "entry"),
            ("Application Theme", theme_var, "theme"),
        ]
        for idx, (lab, var, typ) in enumerate(rows):
            tk.Label(body, text=lab, bg=BLUE_PANEL, fg=TEXT).grid(row=idx, column=0, sticky="w", padx=10, pady=8)
            if typ == "combo":
                e = ttk.Combobox(body, textvariable=var, values=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"], width=30, state="readonly")
            elif typ == "theme":
                e = ttk.Combobox(body, textvariable=var, values=list(THEMES.keys()), width=30, state="readonly")
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
                selected_theme = theme_var.get() if theme_var.get() in THEMES else "Medical Blue"
                self.apply_theme(selected_theme, rebuild=False)
                for widget in self.sidebar.winfo_children():
                    widget.destroy()
                self.build_sidebar()
                self.show_settings()
            except Exception as ex:
                messagebox.showerror(APP_NAME, f"Could not save settings:\n{ex}")
        self.button(body, "Save Settings", save_settings).grid(row=6, column=1, sticky="w", padx=10, pady=14)

        p2, b2 = self.make_panel(self.content, "Item Management")
        p2.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        row = tk.Frame(b2, bg=BLUE_PANEL)
        row.pack(fill="x", pady=(0, 8))
        self.button(
            row,
            f"Add {self.group_display_name(GROUP_NX)} Item",
            lambda: self.open_item_editor(None, GROUP_NX),
        ).pack(side="left", padx=4)
        self.button(
            row,
            f"Add {self.group_display_name(GROUP_DV)} Item",
            lambda: self.open_item_editor(None, GROUP_DV),
        ).pack(side="left", padx=4)

        item_tree = ttk.Treeview(
            b2,
            columns=("group", "item"),
            show="headings",
            height=10,
        )
        item_tree.heading("group", text="Inventory Group")
        item_tree.heading("item", text="Item")
        item_tree.column("group", width=210, minwidth=130, anchor="w")
        item_tree.column("item", width=420, minwidth=220, anchor="w")
        item_tree.pack(fill="both", expand=True, pady=(4, 8))

        for inventory_item in self.db.items():
            item_tree.insert(
                "",
                "end",
                iid=str(inventory_item["id"]),
                values=(
                    self.group_display_name(inventory_item["group_name"]),
                    inventory_item["item_name"],
                ),
            )

        self.attach_responsive_tree(
            item_tree,
            font_size=10,
            min_widths={"group": 140, "item": 240},
            stretch_columns=["item"],
        )

        actions = tk.Frame(b2, bg=BLUE_PANEL)
        actions.pack(fill="x")

        def edit_item_management_selected():
            selection = item_tree.selection()
            if not selection:
                self.themed_dialog(
                    APP_NAME,
                    "Select an item first.",
                    [("Close", None)],
                    width=420,
                    height=210,
                )
                return
            self.open_item_editor(int(selection[0]))

        def delete_item_management_selected():
            selection = item_tree.selection()
            if not selection:
                self.themed_dialog(
                    APP_NAME,
                    "Select an item first.",
                    [("Close", None)],
                    width=420,
                    height=210,
                )
                return

            inventory_item = self.db.item_by_id(int(selection[0]))
            if not inventory_item:
                return

            confirmed = self.themed_confirm(
                "Delete Item",
                "Are you sure?\n\n"
                f"Delete '{inventory_item['item_name']}' from active inventory?\n\n"
                "Historical treatment, received-inventory, and correction records "
                "will be retained.",
            )
            if not confirmed:
                return

            self.db.deactivate_item(inventory_item["id"])
            self.db.backup_database("change")
            self.show_settings()

        self.button(
            actions,
            "Edit Selected Item",
            edit_item_management_selected,
        ).pack(side="left", padx=(0, 8))
        self.button(
            actions,
            "Delete Selected Item",
            delete_item_management_selected,
        ).pack(side="left")

        tk.Label(
            actions,
            text="Deleted items are removed from active inventory; historical records remain.",
            bg=BLUE_PANEL,
            fg=MUTED,
        ).pack(side="left", padx=14)

    def export_csv(self):
        filename = filedialog.asksaveasfilename(
            title="Export Inventory CSV",
            defaultextension=".csv",
            initialfile=f"HHD_Inventory_{date.today().isoformat()}.csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if not filename:
            return
        try:
            self.db.export_csv(filename)
            self.themed_export_complete(filename, "CSV Export")
        except Exception as ex:
            self.themed_dialog(
                APP_NAME,
                f"CSV export failed:\n{ex}",
                [("Close", None)],
                width=540,
                height=240,
            )

if __name__ == "__main__":
    app = HHDApp()
    app.mainloop()
