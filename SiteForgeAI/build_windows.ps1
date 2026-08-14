$ErrorActionPreference = 'Stop'
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --windowed --name SiteForgeAI --collect-all PySide6 --hidden-import paramiko --hidden-import cryptography main.py

# Ship buyer-facing documentation with the Windows application.
New-Item -ItemType Directory -Force -Path dist\SiteForgeAI\docs | Out-Null
Copy-Item docs\index.html dist\SiteForgeAI\docs\UserGuide.html -Force
Copy-Item PRIVACY_POLICY.html dist\SiteForgeAI\PRIVACY_POLICY.html -Force
Copy-Item LICENSE.txt dist\SiteForgeAI\LICENSE.txt -Force
Copy-Item THIRD_PARTY_LICENSES.md dist\SiteForgeAI\THIRD_PARTY_LICENSES.md -Force
Copy-Item CHANGELOG.md dist\SiteForgeAI\CHANGELOG.md -Force

if (Test-Path dist\SiteForgeAI.zip) { Remove-Item dist\SiteForgeAI.zip -Force }
Compress-Archive -Path dist\SiteForgeAI -DestinationPath dist\SiteForgeAI.zip
Write-Host 'Build complete: dist\SiteForgeAI.zip'
