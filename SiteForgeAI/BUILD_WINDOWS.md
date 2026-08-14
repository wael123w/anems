# Windows Release Build

Use a clean Windows 10 or Windows 11 x64 machine. Install Python 3.11 or newer for the build step only, then open PowerShell in the project root and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

The script installs the pinned dependency ranges, runs PyInstaller, copies the buyer documentation into the application folder, and creates `dist\SiteForgeAI.zip`.

To create the installer, install Inno Setup 6 on the build machine and open `installer\SiteForgeAI.iss`. Compile the script after `dist\SiteForgeAI` exists. The installer output is written to `dist\installer\SiteForgeAI-Setup.exe`.

Before release, test the installer on a clean Windows machine that does not have Python, Node.js or the development repository. Verify first launch, local project creation, import, preview, AI setup, visual edit, version restore, export, validation, deployment configuration, uninstall and preservation of user project files.

The Linux development environment used to prepare this package cannot produce or verify a Windows EXE or Inno Setup installer. A publisher must perform that final Windows gate before submitting to a marketplace.
