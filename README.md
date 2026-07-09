# HHD Inventory Manager

HHD Inventory Manager is a Windows desktop application for tracking Home Hemodialysis inventory.

It was created to help manage NxStage and DaVita supplies, monitor remaining units, record received inventory, log dialysis sessions, and identify supplies that need reordering.

## Purpose

The program helps a home hemodialysis caregiver or patient maintain a clear, local inventory record of treatment supplies. It calculates estimated inventory usage from logged dialysis sessions and item-specific configuration rules.

## Main Features

- Tracks two supply groups:
  - NxStage Supplies
  - DaVita Supplies
- Configurable patient name.
- Configurable dialysis schedule.
- Per-item settings:
  - Item name
  - Inventory group
  - Baseline inventory count
  - Baseline count date
  - Units used per session
  - Additional units used per week
  - Reuse count across sessions
  - Lifespan days per unit
  - Low threshold
  - Reorder threshold
  - Automatic session usage on/off
- Add, rename, edit, and remove inventory items.
- Record received inventory with date and notes.
- Log regular, extra, missed, and incomplete dialysis sessions.
- Calculates current inventory from:
  - baseline inventory
  - received inventory
  - logged sessions
  - configured usage rules
- Dashboard with current units, estimated weeks remaining, and reorder status.
- Local SQLite database storage.
- Automatic database backup every 10 minutes.
- Database import function for moving the program to another computer.
- CSV export.
- Remembers window size, position, and maximized state.
- Includes a PDF user manual.

## Data Storage

The live database file is:

```text
hhd_inventory.db
```

When running from source, it is stored next to the Python file. When running the built EXE, it is stored next to the executable.

Automatic backup files are stored in:

```text
Documents\HHD Inventory Backups
```

The rolling backup files are:

```text
HHD_Inventory_Backup_Current.db
HHD_Settings_Backup_Current.json
```

## Running from Source

Requirements:

- Windows 10 or Windows 11
- Python 3.11 or newer

Run:

```text
run_HHD_Inventory_Manager.bat
```

## Building the EXE

Run:

```text
build_exe.bat
```

The executable folder will be created under:

```text
dist\HHD_Inventory_Manager
```

## Creating the Installer

Open the included Inno Setup script:

```text
HHD_Inventory_Manager_Setup.iss
```

Compile it with Inno Setup to create the Windows installer.

## Important Safety Note

This software is an inventory tracking tool only. It does not replace medical, DaVita, NxStage, physician, nurse, or clinical instructions. Always verify physical inventory before treatment.
