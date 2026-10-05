# sidebar.py
# القائمة الجانبية (للصفحات الداخلية) + الصلاحيات + حارس الدخول
# ✅ جديد: مسح بيانات الصفحة السابقة تلقائيًا عند التنقل لصفحة جديدة
import inspect
import re
from pathlib import Path

import streamlit as st

from session_auth import restore_session, logout_user

PAGES_DIR = Path(__file__).parent / "pages"

# احتياطي لإخفاء القائمة التلقائية (الأساس هو config.toml)
HIDE_DEFAULT_NAV = """
<style>
    [data-testid="stSidebarNav"],
    [data-testid="stSidebarNavItems"],
    [data-testid="stSidebarNavSeparator"],
    [data-testid="stSidebarNavView"] {
        display: none !important;
    }
</style>
"""

# ==========================================================
# الصلاحيات: من يستطيع فتح كل صفحة؟
# الأدوار (كما في UserRole داخل models.py):
#   ADMIN / ACCOUNTANT / SALESPERSON / VIEWER
# للتعديل: غيّر المجموعة المقابلة للصفحة فقط.
# صفحة غير مذكورة هنا = للمدير فقط (احتياط آمن).
# ==========================================================
ALL = {"ADMIN", "ACCOUNTANT", "SALESPERSON", "VIEWER"}
ADMIN_ONLY = {"ADMIN"}
MANAGEMENT = {"ADMIN", "ACCOUNTANT"}
REPORTS = {"ADMIN", "ACCOUNTANT", "VIEWER"}
SALES = {"ADMIN", "ACCOUNTANT", "SALESPERSON"}

PAGE_ACCESS = {
    # الحساب
    "تسجيل_الدخول": ALL,          # صفحة "حسابي"
    "إدارة_المستخدمين": ADMIN_ONLY,
    # تكويد
    "الاصناف": ALL,
    "التصنيفات": MANAGEMENT,
    "عملاء": ALL,
    "شجرة_الحسابات": MANAGEMENT,
    "كشف_حساب": REPORTS,
    "العملات": MANAGEMENT,
    # عمليات
    "الفواتير": SALES,
    "فهرس_الفواتير": ALL,
    "المدفوعات": MANAGEMENT,
    "المصروفات": MANAGEMENT,
    "الخزائن": MANAGEMENT,
    # مخزون
    "إدارة_المخزون": MANAGEMENT,
    "الأصول_الثابتة": MANAGEMENT,
    # مالية
    "إدارة_القروض": MANAGEMENT,
    "الموظفين_والرواتب": ADMIN_ONLY,
    "الإغلاق_المحاسبي": MANAGEMENT,
    "مراكز_التكلفة": MANAGEMENT,
    "الميزانية_العمومية": REPORTS,
    # تقارير
    "لوحة_التحكم": REPORTS,
    "التقارير": REPORTS,
    "تقارير_متقدمة": REPORTS,
    "تحليل_الربحية": MANAGEMENT,
    "تقرير_الارباح": MANAGEMENT,
    "التقارير_المالية": REPORTS,
    "التنبيهات": ALL,
    "مركز_التذكيرات": ALL,
    # نظام
    "النسخ_الاحتياطي": MANAGEMENT,
}

# (اسم المجموعة, [(الاسم الظاهر, كلمة البحث في اسم الملف, الأيقونة)])
GROUPS = [
    ("👤 الحساب", [
        ("حسابي", "تسجيل_الدخول", "👤"),
        ("إدارة المستخدمين", "إدارة_المستخدمين", "👥"),
    ]),
    ("📋 تكويد", [
        ("الأصناف", "الاصناف", "📦"),
        ("التصنيفات", "التصنيفات", "🗂️"),
        ("العملاء والموردين", "عملاء", "👥"),
        ("شجرة الحسابات", "شجرة_الحسابات", "📚"),
        ("كشف حساب", "كشف_حساب", "📋"),
        ("العملات", "العملات", "💱"),
    ]),
    ("⚙️ عمليات", [
        ("الفواتير", "الفواتير", "🧾"),
        ("فهرس الفواتير", "فهرس_الفواتير", "📋"),
        ("المدفوعات", "المدفوعات", "💰"),
        ("المصروفات", "المصروفات", "💸"),
        ("الخزائن", "الخزائن", "🏦"),
    ]),
    ("📦 مخزون", [
        ("إدارة المخزون", "إدارة_المخزون", "📦"),
        ("الأصول الثابتة", "الأصول_الثابتة", "🏭"),
    ]),
    ("💼 مالية", [
        ("إدارة القروض", "إدارة_القروض", "🏦"),
        ("الموظفين والرواتب", "الموظفين_والرواتب", "👔"),
        ("الإغلاق المحاسبي", "الإغلاق_المحاسبي", "📅"),
        ("مراكز التكلفة", "مراكز_التكلفة", "🏢"),
        ("الميزانية العمومية", "الميزانية_العمومية", "⚖️"),
    ]),
    ("📊 تقارير", [
        ("لوحة التحكم", "لوحة_التحكم", "🏠"),
        ("التقارير", "التقارير", "📑"),
        ("تقارير متقدمة", "تقارير_متقدمة", "📈"),
        ("تحليل الربحية", "تحليل_الربحية", "📈"),
        ("تقرير الأرباح", "تقرير_الارباح", "💰"),
        ("التقارير المالية", "التقارير_المالية", "📊"),
        ("التنبيهات", "التنبيهات", "🔔"),
        ("مركز التذكيرات", "مركز_التذكيرات", "⏰"),
    ]),
    ("🛠️ نظام", [
        ("النسخ الاحتياطي", "النسخ_الاحتياطي", "💾"),
    ]),
]


# ==========================================================
# أدوات مساعدة
# ==========================================================
def _norm(text):
    """يحذف الرقم البادئ والإيموجي من اسم الملف: '3_👥عملاء' -> 'عملاء'."""
    text = re.sub(r"^\d+_", "", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def _build_index():
    return [(f, _norm(f.stem)) for f in sorted(PAGES_DIR.glob("*.py"))]


def _find_page(term, index):
    t = _norm(term)
    # تطابق تام أولاً (حتى لا تلتبس "التقارير" مع "التقارير_المالية")
    for f, name in index:
        if name == t:
            return f
    for f, name in index:
        if t in name:
            return f
    return None


def _role_name(user):
    """اسم دور المستخدم بالحروف الكبيرة: ADMIN / ACCOUNTANT / ..."""
    role = user.get("role")
    name = getattr(role, "name", None)
    if name:
        return str(name).upper()
    try:  # إن عادت القيمة كنص (مثلاً "مدير") نحوّلها لاسم الدور
        from models import UserRole
        return UserRole(role).name.upper()
    except Exception:
        return str(role).upper()


def role_label(user):
    """الدور بالعربية للعرض (Enum -> 'مدير')."""
    role = user.get("role", "")
    return getattr(role, "value", role)


def can_access(term, user):
    """هل يحق لهذا المستخدم فتح الصفحة؟"""
    if not user:
        return False
    allowed = PAGE_ACCESS.get(term, ADMIN_ONLY)
    return _role_name(user) in allowed


# ==========================================================
# صلاحيات العمليات (منفصلة عن صلاحية فتح الصفحات)
#   - الإنشاء : لكل حساب ضمن الصفحات المسموحة له (ما عدا المشاهد)
#   - التعديل والحذف : صلاحية مختلفة، للمدير فقط
# ==========================================================
CREATE_ROLES = {"ADMIN", "ACCOUNTANT", "SALESPERSON"}
MODIFY_ROLES = {"ADMIN"}  # التعديل والحذف

# أي زر يحتوي إحدى هذه الكلمات يُعطَّل لغير المدير (للتعديل: عدّل القائمة)
MODIFY_WORDS = ("حذف", "تعديل", "delete", "edit", "🗑", "✏")


def can_create(user=None):
    """هل يحق للمستخدم إنشاء سجلات جديدة؟"""
    user = user or st.session_state.get("current_user")
    return bool(user) and _role_name(user) in CREATE_ROLES


def can_modify(user=None):
    """هل يحق للمستخدم التعديل أو الحذف؟ (المدير فقط)"""
    user = user or st.session_state.get("current_user")
    return bool(user) and _role_name(user) in MODIFY_ROLES


def require_modify(action="هذه العملية"):
    """للاستخدام داخل الصفحات قبل تنفيذ تعديل/حذف:
        if st.button("..."):
            if not require_modify("حذف الفاتورة"):
                st.stop()
    """
    if can_modify():
        return True
    st.error(f"⛔ {action} للمدير فقط.")
    return False


# ==========================================================
# ✅ جديد: مسح بيانات الصفحة السابقة عند التنقل
# ==========================================================
# المفاتيح التي يجب الحفاظ عليها عند التنقل بين الصفحات
_PRESERVE_KEYS = ("current_user", "_active_page")

# مفاتيح إضافية تبدأ بـ _ ولكن يجب مسحها عند التنقل
# (بيانات النماذج القابلة للتعديل + الرسائل المؤقتة)
_EXTRA_CLEAR_KEYS = (
    "_editing_invoice_id",
    "_editing_invoice_no",
    "_editing_invoice_type",
    "_pending_state",
    "_inv_flash",
    "_items_flash",
    "_inv_edit_flash",
)


def _reset_page_state_on_navigation(caller_path):
    """
    عند التنقل لصفحة جديدة: امسح كل بيانات الصفحة السابقة
    (المدخلات، السلة، الفلاتر، ...) عشان المستخدم يبدأ نظيف.
    """
    current = str(caller_path)
    prev = st.session_state.get("_active_page")

    # أول تشغيل — سجّل الصفحة الحالية فقط
    if prev is None:
        st.session_state["_active_page"] = current
        return

    # نفس الصفحة → لا تمسح أي شيء
    if prev == current:
        return

    # ✅ الصفحة اتغيرت → امسح:
    # 1) كل المفاتيح العادية (غير التي تبدأ بـ _)
    for k in list(st.session_state.keys()):
        name = str(k)
        if name in _PRESERVE_KEYS:
            continue
        if name.startswith("_"):
            continue  # هنشيلهم تحت بشكل انتقائي
        del st.session_state[k]

    # 2) مفاتيح محددة تبدأ بـ _ لكنها بيانات نماذج أو رسائل مؤقتة
    for k in _EXTRA_CLEAR_KEYS:
        st.session_state.pop(k, None)

    # 3) سجّل الصفحة الحالية
    st.session_state["_active_page"] = current


# ==========================================================
# تفريغ الخانات بعد الحفظ (لكل الصفحات)
# ==========================================================
def queue_state_updates(delete_prefixes=(), delete_keys=(), set_values=None):
    """يؤجّل تعديل session_state إلى بداية التشغيل التالي، قبل إنشاء أي أداة.
    (Streamlit يمنع تغيير قيمة أداة بعد رسمها في نفس التشغيل، فنؤجّل التغيير.)

    الاستخدام بعد نجاح الحفظ، ثم st.rerun():
        queue_state_updates(delete_prefixes=("input_", "edit_"))   # يمسح كل خانة مفتاحها يبدأ بهذا
        queue_state_updates(set_values={"مفتاح": قيمة})              # أو يضبط قيماً (مثل اختيار الصنف التالي)
        st.rerun()
    ملاحظة: يعمل على الأدوات التي لها key. الأداة بلا key أعطها key أولاً.
    """
    pending = st.session_state.get("_pending_state") or {"prefixes": [], "keys": [], "set": {}}
    pending["prefixes"] = list(pending["prefixes"]) + list(delete_prefixes)
    pending["keys"] = list(pending["keys"]) + list(delete_keys)
    pending["set"] = {**pending["set"], **(set_values or {})}
    st.session_state["_pending_state"] = pending


def request_form_clear(*prefixes):
    """اختصار: امسح كل الخانات التي تبدأ مفاتيحها بهذه البادئات في التشغيل التالي."""
    queue_state_updates(delete_prefixes=prefixes)


def _apply_pending_state():
    """تُنفَّذ تلقائياً في أول كل صفحة (داخل render_sidebar)، قبل رسم الأدوات."""
    pending = st.session_state.pop("_pending_state", None)
    if not pending:
        return
    prefixes = tuple(pending.get("prefixes", ()))
    keys = set(pending.get("keys", ()))
    for k in list(st.session_state.keys()):
        name = str(k)
        if name.startswith("_") or name in ("current_user",):
            continue  # لا نمس مفاتيح النظام
        if (prefixes and name.startswith(prefixes)) or k in keys:
            del st.session_state[k]
    for k, v in (pending.get("set") or {}).items():
        st.session_state[k] = v


def _is_modify_label(label):
    text = str(label).lower()
    return any(w in text for w in MODIFY_WORDS)


def _install_modify_guard():
    """يعطّل أزرار التعديل/الحذف لغير المدير في كل الصفحات تلقائياً.
    الزر المعطَّل لا يُنفَّذ أبداً (يعيد False)، فلا تُنفَّذ الشيفرة التابعة له.
    يُركَّب مرة واحدة ويقرأ المستخدم الحالي عند كل استدعاء.
    """
    from streamlit.delta_generator import DeltaGenerator

    if getattr(DeltaGenerator.button, "_modify_guard", False):
        return

    def wrap(orig):
        def guarded(self, *args, **kwargs):
            label = args[0] if args else kwargs.get("label", "")
            if _is_modify_label(label) and not can_modify():
                kwargs["disabled"] = True
                if not kwargs.get("help"):
                    kwargs["help"] = "التعديل والحذف للمدير فقط"
                orig(self, *args, **kwargs)
                return False
            return orig(self, *args, **kwargs)

        guarded._modify_guard = True
        return guarded

    DeltaGenerator.button = wrap(DeltaGenerator.button)
    DeltaGenerator.form_submit_button = wrap(DeltaGenerator.form_submit_button)

    # st.button و st.form_submit_button مربوطتان وقت الاستيراد، فنعيد ربطهما
    main_dg = getattr(st, "_main", None)
    if main_dg is not None:
        st.button = main_dg.button
        st.form_submit_button = main_dg.form_submit_button


def visible_groups(user):
    """المجموعات والصفحات المسموحة للمستخدم فقط.
    تُرجع: [(اسم المجموعة, [(الاسم, الأيقونة, 'pages/x.py', Path)])]
    تستخدمها القائمة الجانبية وصفحة المربعات معاً.
    """
    index = _build_index()
    result = []
    for group_name, pages in GROUPS:
        items = []
        for label, term, icon in pages:
            f = _find_page(term, index)
            if f and can_access(term, user):
                items.append((label, icon, f"pages/{f.name}", f))
        if items:  # المجموعة الفارغة لا تظهر
            result.append((group_name, items))
    return result


def _term_for_file(path):
    index = _build_index()
    for _, pages in GROUPS:
        for _, term, _ in pages:
            f = _find_page(term, index)
            if f and f.resolve() == path:
                return term
    return None  # صفحة غير مدرجة


# ==========================================================
# القائمة الجانبية + الحارس (تُستدعى في أول كل صفحة داخلية)
# ==========================================================
def render_sidebar():
    # الملف الذي استدعى الدالة (لفتح مجموعته تلقائياً ولفحص صلاحيته)
    caller = Path(inspect.currentframe().f_back.f_code.co_filename).resolve()

    restore_session()  # استعادة المستخدم بعد Refresh

    # ✅ جديد: امسح بيانات الصفحة السابقة لو اتغيرت
    _reset_page_state_on_navigation(caller)

    _apply_pending_state()  # تفريغ/ضبط الخانات المؤجَّل بعد الحفظ
    st.markdown(HIDE_DEFAULT_NAV, unsafe_allow_html=True)

    user = st.session_state.get("current_user")

    # غير مسجّل → إلى شاشة الدخول (app.py)
    if not user:
        st.switch_page("app.py")

    _install_modify_guard()  # تعطيل التعديل/الحذف لغير المدير

    with st.sidebar:
        st.title("💼 Techtoon")
        st.caption(f"👤 {user.get('full_name', '')} — {role_label(user)}")
        if not can_modify(user):
            st.caption("✏️ التعديل والحذف للمدير فقط")

        # زر الرئيسية: صفحة المربعات
        st.page_link("app.py", label="🏠 الصفحة الرئيسية")

        for group_name, items in visible_groups(user):
            expanded = any(f.resolve() == caller for _, _, _, f in items)
            with st.expander(group_name, expanded=expanded):
                for label, icon, path, _ in items:
                    st.page_link(path, label=f"{icon} {label}")

        st.divider()
        if st.button("🚪 تسجيل الخروج", key="sidebar_logout"):
            logout_user()
            st.rerun()

    # الحارس: منع فتح الصفحة عبر الرابط المباشر دون صلاحية
    # (إخفاء الزر وحده لا يكفي)
    if caller.parent == PAGES_DIR.resolve():
        term = _term_for_file(caller)
        if not can_access(term, user):
            st.error("⛔ ليست لديك صلاحية للوصول إلى هذه الصفحة.")
            st.page_link("app.py", label="🏠 العودة إلى الصفحة الرئيسية")
            st.stop()