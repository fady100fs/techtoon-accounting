# update_all_pages.py
"""
سكربت تحديث شامل لكل صفحات البرنامج
====================================
يضيف لكل صفحة:
  1. from form_manager import clear_form, show_clear_hint
  2. PFX = "xxx_"  (بادئة فريدة حسب رقم الصفحة)
  3. show_clear_hint()  (بعد العنوان)
  4. key=f"{PFX}..."  لف كل widget keys
  5. clear_form(PFX)  قبل st.rerun() بعد st.success

الاستخدام:
    python update_all_pages.py              # فحص فقط (لا يعدّل)
    python update_all_pages.py --apply      # تطبيق فعلي + نسخ احتياطية
    python update_all_pages.py --rollback   # استرجاع آخر نسخة احتياطية
    python update_all_pages.py --list       # عرض البادئات المقترحة
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).parent
PAGES_DIR = ROOT / "pages"
BACKUP_ROOT = ROOT / "_pages_backup"


# ═══════════════════════════════════════════════════════════
# بادئات فريدة لكل صفحة (لا تكرر)
# ═══════════════════════════════════════════════════════════
PREFIXES = {
    "1":  "dash",       # لوحة التحكم
    "2":  "itm",        # الأصناف
    "3":  "pty",        # عملاء وموردين
    "4":  "inv",        # الفواتير
    "5":  "reports",    # التقارير
    "6":  "inv_idx",    # فهرس الفواتير
    "7":  "cur",        # العملات
    "8":  "pay",        # المدفوعات
    "9":  "coa",        # شجرة الحسابات
    "10": "stmt",       # كشف حساب
    "11": "bkup",       # النسخ الاحتياطي
    "12": "bs",         # الميزانية
    "13": "alerts",     # التنبيهات
    "14": "acct",       # تسجيل الدخول
    "15": "adv_rep",    # تقارير متقدمة
    "16": "rem",        # مركز التذكيرات
    "18": "profit",     # تقرير الأرباح
    "19": "box",        # الخزائن
    "20": "cat",        # التصنيفات
    "21": "users",      # إدارة المستخدمين
    "22": "cm",         # حركات الخزينة
    "23": "wh",         # إدارة المخزون
    "24": "fa",         # الأصول الثابتة
    "25": "prof",       # تحليل الربحية
    "26": "loan",       # القروض
    "27": "emp",        # الموظفين
    "28": "fin_rep",    # التقارير المالية
    "29": "close",      # الإغلاق المحاسبي
    "30": "cc",         # مراكز التكلفة
    "31": "integrity",  # فحص السلامة
    "32": "je",         # قيود اليومية
    "33": "barcode",    # قارئ الباركود
    "34": "rec",        # الفواتير المتكررة
    "35": "search",     # البحث الموحد
    "36": "settings",   # الإعدادات
    "37": "pdf_rep",    # تقارير PDF
    "38": "s3",         # النسخ السحابي
}


# ═══════════════════════════════════════════════════════════
# ألوان للـ Terminal
# ═══════════════════════════════════════════════════════════
class C:
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    GRAY   = "\033[90m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"


# ═══════════════════════════════════════════════════════════
# دوال المساعدة
# ═══════════════════════════════════════════════════════════
def get_prefix(filepath):
    m = re.match(r"^(\d+)_", filepath.stem)
    if not m:
        return None
    num = m.group(1)
    base = PREFIXES.get(num, f"p{num}")
    return f"{base}_"


def already_has_form_manager(text):
    return "from form_manager import" in text


def add_import(text):
    """يضيف import form_manager بعد آخر استيراد من المشروع."""
    if already_has_form_manager(text):
        return text, False
    patterns = [
        r"^(from auth_required import [^\n]+\n)",
        r"^(from sidebar import [^\n]+\n)",
        r"^(from services import [^\n]+\n)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.MULTILINE)
        if m:
            pos = m.end()
            inject = "from form_manager import clear_form, show_clear_hint\n"
            return text[:pos] + inject + text[pos:], True
    return text, False


def add_prefix_constant(text, prefix):
    """يضيف PFX = 'xxx_' بعد آخر استيراد."""
    if re.search(r"^PFX\s*=", text, re.MULTILINE):
        return text, False
    imports = list(re.finditer(r"^(?:from|import)\s+[^\n]+\n", text[:2500], re.MULTILINE))
    if not imports:
        return text, False
    pos = imports[-1].end()
    inject = (
        "\n"
        "# ═══════════════════════════════════════════════════════════\n"
        "# ✅ PFX: بادئة موحّدة لكل مفاتيح هذه الصفحة\n"
        "# ═══════════════════════════════════════════════════════════\n"
        f'PFX = "{prefix}"\n\n'
    )
    return text[:pos] + inject + text[pos:], True


def add_show_clear_hint(text):
    """يضيف show_clear_hint() بعد st.title()."""
    if "show_clear_hint()" in text:
        return text, False
    m = re.search(r"^(st\.title\([^\n]*\)\n)", text, re.MULTILINE)
    if m:
        pos = m.end()
        inject = "\nshow_clear_hint()  # 💡 الحقول ستُفرَّغ تلقائياً بعد كل عملية\n"
        return text[:pos] + inject + text[pos:], True
    return text, False


# regex لـ key="xxx" — فقط string literals بسيطة
KEY_PATTERN = re.compile(
    r'(key\s*=\s*)'
    r'(["\'])'
    r'([a-zA-Z_][a-zA-Z0-9_]*)'
    r'\2'
)


def wrap_widget_keys(text, prefix):
    """يستبدل key="xxx" بـ key=f"{PFX}xxx" لكل widgets."""
    if "{PFX}" in text:
        return text, 0
    count = [0]
    def replacer(m):
        key_part = m.group(1)
        name = m.group(3)
        if name.startswith("_"):
            return m.group(0)
        count[0] += 1
        return f'{key_part}f"{{PFX}}{name}"'
    return KEY_PATTERN.sub(replacer, text), count[0]


def add_clear_form_before_rerun(text):
    """يضيف clear_form(PFX) قبل st.rerun() بعد st.success."""
    if "clear_form(PFX)" in text:
        return text, 0
    lines = text.split("\n")
    result = []
    last_success = -1
    count = 0
    for line in lines:
        if "st.success(" in line:
            last_success = len(result)
        if "st.rerun()" in line and last_success >= 0:
            indent = line[: len(line) - len(line.lstrip())]
            result.append(f"{indent}clear_form(PFX)  # ✅ تفريغ الحقول")
            count += 1
            last_success = -1
        result.append(line)
    return "\n".join(result), count


def process_page(filepath, apply=False):
    """يعالج صفحة واحدة."""
    try:
        original = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return {"file": filepath.name, "error": str(e), "changed": False}

    text = original
    prefix = get_prefix(filepath)
    if not prefix:
        return None

    changes = []

    text, c = add_import(text)
    if c: changes.append("+import")

    text, c = add_prefix_constant(text, prefix)
    if c: changes.append("+PFX")

    text, c = add_show_clear_hint(text)
    if c: changes.append("+show_clear_hint")

    text, c = wrap_widget_keys(text, prefix)
    if c: changes.append(f"+{c} keys")

    text, c = add_clear_form_before_rerun(text)
    if c: changes.append(f"+{c} clear_form")

    result = {
        "file": filepath.name,
        "prefix": prefix,
        "changes": changes,
        "changed": text != original,
    }

    if apply and result["changed"]:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = BACKUP_ROOT / ts
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(filepath, backup_dir / filepath.name)
        filepath.write_text(text, encoding="utf-8")

    return result


def do_rollback():
    """يسترجع آخر نسخة احتياطية."""
    if not BACKUP_ROOT.exists():
        print(f"{C.RED}❌ لا توجد نسخ احتياطية في: {BACKUP_ROOT}{C.RESET}")
        return
    backups = sorted([d for d in BACKUP_ROOT.iterdir() if d.is_dir()], reverse=True)
    if not backups:
        print(f"{C.RED}❌ لا توجد نسخ احتياطية{C.RESET}")
        return
    latest = backups[0]
    print(f"{C.CYAN}🔄 استرجاع من: {latest.name}{C.RESET}")
    print()
    restored = 0
    for f in sorted(latest.glob("*.py")):
        target = PAGES_DIR / f.name
        shutil.copy2(f, target)
        restored += 1
        print(f"  {C.GREEN}✅{C.RESET} {f.name}")
    print()
    print(f"{C.GREEN}✅ تم استرجاع {restored} ملف{C.RESET}")


def list_prefixes():
    """يعرض جدول البادئات."""
    print()
    print(f"{C.BOLD}{'=' * 70}{C.RESET}")
    print(f"{C.BOLD}📋 البادئات المقترحة لكل صفحة{C.RESET}")
    print(f"{C.BOLD}{'=' * 70}{C.RESET}")
    print()
    print(f"{'رقم':<6}{'بادئة':<20}{'اسم الملف'}")
    print("-" * 70)
    for num, base in sorted(PREFIXES.items(), key=lambda x: int(x[0])):
        prefix = f"{base}_"
        matching = list(PAGES_DIR.glob(f"{num}_*.py"))
        fname = matching[0].name if matching else "—"
        print(f"{num:<6}{prefix:<20}{fname}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="تحديث كل الصفحات لتفعيل نظام clear_form"
    )
    parser.add_argument("--apply", action="store_true", help="تطبيق فعلي")
    parser.add_argument("--rollback", action="store_true", help="استرجاع آخر نسخة")
    parser.add_argument("--list", action="store_true", help="عرض البادئات")
    args = parser.parse_args()

    if args.rollback:
        do_rollback()
        return

    if args.list:
        list_prefixes()
        return

    if not PAGES_DIR.exists():
        print(f"{C.RED}❌ مجلد pages غير موجود في: {PAGES_DIR}{C.RESET}")
        return

    apply_mode = args.apply

    print()
    print(f"{C.BOLD}{'=' * 75}{C.RESET}")
    if apply_mode:
        print(f"{C.YELLOW}{C.BOLD}🚀 وضع التطبيق الفعلي{C.RESET}")
    else:
        print(f"{C.CYAN}{C.BOLD}🔍 وضع الفحص فقط (Dry Run) — لا تعديل{C.RESET}")
    print(f"{C.BOLD}{'=' * 75}{C.RESET}")
    print()

    pages = sorted(PAGES_DIR.glob("*.py"))
    results = []
    for page in pages:
        result = process_page(page, apply=apply_mode)
        if result:
            results.append(result)

    changed_count = 0
    skipped_count = 0
    error_count = 0

    for r in results:
        if r.get("error"):
            error_count += 1
            print(f"{C.RED}❌{C.RESET} {r['file']}: {r['error'][:60]}")
            continue

        if r["changed"]:
            changed_count += 1
            icon = "✅" if apply_mode else "📝"
            print(f"{C.GREEN}{icon}{C.RESET} {r['file']:55s} {C.GRAY}({r['prefix']}){C.RESET}")
            for change in r["changes"]:
                print(f"      {C.GRAY}• {change}{C.RESET}")
        else:
            skipped_count += 1
            print(f"{C.GRAY}⏭️  {r['file']:55s} (لا يحتاج تحديث){C.RESET}")

    print()
    print(f"{C.BOLD}{'=' * 75}{C.RESET}")
    print(f"📊 إجمالي: {C.BOLD}{len(results)}{C.RESET} صفحة")
    print(f"   {C.GREEN}✅ تحتاج/تم تحديثها: {changed_count}{C.RESET}")
    print(f"   {C.GRAY}⏭️  لا تحتاج: {skipped_count}{C.RESET}")
    if error_count:
        print(f"   {C.RED}❌ أخطاء: {error_count}{C.RESET}")

    if apply_mode and changed_count > 0:
        print()
        print(f"{C.GREEN}💾 النسخ الاحتياطية: {BACKUP_ROOT}{C.RESET}")
        print(f"{C.CYAN}🔄 للاسترجاع: python update_all_pages.py --rollback{C.RESET}")
    elif not apply_mode and changed_count > 0:
        print()
        print(f"{C.YELLOW}💡 للتطبيق الفعلي:{C.RESET}")
        print(f"   {C.BOLD}python update_all_pages.py --apply{C.RESET}")

    print(f"{C.BOLD}{'=' * 75}{C.RESET}")
    print()


if __name__ == "__main__":
    main()