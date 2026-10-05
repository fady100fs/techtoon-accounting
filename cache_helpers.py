# cache_helpers.py
# طبقة Caching مركزية — تُستخدم في كل الصفحات
# الهدف: تقليل عدد الاستعلامات لـ Neon بشكل كبير
import streamlit as st
from datetime import datetime
from database import SessionLocal
import models
from sqlalchemy import func


# ==========================================================
# 1) Cache للمستخدم الحالي
# ==========================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_user_count():
    """عدد المستخدمين — يتحدث كل 5 دقايق."""
    db = SessionLocal()
    try:
        return db.query(models.User).count()
    finally:
        db.close()


# ==========================================================
# 2) Cache للتصنيفات (نادراً ما تتغير)
# ==========================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_active_categories():
    """التصنيفات النشطة — استعلام واحد."""
    db = SessionLocal()
    try:
        rows = db.query(models.Category).filter(
            models.Category.is_active == True
        ).all()
        return [(c.id, c.name) for c in rows]
    finally:
        db.close()


# ==========================================================
# 3) Cache لقوائم الأصناف (تُستخدم في الفواتير)
# ==========================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_items_for_picker():
    """كل الأصناف — للاختيار في الفواتير."""
    db = SessionLocal()
    try:
        rows = db.query(models.Item).all()
        return [
            {
                "id": it.id,
                "name": it.name,
                "barcode": it.barcode,
                "sell_price": float(it.sell_price or 0),
                "cost_price": float(it.cost_price or 0),
                "is_kit": bool(it.is_kit),
            }
            for it in rows
        ]
    finally:
        db.close()


# ==========================================================
# 4) Cache لقوائم العملاء/الموردين
# ==========================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_parties(party_type=None):
    """قائمة العملاء أو الموردين."""
    db = SessionLocal()
    try:
        q = db.query(models.Party)
        if party_type:
            q = q.filter(models.Party.type == party_type)
        return [(p.id, p.name) for p in q.all()]
    finally:
        db.close()


# ==========================================================
# 5) Cache للـ KPIs (Dashboard)
# ==========================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_dashboard_kpis():
    """مؤشرات الأداء الرئيسية — استعلام واحد مُجمَّع."""
    db = SessionLocal()
    try:
        today = datetime.now()
        month_start = today.replace(day=1)

        # استعلام واحد لكل الإحصائيات
        total_sales = db.query(func.sum(models.Invoice.net_amount)).filter(
            models.Invoice.type == 'sale',
            models.Invoice.status != 'cancelled'
        ).scalar() or 0.0

        monthly_sales = db.query(func.sum(models.Invoice.net_amount)).filter(
            models.Invoice.type == 'sale',
            models.Invoice.status != 'cancelled',
            models.Invoice.date >= month_start
        ).scalar() or 0.0

        total_expenses = db.query(func.sum(models.Expense.amount)).scalar() or 0.0

        total_invoices = db.query(models.Invoice).filter(
            models.Invoice.status != 'cancelled'
        ).count()

        total_customers = db.query(models.Party).filter(
            models.Party.type == 'customer'
        ).count()

        return {
            "total_sales": float(total_sales),
            "monthly_sales": float(monthly_sales),
            "total_expenses": float(total_expenses),
            "total_invoices": int(total_invoices),
            "total_customers": int(total_customers),
        }
    finally:
        db.close()


# ==========================================================
# 6) Cache لـ stock map (يُستخدم في الأصناف)
# ==========================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_stock_map():
    """خريطة أرصدة كل الأصناف — استعلام واحد."""
    db = SessionLocal()
    try:
        rows = db.query(
            models.InventoryMovement.item_id,
            models.InventoryMovement.type,
            models.InventoryMovement.quantity,
        ).all()
        stock_map = {}
        for iid, mtype, qty in rows:
            q = float(qty or 0)
            stock_map[iid] = stock_map.get(iid, 0.0) + (q if mtype == 'in' else -q)
        return stock_map
    finally:
        db.close()


# ==========================================================
# 7) دالة لمسح الـ Cache يدويًا
# ==========================================================
def invalidate_all():
    """يُستدعى بعد أي عملية كتابة (حفظ/تعديل/حذف)."""
    st.cache_data.clear()