
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
from datetime import datetime, date
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_NAME = "HHD Inventory Manager"
APP_VERSION = "1.0.2"
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
        defaults = {
            "patient_name": "Patient Name",
            "sessions_per_week": "4",
            "first_session_day": "Sunday",
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
                 units_per_week=0, reusable_sessions=1, lifespan_days=0, auto_session_usage=1):
        item_name = item_name.strip()
        if not item_name:
            raise ValueError("Item name cannot be blank.")
        if group_name not in (GROUP_NX, GROUP_DV):
            raise ValueError("Invalid inventory group.")
        baseline_date = baseline_date or iso_today()
        self.conn.execute("""
            INSERT INTO items(
                group_name,item_name,baseline_units,baseline_date,min_threshold,low_threshold,
                units_per_session,units_per_week,reusable_sessions,lifespan_days,auto_session_usage,active
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,1)
        """, (
            group_name, item_name, float(baseline_units), baseline_date,
            float(min_threshold), float(low_threshold), float(units_per_session),
            float(units_per_week), max(float(reusable_sessions), 1.0),
            int(lifespan_days), int(auto_session_usage)
        ))
        self.conn.commit()

    def update_item(self, item_id, **kwargs):
        allowed = {
            "group_name", "item_name", "baseline_units", "baseline_date", "min_threshold",
            "low_threshold", "units_per_session", "units_per_week", "reusable_sessions",
            "lifespan_days", "auto_session_usage", "active"
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

    def session_equiv_sum(self, since_date):
        row = self.conn.execute(
            "SELECT COALESCE(SUM(session_equivalent),0) AS total FROM session_log WHERE session_date>=?",
            (since_date,)
        ).fetchone()
        return float(row["total"])

    def weeks_since(self, since_date):
        d = parse_date(since_date)
        return max(0, (date.today() - d).days / 7.0)

    def current_count(self, item):
        baseline = float(item["baseline_units"])
        since = item["baseline_date"] or self.get_setting("created_date", iso_today())
        received = self.received_sum(item["id"], since)
        corrections = self.corrections_sum(item["id"], since)
        sessions = self.session_equiv_sum(since)

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
        self.build_sidebar()
        self.show_dashboard()
        self.schedule_clock_update()
        self.schedule_auto_backup()

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
        messagebox.showinfo(
            "About HHD Inventory Manager",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "Created by Eduardo A. de Carvalho,\n"
            "husband and caregiver of Joelle.\n\n"
            "This software is an inventory tracking tool only. "
            "Always verify physical inventory before treatment."
        )

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

    def configure_styles(self):
        self.style.configure("Treeview", background=BLUE_PANEL, foreground=TEXT, fieldbackground=BLUE_PANEL, rowheight=28, font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading", background=BLUE_HEADER, foreground=TEXT, font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[("selected", "#126A9F")], foreground=[("selected", "white")])

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

    def button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=BUTTON_BG, fg=TEXT, activebackground=BUTTON_HOVER,
                         activeforeground=TEXT, relief="flat", padx=14, pady=7, font=("Segoe UI", 10), cursor="hand2")

    def build_sidebar(self):
        tk.Label(self.sidebar, text="HHD MENU", bg=BLUE_PANEL, fg=CYAN, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18, pady=(18, 8))
        buttons = [
            ("⌂  Dashboard", self.show_dashboard),
            ("▣  NxStage Supplies", lambda: self.show_inventory(GROUP_NX)),
            ("▣  DaVita Supplies", lambda: self.show_inventory(GROUP_DV)),
            ("☑  Log Session", self.show_log_session),
            ("＋  Received Inventory", self.show_received),
            ("⚙  Settings / Items", self.show_settings),
            ("⇧  Import Database", self.import_database_action),
            ("⇩  Export CSV", self.export_csv),
            ("ⓘ  About", self.show_about),
        ]
        for text, cmd in buttons:
            tk.Button(self.sidebar, text=text, command=cmd, anchor="w", bg=BLUE_PANEL, fg=TEXT, activebackground=BLUE_HEADER,
                      activeforeground=TEXT, relief="flat", bd=0, font=("Segoe UI", 10), padx=14, pady=10, cursor="hand2").pack(fill="x", padx=8, pady=2)

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
        self.button(top, "Log Session", self.show_log_session).pack(side="right", padx=6)

        row = tk.Frame(self.content, bg=BLUE_BG)
        row.pack(fill="both", expand=True, padx=16, pady=8)
        p1, b1 = self.make_panel(row, "NXSTAGE SUPPLIES")
        p1.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.inventory_tree(b1, GROUP_NX, compact=True)
        p2, b2 = self.make_panel(row, "DAVITA SUPPLIES")
        p2.pack(side="left", fill="both", expand=True, padx=(8, 0))
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
        cols = ("item", "units", "weeks", "status")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=8 if compact else 18)
        for c, h, w in [("item","Item",300),("units","Units Left",90),("weeks","Weeks Left",90),("status","Status",110)]:
            tree.heading(c, text=h)
            tree.column(c, width=w, anchor="w" if c=="item" else "center")
        tree.pack(fill="both", expand=True)
        tree.tag_configure("ok", foreground=GREEN)
        tree.tag_configure("low", foreground=YELLOW)
        tree.tag_configure("reorder", foreground=RED)
        for item in self.db.items(group):
            current, *_ = self.db.current_count(item)
            status, _ = self.db.status(item, current)
            weeks = self.db.weeks_remaining(item, current)
            weeks_txt = "Manual" if weeks is None else f"{weeks:.1f}"
            units_txt = f"{current:.1f}".rstrip("0").rstrip(".")
            tag = "ok" if status == "OK" else ("low" if status == "LOW" else "reorder")
            tree.insert("", "end", iid=str(item["id"]), values=(item["item_name"], units_txt, weeks_txt, status), tags=(tag,))
        if not compact:
            tree.bind("<Double-1>", lambda e: self.open_item_editor(int(tree.selection()[0])) if tree.selection() else None)
        return tree

    def show_inventory(self, group):
        self.clear_content()
        top = tk.Frame(self.content, bg=BLUE_BG)
        top.pack(fill="x", padx=16, pady=12)
        tk.Label(top, text=group, bg=BLUE_BG, fg=CYAN, font=("Segoe UI", 16, "bold")).pack(side="left")
        self.button(top, "Add New Item", lambda: self.open_item_editor(None, default_group=group)).pack(side="right", padx=6)
        self.button(top, "Remove Selected Item", lambda: self.remove_selected_item()).pack(side="right", padx=6)
        self.button(top, "Edit / Rename Selected", lambda: self.edit_selected_item()).pack(side="right", padx=6)
        p, b = self.make_panel(self.content, f"{group} Inventory")
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
        self.center_child_window(win, 580, 680)
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="Add New Item" if is_new else f"Edit Item: {item['item_name']}",
                 bg=BLUE_BG, fg=CYAN, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=14)

        form = tk.Frame(win, bg=BLUE_PANEL, highlightbackground=BORDER, highlightthickness=1)
        form.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        vars_ = {}

        def val(key, default):
            return str(default if is_new else item[key])

        group_var = tk.StringVar(value=default_group if is_new else item["group_name"])
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
                e = ttk.Combobox(form, textvariable=var, values=[GROUP_NX, GROUP_DV], width=34, state="readonly")
            else:
                e = tk.Entry(form, textvariable=var, bg=INPUT_BG, fg=TEXT, insertbackground=TEXT, relief="solid", bd=1, font=("Segoe UI", 10), width=38)
            e.grid(row=idx, column=1, sticky="ew", padx=14, pady=7)

        auto_var = tk.IntVar(value=1 if is_new else int(item["auto_session_usage"]))
        tk.Checkbutton(form, text="Auto-calculate usage from logged dialysis sessions", variable=auto_var,
                       bg=BLUE_PANEL, fg=TEXT, activebackground=BLUE_PANEL, activeforeground=TEXT,
                       selectcolor=INPUT_BG, font=("Segoe UI", 10)).grid(row=len(rows), column=0, columnspan=2, sticky="w", padx=14, pady=10)

        sessions_per_week = self.db.get_setting("sessions_per_week", "4")
        tk.Label(
            form,
            text=f"Forecast weekly usage = (Units per session ÷ reusable sessions × {sessions_per_week} scheduled sessions/week) + additional weekly usage.",
            bg=BLUE_PANEL,
            fg=MUTED,
            wraplength=500,
            justify="left",
            font=("Segoe UI", 9)
        ).grid(row=len(rows)+1, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 10))

        form.columnconfigure(1, weight=1)

        def save():
            try:
                group = vars_["group_name"].get()
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
                label = f"{r['group_name']} — {r['item_name']}"
            else:
                label = r["item_name"]
            labels.append(label)
            self._item_dropdown_map[label] = r["id"]

        return labels

    def selected_item_id_from_value(self, value):
        return getattr(self, "_item_dropdown_map", {}).get(value)

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
            tree.insert("", "end", values=(r["received_date"], r["group_name"], r["item_name"], r["units"], r["notes"] or ""))

    def show_log_session(self):
        self.clear_content()
        tk.Label(self.content, text="Log Dialysis Session", bg=BLUE_BG, fg=CYAN, font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=12)
        panel, body = self.make_panel(self.content, "Session Entry")
        panel.pack(fill="x", padx=16, pady=(0, 14))
        date_var = tk.StringVar(value=iso_today())
        type_var = tk.StringVar(value="Regular Session")
        equiv_var = tk.StringVar(value="1")
        notes_var = tk.StringVar()
        for idx, (lab, var) in enumerate([("Session Date YYYY-MM-DD", date_var), ("Session Type", type_var), ("Session Equivalent", equiv_var), ("Notes", notes_var)]):
            tk.Label(body, text=lab, bg=BLUE_PANEL, fg=TEXT).grid(row=idx, column=0, sticky="w", padx=10, pady=8)
            if idx == 1:
                e = ttk.Combobox(body, textvariable=var, values=["Regular Session", "Extra Session", "Missed Session", "Incomplete Session"], width=30, state="readonly")
            else:
                e = tk.Entry(body, textvariable=var, bg=INPUT_BG, fg=TEXT, insertbackground=TEXT, relief="solid", bd=1, width=34)
            e.grid(row=idx, column=1, sticky="w", padx=10, pady=8)
        tk.Label(body, text="Equivalent: Regular/Extra = 1, Missed = 0, Incomplete = 0.5 or any decimal.",
                 bg=BLUE_PANEL, fg=MUTED).grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))
        def adjust(*_):
            if type_var.get() == "Missed Session": equiv_var.set("0")
            elif type_var.get() == "Incomplete Session": equiv_var.set("0.5")
            else: equiv_var.set("1")
        type_var.trace_add("write", adjust)

        def save_session():
            try:
                eq = float(equiv_var.get())
                if eq < 0: raise ValueError("Session equivalent cannot be negative.")
                self.db.add_session(parse_date(date_var.get()).isoformat(), type_var.get(), eq, notes_var.get())
                self.db.backup_database("change")
                notes_var.set("")
                self.show_log_session()
            except Exception as ex:
                messagebox.showerror(APP_NAME, f"Could not save session:\n{ex}")
        self.button(body, "Save Session", save_session).grid(row=5, column=1, sticky="w", padx=10, pady=14)

        p2, b2 = self.make_panel(self.content, "Recent Sessions")
        p2.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        tree = ttk.Treeview(b2, columns=("date","type","equiv","notes"), show="headings")
        for c, h, w in [("date","Date",120),("type","Type",180),("equiv","Equivalent",100),("notes","Notes",500)]:
            tree.heading(c, text=h); tree.column(c, width=w, anchor="w")
        tree.pack(fill="both", expand=True)
        for r in self.db.recent_sessions(50):
            tree.insert("", "end", values=(r["session_date"], r["session_type"], r["session_equivalent"], r["notes"] or ""))

    def show_settings(self):
        self.clear_content()
        tk.Label(self.content, text="Settings / Items", bg=BLUE_BG, fg=CYAN, font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=16, pady=12)
        panel, body = self.make_panel(self.content, "General and Schedule Settings")
        panel.pack(fill="x", padx=16, pady=(0, 14))
        patient_var = tk.StringVar(value=self.db.get_setting("patient_name", "Patient Name"))
        sessions_var = tk.StringVar(value=self.db.get_setting("sessions_per_week", "4"))
        first_day_var = tk.StringVar(value=self.db.get_setting("first_session_day", "Sunday"))
        rows = [("Patient Name", patient_var, "entry"), ("Dialysis Sessions Per Week", sessions_var, "entry"), ("Week's First Session Day", first_day_var, "combo")]
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
                self.save_local_settings()
                self.show_settings()
            except Exception as ex:
                messagebox.showerror(APP_NAME, f"Could not save settings:\n{ex}")
        self.button(body, "Save Settings", save_settings).grid(row=3, column=1, sticky="w", padx=10, pady=14)

        p2, b2 = self.make_panel(self.content, "Item Management")
        p2.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        row = tk.Frame(b2, bg=BLUE_PANEL)
        row.pack(fill="x", pady=(0, 8))
        self.button(row, "Add NxStage Item", lambda: self.open_item_editor(None, GROUP_NX)).pack(side="left", padx=4)
        self.button(row, "Add DaVita Item", lambda: self.open_item_editor(None, GROUP_DV)).pack(side="left", padx=4)
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
