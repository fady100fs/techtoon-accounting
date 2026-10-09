# app.py
# الشاشة الأولى:
#   - غير مسجّل  → شاشة تسجيل الدخول فقط (بدون قائمة أو صفحات)
#   - مسجّل      → صفحة المربعات الملونة (Metro) بدون قائمة جانبية
# يتطلب Streamlit 1.39 أو أحدث (st.container(key=...))
import time
_t0 = time.time()
import streamlit as st
import time
_t0 = time.time()
st.set_page_config(
    page_title="Techtoon Accounting",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from datetime import datetime

from auth import authenticate_user, hash_password
from models import UserRole, User
from database import SessionLocal
from session_auth import (
    restore_session, login_user, logout_user,
    check_rate_limit, record_failed_attempt, clear_attempts,
    get_remaining_attempts,
)
from sidebar import visible_groups, role_label

# ==========================================================
# إعدادات شكل المربعات
# ==========================================================
MAX_PER_ROW = 4
GRID_COLS = 12

PALETTE = [
    "#27ae60", "#2d9cdb", "#e04f39", "#0d3b66", "#9b2d5a", "#00897b",
    "#f2705f", "#16a085", "#8e44ad", "#2c7fb8", "#d35400", "#1e8449",
]

NO_SIDEBAR_CSS = """
<style>
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
</style>
"""

LOGIN_CSS = """
<style>
    .block-container { max-width: 520px !important; padding-top: 6vh !important; }
    .login-title { text-align: center; margin-bottom: 4px; }
    .login-sub { text-align: center; opacity: .7; margin-bottom: 28px; }
</style>
"""

HOME_CSS = """
<style>
    .block-container {
        max-width: min(max(62vw, 780px), 1250px) !important;
        margin: 0 auto;
        direction: rtl;
        padding-top: 2rem !important;
    }
    [data-testid="stHeaderActionElements"] { display: none !important; }

    .hero { display: flex; align-items: center; gap: 18px; margin-bottom: 4px; }
    .hero-logo {
        width: 84px; height: 84px; border-radius: 14px; flex-shrink: 0;
        background: linear-gradient(135deg, #27ae60, #1e8449);
        display: flex; align-items: center; justify-content: center;
        font-size: 2.8rem;
    }
    .hero h1 { margin: 0; padding: 0; font-size: 2.1rem; line-height: 1.2; }
    .hero p { margin: 2px 0; opacity: .8; }
    .hero small { opacity: .6; }

    .grp-title { font-size: 1.05rem; font-weight: 600; opacity: .85; margin: 22px 0 8px; }

    [class*="st-key-grp_"],
    [class*="st-key-grp_"] > [data-testid="stVerticalBlock"] {
        display: grid !important;
        grid-template-columns: repeat(12, 1fr);
        grid-auto-flow: dense;
        grid-auto-rows: 128px;
        align-items: stretch;
        column-gap: 6px !important;
        row-gap: 6px !important;
    }
    [class*="st-key-grp_"] > [data-testid="stVerticalBlock"] { grid-column: 1 / -1; }

    [class*="st-key-grp_"] > *,
    [class*="st-key-grp_"] [data-testid="stElementContainer"],
    [class*="st-key-grp_"] [data-testid="element-container"],
    [class*="st-key-grp_"] [data-testid="stPageLink"],
    [class*="st-key-grp_"] [data-testid="stPageLink"] > * {
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
        justify-self: stretch;
    }

    [class*="st-key-grp_"] a {
        width: 100% !important;
        height: 128px;
        box-sizing: border-box;
        display: flex !important;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 8px;
        border: none !important;
        border-radius: 6px;
        color: #fff !important;
        text-decoration: none !important;
        transition: filter .15s ease, transform .15s ease;
    }
    [class*="st-key-grp_"] a:hover { filter: brightness(1.12); transform: translateY(-2px); }
    [class*="st-key-grp_"] a p {
        color: #fff !important; font-size: 1.1rem; font-weight: 600; margin: 0;
    }
    [class*="st-key-grp_"] a [data-testid="stIconEmoji"],
    [class*="st-key-grp_"] a [data-testid="stIconMaterial"] {
        font-size: 2.6rem !important; line-height: 1;
    }
</style>
"""


# ==========================================================
# شاشة تسجيل الدخول
# ==========================================================
def render_login():
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)

    try:
        from keyboard_nav import enable_enter_navigation, add_enter_hint
        enable_enter_navigation()
        add_enter_hint()
    except Exception:
        pass

    st.markdown(
        """
        <h1 class="login-title">🔐 Techtoon Accounting</h1>
        <h4 class="login-sub">نظام المحاسبة المتكامل</h4>
        """,
        unsafe_allow_html=True,
    )

    db = SessionLocal()
    users_count = db.query(User).count()
    db.close()

    # ---------- نظام جديد: إنشاء المدير الأول ----------
    if users_count == 0:
        st.warning("⚠️ **نظام جديد** - لم يتم إنشاء أي مستخدمين بعد.")
        st.subheader("➕ إنشاء حساب المدير الأول")

        with st.form("create_first_admin_form", clear_on_submit=True):
            username = st.text_input("اسم المستخدم:", placeholder="admin")
            full_name = st.text_input("الاسم الكامل:", placeholder="المدير العام")
            email = st.text_input("البريد الإلكتروني (اختياري):", placeholder="admin@techtoon.com")
            password = st.text_input("كلمة المرور:", type="password", placeholder="6 أحرف على الأقل")
            confirm_password = st.text_input("تأكيد كلمة المرور:", type="password")
            submit_create = st.form_submit_button("إنشاء حساب المدير", type="primary", use_container_width=True)

        if submit_create:
            if not username or not password or not full_name:
                st.error("❌ يرجى ملء جميع الحقول المطلوبة")
            elif len(password) < 6:
                st.error("❌ كلمة المرور يجب أن تكون 6 أحرف على الأقل")
            elif password != confirm_password:
                st.error("❌ كلمتا المرور غير متطابقتين")
            else:
                db = SessionLocal()
                try:
                    db.add(User(
                        username=username,
                        password_hash=hash_password(password),
                        full_name=full_name,
                        email=email if email else None,
                        role=UserRole.ADMIN,
                        is_active=True,
                        created_at=datetime.now(),
                    ))
                    db.commit()
                    st.success("✅ تم إنشاء حساب المدير بنجاح!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    db.rollback()
                    st.error(f"❌ خطأ: {e}")
                finally:
                    db.close()
        return

    # ---------- تسجيل الدخول مع Rate Limiting ----------
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("اسم المستخدم:", placeholder="أدخل اسم المستخدم")
        password = st.text_input("كلمة المرور:", type="password", placeholder="أدخل كلمة المرور")
        submit_login = st.form_submit_button("🔓 دخول", type="primary", use_container_width=True)

    if submit_login:
        if not username or not username.strip():
            st.error("❌ يرجى إدخال اسم المستخدم")
        elif not password or not password.strip():
            st.error("❌ يرجى إدخال كلمة المرور")
        else:
            allowed, seconds = check_rate_limit(username)
            if not allowed:
                mins = seconds // 60
                secs = seconds % 60
                st.error(
                    f"🚫 تم تجاوز عدد المحاولات المسموحة. "
                    f"حاول مرة أخرى بعد **{mins} دقيقة {secs} ثانية**."
                )
            else:
                user_data, error = authenticate_user(username, password)
                if user_data:
                    clear_attempts(username)
                    login_user(user_data)
                    st.rerun()
                else:
                    record_failed_attempt(username)
                    remaining = get_remaining_attempts(username)
                    if 0 < remaining <= 2:
                        st.warning(f"⚠️ باقي {remaining} محاولة قبل الحظر.")
                    elif remaining == 0:
                        st.error("🚫 تم استنفاد المحاولات المسموحة. انتظر 15 دقيقة.")
                    st.error(f"❌ {error}")


# ==========================================================
# الصفحة الرئيسية: مربعات ملونة
# ==========================================================
def _balanced_rows(items, max_cols=MAX_PER_ROW):
    n = len(items)
    rows = -(-n // max_cols)
    base, extra = divmod(n, rows)
    result, i = [], 0
    for r in range(rows):
        size = base + (1 if r < extra else 0)
        result.append(items[i:i + size])
        i += size
    return result


def _grid_css(groups):
    prefixes = ["", ' > [data-testid="stVerticalBlock"]']
    rules = []
    color_i = 0
    for g, (_, items) in enumerate(groups):
        k = 1
        for row in _balanced_rows(items):
            span = GRID_COLS // len(row)
            for _ in row:
                color = PALETTE[color_i % len(PALETTE)]
                for p in prefixes:
                    base = f".st-key-grp_{g}{p} > *:nth-child({k})"
                    rules.append(f"{base} {{ grid-column: span {span}; }}")
                    rules.append(f"{base} a {{ background: {color} !important; }}")
                k += 1
                color_i += 1
    return "<style>" + "\n".join(rules) + "</style>"


def _tile(path, label, icon):
    try:
        st.page_link(path, label=label, icon=icon)
    except Exception:
        st.page_link(path, label=f"{icon} {label}")


def render_home(user):
    groups = visible_groups(user)
    st.markdown(HOME_CSS + _grid_css(groups), unsafe_allow_html=True)

    col_hero, col_search, col_out = st.columns([5, 1, 1])
    with col_hero:
        st.markdown(
            f"""
            <div class="hero">
                <div class="hero-logo">💼</div>
                <div>
                    <h1>Techtoon Accounting</h1>
                    <p>نظام المحاسبة المتكامل</p>
                    <small>👤 {user.get('full_name', '')} — {role_label(user)}</small>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_search:
        st.write("")
        # ✅ زر البحث الموحد السريع
        if st.button("🔍 بحث", use_container_width=True, key="home_global_search"):
            # ابحث عن صفحة البحث الموحد
            from pathlib import Path as _Path
            pages_dir = _Path(__file__).parent / "pages"
            for f in pages_dir.glob("*البحث_الموحد*.py"):
                st.switch_page(f"pages/{f.name}")
                break
            else:
                st.info("صفحة البحث غير موجودة.")
    with col_out:
        st.write("")
        if st.button("🚪 خروج", key="home_logout", use_container_width=True):
            logout_user()
            st.rerun()

    if not groups:
        st.info("لا توجد صفحات متاحة لحسابك. تواصل مع مدير النظام.")
        return

    for g, (group_name, items) in enumerate(groups):
        st.markdown(f'<div class="grp-title">{group_name}</div>', unsafe_allow_html=True)
        try:
            box = st.container(key=f"grp_{g}")
        except TypeError:
            box = st.container()
        with box:
            for label, icon, path, _ in items:
                _tile(path, label, icon)


# ==========================================================
# المسار الرئيسي
# ==========================================================
st.markdown(NO_SIDEBAR_CSS, unsafe_allow_html=True)

restore_session()
current = st.session_state.get("current_user")

if not current:
    render_login()
else:
    render_home(current)

# ⭐ إخفاء شريط Streamlit العلوي (لنافذة سطح المكتب)
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header[data-testid="stHeader"] {display: none;}
    .stDeployButton {display: none;}
    [data-testid="stToolbar"] {display: none;}
    [data-testid="stDecoration"] {display: none;}
    footer {visibility: hidden;}
    .block-container {padding-top: 1rem !important;}
</style>
""", unsafe_allow_html=True)


# ⭐⭐⭐ إخفاء كامل لعناصر Streamlit (نسخة 1.64+)
st.markdown("""
<style>
    /* ═══ شريط علوي ═══ */
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stDeployButton"] { display: none !important; }
    .stDeployButton { display: none !important; }
    #MainMenu { visibility: hidden !important; display: none !important; }

    /* ═══ القائمة الافتراضية (multipage nav) ═══ */
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="stSidebarNavItems"] { display: none !important; }
    [data-testid="stSidebarNavSeparator"] { display: none !important; }
    section[data-testid="stSidebar"] > div:first-child > div:first-child > div:first-child { display: none !important; }

    /* ═══ Footer + Badge ═══ */
    footer { display: none !important; visibility: hidden !important; }
    [data-testid="stBottom"] { display: none !important; }
    .viewerBadge_container__1QSob { display: none !important; }
    [class*="viewerBadge"] { display: none !important; }
    a[href*="streamlit.io"] { display: none !important; }

    /* ═══ تحسين المساحة ═══ */
    .block-container { padding-top: 1rem !important; }
    section.main > div { padding-top: 0.5rem !important; }
</style>
""", unsafe_allow_html=True)
