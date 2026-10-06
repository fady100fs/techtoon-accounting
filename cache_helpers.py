# cache_helpers.py
# طبقة Caching مركزية — محدّثة لدعم N+1 fixes و pagination
import streamlit as st
from datetime import datetime
from database import SessionLocal
import models
from sqlalchemy import func, case


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
# 2) Cache للتصنيفات
# ==========================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_active_categories():
    """التصنيفات النشطة — قائمة (id, name)."""
    db = SessionLocal()
    try:
        rows = db.query(models.Category).filter(
            models.Category.is_active == True
        ).order_by(models.Category.name).all()
        return [(c.id, c.name) for c in rows]
    finally:
        db.close()


# ==========================================================
# 3) Cache لقوائم الأصناف
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
                "category_id": it.category_id,
                "min_stock": float(it.min_stock or 0),
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
        return [(p.id, p.name) for p in q.order_by(models.Party.name).all()]
    finally:
        db.close()


# ==========================================================
# 5) Cache للـ KPIs — استعلام واحد مُجمَّع
# ==========================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_dashboard_kpis():
    """مؤشرات الأداء الرئيسية."""
    db = SessionLocal()
    try:
        today = datetime.now()
        month_start = today.replace(day=1)

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
# 6) stock_map — استعلام SQL واحد (بدل N استعلام)
# ==========================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_stock_map():
    """خريطة أرصدة كل الأصناف — استعلام واحد باستخدام CASE."""
    db = SessionLocal()
    try:
        rows = db.query(
            models.InventoryMovement.item_id,
            func.sum(
                case(
                    (models.InventoryMovement.type == 'in',
                     models.InventoryMovement.quantity),
                    else_=-models.InventoryMovement.quantity
                )
            ).label('balance')
        ).group_by(models.InventoryMovement.item_id).all()

        return {item_id: float(balance or 0) for item_id, balance in rows}
    finally:
        db.close()


# ==========================================================
# 7) ملخص المخزون
# ==========================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_inventory_summary():
    """ملخص المخزون: عدد الأصناف، عدد تحت الحد، القيمة."""
    db = SessionLocal()
    try:
        items = db.query(models.Item).filter(models.Item.is_kit == False).all()

        # نستخدم نسخة داخلية (بدون cache layer)
        rows = db.query(
            models.InventoryMovement.item_id,
            func.sum(
                case(
                    (models.InventoryMovement.type == 'in',
                     models.InventoryMovement.quantity),
                    else_=-models.InventoryMovement.quantity
                )
            ).label('balance')
        ).group_by(models.InventoryMovement.item_id).all()
        stock_map = {iid: float(b or 0) for iid, b in rows}

        total_items = len(items)
        low_stock_count = 0
        total_value = 0.0
        for item in items:
            balance = stock_map.get(item.id, 0.0)
            if balance <= (item.min_stock or 0):
                low_stock_count += 1
            total_value += balance * float(item.cost_price or 0)

        return {
            "total_items": total_items,
            "low_stock_count": low_stock_count,
            "good_stock_count": total_items - low_stock_count,
            "total_value": total_value,
        }
    finally:
        db.close()


# ==========================================================
# 8) كل الأصناف + الرصيد + التصنيف — استعلامان فقط
# ==========================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_items_with_stock():
    """كل الأصناف مع الرصيد والتصنيف — لصفحة التقارير والأصناف."""
    db = SessionLocal()
    try:
        items = db.query(models.Item).order_by(models.Item.name).all()
        categories = {c.id: c.name for c in db.query(models.Category).all()}

        rows = db.query(
            models.InventoryMovement.item_id,
            func.sum(
                case(
                    (models.InventoryMovement.type == 'in',
                     models.InventoryMovement.quantity),
                    else_=-models.InventoryMovement.quantity
                )
            ).label('balance')
        ).group_by(models.InventoryMovement.item_id).all()
        stock_map = {iid: float(b or 0) for iid, b in rows}

        return [
            {
                "id": it.id,
                "name": it.name,
                "barcode": it.barcode or "",
                "cost_price": float(it.cost_price or 0),
                "sell_price": float(it.sell_price or 0),
                "is_kit": bool(it.is_kit),
                "min_stock": float(it.min_stock or 0),
                "category_name": categories.get(it.category_id, ""),
                "category_id": it.category_id,
                "current_stock": stock_map.get(it.id, 0.0),
            }
            for it in items
        ]
    finally:
        db.close()


# ==========================================================
# 9) فهرس الفواتير — استعلامات مجمّعة (بدل N+1)
# ==========================================================
@st.cache_data(ttl=30, show_spinner=False)
def get_invoices_index(limit=500):
    """فهرس الفواتير مع بياناتها — بدون N+1."""
    db = SessionLocal()
    try:
        invoices = db.query(models.Invoice).order_by(
            models.Invoice.date.desc()
        ).limit(limit).all()

        if not invoices:
            return []

        party_ids = list({inv.party_id for inv in invoices if inv.party_id})
        creator_ids = list({inv.created_by for inv in invoices if inv.created_by})
        invoice_numbers = [inv.invoice_number for inv in invoices]

        parties = {}
        if party_ids:
            parties = {p.id: p.name for p in db.query(models.Party).filter(
                models.Party.id.in_(party_ids)
            ).all()}

        users = {}
        if creator_ids:
            users = {u.id: u.full_name for u in db.query(models.User).filter(
                models.User.id.in_(creator_ids)
            ).all()}

        # مجموع المدفوعات لكل فاتورة — استعلام واحد
        payments_agg = db.query(
            models.Payment.reference_number,
            func.sum(models.Payment.amount).label('total')
        ).filter(
            models.Payment.reference_number.in_(invoice_numbers)
        ).group_by(models.Payment.reference_number).all()
        paid_by_ref = {ref: float(total or 0) for ref, total in payments_agg}

        return [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "date": inv.date,
                "type": inv.type,
                "party_id": inv.party_id,
                "party_name": parties.get(inv.party_id, "غير محدد"),
                "net_amount": float(inv.net_amount or 0),
                "paid_amount": paid_by_ref.get(inv.invoice_number, 0.0),
                "remaining": float(inv.net_amount or 0) - paid_by_ref.get(inv.invoice_number, 0.0),
                "status": inv.status,
                "created_by": inv.created_by,
                "created_by_name": users.get(inv.created_by, "النظام"),
                "currency_id": inv.currency_id,
            }
            for inv in invoices
        ]
    finally:
        db.close()


# ==========================================================
# 10) فهرس المدفوعات
# ==========================================================
@st.cache_data(ttl=30, show_spinner=False)
def get_payments_index(limit=500):
    """فهرس المدفوعات مع بياناتها."""
    db = SessionLocal()
    try:
        payments = db.query(models.Payment).order_by(
            models.Payment.date.desc()
        ).limit(limit).all()

        if not payments:
            return []

        party_ids = list({p.party_id for p in payments if p.party_id})
        currency_ids = list({p.currency_id for p in payments if p.currency_id})
        cash_box_ids = list({p.cash_box_id for p in payments if p.cash_box_id})

        parties = {}
        if party_ids:
            parties = {p.id: p.name for p in db.query(models.Party).filter(
                models.Party.id.in_(party_ids)
            ).all()}

        currencies = {}
        if currency_ids:
            currencies = {c.id: c.symbol for c in db.query(models.Currency).filter(
                models.Currency.id.in_(currency_ids)
            ).all()}

        cash_boxes = {}
        if cash_box_ids:
            cash_boxes = {b.id: b.name for b in db.query(models.CashBox).filter(
                models.CashBox.id.in_(cash_box_ids)
            ).all()}

        return [
            {
                "id": p.id,
                "date": p.date,
                "party_id": p.party_id,
                "party_name": parties.get(p.party_id, "غير محدد"),
                "amount": float(p.amount or 0),
                "payment_type": p.payment_type,
                "payment_method": p.payment_method,
                "reference_number": p.reference_number or "",
                "notes": p.notes or "",
                "currency_id": p.currency_id,
                "currency_symbol": currencies.get(p.currency_id, "ج.م"),
                "cash_box_id": p.cash_box_id,
                "cash_box_name": cash_boxes.get(p.cash_box_id, "-"),
            }
            for p in payments
        ]
    finally:
        db.close()


# ==========================================================
# 11) Invalidation — استدعِ بعد أي كتابة
# ==========================================================
def invalidate_all():
    """مسح شامل — استدعِ بعد الحفظ/التعديل/الحذف."""
    st.cache_data.clear()


def invalidate(*keys):
    """مسح cache محدد. حالياً يمسح الكل (Streamlit لا يدعم الجزئي)."""
    st.cache_data.clear()