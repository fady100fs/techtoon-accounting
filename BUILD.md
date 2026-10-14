# 📦 دليل بناء وتوزيع Techtoon Accounting

> **آخر تحديث:** 2026-10-13
> **الإصدار:** v1.0

---

## 📋 المتطلبات الأساسية

| المتطلب | الإصدار | ملاحظات |
|---|---|---|
| Python | 3.11+ | مطلوب |
| Windows | 10/11 64-bit | لبناء EXE |
| PyInstaller | 6.0+ | `pip install pyinstaller` |
| Neon DB | أي حساب | [neon.tech](https://neon.tech) مجاني |
| Git | أي إصدار | للرفع على GitHub |

---

## 🚀 خطوات البناء

### 1) جهّز بيئة العمل

```powershell
cd "D:\PROG\Accounting Prog\Techtoon Accounting"

# ثبّت كل المكتبات
pip install -r requirements.txt

# ثبّت PyInstaller
pip install pyinstaller
```

### 2) تحقق من ملف `.env`

```env
DATABASE_URL=postgresql://user:password@host/db?sslmode=require
SECRET_KEY=your-random-40-char-secret
DEPLOY_MODE=local
```

### 3) اضبط `TechtoonAccounting.spec`

تأكد أن `icon=None` (أو ضع `logo.ico` لو متوفر):

```python
# في TechtoonAccounting.spec
icon=None,  # أو icon=['logo.ico']
```

### 4) اضبط حد الـ recursion (مهم لـ Streamlit)

```python
# في أعلى TechtoonAccounting.spec
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 10)
```

### 5) ابنِ الـ EXE

```powershell
# الطريقة المباشرة
pyinstaller TechtoonAccounting.spec --noconfirm --clean

# أو استخدم سكربت البناء
.\build_exe.bat
```

**النتيجة:** `dist\TechtoonAccounting\` يحتوي على:
```
TechtoonAccounting.exe          ← البرنامج الرئيسي
_internal/                      ← ملفات PyInstaller
```

> ⏳ البناء يستغرق 5-15 دقيقة

---

## 📦 تجهيز حزمة التوزيع

### 1) أنشئ مجلد الحزمة

```powershell
# انسخ الـ EXE + ملفاته
Copy-Item "dist\TechtoonAccounting" "Techtoon_Accounting_v1.0" -Recurse -Force

# انسخ الإعدادات
Copy-Item ".env" "Techtoon_Accounting_v1.0\.env" -Force
Copy-Item ".streamlit" "Techtoon_Accounting_v1.0\.streamlit" -Recurse -Force

# انسخ ملفات المساعدة
Copy-Item "check_requirements.py" "Techtoon_Accounting_v1.0\" -Force
```

### 2) أنشئ `requirements.txt` للعميل

```powershell
@'
streamlit>=1.30
pandas>=2.0
SQLAlchemy>=2.0
psycopg2-binary>=2.9
python-dotenv>=1.0
plotly>=5.18
reportlab>=4.0
xlsxwriter>=3.1
openpyxl>=3.1
bcrypt>=4.1
pywebview>=4.2
WMI>=1.2
'@ | Set-Content "Techtoon_Accounting_v1.0\requirements.txt" -Encoding UTF8
```

### 3) أنشئ `README.txt` للعميل

```powershell
@'
╔════════════════════════════════════════════════╗
║     Techtoon Accounting — دليل التشغيل         ║
╚════════════════════════════════════════════════╝

الخطوات:
  1) ثبّت المكتبات:
     pip install -r requirements.txt

  2) عدّل DATABASE_URL في ملف .env
     (اطلب الرابط من البائع أو أنشئ من neon.tech)

  3) شغّل البرنامج:
     TechtoonAccounting.exe

الفترة التجريبية: 30 يوماً مجاناً
بعد انتهائها: أرسل machine_id للبائع لشراء الرخصة

للوصول من الموبايل (نفس شبكة Wi-Fi):
  شغّل: TechtoonAccounting.exe
  افتح المتصفح على الموبايل: http://IP_الجهاز:8501

الدعم الفني: [رقم البائع]
'@ | Set-Content "Techtoon_Accounting_v1.0\README.txt" -Encoding UTF8
```

### 4) اضغط في ZIP

```powershell
Compress-Archive -Path "Techtoon_Accounting_v1.0\*" `
  -DestinationPath "Techtoon_Accounting_v1.0.zip" -Force
```

---

## 🔑 نظام التراخيص

### هيكل المجلدات

```
Techtoon_Accounting/          ← مجلد المشروع
├── licence/                   ← للبائع فقط
│   ├── generate_license.py   ← مولّد الرخص
│   ├── issued_licenses/      ← أرشيف الرخص
│   └── README_SELLER.md
├── Techtoon_Accounting_v1.0/ ← حزمة العميل
│   ├── TechtoonAccounting.exe
│   ├── .env
│   ├── requirements.txt
│   └── README.txt
└── license_manager.py         ← نظام الترخيص (داخل البرنامج)
```

### توليد رخصة لعميل

```powershell
cd "D:\PROG\Accounting Prog\Techtoon Accounting\licence"

# رخصة دائمة
python generate_license.py --machine-id A1B2C3D4E5F67890 --customer "اسم العميل"

# رخصة سنوية
python generate_license.py --machine-id A1B2C3D4 --customer "الاسم" --type annual --days 365

# عرض كل الرخص
python generate_license.py --list
```

### النتيجة

```
  ✔ تم توليد الرخصة!
    machine_id: A1B2C3D4E5F67890
    نوع الرخصة: lifetime
    مدة الصلاحية: دائمة
    الملف: license.key
```

أرسل `license.key` للعميل → يضعه بجانب `TechtoonAccounting.exe` → ✅ مُفعّل!

---

## 📱 تفعيل الوصول من الموبايل

### الطريقة 1: نفس شبكة Wi-Fi

```powershell
# شغّل البرنامج مع تفعيل الموبايل
python -m streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

- افتح متصفح الموبايل: `http://IP_الجهاز:8501`
- الجهاز والموبايل على نفس Wi-Fi

### الطريقة 2: من أي مكان (Streamlit Cloud)

1. ارفع الكود على GitHub
2. اذهب إلى [share.streamlit.io](https://share.streamlit.io)
3. اربط المستودع
4. أضف `DATABASE_URL` في Secrets
5. احصل على رابط: `https://yourname-techtoon.streamlit.app`
6. افتحه من الموبايل أو أضفه للشاشة الرئيسية

---

## 🔒 أمان الـ SECRET

```python
# في license_manager.py و generate_license.py
SECRET = b"TECHTOON_LICENSE_2026_V1"
```

**قبل التوزيع الأول:**
```python
import secrets
print(secrets.token_bytes(40))
# ضع الناتج في كلا الملفين
```

**لا ترفع `generate_license.py` أو `issued_licenses/` على GitHub:**

```gitignore
# .gitignore
generate_license.py
issued_licenses/
licence/
*.key
```

---

## 🧪 اختبار قبل التوزيع

### 1) اختبر الـ EXE

```powershell
# شغّل على جهازك
dist\TechtoonAccounting\TechtoonAccounting.exe
```

### 2) اختبر الترخيص

```powershell
# احصل على machine_id من شاشة الترخيص
# ولّد رخصة
python licence\generate_license.py --machine-id XXXX --customer "اختبار"

# ضع license.key بجانب EXE
copy license.key dist\TechtoonAccounting\

# أعد التشغيل — يجب أن يظهر "رخصة مدى الحياة"
```

### 3) اختبر على جهاز آخر

- انسخ مجلد `dist\TechtoonAccounting` لجهاز آخر
- شغّل `TechtoonAccounting.exe`
- يجب أن يعمل (مع فترة تجريبية 30 يوماً)

---

## 📊 قائمة الملفات للتوزيع

| الملف | الوصف | للعميل؟ |
|---|---|---|
| `TechtoonAccounting.exe` | البرنامج الرئيسي | ✅ |
| `_internal/` | ملفات PyInstaller | ✅ |
| `.env` | إعدادات DB | ✅ (يُعدّلها العميل) |
| `.streamlit/` | إعدادات Streamlit | ✅ |
| `requirements.txt` | قائمة المكتبات | ✅ |
| `README.txt` | دليل العميل | ✅ |
| `license.key` | رخصة العميل | ✅ (بعد الشراء) |
| `generate_license.py` | مولّد الرخص | ❌ للبائع فقط |
| `issued_licenses/` | أرشيف الرخص | ❌ للبائع فقط |

---

## 🚀 أوامر سريعة (Quick Reference)

```powershell
# بناء EXE
pyinstaller TechtoonAccounting.spec --noconfirm --clean

# تجهيز الحزمة
Copy-Item "dist\TechtoonAccounting" "Techtoon_Accounting_v1.0" -Recurse -Force
Copy-Item ".env" "Techtoon_Accounting_v1.0\" -Force

# ضغط ZIP
Compress-Archive -Path "Techtoon_Accounting_v1.0\*" -DestinationPath "Techtoon_v1.0.zip" -Force

# توليد رخصة
python licence\generate_license.py --machine-id XXXX --customer "الاسم"

# رفع لـ GitHub
git add -A
git commit -m "v1.0: إصدار التوزيع"
git push
```

---

## ✅ قائمة تحقق نهائية قبل التوزيع

```
□ .env يحتوي DATABASE_URL صحيح
□ SECRET في license_manager.py = SECRET في generate_license.py
□ TechtoonAccounting.spec: recursionlimit مضبوط + icon=None
□ EXE بُني بنجاح (dist\TechtoonAccounting\TechtoonAccounting.exe)
□ حزمة ZIP جاهزة (Techtoon_v1.0.zip)
□ generate_license.py في مجلد licence/ (خارج الحزمة)
□ .gitignore يستثنى generate_license.py و issued_licenses/
□ اختبرت EXE على جهازك
□ اختبرت الترخيص (توليد + تفعيل)
□ ارفع الكود على GitHub
□ جهّز رابط تحميل الحزمة للعملاء
```

---

## 🔄 تحديثات مستقبلية

### لإصدار نسخة محدّثة:

```powershell
# 1) حدّث الكود
# ... تعديلات ...

# 2) ارفع لـ GitHub
git add -A
git commit -m "v1.1: تحديثات"
git push

# 3) أعد بناء EXE
pyinstaller TechtoonAccounting.spec --noconfirm --clean

# 4) أعد تجهيز الحزمة
# (كرر خطوات تجهيز الحزمة)

# 5) أرسل التحديث للعملاء الحاليين
# (رخصهم ستبقى فعالة — لا حاجة لإعادة التفعيل)
```

---

**© 2026 Techtoon Accounting. جميع الحقوق محفوظة.**
