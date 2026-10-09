# sidebar.py
# القائمة الجانبية (للصفحات الداخلية) + الصلاحيات + حارس الدخول
import inspect
import re
from pathlib import Path

import streamlit as st
from feature_flags import (
    s3_backup_enabled, barcode_enabled, pdf_reports_enabled,
    recurring_invoices_enabled, fixed_assets_enabled,
    loans_enabled, payroll_enabled,
)
from session_auth import restore_session, logout_user
from form_manager import apply_pending_clears
# sidebar.py — إضافات السرعة والمزامنة
import os
from datetime import datetime

# ⭐ معلومات المزامنة (محلياً فقط)
try:
    if os.getenv("DEPLOY_MODE", "cloud").lower() == "local":
        from sync_manager import get_sync_state, full_sync
        from local_mirror import get_local_db_size_mb

        _sync = get_sync_state()
        _size = get_local_db_size_mb()

        with st.sidebar:
            st.markdown("---")
            st.markdown("### 💾 حالة المزامنة")

            if _sync["in_progress"]:
                st.info("⏳ جاري المزامنة...")
            elif _sync["ok"] and _sync["last_sync"]:
                _ago = (datetime.now() - _sync["last_sync"]).total_seconds() / 60
                _color = "🟢" if _ago < 35 else "🟡" if _ago < 60 else "🔴"
                st.success(
                    f"{_color} آخر مزامنة: "
                    f"{_sync['last_sync'].strftime('%H:%M')} "
                    f"(منذ {int(_ago)}د)"
                )
            else:
                st.warning("⚠️ لم تتم المزامنة بعد")

            if _sync["error"]:
                st.caption(f"❌ {_sync['error'][:80]}")

            st.caption(f"📊 حجم SQLite: {_size:.1f} MB")
            st.caption(f"📈 صفوف مُزامَنة: {_sync['rows_synced']:,}")

            _c1, _c2 = st.columns(2)
            with _c1:
                if st.button("🔄 مزامنة", use_container_width=True):
                    with st.spinner("جاري المزامنة..."):
                        full_sync(verbose=False)
                    st.cache_data.clear()
                    st.rerun()
            with _c2:
                if st.button("🧹 كاش", use_container_width=True):
                    st.cache_data.clear()
                    st.toast("✅ تم مسح الكاش")
                    st.rerun()
except Exception as _e:
    pass   # تجاهل الأخطاء في sidebar
PAGES_DIR = Path(__file__).parent / "pages"

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
# الصلاحيات
# ==========================================================
ALL = {"ADMIN", "ACCOUNTANT", "SALESPERSON", "VIEWER"}
ADMIN_ONLY = {"ADMIN"}
MANAGEMENT = {"ADMIN", "ACCOUNTANT"}
REPORTS = {"ADMIN", "ACCOUNTANT", "VIEWER"}
SALES = {"ADMIN", "ACCOUNTANT", "SALESPERSON"}

PAGE_ACCESS = {
    # الحساب
    "تسجيل_الدخول": ALL,
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
    "قيود_اليومية": MANAGEMENT,
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
    # أدوات
    "قارئ_الباركود": ALL,
    # "الفواتير_المتكررة": MANAGEMENT,  # ⏸️ معطّلة مؤقتاً
    "البحث_الموحد": ALL,
    "تقارير_PDF": MANAGEMENT,
    # نظام
    "النسخ_الاحتياطي": MANAGEMENT,
    "النسخ_السحابي": MANAGEMENT,
    "فحص_السلامة": MANAGEMENT,
    "الإعدادات": MANAGEMENT,
}

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
        ("حركات الخزينة", "المصروفات", "💹"),
        ("الخزائن", "الخزائن", "🏦"),
        ("قيود اليومية", "قيود_اليومية", "📝"),
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
    ("🛠️ أدوات", [
        ("🔍 البحث الموحد", "البحث_الموحد", "🔍"),
        ("قارئ الباركود", "قارئ_الباركود", "📷"),
        # ("الفواتير المتكررة", "الفواتير_المتكررة", "🔄"),  # ⏸️ معطّلة مؤقتاً
        ("📄 تقارير PDF", "تقارير_PDF", "📄"),
    ]),
    ("🛠️ نظام", [
        ("⚙️ الإعدادات", "الإعدادات", "⚙️"),
        ("☁️ النسخ السحابي", "النسخ_السحابي", "☁️"),
        ("💾 النسخ الاحتياطي", "النسخ_الاحتياطي", "💾"),
        ("🔍 فحص السلامة", "فحص_السلامة", "🔍"),
    ]),
]


# ==========================================================
# أدوات مساعدة
# ==========================================================
def _norm(text):
    """يحذف الرقم البادئ والرموز غير الأبجدية من اسم الملف."""
    text = re.sub(r"^\d+_", "", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


@st.cache_data(ttl=3600, show_spinner=False)
def _build_index():
    return [(f, _norm(f.stem)) for f in sorted(PAGES_DIR.glob("*.py"))]


def _find_page(term, index):
    """يبحث عن صفحة بالاسم.

    الترتيب:
    1) تطابق تام (normalized)
    2) الأقصر بين كل من يحتوي على term
       ← هذا يحل مشكلة "الفواتير" (يختار 4_ وليس 34_)
    """
    t = _norm(term)

    # 1) تطابق تام
    for f, name in index:
        if name == t:
            return f

    # 2) أي تطابق جزئي — نرتّب حسب طول الاسم (الأقصر أولاً)
    matches = [(f, name) for f, name in index if t in name]
    if not matches:
        return None

    matches.sort(key=lambda x: len(x[1]))
    return matches[0][0]


def _role_name(user):
    role = user.get("role")
    name = getattr(role, "name", None)
    if name:
        return str(name).upper()
    try:
        from models import UserRole
        return UserRole(role).name.upper()
    except Exception:
        return str(role).upper()


def role_label(user):
    role = user.get("role", "")
    return getattr(role, "value", role)


def can_access(term, user):
    if not user:
        return False
    allowed = PAGE_ACCESS.get(term, ADMIN_ONLY)
    return _role_name(user) in allowed


# ==========================================================
# صلاحيات العمليات
# ==========================================================
CREATE_ROLES = {"ADMIN", "ACCOUNTANT", "SALESPERSON"}
MODIFY_ROLES = {"ADMIN"}
MODIFY_WORDS = ("حذف", "تعديل", "delete", "edit", "🗑", "✏")


def can_create(user=None):
    user = user or st.session_state.get("current_user")
    return bool(user) and _role_name(user) in CREATE_ROLES


def can_modify(user=None):
    user = user or st.session_state.get("current_user")
    return bool(user) and _role_name(user) in MODIFY_ROLES


def require_modify(action="هذه العملية"):
    if can_modify():
        return True
    st.error(f"⛔ {action} للمدير فقط.")
    return False


# ==========================================================
# إدارة حالة الصفحة
# ==========================================================
_PRESERVE_KEYS = ("current_user", "_active_page")

_EXTRA_CLEAR_KEYS = (
    "_editing_invoice_id",
    "_editing_invoice_no",
    "_editing_invoice_type",
    "_pending_state",
    "_pending_form_clear",
    "_inv_flash",
    "_items_flash",
    "_inv_edit_flash",
)


def _reset_page_state_on_navigation(caller_path):
    current = str(caller_path)
    prev = st.session_state.get("_active_page")

    if prev is None:
        st.session_state["_active_page"] = current
        return

    if prev == current:
        return

    for k in list(st.session_state.keys()):
        name = str(k)
        if name in _PRESERVE_KEYS:
            continue
        if name.startswith("_"):
            continue
        del st.session_state[k]

    for k in _EXTRA_CLEAR_KEYS:
        st.session_state.pop(k, None)

    st.session_state["_active_page"] = current


def queue_state_updates(delete_prefixes=(), delete_keys=(), set_values=None):
    pending = st.session_state.get("_pending_state") or {"prefixes": [], "keys": [], "set": {}}
    pending["prefixes"] = list(pending["prefixes"]) + list(delete_prefixes)
    pending["keys"] = list(pending["keys"]) + list(delete_keys)
    pending["set"] = {**pending["set"], **(set_values or {})}
    st.session_state["_pending_state"] = pending


def request_form_clear(*prefixes):
    queue_state_updates(delete_prefixes=prefixes)


def _apply_pending_state():
    """تطبيق التحديثات المُعلّقة على session_state بأمان."""
    try:
        pending = st.session_state.pop("_pending_state_updates", None)
        if not pending:
            return

        delete_keys = pending.get("delete_keys", [])
        set_values = pending.get("set_values", {})

        if delete_keys:
            try:
                keys_iter = list(delete_keys) if not isinstance(delete_keys, str) else [delete_keys]
            except Exception:
                keys_iter = []

            for k in keys_iter:
                try:
                    name = str(k) if k is not None else ""
                    if not name:
                        continue
                    st.session_state.pop(name, None)
                except Exception:
                    continue

        if set_values and isinstance(set_values, dict):
            for k, v in set_values.items():
                try:
                    name = str(k) if k is not None else ""
                    if not name:
                        continue
                    st.session_state[name] = v
                except Exception:
                    continue

    except Exception:
        pass



def _is_modify_label(label):
    text = str(label).lower()
    return any(w in text for w in MODIFY_WORDS)


def _install_modify_guard():
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

    main_dg = getattr(st, "_main", None)
    if main_dg is not None:
        st.button = main_dg.button
        st.form_submit_button = main_dg.form_submit_button


def visible_groups(user):
    index = _build_index()
    result = []
    for group_name, pages in GROUPS:
        items = []
        for label, term, icon in pages:
            f = _find_page(term, index)
            if f and can_access(term, user):
                items.append((label, icon, f"pages/{f.name}", f))
        if items:
            result.append((group_name, items))
    return result


def _term_for_file(path):
    index = _build_index()
    for _, pages in GROUPS:
        for _, term, _ in pages:
            f = _find_page(term, index)
            if f and f.resolve() == path:
                return term
    return None


# ==========================================================
# القائمة الجانبية
# ==========================================================
def render_sidebar():
    caller = Path(inspect.currentframe().f_back.f_code.co_filename).resolve()

    apply_pending_clears()
    restore_session()
    _reset_page_state_on_navigation(caller)
    _apply_pending_state()
    st.markdown(HIDE_DEFAULT_NAV, unsafe_allow_html=True)

    user = st.session_state.get("current_user")

    if not user:
        st.switch_page("app.py")

    _install_modify_guard()

    with st.sidebar:
        st.title("💼 Techtoon")
        st.caption(f"👤 {user.get('full_name', '')} — {role_label(user)}")
        if not can_modify(user):
            st.caption("✏️ التعديل والحذف للمدير فقط")

        if st.button("🔍 البحث الموحد", use_container_width=True,
                     key="top_global_search"):
            index = _build_index()
            f = _find_page("البحث_الموحد", index)
            if f:
                st.switch_page(f"pages/{f.name}")

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

    if caller.parent == PAGES_DIR.resolve():
        term = _term_for_file(caller)
        if not can_access(term, user):
            st.error("⛔ ليست لديك صلاحية للوصول إلى هذه الصفحة.")
            st.page_link("app.py", label="🏠 العودة إلى الصفحة الرئيسية")
            st.stop()