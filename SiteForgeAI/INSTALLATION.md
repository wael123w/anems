# Installation

على Windows 10/11 شغّل `SiteForgeAI-Setup.exe` بصلاحيات المستخدم العادي. لا يحتاج المستخدم النهائي إلى Python أو Node.js أو Git أو Terminal. يحتفظ التطبيق ببيانات SQLite والأسرار المشفرة في `%APPDATA%\SiteForgeAI`.

للبناء من المصدر، استخدم Python 3.11+ ثم شغّل `build_windows.ps1` على Windows، وبعدها افتح ملف `installer/SiteForgeAI.iss` في Inno Setup لإنتاج `SiteForgeAI-Setup.exe`.

قبل التوزيع التجاري، وقّع الملف التنفيذي رقميًا واختبره على Windows 10 وWindows 11 بحساب مستخدم محدود.
