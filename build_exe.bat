@echo off
setlocal
cd /d "%~dp0"
set "APP_VERSION=1.5.5"

echo Building HHD Inventory Manager v%APP_VERSION%
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Please install Python 3.11 or newer.
    pause
    exit /b 1
)

python -m pip show pyinstaller >nul 2>nul
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

python -m py_compile hhd_inventory_manager.py
if errorlevel 1 (
    echo.
    echo Python syntax check failed. Build stopped.
    pause
    exit /b 1
)

python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 (
    echo.
    echo Compatibility tests failed. Build stopped.
    pause
    exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name "HHD_Inventory_Manager" ^
  --icon=hhd_inventory_manager.ico ^
  --add-data "hhd_inventory_manager.ico;." ^
  --add-data "hhd_inventory_manager.png;." ^
  --add-data "hhd_inventory_manager_about.png;." ^
  --add-data "hhd_menu_icon.png;." ^
  hhd_inventory_manager.py

if errorlevel 1 (
    echo.
    echo PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo HHD Inventory Manager v%APP_VERSION% build complete.
echo EXE folder: dist\HHD_Inventory_Manager
pause
