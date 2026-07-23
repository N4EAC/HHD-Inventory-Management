# HHD Inventory Manager


<img width="1408" height="1032" alt="image" src="https://github.com/user-attachments/assets/d5e2db8b-052b-40f7-8a8c-1f9ee62516e9" />

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/ed4f8eb2-2801-40ab-ba78-e1900c7900f7" />


HHD Inventory Manager is a Windows desktop application for tracking Home Hemodialysis inventory.

It was created to help manage NxStage and DaVita supplies, monitor remaining units, record received inventory, log dialysis sessions, and identify supplies that need reordering.

## Purpose

The program helps a home hemodialysis caregiver or patient maintain a clear, local inventory record of treatment supplies. It calculates estimated inventory usage from logged dialysis sessions and item-specific configuration rules.

## Main Features

- Tracks two supply groups with editable display names.
  - Default: NxStage Supplies
  - Default: DaVita Supplies
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
- Calculates current inventory from baseline inventory, received inventory, logged sessions, and configured usage rules.
- Dashboard with current units, estimated weeks remaining, reorder status, and animated status LEDs.
- Green LED for OK, flashing yellow LED for LOW, and flashing red LED for RE-ORDER.
- Larger inventory and sidebar fonts for improved readability.
- User-adjustable inventory font controls on the Dashboard and inventory group screens.
- Inventory font adjustment is limited to five points below or above the default size.
- Alert column uses animated status LEDs; Status labels are shown in bold text.
- Local SQLite database storage.
- Automatic database backup every 10 minutes.
- Database import function for moving the program to another computer.
- CSV export.
- Remembers window size, position, and maximized state.
- Includes a PDF user manual.


- Prominent Submit Treatment button positioned separately at the bottom of the sidebar.
- Treatment Notes field stored with each treatment record.
- Treatment history notes reading panel with controlled Edit and Save Notes actions.
- Inventory History graph with selectable periods: 1 week, 1 month, 3 months, 6 months, 1 year, or all time.

- SAK attempted-treatment accounting: regular, extra, and incomplete treatments each consume one reusable-session slot; missed treatments consume none.
- Per-item option to count incomplete treatments as a full item use.

- Responsive, equal-width NxStage and DaVita dashboard panels at normal and maximized window sizes.
- Treatment history hides the internal Equivalent value to avoid end-user confusion.

- Dark medical-blue themed About dialog matching the main application.
- Larger Treatment History table, headings, and treatment notes fonts.

- Corrected selected Inventory History period dates so the requested range is always displayed, even when available item data begins later.

- Inventory History X-axis now always spans the selected period.
- Dates before an item's baseline are visibly marked as unavailable instead of being plotted as calculated history.


- Responsive tables automatically adjust row heights and column widths to the selected font size and available panel width.
- Theme selection in Settings: Medical Blue, Beige, and Dark.
- Database export action located beside database import in the left menu.
- Treatments button replaces the former Submit Treatment label.
- Treatment Calendar with Month and Week views; performed treatments are green, missed treatments red, and incomplete treatments yellow.


- Inventory quantities are normalized to whole or half units only; values such as .4 or .8 are not displayed.
- One-time option removes the existing .5 fraction from the calculated total; unchecked by default.
- Saving verifies the result before closing; for example, 23.5 must become 23.0.
- Treatment notes are displayed inside the corresponding Treatment Calendar day.

- Calendar legend remains visible in Month and Week views.
- Week view opens on the current week when selected.
- Added Cyberpunk theme with neon cyan, purple, green, yellow, and magenta accents.


- Calendar wording changed to Complete treatment; legend now says Complete.
- Settings / Items moved directly above About.
- Item Management now includes a selectable item list and Delete Selected Item action with themed confirmation.
- About dialog follows the current theme and includes a link to the GitHub Releases page.
- CSV and database export completion dialogs follow the current theme and can open the export folder.
- HHD MENU heading now includes a medical kidney-style icon.

- Fixed themed confirmation dialog sizing so Yes/No buttons remain fully visible at Windows display scaling levels.

## Data Storage

Program files can be installed under:

```text
C:\Program Files\HHD Inventory Manager
```

The live writable database and settings are stored per Windows user under:

```text
C:\Users\<username>\AppData\Local\HHD Inventory Manager
```

Main user data files:

```text
hhd_inventory.db
hhd_inventory_settings.json
```

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
HHD_Inventory_Manager_Setup_ProgramFiles_v1.1.6.iss
```

Compile it with Inno Setup to create the Windows installer.

## Important Safety Note

This software is an inventory tracking tool only. It does not replace medical, DaVita, NxStage, physician, nurse, or clinical instructions. Always verify physical inventory before treatment.

## Version 1.1.6

- Added a unified kidney application icon for the EXE, taskbar, title bar, installer, shortcuts, and About window.
- Added multi-resolution Windows icon sizes from 16×16 through 256×256.


### v1.1.6 corrected icon
- Replaced the bean-shaped icon with the user-approved cyan kidney icon.
- The same icon is used in the HHD menu, application window, taskbar, executable, installer, and shortcuts.
