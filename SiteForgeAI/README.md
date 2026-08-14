# SiteForge AI

**SiteForge AI** تطبيق Windows Desktop محلي لبناء مواقع HTML/CSS/JavaScript حقيقية من وصف طبيعي، مع معاينة محلية وتحرير وفحص وتصدير ونشر عبر FTP/FTPS/SFTP. لا يحتاج إلى SaaS backend، ولا يضع مفاتيح API داخل المصدر.

## المزايا المنفذة

| المجال | الحالة |
|---|---|
| مشاريع متعددة محليًا | SQLite مع سجل المواقع |
| ملفات موقع حقيقية | HTML وCSS وJS وfavicon وSEO وrobots وsitemap |
| قوالب جاهزة | Business وRestaurant وPortfolio وAgency وSaaS وLanding |
| Live Preview | QWebEngineView مع Desktop/Tablet/Mobile |
| AI providers | OpenAI وGemini وClaude وOpenRouter عبر BYOK HTTPS |
| AI Editor | تعديل ملفات المشروع المحلية مع سجل التغييرات |
| Import/ZIP | الهيكل جاهز لإضافة الاستيراد التفاعلي |
| Validation | فحص الملفات المطلوبة والروابط والعنوان والوصف |
| Deployment | FTP وFTPS وSFTP مع تأكيد ونسخ احتياطي |
| Export | ZIP قابل للرفع |
| Security | مخزن مشفر محليًا للمفاتيح |
| Testing | اختبارات للنواة والبناء والتصدير |

## التشغيل من المصدر

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

على Linux للتطوير يمكن استخدام `python3 main.py` بعد تثبيت PySide6. في Windows يُنصح باستخدام Python 3.11 أو أحدث.

## BYOK

افتح **Settings** واختر المزود وأدخل model وAPI key. تُحفظ القيم في `%APPDATA%\SiteForgeAI\secrets.bin` بتشفير Fernet مع اشتقاق مفتاح PBKDF2. لا يُحفظ أي مفتاح داخل المشروع أو ملفات الموقع أو ملف التثبيت.

## التوزيع كمنتج Windows

```powershell
.\build_windows.ps1
```

ينتج الأمر مجلد `dist\SiteForgeAI` وملف ZIP للتوزيع. لإنشاء Installer باستخدام Inno Setup، افتح `installer\SiteForgeAI.iss` بعد تثبيت Inno Setup ثم شغّل:

```powershell
iscc installer\SiteForgeAI.iss
```

## سياسة النشر الآمن

قبل النشر، يفحص التطبيق المشروع ويمنع الرفع عند وجود أخطاء blocking، ثم يطلب تأكيدًا صريحًا وينشئ نسخة احتياطية محلية. التطبيق لا يحذف ملفات الاستضافة تلقائيًا. يجب اختبار بيانات FTP/SFTP على استضافة تجريبية قبل النشر التجاري.

## الاختبارات

```bash
pytest
```

## البنية

`main.py` يحتوي واجهة PySide6، و`siteforge/core` لقاعدة البيانات والأسرار، و`siteforge/providers` لمزودي AI، و`siteforge/services` لبناء المواقع والفحص والنشر، و`tests` للاختبارات.

## ملاحظات CodeCanyon

قبل البيع، أضف اسم الشركة وشعارها، سياسة الخصوصية والترخيص، شاشة About، رقم إصدار ثابت، توقيعًا رقميًا لملفات Windows، واختبارًا على Windows 10/11 مع استضافة FTP وSFTP فعلية. لا تُعلن عن مزود AI باعتباره متاحًا دون API key صالح من المستخدم.

## Update 0.2.0

أضيفت خدمة `AIRepairService` التي تنتج Findings وProposed Fix وUnified Diff دون تطبيق تلقائي، و`VersionStore` للإصدارات والاستعادة، و`VisualEditor` لتعديل عناصر HTML/CSS الفعلية، و`AIGenerationService` لمسار الخطة ثم الملفات، و`deployment_diff` وHTTP verification. كما أضيفت القوالب Real Estate وHotel وMedical وConstruction، وملفات CodeCanyon: `INSTALLATION.md` و`AI_PROVIDER_SETUP.md` و`DEPLOYMENT_GUIDE.md` و`TROUBLESHOOTING.md` و`CHANGELOG.md` و`LICENSE.txt` و`THIRD_PARTY_LICENSES.md`.

النسخة الحالية لا تنفذ حذفًا بعيدًا للملفات عند وجود Diff دون تأكيد، ولا تُرسل ملفات المشروع إلى مزود AI إلا عند تشغيل عملية AI صريحة.

## Live Preview Direct Editing

في صفحة Live Preview، انقر أي عنصر داخل الموقع الحقيقي لتحديده. يظهر selector العنصر، ثم اكتب طلبًا مثل تغيير اللون أو تكبير العنوان أو حذف القسم أو إضافة صورة. عند تشغيل Ask AI مع BYOK صالح، يُرسل سياق العنصر وملفات HTML/CSS ذات الصلة إلى المزود ويعاد اقتراح منظم. لا تُكتب النتيجة قبل الضغط على Apply Changes.

عند التطبيق، ينشئ SiteForge AI نسخة داخل `.siteforge/versions`، يكتب التعديل في ملفات المشروع الفعلية، ثم يعيد تحميل `index.html` في المعاينة. يدعم المحرك النص والأنماط والحذف وإضافة الصور، مع Undo وRedo مبنيين على الإصدارات المحلية. عند عدم إعداد BYOK، يعرض التطبيق اقتراحًا محليًا صريحًا ولا يدّعي أنه استدعى AI.
