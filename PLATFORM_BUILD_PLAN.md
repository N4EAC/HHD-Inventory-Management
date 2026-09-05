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

## Linux — builder ready for testing

Run `./build.linux.sh` on the target distribution. It detects the distro,
architecture, and package manager, installs build prerequisites, creates an
isolated Python environment, runs tests, and packages the PyInstaller output.

- Debian, Ubuntu, Mint, and derivatives: `.deb`
- Fedora, RHEL, Rocky, AlmaLinux, openSUSE, and derivatives: `.rpm`
- Arch, Manjaro, EndeavourOS, and derivatives: `.pkg.tar.zst`
- Every distribution: portable `.tar.gz`

Use `--no-install` when dependencies are externally managed, `--yes` for
noninteractive installation, and `--format` to override detection. Builds must
run on Linux; Windows and macOS PyInstaller output cannot be reused.

## Release gates for every platform

- Existing databases open without record loss.
- Complete/incomplete treatments deduct configured inventory correctly.
- Missed and in-center treatments deduct no inventory.
- Database backup, import, export, and CSV export work.
- Package launches on a clean supported operating-system installation.
