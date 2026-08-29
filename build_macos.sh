#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
APP_VERSION="1.5.6"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "Building HHD Inventory Manager v${APP_VERSION} for macOS"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python 3 was not found. Install Python 3.11 or newer."
    exit 1
fi

if ! "$PYTHON_BIN" -m pip show pyinstaller >/dev/null 2>&1; then
    echo "Installing PyInstaller..."
    "$PYTHON_BIN" -m pip install pyinstaller
fi

if ! "$PYTHON_BIN" -m pip show pillow >/dev/null 2>&1; then
    echo "Installing Pillow for macOS icon generation..."
    "$PYTHON_BIN" -m pip install pillow
fi

"$PYTHON_BIN" -m unittest discover -s tests -p "test_*.py" -v
"$PYTHON_BIN" -m py_compile hhd_inventory_manager.py

SOURCE_VERSION=$("$PYTHON_BIN" -c 'import hhd_inventory_manager as app; print(app.APP_VERSION)')
if [[ "$SOURCE_VERSION" != "$APP_VERSION" ]]; then
    echo "Version mismatch: build script is ${APP_VERSION} but source is ${SOURCE_VERSION}."
    exit 1
fi

ICON_FILE="$(pwd)/build/macos/hhd_inventory_manager.icns"
mkdir -p "$(dirname "$ICON_FILE")"
"$PYTHON_BIN" -c \
    'from PIL import Image; import sys; Image.open("hhd_inventory_manager.png").save(sys.argv[1], format="ICNS")' \
    "$ICON_FILE"

"$PYTHON_BIN" -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --name "HHD Inventory Manager" \
    --osx-bundle-identifier "com.n4eac.hhd-inventory-manager" \
    --icon "$ICON_FILE" \
    --specpath build/macos \
    --workpath build/macos/pyinstaller \
    --distpath dist/macos \
    --add-data "$(pwd)/hhd_inventory_manager.png:." \
    --add-data "$(pwd)/hhd_inventory_manager_about.png:." \
    --add-data "$(pwd)/hhd_menu_icon.png:." \
    hhd_inventory_manager.py

APP_BUNDLE="dist/macos/HHD Inventory Manager.app"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString ${APP_VERSION}" \
    "$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleVersion string ${APP_VERSION}" \
    "$APP_BUNDLE/Contents/Info.plist" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Set :CFBundleVersion ${APP_VERSION}" \
        "$APP_BUNDLE/Contents/Info.plist"

# Re-apply an ad-hoc signature after updating bundle metadata. Distribution
# builds will replace this with a Developer ID signature before notarization.
codesign --force --deep --sign - "$APP_BUNDLE"

DMG_STAGING="build/macos/dmg-staging"
DMG_FILE="dist/macos/HHD_Inventory_Manager_macOS_arm64_v${APP_VERSION}.dmg"
rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"
ditto "$APP_BUNDLE" "$DMG_STAGING/HHD Inventory Manager.app"
ln -s /Applications "$DMG_STAGING/Applications"
hdiutil create \
    -volname "HHD Inventory Manager ${APP_VERSION}" \
    -srcfolder "$DMG_STAGING" \
    -ov \
    -format UDZO \
    "$DMG_FILE"

echo
echo "Build complete: dist/macos/HHD Inventory Manager.app"
echo "DMG complete: ${DMG_FILE}"
echo "This local build is unsigned. Apple notarization is required for public distribution."
