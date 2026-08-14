# SiteForge AI 1.0.0 — Release Readiness

## Completed in this release package

The package contains the local-first PySide6 application, SQLite storage, encrypted local secret store, BYOK provider adapters, real website generation, folder and ZIP import, Live Preview, QWebChannel element selection, direct visual AI editing, preview-before-apply, version backups, Undo/Redo, AI Repair, SEO analysis, validation, ZIP export, deployment diff, backup-before-deploy, FTP/FTPS/SFTP adapters, cPanel and DirectAdmin adapters, HTTP verification, deployment history, English HTML help documentation, privacy policy, support policy, release manifest, item listing copy, license notice, third-party license inventory, build instructions, tests and preview assets.

## Verification completed in the current environment

Python compilation passes. The automated suite passes with 12 tests. The final source ZIP passes `unzip -t`. No API keys, hosting credentials, local databases, project folders or development caches are included in the release ZIP.

## Final publisher gate

The current environment is Linux and does not contain Wine, PowerShell or Inno Setup. Therefore a Windows EXE and Inno Setup installer were not built or smoke-tested here. Before public submission, run `BUILD_WINDOWS.md` on a clean Windows 10/11 x64 machine, create `SiteForgeAI-Setup.exe`, install it on a second clean machine, and execute the acceptance checklist in `RELEASE_CHECKLIST.md`.

This is a release candidate source package, not a claim that the Envato review outcome is guaranteed. Envato review still depends on the final Windows artifact, presentation assets, metadata, legal review and the behavior observed by the reviewer.
