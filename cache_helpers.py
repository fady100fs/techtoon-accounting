"""
cache_helpers.py — طبقة Caching موحّدة
الدوال تجلب engine داخلياً، ولا تحتاج تمريره من الصفحات.
"""

import streamlit as st
import hashlib
from functools import wraps


# ============ إعدادات TTL ============
class TTL:
    VERY_SHORT = 30
    SHORT = 120
    MEDIUM = 300
    LONG = 900
    VERY_LONG = 3600


def make_key(*args, **kwargs) -> str:
    raw = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


# ============ مسح الكاش ============
def clear_all_caches():
    st.cache_data.clear()
    st.cache_resource.clear()


def invalidate_all():
    clear_all_caches()


def invalidate(prefix: str = None):
    clear_all_caches()


def clear_cache_by_prefix(prefix: str):
    st.cache_data.clear()


def cached_data(ttl: int = TTL.MEDIUM, show_spinner: bool = False):
    def decorator(func):
        @st.cache_data(ttl=ttl, show_spinner=show_spinner)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============ محرك قاعدة البيانات الداخلي ============
def _get_engine():
    try:
        from database import engine
        return engine
    except Exception:
        return None


# ============ العملات ============
@st.cache_data(ttl=TTL.VERY_LONG, show_spinner=False)
def get_currencies_cached(_engine=None):
    from sqlalchemy import text
    engine = _engine or _get_engine()
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, code, name, symbol FROM currencies ORDER BY id"
            )).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception:
        return []


# ============ شجرة الحسابات ============
@st.cache_data(ttl=TTL.LONG, show_spinner=False)
def get_accounts_tree_cached(_engine=None):
    from sqlalchemy import text
    engine = _engine or _get_engine()
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, code, name, parent_id, type FROM accounts ORDER BY code"
            )).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception:
        return []


# ============ العملاء والموردين ============
@st.cache_data(ttl=TTL.SHORT, show_spinner=False)
def get_parties_cached(_engine=None, party_type: str = None):
    from sqlalchemy import text
    engine = _engine or _get_engine()
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            if party_type:
                rows = conn.execute(text(
                    "SELECT id, name, type, phone, address, credit_limit "
                    "FROM parties WHERE type=:t ORDER BY name"
                ), {"t": party_type}).fetchall()
            else:
                rows = conn.execute(text(
                    "SELECT id, name, type, phone, address, credit_limit "
                    "FROM parties ORDER BY name"
                )).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception:
        return []


# ============ الأصناف ============
@st.cache_data(ttl=TTL.SHORT, show_spinner=False)
def get_items_cached(_engine=None):
    from sqlalchemy import text
    engine = _engine or _get_engine()
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, barcode, name, cost_price, sell_price, "
                "min_stock, is_kit, category_id "
                "FROM items ORDER BY name"
            )).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception:
        return []


# ============ الخزائن ============
@st.cache_data(ttl=TTL.SHORT, show_spinner=False)
def get_cash_boxes_cached(_engine=None):
    from sqlalchemy import text
    engine = _engine or _get_engine()
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, name, code FROM cash_boxes "
                "WHERE is_active = true ORDER BY name"
            )).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception:
        try:
            with engine.connect() as conn:
                rows = conn.execute(text(
                    "SELECT id, name, code FROM cash_boxes ORDER BY name"
                )).fetchall()
            return [dict(r._mapping) for r in rows]
        except Exception:
            return []


# ============ التصنيفات النشطة ============
@st.cache_data(ttl=TTL.SHORT, show_spinner=False)
def get_active_categories(_engine=None):
    from sqlalchemy import text
    engine = _engine or _get_engine()
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, name FROM categories ORDER BY name"
            )).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception:
        return []


# ============ الأصناف مع المخزون ============
@st.cache_data(ttl=TTL.SHORT, show_spinner=False)
def get_items_with_stock(_engine=None):
    from sqlalchemy import text
    engine = _engine or _get_engine()
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT
                    it.id,
                    it.name,
                    it.barcode,
                    it.cost_price,
                    it.sell_price,
                    it.min_stock,
                    it.is_kit,
                    COALESCE(SUM(sl.quantity), 0) AS total_stock,
                    COALESCE(SUM(sl.quantity), 0) AS current_stock
                FROM items it
                LEFT JOIN stock_levels sl ON sl.item_id = it.id
                GROUP BY it.id, it.name, it.barcode, it.cost_price,
                         it.sell_price, it.min_stock, it.is_kit
                ORDER BY it.name
            """)).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception:
        try:
            with engine.connect() as conn:
                rows = conn.execute(text(
                    "SELECT id, name, barcode, cost_price, sell_price, "
                    "min_stock, is_kit, 0 AS total_stock, 0 AS current_stock "
                    "FROM items ORDER BY name"
                )).fetchall()
            return [dict(r._mapping) for r in rows]
        except Exception:
            return []


# ============ خريطة المخزون ============
@st.cache_data(ttl=TTL.SHORT, show_spinner=False)
def get_stock_map(_engine=None):
    from sqlalchemy import text
    engine = _engine or _get_engine()
    if engine is None:
        return {}
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT item_id, COALESCE(SUM(quantity), 0) AS qty
                FROM stock_levels
                GROUP BY item_id
            """)).fetchall()
        return {r.item_id: float(r.qty) for r in rows}
    except Exception:
        return {}


# ============ ملخّص المخزون ============
@st.cache_data(ttl=TTL.MEDIUM, show_spinner=False)
def get_inventory_summary(_engine=None):
    from sqlalchemy import text
    engine = _engine or _get_engine()
    result = {
        "total_items": 0,
        "total_value": 0.0,
        "low_stock_count": 0,
        "total_stock_qty": 0.0,
    }
    if engine is None:
        return result
    try:
        with engine.connect() as conn:
            try:
                result["total_items"] = conn.execute(
                    text("SELECT COUNT(*) FROM items")
                ).scalar() or 0
            except Exception:
                pass
            try:
                row = conn.execute(text("""
                    SELECT
                        COALESCE(SUM(sl.quantity * it.cost_price), 0) AS total_value,
                        COALESCE(SUM(sl.quantity), 0) AS total_qty
                    FROM stock_levels sl
                    JOIN items it ON it.id = sl.item_id
                """)).fetchone()
                if row:
                    result["total_value"] = float(row.total_value or 0)
                    result["total_stock_qty"] = float(row.total_qty or 0)
            except Exception:
                pass
    except Exception:
        pass
    return result


# ============ لوحة التحكم KPIs ============
@st.cache_data(ttl=TTL.MEDIUM, show_spinner=False)
def get_dashboard_kpis(_engine=None):
    from sqlalchemy import text
    engine = _engine or _get_engine()
    result = {
        "invoices_count": 0,
        "invoices_total": 0.0,
        "total_sales": 0.0,
        "total_purchases": 0.0,
        "monthly_sales": 0.0,
        "monthly_purchases": 0.0,
        "monthly_profit": 0.0,
        "parties_count": 0,
        "customers_count": 0,
        "suppliers_count": 0,
        "items_count": 0,
        "payments_total": 0.0,
        "expenses_total": 0.0,
        "cash_balance": 0.0,
        "low_stock_count": 0,
        "profit": 0.0,
        "net_profit": 0.0,
    }
    if engine is None:
        return result
    try:
        with engine.connect() as conn:
            # أعداد
            for key, query in [
                ("invoices_count", "SELECT COUNT(*) FROM invoices"),
                ("parties_count", "SELECT COUNT(*) FROM parties"),
                ("customers_count", "SELECT COUNT(*) FROM parties WHERE type='customer'"),
                ("suppliers_count", "SELECT COUNT(*) FROM parties WHERE type='supplier'"),
                ("items_count", "SELECT COUNT(*) FROM items"),
            ]:
                try:
                    result[key] = conn.execute(text(query)).scalar() or 0
                except Exception:
                    pass

            # إجماليات
            for key, query in [
                ("invoices_total", "SELECT COALESCE(SUM(net_amount), 0) FROM invoices"),
                ("total_sales", "SELECT COALESCE(SUM(net_amount), 0) FROM invoices WHERE type='sale'"),
                ("total_purchases", "SELECT COALESCE(SUM(net_amount), 0) FROM invoices WHERE type='purchase'"),
                ("payments_total", "SELECT COALESCE(SUM(amount), 0) FROM payments"),
                ("expenses_total", "SELECT COALESCE(SUM(amount), 0) FROM expenses"),
            ]:
                try:
                    result[key] = float(conn.execute(text(query)).scalar() or 0)
                except Exception:
                    pass

            # مبيعات ومشتريات الشهر
            try:
                result["monthly_sales"] = float(conn.execute(text("""
                    SELECT COALESCE(SUM(net_amount), 0) FROM invoices
                    WHERE type='sale'
                    AND date >= DATE_TRUNC('month', CURRENT_DATE)
                """)).scalar() or 0)
            except Exception:
                pass

            try:
                result["monthly_purchases"] = float(conn.execute(text("""
                    SELECT COALESCE(SUM(net_amount), 0) FROM invoices
                    WHERE type='purchase'
                    AND date >= DATE_TRUNC('month', CURRENT_DATE)
                """)).scalar() or 0)
            except Exception:
                pass

            # الربح
            result["profit"] = result["total_sales"] - result["expenses_total"]
            result["net_profit"] = result["profit"]
            result["monthly_profit"] = result["monthly_sales"]
    except Exception:
        pass
    return result


# ============ توافق خلفي ============
@st.cache_data(ttl=TTL.MEDIUM, show_spinner=False)
def get_dashboard_stats_cached(_engine=None, start_date: str = None, end_date: str = None):
    return get_dashboard_kpis(_engine)


# ============ فهرس الفواتير ============
@st.cache_data(ttl=TTL.SHORT, show_spinner=False)
def get_invoices_index(_engine=None, limit: int = 500):
    from sqlalchemy import text
    engine = _engine or _get_engine()
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT
                    i.id,
                    i.invoice_number,
                    i.date,
                    i.type,
                    i.net_amount,
                    i.total_amount,
                    i.discount_amount,
                    i.tax_amount,
                    i.status,
                    i.party_id,
                    i.created_by,
                    i.currency_id,
                    p.name AS party_name,
                    p.type AS party_type,
                    u.full_name AS created_by_name,
                    u.username AS created_by_username,
                    c.symbol AS currency_symbol,
                    c.code AS currency_code
                FROM invoices i
                LEFT JOIN parties p ON p.id = i.party_id
                LEFT JOIN users u ON u.id = i.created_by
                LEFT JOIN currencies c ON c.id = i.currency_id
                ORDER BY i.date DESC NULLS LAST, i.id DESC
                LIMIT :lim
            """), {"lim": limit}).fetchall()

            results = []
            for r in rows:
                d = dict(r._mapping)
                try:
                    paid = conn.execute(text("""
                        SELECT COALESCE(SUM(amount), 0) FROM payments
                        WHERE reference_number = :ref AND party_id = :pid
                    """), {
                        "ref": d.get("invoice_number"),
                        "pid": d.get("party_id"),
                    }).scalar() or 0
                    d["paid_amount"] = float(paid)
                except Exception:
                    d["paid_amount"] = 0.0

                net = float(d.get("net_amount") or 0)
                d["remaining"] = max(0.0, net - d["paid_amount"])
                d.setdefault("created_by_name", "—")
                d.setdefault("created_by_username", "—")
                d.setdefault("currency_symbol", "ج.م")
                d.setdefault("currency_code", "EGP")
                results.append(d)
            return results
    except Exception:
        # fallback بدون joins
        try:
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT
                        i.id, i.invoice_number, i.date, i.type,
                        i.net_amount, i.total_amount, i.discount_amount,
                        i.tax_amount, i.status, i.party_id, i.created_by,
                        i.currency_id,
                        p.name AS party_name, p.type AS party_type,
                        '—' AS created_by_name, '—' AS created_by_username,
                        'ج.م' AS currency_symbol, 'EGP' AS currency_code
                    FROM invoices i
                    LEFT JOIN parties p ON p.id = i.party_id
                    ORDER BY i.date DESC NULLS LAST, i.id DESC
                    LIMIT :lim
                """), {"lim": limit}).fetchall()
                results = []
                for r in rows:
                    d = dict(r._mapping)
                    d["paid_amount"] = 0.0
                    d["remaining"] = max(0.0, float(d.get("net_amount") or 0))
                    results.append(d)
                return results
        except Exception:
            return []


# ============ فهرس المدفوعات ============
@st.cache_data(ttl=TTL.SHORT, show_spinner=False)
def get_payments_index(_engine=None, limit: int = 500):
    from sqlalchemy import text
    engine = _engine or _get_engine()
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT
                    pay.id,
                    pay.date,
                    pay.amount,
                    pay.payment_type,
                    pay.payment_method,
                    pay.reference_number,
                    pay.notes,
                    pay.party_id,
                    pay.cash_box_id,
                    pay.currency_id,
                    p.name AS party_name,
                    cb.name AS cash_box_name,
                    u.full_name AS created_by_name,
                    c.symbol AS currency_symbol,
                    c.code AS currency_code
                FROM payments pay
                LEFT JOIN parties p ON p.id = pay.party_id
                LEFT JOIN cash_boxes cb ON cb.id = pay.cash_box_id
                LEFT JOIN users u ON u.id = pay.created_by
                LEFT JOIN currencies c ON c.id = pay.currency_id
                ORDER BY pay.date DESC NULLS LAST, pay.id DESC
                LIMIT :lim
            """), {"lim": limit}).fetchall()

            results = []
            for r in rows:
                d = dict(r._mapping)
                d.setdefault("cash_box_name", "—")
                d.setdefault("created_by_name", "—")
                d.setdefault("currency_symbol", "ج.م")
                d.setdefault("currency_code", "EGP")
                results.append(d)
            return results
    except Exception:
        try:
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT
                        pay.id, pay.date, pay.amount, pay.payment_type,
                        pay.payment_method, pay.reference_number, pay.notes,
                        pay.party_id, pay.cash_box_id, pay.currency_id,
                        p.name AS party_name,
                        '—' AS cash_box_name, '—' AS created_by_name,
                        'ج.م' AS currency_symbol, 'EGP' AS currency_code
                    FROM payments pay
                    LEFT JOIN parties p ON p.id = pay.party_id
                    ORDER BY pay.date DESC NULLS LAST, pay.id DESC
                    LIMIT :lim
                """), {"lim": limit}).fetchall()
            return [dict(r._mapping) for r in rows]
        except Exception:
            return []


# ============ معلومات الكاش ============
def show_cache_info():
    with st.sidebar.expander("🗂️ معلومات الكاش"):
        st.caption("استخدم هذا الزر عند تغيير البيانات:")
        if st.button("🔄 مسح الكاش", use_container_width=True, key="cache_clear_btn"):
            clear_all_caches()
            st.success("✅ تم مسح الكاش")
            st.rerun()