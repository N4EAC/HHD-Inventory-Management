# Release Build Instructions

To create the Windows installer:

1. Extract this ZIP.
2. Double-click `build_exe.bat`.
3. Wait until it says:

   Build complete.
   EXE folder: dist\HHD_Inventory_Manager

4. Open `HHD_Inventory_Manager_Setup_ProgramFiles_v1.0.10.iss` in Inno Setup.
5. Compile the script.
6. The installer will be created in:

   installer_output\HHD_Inventory_Manager_Setup_v1.0.10.exe

The program installs to Program Files. User data is stored in:

   C:\Users\<username>\AppData\Local\HHD Inventory Manager
