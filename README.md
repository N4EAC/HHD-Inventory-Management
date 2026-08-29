# HHD Inventory Manager

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows11&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-Apple%20silicon-000000?logo=apple&logoColor=white)

HHD Inventory Manager was created to help home hemodialysis patients and caregivers organize treatment supplies, record treatment activity, and maintain a clear history of inventory and treatment information.

Release packages are available for Windows and Apple-silicon Macs, with Ubuntu
24.04 planned next. All platforms use the same SQLite database format so
databases can be exported and imported between systems.

<img width="1584" height="988" alt="image" src="https://github.com/user-attachments/assets/3e618332-5457-4214-80de-8d2de28d12d1" />

## New in version 1.5.6

- Brand-new users start with an empty inventory instead of preloaded items.
- A first-run setup assistant collects the patient name, two provider names,
  scheduled treatments per week, and first treatment day.
- The assistant explains that the weekly schedule is used to calculate
  **Weeks Remaining** and never deducts inventory automatically.
- New users may import an existing HHDIM database before entering setup data.
- Initial inventory can be entered one item at a time for either provider, or
  skipped and entered later.
- **Set Up Later — Exit HHDIM** safely closes the application and resumes setup
  on the next launch.
- Existing databases bypass onboarding and are upgraded without removing or
  replacing existing data.
- Added **In Center Treatment**, which records the treatment without deducting
  home inventory.
- Improved macOS button colors and made Treatment Entry vertically scrollable.

## Functions

- Track NxStage and DaVita treatment supplies.
- Display current quantities and supply status.
- Estimate remaining weeks of supplies.
- Record received inventory and quantity corrections.
- Record completed, incomplete, extra, missed, and in-center treatments.
- In-center treatments are recorded without deducting any home inventory.
- Automatically deduct configured supply usage from inventory.
- Record PAK, SAK, and cartridge lot numbers.
- Record cycler and PureFlow serial numbers.
- Add and edit treatment notes.
- View treatments in a monthly calendar.
- View treatment history on a dedicated screen.
- Search for PAK, SAK, and cartridge lot numbers and identify treatment dates when they were used.
- Export lot-number search results to CSV.
- Export treatment calendar data to CSV.
- Export inventory data to CSV.
- View inventory history.
- Add, rename, deactivate, and configure inventory items.
- Configure treatment schedules and supply usage.
- Guide new users through patient/provider setup, optional database import,
  and initial inventory entry without preloading inventory items.
- Import and export the application database.
- Create and restore backups.
- Remember application settings, window size, and position.
- Select from multiple visual themes, including Medical Blue, Beige, Dark, Gray 95, Red Shadow, and Cyberpunk.

## Platform builds

### Windows

Run `build_exe.bat` on Windows, then compile
`HHD_Inventory_Manager_Setup.iss` with Inno Setup. The build runs syntax,
version-consistency, and database-compatibility tests before packaging.

### macOS

Run `./build_macos.sh` on an Apple-silicon Mac. It produces the application and
compressed DMG under `dist/macos`. Public distribution still requires a
Developer ID signature and Apple notarization to avoid a Gatekeeper warning.

### Linux

Ubuntu 24.04 packaging is planned. See `PLATFORM_BUILD_PLAN.md` for the staged
AppImage/portable archive and `.deb` plan.
