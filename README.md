# HHD Inventory Manager

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows11&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-Apple%20silicon-000000?logo=apple&logoColor=white)

HHD Inventory Manager was created to help home hemodialysis patients and caregivers organize treatment supplies, record treatment activity, and maintain a clear history of inventory and treatment information.

Release packages are available for Windows and Apple-silicon Macs, with Ubuntu
24.04 planned next. All platforms use the same SQLite database format so
databases can be exported and imported between systems.

**[Download HHD Inventory Manager v1.5.7](https://github.com/N4EAC/HHD-Inventory-Management/releases/tag/v1.5.7)**

- Windows 10/11: `HHD_Inventory_Manager_Setup_v1.5.7.1.exe`
- Apple-silicon macOS: `HHD_Inventory_Manager_macOS_arm64_v1.5.7.dmg`

The current macOS package is not Apple-notarized. macOS may require the user to
approve the application in Privacy & Security before its first launch.

<img width="1584" height="988" alt="image" src="https://github.com/user-attachments/assets/3e618332-5457-4214-80de-8d2de28d12d1" />

## New in version 1.5.7

Version 1.5.7 expands Complete Treatment inventory tracking, improves the
native macOS experience, and adds the C77 visual theme. See the
[v1.5.7 release page](https://github.com/N4EAC/HHD-Inventory-Management/releases/tag/v1.5.7)
for installers and release notes.

- Complete treatments now record a **Warmer Line lot number** and the number
  of **Hanging bags used** from 0 through 10.
- Inventory items have a stable **Inventory Type** classification: Standard,
  SAK, Hanging bags, or Warmer lines. Treatment deductions use this
  classification instead of relying on an editable item name.
- A SAK is deducted from a Complete Treatment only when a SAK lot number is
  entered.
- Complete Treatments record the treatment time. After the first treatment on
  a SAK, the user enters the estimated hours remaining (1–80). HHDIM deducts
  the remaining half when it is used by a second SAK treatment, when that time
  expires, or when a later Complete Treatment switches to hanging bags and a
  Warmer Line without a SAK.
- Hanging bags replace the SAK for that treatment. HHDIM prevents entering a
  SAK lot and hanging bags together, then deducts the selected number of bags.
- A Warmer Line lot number is required whenever one or more hanging bags are
  entered, preventing an incomplete alternative-treatment inventory record.
- Entering a Warmer Line lot deducts one classified Warmer Line from inventory.
- Existing databases are migrated safely. Recognizable SAK, Hanging Bags, and
  Warmer Lines items are classified automatically and can be reviewed in Item
  Settings.
- Treatment history, calendar exports, and lot-number search now include the
  new Warmer Line and Hanging Bags information.
- macOS now has native application, File, Treatment, Inventory, and Help menus,
  including working About and Settings commands.
- The Incomplete Treatment item-usage fields are shown only when Incomplete
  Treatment is selected.
- Added the distressed post-apocalyptic C77 theme with accessible button and
  treatment-status colors.

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
- Record PAK, SAK, cartridge, and Warmer Line lot numbers.
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
- Select from multiple visual themes, including Medical Blue, Beige, Dark,
  Gray 95, Red Shadow, Cyberpunk, and the distressed post-apocalyptic C77.

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
