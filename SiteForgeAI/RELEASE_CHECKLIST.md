# SiteForge AI 1.0.0 Release Checklist

## Included in the source distribution

The buyer package should contain the application source, `siteforge/`, `main.py`, `requirements.txt`, `pyproject.toml`, `build_windows.ps1`, `installer/SiteForgeAI.iss`, the English help file under `docs/`, `PRIVACY_POLICY.html`, `README.md`, `USER_GUIDE.md`, `DEPLOYMENT_GUIDE.md`, `AI_PROVIDER_SETUP.md`, `TROUBLESHOOTING.md`, `LICENSE.txt`, `THIRD_PARTY_LICENSES.md`, `CHANGELOG.md`, and the tests.

## Excluded from the buyer package

Do not ship caches, `.pyc` files, `__pycache__`, `.pytest_cache`, local `.siteforge` data, screenshots generated during development, capture scripts, private keys, credentials, personal project folders, or the HTML UI prototype unless it is explicitly labeled as a separate design reference.

## Windows acceptance gate

Build on a clean Windows 10/11 x64 machine. Install from the Inno Setup installer, launch without Python or Node.js installed, create a project without a provider key, configure one provider, generate a project, import a ZIP, click-select an element, preview and apply an edit, undo and redo it, export the project, run validation, create a backup, and uninstall. Repeat deployment tests using safe staging accounts before publishing.

## Marketplace submission gate

Confirm that the final ZIP matches the screenshots and description, all included assets have redistribution rights, the title and tags describe the actual product, the English documentation is publicly viewable, the version is consistent, the publisher identity is correct, and no visible feature is presented as available when it is not supported in the submitted build.
