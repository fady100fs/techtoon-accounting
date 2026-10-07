"""
cache_helpers.py — طبقة Caching موحّدة
"""

import streamlit as st
import hashlib
from functools import wraps


# ============ إعدادات TTL موحّدة ============
class TTL:
    VERY_SHORT = 30       # بيانات تتغير كثيراً
    SHORT = 120           # قوائم منسدلة
    MEDIUM = 300          # تقارير
    LONG = 900            # إعدادات ثابتة
    VERY_LONG = 3600      # شجرة الحسابات، العملات


def make_key(*args, **kwargs) -> str:
    """توليد مفتاح فريد من الوسائط."""
    raw = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


# ============ Clear Cache Helpers ============
def clear_all_caches():
    """مسح كل الكاش."""
    st.cache_data.clear()
    st.cache_resource.clear()


def clear_cache_by_prefix(prefix: str):
    """مسح الكاش المرتبط بمفتاح معين (يستخدم فقط مع cache_data)."""
    # Streamlit لا يدعم المسح الجزئي، لذلك نمسح الكل بأمان
    st.cache_data.clear()


# ============ Decorator موحّد ============
def cached_data(ttl: int = TTL.MEDIUM, show_spinner: bool = False):
    """Decorator مبسّط لـ st.cache_data مع TTL موحّد."""
    def decorator(func):
        @st.cache_data(ttl=ttl, show_spinner=show_spinner)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============ دوال مساعدة شائعة ============

@st.cache_data(ttl=TTL.VERY_LONG, show_spinner=False)
def get_currencies_cached(_engine):
    """قائمة العملات — تكاد لا تتغير."""
    from sqlalchemy import text
    with _engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, code, name, symbol FROM currencies ORDER BY id"
        )).fetchall()
    return [dict(r._mapping) for r in rows]


@st.cache_data(ttl=TTL.LONG, show_spinner=False)
def get_accounts_tree_cached(_engine):
    """شجرة الحسابات — تتغير قليلاً."""
    from sqlalchemy import text
    with _engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, code, name, parent_id, account_type FROM accounts ORDER BY code"
        )).fetchall()
    return [dict(r._mapping) for r in rows]


@st.cache_data(ttl=TTL.SHORT, show_spinner=False)
def get_parties_cached(_engine, party_type: str = None):
    """العملاء أو الموردين."""
    from sqlalchemy import text
    with _engine.connect() as conn:
        if party_type:
            rows = conn.execute(text(
                "SELECT id, name, party_type FROM parties WHERE party_type=:t ORDER BY name"
            ), {"t": party_type}).fetchall()
        else:
            rows = conn.execute(text(
                "SELECT id, name, party_type FROM parties ORDER BY name"
            )).fetchall()
    return [dict(r._mapping) for r in rows]


@st.cache_data(ttl=TTL.SHORT, show_spinner=False)
def get_items_cached(_engine):
    """الأصناف."""
    from sqlalchemy import text
    with _engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, item_code, name, unit, sale_price FROM items ORDER BY name"
        )).fetchall()
    return [dict(r._mapping) for r in rows]


@st.cache_data(ttl=TTL.SHORT, show_spinner=False)
def get_cash_boxes_cached(_engine):
    """الخزائن."""
    from sqlalchemy import text
    with _engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, name, currency_id FROM cash_boxes ORDER BY name"
        )).fetchall()
    return [dict(r._mapping) for r in rows]


@st.cache_data(ttl=TTL.MEDIUM, show_spinner=False)
def get_dashboard_stats_cached(_engine, start_date: str, end_date: str):
    """إحصائيات لوحة التحكم."""
    from sqlalchemy import text
    with _engine.connect() as conn:
        stats = conn.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM invoices WHERE date BETWEEN :s AND :e) AS invoices_count,
                (SELECT COALESCE(SUM(total),0) FROM invoices WHERE date BETWEEN :s AND :e) AS invoices_total,
                (SELECT COUNT(*) FROM parties) AS parties_count,
                (SELECT COUNT(*) FROM items) AS items_count
        """), {"s": start_date, "e": end_date}).fetchone()
    return dict(stats._mapping) if stats else {}


# ============ معلومات الكاش (للتشخيص) ============
def show_cache_info():
    """عرض معلومات الكاش في الشريط الجانبي."""
    with st.sidebar.expander("🗂️ معلومات الكاش"):
        st.caption("استخدم هذا الزر عند تغيير البيانات:")
        if st.button("🔄 مسح الكاش بالكامل", use_container_width=True):
            clear_all_caches()
            st.success("✅ تم مسح الكاش")
            st.rerun()