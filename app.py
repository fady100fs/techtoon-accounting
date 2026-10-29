<<<<<<< HEAD
import streamlit as st
import database as db
from datetime import datetime, date

st.set_page_config(
    page_title="Techtoon Accounting",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"

def login_page():
    st.markdown("""
    <style>
    .main > div {padding-top: 2rem;}
    .stButton > button {width: 100%; border-radius: 8px; border: none; padding: 12px;}
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("## 📊 Techtoon Accounting")
        st.markdown("### نظام المحاسبة - تسجيل الدخول")
        st.markdown("---")
        
        username = st.text_input("اسم المستخدم", placeholder="أدخل اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password", placeholder="أدخل كلمة المرور")
        
        if st.button("🔐 تسجيل الدخول", use_container_width=True):
            if username and password:
                try:
                    cols, rows = db.execute_query(
                        "SELECT id, username, full_name, role, is_active, password_hash FROM users WHERE username=%s AND is_active=TRUE",
                        (username,), fetch=True
                    )
                    if rows:
                        user_data = rows[0]
                        if db.verify_password(password, user_data[5]):
                            st.session_state.user = {
                                "id": user_data[0],
                                "username": user_data[1],
                                "full_name": user_data[2],
                                "role": user_data[3]
                            }
                            st.rerun()
                        else:
                            st.error("❌ كلمة المرور غير صحيحة")
                    else:
                        st.error("❌ المستخدم غير موجود أو معطل")
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
            else:
                st.warning("⚠️ أدخل اسم المستخدم وكلمة المرور")

def dashboard():
    st.title("📊 لوحة التحكم")
    
    try:
        cols, rows = db.execute_query(
            "SELECT COALESCE(SUM(total),0), COUNT(*) FROM invoices WHERE type=%s AND DATE(date)=CURRENT_DATE",
            ("sales",), fetch=True
        )
        today_sales = float(rows[0][0]) if rows else 0
        today_count = rows[0][1] if rows else 0
        
        cols2, rows2 = db.execute_query(
            "SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_type=%s AND DATE(date)=CURRENT_DATE",
            ("receipt",), fetch=True
        )
        collections = float(rows2[0][0]) if rows2 else 0
        
        cols3, rows3 = db.execute_query(
            "SELECT COALESCE(SUM(total-paid_amount),0) FROM invoices WHERE type=%s AND paid_amount<total AND status<>%s",
            ("sales", "cancelled"), fetch=True
        )
        receivables = float(rows3[0][0]) if rows3 else 0
        
        cols4, rows4 = db.execute_query(
            "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE DATE(date)=CURRENT_DATE",
            (), fetch=True
        )
        expenses = float(rows4[0][0]) if rows4 else 0
        
        cols5, rows5 = db.execute_query(
            "SELECT COALESCE(SUM(opening_quantity * COALESCE(avg_cost_price, cost_price, 0)),0) FROM items WHERE is_kit IS NOT TRUE",
            (), fetch=True
        )
        stock_value = float(rows5[0][0]) if rows5 else 0
        
        cols6, rows6 = db.execute_query(
            "SELECT COUNT(*) FROM items WHERE is_active=TRUE AND is_kit IS NOT TRUE AND min_stock IS NOT NULL AND min_stock > 0 AND (opening_quantity + COALESCE((SELECT SUM(CASE WHEN type IN ('in','opening') THEN quantity WHEN type='out' THEN -quantity WHEN type='adjustment' THEN quantity ELSE 0 END) FROM inventory_movements WHERE item_id=items.id),0)) <= min_stock",
            (), fetch=True
        )
        low_stock_count = rows6[0][0] if rows6 else 0
        
        cols7, rows7 = db.execute_query(
            "SELECT COUNT(*) FROM invoices WHERE type=%s AND status<>%s AND due_date IS NOT NULL AND due_date < CURRENT_DATE AND paid_amount < total",
            ("sales", "cancelled"), fetch=True
        )
        overdue_count = rows7[0][0] if rows7 else 0
        
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {e}")
        today_sales = today_count = collections = receivables = expenses = stock_value = low_stock_count = overdue_count = 0
    
    if low_stock_count > 0:
        st.warning(f"⚠️ تنبيه: {low_stock_count} صنف بالحد الأدنى للمخزون")
    if overdue_count > 0:
        st.error(f"🔔 تنبيه: {overdue_count} فاتورة متأخرة السداد")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 مبيعات اليوم", f"{today_sales:,.2f}", f"{today_count} فاتورة")
        st.metric("💵 التحصيلات", f"{collections:,.2f}", "اليوم")
    
    with col2:
        st.metric("💳 ديون العملاء", f"{receivables:,.2f}", "مستحقة")
        st.metric("💸 مصروفات اليوم", f"{expenses:,.2f}", "مصروف")
    
    with col3:
        st.metric("📦 قيمة المخزون", f"{stock_value:,.2f}", "تكلفة")
        st.metric("⚠️ مخزون منخفض", f"{low_stock_count} صنف")
    
    with col4:
        st.metric("🔔 فواتير متأخرة", f"{overdue_count}", "فاتورة")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏆 أفضل الأصناف مبيعاً")
        try:
            cols, rows = db.execute_query(
                "SELECT i.name, SUM(il.quantity) as qty, SUM(il.total) as total "
                "FROM invoice_lines il "
                "JOIN invoices inv ON il.invoice_id=inv.id "
                "JOIN items i ON il.item_id=i.id "
                "WHERE inv.type=%s AND inv.date >= CURRENT_DATE - INTERVAL '30 days' "
                "GROUP BY i.name ORDER BY total DESC LIMIT 5",
                ("sales",), fetch=True
            )
            if rows:
                import pandas as pd
                df = pd.DataFrame(rows, columns=["الصنف", "الكمية", "الإجمالي"])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد مبيعات في آخر 30 يوم")
        except:
            st.info("لا توجد بيانات")
    
    with col2:
        st.markdown("### 📋 آخر الفواتير")
        try:
            cols, rows = db.execute_query(
                "SELECT i.invoice_number, i.date, i.type, COALESCE(p.name,''), i.total, i.status "
                "FROM invoices i LEFT JOIN parties p ON i.party_id=p.id "
                "ORDER BY i.date DESC LIMIT 5",
                (), fetch=True
            )
            if rows:
                import pandas as pd
                df = pd.DataFrame(rows, columns=["رقم", "التاريخ", "النوع", "العميل", "الإجمالي", "الحالة"])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد فواتير")
        except:
            st.info("لا توجد بيانات")

if st.session_state.user is None:
    login_page()
else:
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['full_name']}")
        st.caption(f"الدور: {st.session_state.user['role']}")
        st.markdown("---")
        
        pages = {
            "dashboard": "📊 لوحة التحكم",
            "invoices": "🛒 الفواتير",
            "items": "📦 الأصناف",
            "parties": "👥 العملاء والموردين",
            "payments": "💰 المدفوعات",
            "stock_levels": "📦 أرصدة المخزون",
            "stock_counts": "📋 جلسات الجرد",
            "stock_adjustments": "⚖️ تسويات المخزون",
            "damaged_items": "💣 الأصناف التالفة",
            "writeoff_requests": "🗑️ طلبات الشطب",
            "reports": "📈 التقارير",
        }
        
        for key, label in pages.items():
            if st.button(label, use_container_width=True, key=f"nav_{key}"):
                st.session_state.current_page = key
                st.rerun()
        
        st.markdown("---")
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    
    page = st.session_state.current_page
    
    if page == "dashboard":
        dashboard()
    elif page == "invoices":
        import pages.invoices as inv
        inv.show()
    elif page == "items":
        import pages.items as itm
        itm.show()
    elif page == "parties":
        import pages.parties as prt
        prt.show()
    elif page == "payments":
        import pages.payments as pmt
        pmt.show()
    elif page == "stock_levels":
        import pages.stock_levels as sl
        sl.show()
    elif page == "stock_counts":
        import pages.stock_counts as sc
        sc.show()
    elif page == "stock_adjustments":
        import pages.stock_adjustments as sa
        sa.show()
    elif page == "damaged_items":
        import pages.damaged_items as di
        di.show()
    elif page == "writeoff_requests":
        import pages.writeoff_requests as wr
        wr.show()
    elif page == "reports":
        import pages.reports as rep
        rep.show()
=======
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


# === تحسينات الواجهة ===

try:
    from ui_enhancements import render_enhancements
    render_enhancements()
except Exception:
    pass

try:
    from quick_stats import render_quick_stats
    render_quick_stats()
except Exception:
    pass

try:
    from smart_alerts import render_smart_alerts
    render_smart_alerts()
except Exception:
    pass

try:
    from theme_toggle import render_theme_toggle
    render_theme_toggle()
except Exception:
    pass

try:
    from print_styles import render_print_styles
    render_print_styles()
except Exception:
    pass

try:
    from keyboard_nav import enable_enter_navigation, add_enter_hint
    enable_enter_navigation()
    add_enter_hint()
except Exception:
    pass


# Pre-warm cache at startup
try:
    import threading
    def _prewarm_cache():
        try:
            from cache_helpers import get_dashboard_kpis, get_invoices_index, get_items_with_stock, get_stock_map, get_active_categories
            get_dashboard_kpis()
            get_invoices_index()
            get_items_with_stock()
            get_stock_map()
            get_active_categories()
        except Exception:
            pass
    threading.Thread(target=_prewarm_cache, daemon=True).start()
except Exception:
    pass


# ⭐ مزامنة سريعة عند بدء التشغيل — تسحب أحدث البيانات من Neon
try:
    import os as _os
    if _os.getenv("DEPLOY_MODE", "cloud").lower() == "local":
        from sync_manager import quick_sync
        import threading
        def _startup_sync():
            try:
                quick_sync()
            except Exception:
                pass
        threading.Thread(target=_startup_sync, daemon=True).start()
except Exception:
    pass


# Preload
try:
    from cache_helpers import preload_cache
    preload_cache()
except Exception:
    pass


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

    # ⭐ اختصارات سريعة بمربعات ملونة
    
    # ⭐ اختصارات سريعة بمربعات ملونة (تعمل داخل webview)
    st.markdown(
        "<style>"
        "height: 80px !important; border-radius: 10px !important; border: none !important;"
        "color: white !important; font-size: 14px !important; font-weight: 600 !important;"
        "display: flex !important; flex-direction: column !important;"
        "align-items: center !important; justify-content: center !important; gap: 4px !important;"
        "}"
        "color: white !important; font-size: 14px !important; font-weight: 600 !important;"
        "}"
        "font-size: 1.6rem !important;"
        "}"
        "</style>",
        unsafe_allow_html=True,
    )

    _qc1, _qc2, _qc3, _qc4 = st.columns(4)
    with _qc1:
        st.page_link("pages/4A_🛒_فواتير_البيع.py", label="🛒 فاتورة بيع")
    with _qc2:
        st.page_link("pages/4B_🛍️_فواتير_الشراء.py", label="🛍️ فاتورة شراء")
    with _qc3:
        st.page_link("pages/41_📥_سند_قبض.py", label="📥 سند قبض")
    with _qc4:
        st.page_link("pages/42_📤_سند_صرف.py", label="📤 سند صرف")

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



>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
