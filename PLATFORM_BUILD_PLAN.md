# Cross-Platform Build Plan

## Shared application and database

- Keep one Python/Tkinter application and one SQLite schema for Windows,
  macOS, and Linux.
- Store live data in the platform-standard per-user data directory.
- Keep database export/import as the supported transfer path between systems.
- Run the legacy-database and inventory tests before every platform build.

## macOS — implementation started

1. Build `HHD Inventory Manager.app` with `build_macos.sh` and PyInstaller.
2. Test on both Apple silicon and Intel Macs. PyInstaller builds are
   architecture-specific unless a universal2 Python runtime is used.
3. Verify first launch, database creation/import, backups, calendar, exports,
   dialogs, and all treatment classifications.
4. Add Developer ID Application signing and hardened runtime settings.
5. Notarize the application with Apple and staple the notarization ticket.
6. Package the signed app in a DMG and attach it to a GitHub pre-release.

The first local `.app` and DMG builds use an ad-hoc development signature.
They are suitable for testing, but public distribution without Developer ID
signing and notarization will trigger a macOS Gatekeeper warning.

## Ubuntu 24.04 — planned

1. Develop and test in a clean Ubuntu 24.04 environment with Python 3,
   `python3-tk`, `python3-venv`, and the standard build toolchain installed.
2. Build with PyInstaller on Ubuntu 24.04; do not reuse Windows or macOS
   binaries because PyInstaller packages are operating-system-specific.
3. Adopt XDG locations (`$XDG_DATA_HOME`, falling back to
   `~/.local/share`) for the database and settings.
4. Add a `.desktop` launcher and install icons at freedesktop-standard sizes.
5. Validate under the default Ubuntu desktop on both X11 and Wayland.
6. Produce an initial portable archive or AppImage for testing.
7. Produce a `.deb` package after the installation paths and desktop
   integration are stable.
8. Add an Ubuntu 24.04 GitHub Actions build after local validation, then
   publish Linux packages as pre-release assets until field-tested.

## Release gates for every platform

- Existing databases open without record loss.
- Complete/incomplete treatments deduct configured inventory correctly.
- Missed and in-center treatments deduct no inventory.
- Database backup, import, export, and CSV export work.
- Package launches on a clean supported operating-system installation.
