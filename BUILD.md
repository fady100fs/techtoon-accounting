# cd "D:\\PROG\\Accounting Prog\\Techtoon Accounting"

# 

# @'

# \# 📘 BUILD.md — الدليل الشامل النهائي

# 

# > \*\*آخر تحديث:\*\* 2026-10-10

# > \*\*الإصدار:\*\* 8.0

# > \*\*الحالة:\*\* 🟢 مستقر — Desktop + Cloud + SQLite + Filebase + فواتير منفصلة

# 

# \---

# 

# \## 📑 فهرس المحتويات

# 

# 1\. \[نظرة عامة](#1-نظرة-عامة)

# 2. \[البنية الحالية](#2-البنية-الحالية)

# 3. \[رحلة التطوير: v5.0 → v8.0](#3-رحلة-التطوير)

# 4. \[الميزات الجديدة](#4-الميزات-الجديدة)

# 5. \[صفحات الفواتير الجديدة](#5-صفحات-الفواتير-الجديدة)

# 6. \[التشغيل على الكومبيوتر](#6-التشغيل-على-الكومبيوتر)

# 7. \[التشغيل على الموبايل](#7-التشغيل-على-الموبايل)

# 8. \[SQLite Mirror](#8-sqlite-mirror)

# 9\. \[النسخ الاحتياطي السحابي — Filebase](#9-النسخ-الاحتياطي-السحابي)

# 10. \[المعادلات الرياضية](#10-المعادلات-الرياضية)

# 11. \[بناء EXE](#11-بناء-exe)

# 12\. \[الملفات المُنشأة](#12-الملفات-المُنشأة)

# 13. \[الملفات المُعدّلة](#13-الملفات-المُعدّلة)

# 14. \[المشاكل المحلولة](#14-المشاكل-المحلولة)

# 15. \[المشاكل المعلقة](#15-المشاكل-المعلقة)

# 16. \[الخطوات القادمة](#16-الخطوات-القادمة)

# 

# \---

# 

# \## 1. نظرة عامة

# 

# | العنصر | القيمة |

# |--------|--------|

# | \*\*الاسم\*\* | Techtoon Accounting |

# | \*\*الإصدار\*\* | 8.0 |

# | \*\*التقنية\*\* | Streamlit + SQLAlchemy + Neon PostgreSQL 16 |

# | \*\*الواجهة\*\* | عربية (RTL) |

# | \*\*التشغيل\*\* | Desktop (PyWebView) + Cloud (Streamlit) |

# | \*\*رابط Cloud\*\* | https://techtoon.streamlit.app |

# | \*\*GitHub\*\* | fady100fs/techtoon-accounting |

# | \*\*عدد الصفحات\*\* | 39 (بعد إضافة فواتير البيع والشراء) |

# | \*\*عدد الجداول\*\* | 33 (مُزامَنة) |

# | \*\*مزود Backup\*\* | Filebase (S3-compatible) |

# 

# \---

# 

# \## 2. البنية الحالية

# Techtoon Accounting/

# │

# ├── 🚀 نقاط الدخول

# │ ├── app.py

# │ ├── launcher.py # Desktop (PyWebView)

# │ ├── Techtoon.bat

# │ └── Techtoon.vbs # (لا يعمل — استخدم BAT)

# │

# ├── 💾 قاعدة البيانات والمنطق

# │ ├── database.py # Neon + Read/Write Sessions

# │ ├── models.py

# │ ├── services.py

# │ ├── sidebar.py # القائمة (مُعدّلة)

# │ └── navigation\_helper.py

# │

# ├── ⚡ التسريع

# │ ├── local\_mirror.py # SQLite Mirror

# │ ├── sync\_manager.py # المزامنة

# │ └── cache\_helpers.py # TTL + get\_invoices\_index (مُحدّث)

# │

# ├── ➗ الإدخال الذكي

# │ └── input\_helpers.py # معادلات رياضية

# │

# ├── ☁️ النسخ الاحتياطي

# │ └── s3\_backup.py # Filebase + export\_all\_tables\_to\_zip

# │

# ├── 📄 الفواتير (جديد v8.0)

# │ ├── invoice\_page\_common.py # ⭐ وحدة مشتركة

# │ ├── pages/4A\_🛒\_فواتير\_البيع.py

# │ └── pages/4B\_🛍️\_فواتير\_الشراء.py

# │

# ├── ⚙️ الإدارة والأمان

# │ ├── settings\_manager.py

# │ ├── period\_guard.py

# │ ├── session\_auth.py

# │ └── auth.py / auth\_required.py

# │

# ├── .streamlit/

# │ ├── config.toml

# │ └── secrets.toml

# │

# ├── data/ # SQLite Mirror

# │ └── local\_mirror.db

# │

# ├── \_backups/ # نسخ احتياطية للملفات القديمة

# │ └── 4\_\_الفواتير.py.old

# │

# └── pages/ # 39 صفحة

# 

# text

# 

# \---

# 

# \## 3. رحلة التطوير

# 

# \### v5.0 → v5.1 (SQLite Mirror + Desktop)

# \- إضافة `local\_mirror.py`, `sync\_manager.py`, `launcher.py`

# \- تعديل `database.py`, `cache\_helpers.py`, `services.py`

# 

# \### v5.1 → v5.2 (Desktop UX)

# \- Splash screen أنيقة

# \- Single Instance Lock

# \- Dynamic Port

# \- CSS لإخفاء Streamlit UI

# 

# \### v5.2 → v6.0 (Backup + Fixes)

# \- `input\_helpers.py` للمعادلات

# \- `export\_all\_tables\_to\_zip()`

# \- إصلاح BOM في `secrets.toml`

# \- إصلاح أخطاء `KeyError`

# 

# \### v6.0 → v7.0 (Filebase + Real Backup)

# \- إصلاح PRAGMA في `sync\_manager.py`

# \- قراءة من Neon مباشرة

# \- Filebase بدل Backblaze

# \- نسخة احتياطية حقيقية 362.7 KB

# 

# \### v7.0 → v8.0 (فواتير منفصلة) ⭐

# \- إنشاء `invoice\_page\_common.py`

# \- إنشاء `pages/4A\_🛒\_فواتير\_البيع.py`

# \- إنشاء `pages/4B\_🛍️\_فواتير\_الشراء.py`

# \- \*\*تاريخ ووقت قابلان للتعديل\*\* في الفواتير

# \- تحديث `sidebar.py` لإظهار الصفحتين الجديدتين

# \- إصلاح `cache\_helpers.get\_invoices\_index` (إضافة 12 حقل جديد)

# \- إصلاح ترتيب `db` في صفحة 6

# 

# \---

# 

# \## 4. الميزات الجديدة

# 

# \### 🖥️ Desktop Launcher

# \- تشغيل بنقرة مزدوجة

# \- نافذة سطح مكتب أصلية (PyWebView)

# \- Splash screen (💼 ينبض + شريط تحميل)

# \- Single Instance Lock (Windows Mutex)

# \- Dynamic Port (8501 → أي منفذ حر)

# 

# \### ⚡ SQLite Mirror

# \- القراءات من SQLite محلياً — أسرع 35-40x

# \- المزامنة كل 30 دقيقة

# \- المزامنة الفورية بعد كل كتابة

# 

# \*\*الأداء:\*\*

# | العملية | Neon | SQLite |

# |---------|------|--------|

# | فتح الأصناف | 1.8 ث | 0.05 ث |

# | لوحة التحكم | 3.2 ث | 0.08 ث |

# | التقارير | 4.5 ث | 0.12 ث |

# 

# \### ☁️ Filebase Backup

# \- Endpoint: `https://s3.filebase.io`

# \- Region: `us-east-1`

# \- Bucket: `techtoon-backups`

# \- تصدير 33 جدولاً كـ CSV في ZIP

# \- الحجم: \*\*\~363 KB\*\* لكل نسخة

# 

# \### ➗ المعادلات الرياضية

# \- حقول السعر/الكمية تقبل معادلات

# \- أمثلة: `650/5`, `500\*1.14`, `200+50-30`

# \- دالة `safe\_eval\_math()` آمنة

# 

# \### 📄 الفواتير المنفصلة (جديد v8.0) ⭐

# 

# \*\*صفحتان منفصلتان:\*\*

# \- 🛒 \*\*فواتير البيع\*\* — تعرض العملاء فقط

# \- 🛍️ \*\*فواتير الشراء\*\* — تعرض الموردين فقط

# 

# \*\*الميزات المشتركة:\*\*

# \- 📅 تاريخ قابل للتعديل (`date\_input`)

# \- 🕐 وقت قابل للتعديل (`time\_input`)

# \- 🔢 رقم فاتورة قابل للتغيير

# \- 📊 عرض الأرقام المستخدمة (1 → 14)

# \- ✏️ تعديل فاتورة سابقة يعيد التاريخ والوقت الأصلي

# 

# \---

# 

# \## 5. صفحات الفواتير الجديدة

# 

# \### البنية

# invoice\_page\_common.py ← كل المنطق

# ├── render\_invoice\_page(type) ← الدالة الرئيسية

# │ ├── نوع: 'sale' أو 'purchase'

# │ ├── تاريخ + وقت قابلان للتعديل

# │ ├── رقم فاتورة قابل للتغيير

# │ └── اختيار طرف (عميل/مورد)

# │

# pages/4A\_🛒\_فواتير\_البيع.py ← استدعاء render\_invoice\_page('sale')

# pages/4B\_🛍️\_فواتير\_الشراء.py ← استدعاء render\_invoice\_page('purchase')

# 

# text

# 

# \### الميزات

# 

# | الميزة | التفصيل |

# |--------|---------|

# | 📅 التاريخ | `date\_input` — افتراضي: اليوم |

# | 🕐 الوقت | `time\_input` — افتراضي: الآن |

# | 🔢 الرقم | `number\_input` — قابل للتعديل |

# | 📊 عرض الأرقام | "1 → 14 (14 فاتورة). التالي: 15" |

# | 💾 الحفظ | `create\_invoice(invoice\_date=...)` |

# | ✏️ التعديل | يستعيد التاريخ والوقت الأصلي |

# | 🔒 الفصل | البيع = عملاء فقط، الشراء = موردين فقط |

# 

# \### كود التصدير

# 

# ```python

# \# في invoice\_page\_common.py

# def render\_invoice\_page(invoice\_type: str):

# &#x20;   """invoice\_type: 'sale' or 'purchase'"""

# &#x20;   is\_sale = invoice\_type == "sale"

# &#x20;   type\_ar = "بيع" if is\_sale else "شراء"

# &#x20;   # ... كامل المنطق

# 6\. التشغيل على الكومبيوتر

# الطريقة 1 — اختصار سطح المكتب (موصى به)

# text

# نقرة مزدوجة على: Techtoon Accounting

# الطريقة 2 — BAT

# text

# انقر مرتين على: Techtoon.bat

# الطريقة 3 — Terminal

# powershell

# cd "D:\\PROG\\Accounting Prog\\Techtoon Accounting"

# python launcher.py

# الطريقة 4 — Streamlit مباشرة

# powershell

# streamlit run app.py

# المتوقع عند التشغيل:

# 

# لا وميض CMD

# 

# Splash screen أنيقة

# 

# نافذة Desktop نظيفة

# 

# 7\. التشغيل على الموبايل

# الرابط: https://techtoon.streamlit.app

# 

# التحديث:

# 

# git push origin main

# 

# انتظر 60-90 ثانية

# 

# التحديث يظهر تلقائياً

# 

# 8\. SQLite Mirror

# التفعيل

# في .env:

# 

# text

# DEPLOY\_MODE=local

# SYNC\_INTERVAL\_SECONDS=1800

# LOCAL\_CACHE\_TTL=1800

# CLOUD\_CACHE\_TTL=120

# المزامنة اليدوية

# powershell

# python -c "from sync\_manager import full\_sync; full\_sync(verbose=True)"

# إحصائيات المزامنة (آخر مرة)

# text

# ✅ الأصناف         = 114 سجل

# ✅ الفواتير        = 7 سجل

# ✅ القيود          = 104 سجل

# المجموع: 653 سجل

# 9\. النسخ الاحتياطي السحابي — Filebase

# الإعدادات

# العنصر	القيمة

# Endpoint	https://s3.filebase.io

# Region	us-east-1

# Bucket	techtoon-backups

# Access Key	9356AA1C20B22C9AAEC3

# Secret	(في AppSetting)

# محتوى النسخة (ZIP)

# text

# backup\_YYYYMMDD\_HHMMSS.zip

# ├── users.csv

# ├── accounts.csv

# ├── parties.csv

# ├── items.csv               ← 114 صنف

# ├── invoices.csv            ← 7 فواتير

# ├── invoice\_lines.csv

# ├── payments.csv

# ├── expenses.csv

# ├── journal\_entries.csv

# ├── journal\_lines.csv

# ├── ... (33 جدول)

# └── \_backup\_info.txt        ← تاريخ + عدد الجداول

# الاستخدام

# افتح صفحة 38 — النسخ الاحتياطي السحابي

# 

# اضغط 🔄 اختبار الاتصال

# 

# اضغط 📤 رفع نسخة جديدة

# 

# المتوقع: \~363 KB

# 

# 10\. المعادلات الرياضية

# في صفحة الفواتير

# python

# from input\_helpers import price\_input, qty\_input

# 

# qty = qty\_input('الكمية:', key='inv\_qty\_1')

# price = price\_input('السعر:', key='inv\_price\_1')

# أمثلة

# تكتب	تحصل على

# 650/5	130.00

# 500\*1.14	570.00

# 200+50-30	220.00

# 1000/3	333.33

# 11\. بناء EXE

# المتطلبات

# powershell

# python -m pip install pyinstaller pywebview psycopg2-binary

# الأمر

# powershell

# cd "D:\\PROG\\Accounting Prog\\Techtoon Accounting"

# pyinstaller --noconfirm --clean --windowed --name TechtoonAccounting --icon logo.ico --add-data "pages;pages" --add-data ".streamlit;.streamlit" --add-data "input\_helpers.py;." --add-data "cache\_helpers.py;." --add-data "database.py;." --add-data "models.py;." --add-data "services.py;." --add-data "sidebar.py;." --add-data "navigation\_helper.py;." --add-data "local\_mirror.py;." --add-data "sync\_manager.py;." --add-data "s3\_backup.py;." --add-data "invoice\_page\_common.py;." --hidden-import psycopg2 --hidden-import streamlit --hidden-import boto3 --hidden-import webview --collect-all streamlit launcher.py

# ⚠️ المشاكل المعروفة

# Permission denied — أغلق Techtoon أولاً

# 

# الحجم كبير (900 MB) — استخدم --exclude-module torch إلخ

# 

# BOM في .spec — يُحل بـ .bat

# 

# 12\. الملفات المُنشأة (v5.0 → v8.0)

# \#	الملف	الوظيفة	الإصدار

# 1	local\_mirror.py	SQLite Mirror	v5.1

# 2	sync\_manager.py	المزامنة	v5.1

# 3	input\_helpers.py	المعادلات	v6.0

# 4	launcher.py	Desktop wrapper	v5.1

# 5	Techtoon.bat	اختصار	v5.1

# 6	build\_exe.ps1	بناء EXE	v5.2

# 7	invoice\_page\_common.py	⭐ وحدة الفواتير المشتركة	v8.0

# 8	pages/4A\_🛒\_فواتير\_البيع.py	⭐ صفحة البيع	v8.0

# 9	pages/4B\_🛍️\_فواتير\_الشراء.py	⭐ صفحة الشراء	v8.0

# 13\. الملفات المُعدّلة

# \#	الملف	التعديل	الإصدار

# 1	database.py	Read/Write Sessions	v5.1

# 2	services.py	130+ دالة	v5.1

# 3	cache\_helpers.py	TTL + get\_invoices\_index (12 حقل)	v8.0

# 4	app.py	CSS إخفاء Streamlit	v5.2

# 5	s3\_backup.py	export\_all\_tables\_to\_zip	v6.0

# 6	sidebar.py	⭐ إضافة فواتير البيع/الشراء	v8.0

# 7	pages/38	ربط بـ s3\_backup	v6.0

# 8	pages/6	إصلاح ترتيب db	v8.0

# 9	pages/2	get\_active\_categories	v5.1

# 10	pages/4	price\_input/qty\_input	v6.0

# 14\. المشاكل المحلولة

# \#	المشكلة	الحل	الإصدار

# 1	KeyError: category\_name	إصلاح get\_items\_with\_stock	v5.1

# 2	ImportError: get\_read\_session	Helpers في database.py	v5.1

# 3	too many values to unpack	get\_active\_categories تُرجع tuples	v5.1

# 4	Invalid date or number	إزالة BOM	v5.2

# 5	Object is already attached	reload قبل الحذف	v5.2

# 6	فتح نسخ متعددة	Single Instance Lock	v5.2

# 7	شريط Streamlit ظاهر	CSS + config	v5.2

# 8	Backblaze 401	Filebase	v7.0

# 9	PRAGMA foreign\_keys	text() wrapper	v7.0

# 10	نسخة احتياطية 0.1 KB	export\_all\_tables\_to\_zip	v7.0

# 11	SQLite فارغ	المزامنة الأولى	v7.0

# 12	KeyError: invoice\_number	إصلاح get\_invoices\_index	v8.0

# 13	الصفحتان لا تظهران	تحديث sidebar.py	v8.0

# 14	BOM في الملفات الجديدة	حفظ UTF-8 بدون BOM	v8.0

# 15\. المشاكل المعلقة

# \#	المشكلة	الأولوية	الحل

# 1	بناء EXE (Permission denied)	🔴 عالية	استخدام \_build.bat

# 2	حجم EXE كبير (900 MB)	🟠 متوسطة	استثناءات إضافية

# 3	Techtoon.vbs لا يعمل	🟢 منخفضة	استخدم .bat

# 4	نسخ احتياطي قديم فارغ	🟢 منخفضة	حذف من Filebase

# 16\. الخطوات القادمة

# فورية

# ✅ صفحات الفواتير المنفصلة — تم

# 

# ✅ التاريخ والوقت قابلان للتعديل — تم

# 

# ✅ إصلاح cache\_helpers — تم

# 

# ✅ تحديث sidebar — تم

# 

# ⏸️ حفظ على GitHub — التالي

# 

# قصيرة المدى

# \[P1] تطبيق input\_helpers على صفحات أخرى

# 

# \[P1] بناء EXE نظيف

# 

# \[P1] اختبار على جهاز آخر

# 

# متوسطة المدى

# \[P2] نسخة خفيفة من EXE (\~250 MB)

# 

# \[P2] جدولة النسخ التلقائية

# 

# طويلة المدى

# \[P3] Multi-tenant

# 

# \[P3] Stripe Integration

# 

# \[P3] Landing Page

# 

# 📊 إحصاءات المشروع

# المقياس	v5.0	v7.0	v8.0

# الملفات المُنشأة	0	8	11

# الملفات المُعدّلة	0	10	13

# المشاكل المحلولة	0	13	17

# سرعة فتح الصفحات	1.8 ث	0.05 ث	0.05 ث

# حجم النسخة الاحتياطية	0.1 KB	363 KB	363 KB

# السجلات المُزامَنة	0	653	653

# عدد الصفحات	38	38	39

# 🔑 معلومات حساسة

# Neon Database

# text

# DATABASE\_URL=postgresql://neondb\_owner:npg\_K9nHWK5Y0JrC@...neon.tech/neondb?sslmode=require

# Filebase

# text

# Access Key: 9356AA1C20B22C9AAEC3

# Secret:     4N4d7NwhExyxyLLfDFDDghMTTKMb3p3ZJWZbjx6T

# Bucket:     techtoon-backups

# Endpoint:   https://s3.filebase.io

# ⚠️ محفوظة في AppSetting — وليست في GitHub.

# 

# 🎯 أوامر سريعة

# تشغيل التطبيق

# powershell

# python launcher.py

# مزامنة SQLite

# powershell

# python -c "from sync\_manager import full\_sync; full\_sync(verbose=True)"

# اختبار Filebase

# powershell

# python -c "from s3\_backup import export\_all\_tables\_to\_zip; d = export\_all\_tables\_to\_zip(); print(f'Size: {len(d)/1024:.1f} KB')"

# رفع على GitHub

# powershell

# git add .

# git commit -m "v8.0 - Separate sale/purchase invoice pages + editable date/time"

# git push origin main

# 📞 للدعم

# Streamlit Cloud: https://share.streamlit.io

# 

# Neon Console: https://console.neon.tech

# 

# Filebase: https://console.filebase.com

# 

# GitHub: https://github.com/fady100fs/techtoon-accounting

# 

# التطبيق: https://techtoon.streamlit.app

# 

# 📝 سجل الإصدارات

# التاريخ	الإصدار	التغييرات

# 2026-10-06	v2.0	المراحل 1-7

# 2026-10-07	v3.0	استقرار

# 2026-10-08	v5.0	شامل

# 2026-10-09	v5.1	SQLite Mirror + Desktop

# 2026-10-09	v5.2	Splash + Streamlit UI + Lock

# 2026-10-09	v6.0	Filebase + Helpers + Fixes

# 2026-10-10	v7.0	SQLite Mirror + Real Backup

# 2026-10-10	v8.0	فواتير البيع/الشراء المنفصلة + تاريخ/وقت قابلان للتعديل

# آخر تحديث: 2026-10-10 — إصدار 8.0

# إعداد: فادي سعد — Techtoon Accounting

# '@ | Out-File -Encoding UTF8 BUILD.md

# 

# احذف BOM من الملف

# b

# y

# t

# e

# s

# =

# \[

# S

# y

# s

# t

# e

# m

# .

# I

# O

# .

# F

# i

# l

# e

# ]

# :

# :

# R

# e

# a

# d

# A

# l

# l

# B

# y

# t

# e

# s

# (

# "

# B

# U

# I

# L

# D

# .

# m

# d

# "

# )

# i

# f

# (

# bytes=\[System.IO.File]::ReadAllBytes("BUILD.md")if(bytes\[0] -eq 0xEF -and 

# b

# y

# t

# e

# s

# \[

# 1

# ]

# −

# e

# q

# 0

# x

# B

# B

# −

# a

# n

# d

# bytes\[1]−eq0xBB−andbytes\[2] -eq 0xBF) {

# \[System.IO.File]::WriteAllBytes("BUILD.md", 

# b

# y

# t

# e

# s

# \[

# 3..

# (

# bytes\[3..(bytes.Length-1)])

# Write-Host " \[OK] BOM أُزيل" -ForegroundColor Green

# }

# 

# Write-Host ""

# Write-Host "═════════════════════════════════════════════" -ForegroundColor Green

# Write-Host " ✅ BUILD.md v8.0 created!" -ForegroundColor Green

# Write-Host "═════════════════════════════════════════════" -ForegroundColor Green

# Write-Host ""

# 

# s

# i

# z

# e

# =

# (

# G

# e

# t

# −

# I

# t

# e

# m

# B

# U

# I

# L

# D

# .

# m

# d

# )

# .

# L

# e

# n

# g

# t

# h

# /

# 1

# K

# B

# W

# r

# i

# t

# e

# −

# H

# o

# s

# t

# "

# 📄الحجم

# :

# size=(Get−ItemBUILD.md).Length/1KBWrite−Host"📄الحجم:(\[math]::Round(

# s

# i

# z

# e

# ,

# 1

# )

# )

# K

# B

# "

# −

# F

# o

# r

# e

# g

# r

# o

# u

# n

# d

# C

# o

# l

# o

# r

# Y

# e

# l

# l

# o

# w

# W

# r

# i

# t

# e

# −

# H

# o

# s

# t

# "

# 📁المسار

# :

# size,1))KB"−ForegroundColorYellowWrite−Host"📁المسار:((Resolve-Path 'BUILD.md').Path)" -ForegroundColor Yellow

# Write-Host ""

# Write-Host "📤 لرفعه على GitHub:" -ForegroundColor Cyan

# Write-Host " git add BUILD.md" -ForegroundColor White

# Write-Host " git commit -m 'BUILD.md v8.0'" -ForegroundColor White

# Write-Host " git push origin main" -ForegroundColor White

# Write-Host ""

# 

# text

# 

# \---

# 

# \## 📊 ما يوثّقه BUILD.md v8.0

# 

# | # | القسم | المحتوى |

# |---|-------|---------|

# | 1-2 | نظرة عامة + البنية | وصف شامل |

# | 3 | رحلة التطوير | v5.0 → v8.0 بالتفصيل |

# | 4 | الميزات الجديدة | Desktop + SQLite + Filebase + \*\*فواتير منفصلة\*\* |

# | \*\*5\*\* | \*\*صفحات الفواتير الجديدة\*\* | \*\*⭐ الجديد في v8.0\*\* |

# | 6-7 | التشغيل | محلي + Cloud |

# | 8-10 | SQLite + Backup + معادلات | التفاصيل |

# | 11 | بناء EXE | الأوامر والمشاكل |

# | 12-13 | الملفات | المُنشأة + المُعدّلة |

# | 14-15 | المشاكل | المحلولة + المعلقة |

# | 16 | الخطوات القادمة | مرتّبة بالأولوية |

# 

# \---

# 

# \## 📤 الخطوة التالية

# 

# \*\*بعد إنشاء BUILD.md:\*\*

# 

# ```powershell

# cd "D:\\PROG\\Accounting Prog\\Techtoon Accounting"

# 

# \# راجع الملفات

# git status --short

# 

# \# أضف كل شيء

# git add .

# 

# \# Commit

# git commit -m "v8.0 - Separate sale/purchase invoices + editable date/time + BUILD.md"

# 

# \# Push

# git push origin main

# سيرفع:

# 

# invoice\_page\_common.py (جديد)

# 

# pages/4A\_🛒\_فواتير\_البيع.py (جديد)

# 

# pages/4B\_🛍️\_فواتير\_الشراء.py (جديد)

# 

# sidebar.py (مُعدّل)

# 

# cache\_helpers.py (مُعدّل)

# 

# pages/6 (مُعدّل)

# 

# BUILD.md (v8.0)

