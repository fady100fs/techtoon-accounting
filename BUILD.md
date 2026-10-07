# 📘 BUILD.md — دليل بناء برنامج Techtoon Accounting

> **آخر تحديث:** 2026-10-06
> **الإصدار:** 2.0
> **الغرض:** دليل شامل للعودة لأي مرحلة بدون إعادة الخطوات.

---

## 🎯 نظرة عامة

| العنصر | القيمة |
|--------|--------|
| **البرنامج** | نظام محاسبة متكامل (Techtoon Accounting) |
| **التقنية** | Streamlit + SQLAlchemy + Neon PostgreSQL |
| **التشغيل** | Windows محلياً + Streamlit Cloud سحابياً |
| **رابط الموبايل** | https://techtoon.streamlit.app |
| **مستودع GitHub** | fady100fs/techtoon-accounting |
| **لغة الواجهة** | عربية RTL |
| **عدد الصفحات** | 38 صفحة |
| **عدد الجداول** | 36 جدولاً |

---

## 📂 هيكل المشروع

```
Techtoon Accounting/
│
├── app.py                              # نقطة البداية
├── database.py                         # Neon PostgreSQL
├── models.py                           # كل الـ Models (~800 سطر)
├── services.py                         # منطق الأعمال (~2300 سطر)
├── sidebar.py                          # القائمة + الصلاحيات
├── session_auth.py                     # الجلسات + Rate Limiting
├── auth.py                             # تشفير كلمات المرور
├── auth_required.py                    # حماية الصفحات
├── form_manager.py                     # تفريغ تلقائي للنماذج
├── period_guard.py                     # حارس الفترات المحاسبية
├── cache_helpers.py                    # طبقة Caching
├── settings_manager.py                 # الإعدادات المركزية
├── s3_backup.py                        # النسخ السحابي
├── pdf_reports.py                      # محرّك PDF بالعربية
├── code_search.py                      # CodeSearch + FormState
├── backup_manager.py                   # النسخ المحلي
├── audit_log.py                        # سجل العمليات
├── alerts.py / reminders.py            # التنبيهات
├── shortcuts.py / keyboard_nav.py      # اختصارات
├── export_excel.py / export_pdf.py
├── launcher.py                         # تشغيل مستقل
│
├── update.ps1                          # سكربت الرفع على GitHub
├── packages.txt                        # مكتبات Linux
├── requirements.txt                    # مكتبات Python
├── BUILD.md                            # ← هذا الملف
│
├── fonts/                              # خطوط PDF العربية
│   ├── Amiri-Regular.ttf (اختياري)
│   └── README.md
│
└── pages/                              # 38 صفحة
    ├── 1_🏠_لوحة_التحكم.py
    ├── 2_📦_الأصناف.py
    ├── 3_👥_عملاء وموردين.py
    ├── 4__الفواتير.py                  ⭐
    ├── 5_📊_التقارير.py
    ├── 6_📋_فهرس_الفواتير.py
    ├── 7_💱_العملات.py                 ⭐
    ├── 8_💰_المدفوعات.py               ⭐
    ├── 9__شجرة_الحسابات.py
    ├── 10_📋_كشف_حساب.py
    ├── 11__النسخ_الاحتياطي.py
    ├── 12_️_الميزانية_العمومية.py
    ├── 13__التنبيهات.py
    ├── 14_👤_تسجيل_الدخول.py
    ├── 15_📈_تقارير_متقدمة.py
    ├── 16__مركز_التذكيرات.py
    ├── 18__تقرير_الارباح_الدقيق.py
    ├── 19_🏦_الخزائن.py                ⭐
    ├── 20_🗂️_التصنيفات.py              ⭐
    ├── 21_👤_إدارة_المستخدمين.py
    ├── 22_💸_المصروفات.py              ⭐ (حركات الخزينة)
    ├── 23_📦_إدارة_المخزون.py          ⭐
    ├── 24__الأصول_الثابتة.py           ⭐
    ├── 25_📈_تحليل_الربحية.py
    ├── 26_💼_إدارة_القروض.py           ⭐
    ├── 27__الموظفين_والرواتب.py        ⭐
    ├── 28_📊_التقارير_المالية.py
    ├── 29_📅_الإغلاق_المحاسبي.py       ⭐
    ├── 30_🏢_مراكز_التكلفة.py          ⭐
    ├── 31_🔍_فحص_السلامة.py
    ├── 32_📝_قيود_اليومية.py           ⭐
    ├── 33_📷_قارئ_الباركود.py
    ├── 34_🔄_الفواتير_المتكررة.py      ⏸️ معطّلة مؤقتاً
    ├── 35_🔍_البحث_الموحد.py
    ├── 36_⚙️_الإعدادات.py
    ├── 37_📄_تقارير_PDF.py
    └── 38_☁️_النسخ_السحابي.py

⭐ = صفحات مُحدَّثة بـ clear_form
```

---

## 🗓️ سجل المراحل المُنجَزة

### 🔹 المرحلة 0: المسلسل الرقمي الموحّد

**الهدف:** إضافة مسلسل مرئي لكل حركة.

| النوع | البادئة | مثال | الحالة |
|------|---------|------|--------|
| حركة خزينة | `CM` | `CM-000123` | ✅ |
| دفعة | `PAY` | `PAY-000123` | ✅ |
| تحويل خزائن | `TRF` | `TRF-000012` | ✅ |
| فاتورة | `INV` | `INV-000001` | ✅ |
| قرض | `LOAN` | `LOAN-000001` | ✅ |
| قيد يدوي | `JE` | `JE-000045` | ✅ |
| مصروف | `EXP` | `EXP-000012` | ✅ |

**الملفات المُعدّلة:**
- `services.py`: `movement_serial()` + `parse_movement_serial()`
- `pages/22`, `pages/8`, `pages/19`

---

### 🔹 المرحلة 1: تحسينات الأداء

**الهدف:** تسريع البرنامج 3-10x على Neon.

**التغييرات:**
- ✅ تفعيل `cache_helpers.py` في 5 صفحات
- ✅ إصلاح N+1 Queries (Dashboard, Reports, Inventory, Invoices Index, Payments)
- ✅ Pagination في الأصناف والفواتير

**الملفات المُعدّلة:**
- `cache_helpers.py` (كامل)
- `pages/1, 2, 5, 6, 8, 23`

---

### 🔹 المرحلة 2: الأمان المحاسبي

**الهدف:** منع التلاعب + حماية.

**التغييرات:**

#### 2.1 حارس الفترات (`period_guard.py`)
- منع التعديل/الحذف في فترات مغلقة
- دمج في `services.py` + `pages/4, 8, 22`

#### 2.2 فحص توازن القيد (`services.py`)
- `validate_journal_entry()` — يرفض أي قيد debit ≠ credit
- `check_accounting_integrity()` — فحص شامل للنظام

#### 2.3 Rate Limiting (`session_auth.py`)
- حظر IP بعد 5 محاولات دخول فاشلة
- مدة الحظر: 15 دقيقة
- ملف `.login_attempts.json`

#### 2.4 صفحة فحص السلامة (`pages/31_🔍_فحص_السلامة.py`)
- تقرير شامل: قيود غير متوازنة، أسطر يتيمة، أرقام مكررة

**الملفات المُعدّلة:**
- `period_guard.py` (جديد)
- `session_auth.py` (كامل)
- `app.py` (كامل — مع Rate Limiting)
- `sidebar.py`
- `services.py`
- `pages/4, 8, 22, 31`

---

### 🔹 المرحلة 3: الميزات الجديدة

#### 3.1 قيود اليومية اليدوية (`pages/32`)
- إنشاء قيد يدوي (متعدد الأسطر)
- ترحيل عكسي
- بحث + عرض
- مسلسل `JE-xxxxxx`

#### 3.2 Barcode Scanner (`pages/33`)
- مسح من كاميرا الموبايل (pyzbar + Pillow)
- إدخال يدوي
- سجل المسح
- إضافة للسلة

#### 3.3 الفواتير المتكررة (`pages/34`)
- جدولان جديدان: `recurring_invoice_templates`, `recurring_invoice_lines`
- 11 دالة في `services.py`
- ⏸️ **معطّلة مؤقتاً** في `sidebar.py` (سبب: تعارض مع `4__الفواتير.py`)

#### 3.4 البحث الموحد (`pages/35`)
- بحث في 6 أقسام (عملاء، أصناف، فواتير، مدفوعات، مصروفات، قيود)
- زر سريع في `app.py` + `sidebar.py`

**الملفات المُعدّلة:**
- `models.py` (قسم 23)
- `services.py` (قسم 28)
- `requirements.txt` (pyzbar, opencv, Pillow)
- `packages.txt` (libzbar0, libgl1)
- `pages/32, 33, 34, 35`

---

### 🔹 المرحلة 4: البنية التحتية

#### 4.1 الإعدادات المركزية (`pages/36`)
- جدول `app_settings`
- 6 تبويبات: عام، مالية، فواتير، هوية، تنبيهات، أدوات
- تصدير/استيراد JSON
- `settings_manager.py`

#### 4.2 تقارير PDF احترافية (`pages/37`)
- محرّك `pdf_reports.py` بالعربية
- 4 قوالب: فاتورة، كشف حساب، ميزانية، أرباح
- يستخدم خط عربي من `fonts/`
- تكامل مع الإعدادات

#### 4.3 النسخ الاحتياطي السحابي (`pages/38`)
- يدعم: AWS S3, Backblaze B2, Supabase, Wasabi
- `s3_backup.py`
- رفع ZIP كامل (كل الجداول CSV)
- قائمة/تنزيل/حذف/استعادة
- تنظيف تلقائي

**الملفات المُعدّلة:**
- `settings_manager.py` (جديد)
- `s3_backup.py` (جديد)
- `pdf_reports.py` (جديد)
- `requirements.txt` (reportlab, arabic-reshaper, python-bidi, boto3)
- `pages/36, 37, 38`

---

### 🔹 المرحلة 5: تفريغ النماذج (clear_form)

**الهدف:** تفريغ تلقائي لكل النماذج بعد الحفظ/التعديل/الحذف.

**المبدأ العام:**
```python
# 1. في بداية الصفحة:
from form_manager import clear_form, show_clear_hint
PFX = "xx_"   # بادئة فريدة

# 2. بعد العنوان:
show_clear_hint()

# 3. كل widget:
st.text_input("...", key=f"{PFX}name")

# 4. بعد كل عملية ناجحة:
clear_form(PFX)
st.rerun()
```

**بادئات الصفحات:**

| # | الصفحة | البادئة | الحالة |
|---|--------|---------|--------|
| 1 | `4__الفواتير.py` | `inv_` | ✅ |
| 2 | `8_💰_المدفوعات.py` | `pay_` | ✅ |
| 3 | `22_💸_المصروفات.py` | `cm_` | ✅ |
| 4 | `2_📦_الأصناف.py` | `itm_` | ✅ |
| 5 | `3_👥_عملاء وموردين.py` | `pty_` | ✅ |
| 6 | `19_🏦_الخزائن.py` | `box_` | ✅ |
| 7 | `20_🗂️_التصنيفات.py` | `cat_` | ✅ |
| 8 | `7_💱_العملات.py` | `cur_` | ✅ |
| 9 | `32_📝_قيود_اليومية.py` | `je_` | ✅ |
| 10 | `34_🔄_الفواتير_المتكررة.py` | `rec_` | ✅ |
| 11 | `26_💼_إدارة_القروض.py` | `loan_` | ✅ |
| 12 | `27__الموظفين_والرواتب.py` | `emp_` | ✅ |
| 13 | `23_📦_إدارة_المخزون.py` | `wh_` | ✅ |
| 14 | `24__الأصول_الثابتة.py` | `fa_` | ✅ |
| 15 | `30_🏢_مراكز_التكلفة.py` | `cc_` | ✅ |
| 16 | `29_📅_الإغلاق_المحاسبي.py` | `close_` | ✅ |

---

### 🔹 المرحلة 6: شبكة مربعات ملونة

**الهدف:** تحويل اختيار الحساب في `pages/22` من expanders + radios إلى شبكة مربعات ملونة.

**الميزات:**
- ألوان ديناميكية لكل مجموعة
- المربع المختار بإطار أبيض
- 3 مربعات في الصف
- متجاوبة للموبايل

---

### 🔹 المرحلة 7: تحسينات الأداء المتقدمة

**التغييرات:**
- Indexes على Neon PostgreSQL (40+ index)
- `cache_helpers.py` محسّن بـ TTL محدّد
- Pool أكبر (20 → 40)
- Pagination مخفّض (50 → 25)

**⏳ قيد التنفيذ:** تحتاج تنفيذ SQL في Neon Console.

---

## 🚧 المراحل القادمة

### 🔸 المرحلة 8: تحسينات UX
- [ ] Dashboard تفاعلي 2.0 (drill-down)
- [ ] Loading indicators ذكية
- [ ] Toast notifications موحّد
- [ ] تحسين سرعة Neon (cold start)

### 🔸 المرحلة 9: ميزات محاسبية متقدمة
- [ ] FIFO / Weighted Average لتكلفة المخزون
- [ ] القيود العكسية التلقائية
- [ ] إغلاق سنوي حقيقي
- [ ] Approval Workflow

### 🔸 المرحلة 10: ميزات متنوعة
- [ ] تعدد الفروع / الشركات
- [ ] نظام المرفقات
- [ ] إشعارات WhatsApp تلقائية
- [ ] Barcode Scanner محسّن

---

## 🚀 سير العمل الموحّد

### للرفع على GitHub:

```powershell
cd "D:\PROG\Accounting Prog\Techtoon Accounting"
powershell -ExecutionPolicy Bypass -File "update.ps1"
```

### بعد الرفع:
- Streamlit Cloud يعيد النشر تلقائياً (~30-60 ثانية)
- راقب من: https://share.streamlit.io

---

## 🧪 قائمة اختبارات شاملة

### ✅ ميزة المسلسل
- [ ] افتح **حركات الخزينة** → عمود "المسلسل" بصيغة `CM-000123`
- [ ] افتح **المدفوعات** → عمود "المسلسل" بصيغة `PAY-000123`
- [ ] افتح **الخزائن** → عمود "المسلسل" بصيغة `TRF-000012`

### ✅ المرحلة 1 (الأداء)
- [ ] لوحة التحكم < 2 ثانية
- [ ] فهرس الفواتير يعمل مع Pagination
- [ ] الأصناف يعمل مع Pagination

### ✅ المرحلة 2 (الأمان)
- [ ] فحص السلامة → تقرير نظيف
- [ ] جرّب 5 محاولات دخول فاشلة → حظر 15 دقيقة
- [ ] افتح فترة مغلقة → تُرفض الحركة

### ✅ المرحلة 3 (الميزات الجديدة)
- [ ] قيد يدوي + ترحيل عكسي
- [ ] Barcode Scanner من الكاميرا
- [ ] البحث الموحد يعمل

### ✅ المرحلة 4 (البنية التحتية)
- [ ] الإعدادات: عدّل اسم الشركة + ارفع شعار
- [ ] تقارير PDF: عربي صحيح
- [ ] S3: اختبار اتصال + رفع نسخة

### ✅ المرحلة 5 (تفريغ النماذج)
- [ ] كل صفحة: احفظ → الحقول تُفرَّغ

### ✅ المرحلة 6 (شبكة المربعات)
- [ ] حركات الخزينة → اختر حساب → المربع يظهر بإطار أبيض

---

## 🔧 حلول سريعة للمشاكل الشائعة

### 1. `TomlDecodeError: Found invalid character in key name: '['`
```cmd
del .streamlit\config.toml
```

### 2. `NameError: name 'timedelta' is not defined` في `audit_log.py`
أضف في أعلى الملف:
```python
from datetime import datetime, timedelta
```

### 3. `ProgrammingError: column "invoices.date" must appear in GROUP BY`
استخدم `func.to_char` بدل `func.strftime` (PostgreSQL).

### 4. `StreamlitDuplicateElementKey`
استخدم `key_suffix` فريد لكل استدعاء.

### 5. `ModuleNotFoundError: No module named 'X'`
- تأكد من الملف في جذر المشروع
- `sys.path.append(...)` في أعلى الملف
- أعد تشغيل Streamlit

### 6. PDF يظهر مربعات بدل عربي
- حمّل خط عربي في `fonts/`
- أو استخدم `packages.txt` للخطوط

### 7. بوت S3 فشل الاتصال
- تحقق من Endpoint + Bucket + Credentials
- Region = الجزء الأوسط من Endpoint

### 8. Neon بطيء
- نفّذ Indexes (المرحلة 7)
- Cache محدّد
- Pagination أقل

### 9. `Streamlit Cloud: Error installing requirements`
- تحقق من `packages.txt` — لا نصوص عربية، لا `.ttf`
- تحقق من `requirements.txt` — لا تعليقات، لا نصوص عربية

---

## 📊 إحصاءات المشروع

| المقياس | القيمة |
|---------|--------|
| عدد الصفحات | 38 |
| حجم `services.py` | ~2,300 سطر |
| حجم `models.py` | ~800 سطر |
| عدد الجداول في DB | 36 |
| دوال services.py | 130+ |
| مكتبات Python | 17 |
| مكتبات Linux | 2 |

---

## 🔐 الصلاحيات (UserRole)

| الدور | القيمة | الصلاحيات |
|------|-------|-----------|
| مدير | `ADMIN` | كل شيء |
| محاسب | `ACCOUNTANT` | كل شيء ما عدا إدارة المستخدمين |
| بائع | `SALESPERSON` | فواتير + أصناف فقط |
| مشاهد | `VIEWER` | عرض التقارير فقط |

**قاعدة:** التعديل والحذف = للمدير فقط.

---

## 🗄️ الجداول

### الأساسيات
- `currencies`, `accounts`, `users`, `accounting_periods`

### الأطراف
- `parties`, `cash_boxes`, `categories`, `items`, `kit_components`

### الفواتير
- `invoices`, `invoice_lines`, `cost_history`

### القيود
- `journal_entries`, `journal_lines`

### المدفوعات والمصروفات
- `payments`, `cash_transfers`, `expense_categories`, `expenses`

### المخزون
- `warehouses`, `stock_levels`, `warehouse_transfers`, `stock_counts`

### الأصول والقروض
- `fixed_assets`, `depreciation_records`, `loans`, `loan_installments`

### الموظفين
- `employees`, `salary_records`

### محاسبية متقدمة
- `budgets`, `cost_centers`, `cost_allocations`, `cost_center_transactions`

### الفواتير المتكررة ⏸️
- `recurring_invoice_templates`, `recurring_invoice_lines`

### الإعدادات
- `app_settings`

---

## 📌 ملاحظات مهمة

### 1. قاعدة البيانات
- **Neon PostgreSQL** (سحابي مجاني 10 GB)
- الاتصال: `.env` محلياً / `secrets.toml` على السحابة
- `DATABASE_URL` يحوّل تلقائياً إلى `postgresql+psycopg://`

### 2. النشر
- **GitHub** → **Streamlit Cloud** (تلقائي عند push)
- الرابط: https://techtoon.streamlit.app
- الموبايل: نفس الرابط + "إضافة للشاشة الرئيسية"

### 3. الملفات الحساسة (يجب في `.gitignore`)
```
.sessions.json
.login_attempts.json
*.backup_*
*.before_*
fonts/*.ttf
.env
.streamlit/secrets.toml
```

### 4. النسخ الاحتياطي
- **محلي:** مجلد `backups/` (CSV لكل جدول)
- **سحابي:** S3 (Backblaze B2 — 10 GB مجاناً)

### 5. الفواتير المتكررة معطّلة
- الملف موجود: `pages/34_🔄_الفواتير_المتكررة.py`
- معطّلة في `sidebar.py` بـ comment
- لإعادة تفعيلها: أزل التعليق عن السطرين

---

## 🎯 الخطوة التالية

**الوضع الحالي:** المراحل 1-7 مكتملة ✅  
**الأولويات القادمة:**
1. تنفيذ Indexes على Neon (أداء)
2. اختبار شامل لكل الميزات
3. إكمال باقي الصفحات بـ clear_form (9, 21)

---

## 📞 للدعم

- **رابط Streamlit Cloud:** https://share.streamlit.io
- **رابط Neon Console:** https://console.neon.tech
- **رابط GitHub Repo:** https://github.com/fady100fs/techtoon-accounting

---

*آخر تحرير: 2026-10-06 — إصدار 2.0 (المراحل 1-7 مكتملة)*