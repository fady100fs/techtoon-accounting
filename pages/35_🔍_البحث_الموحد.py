# pages/35_🔍_البحث_الموحد.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from database import SessionLocal
import models
from models import (
    Party, Item, Invoice, Payment, Expense, JournalEntry, CashBox,
    Category, ExpenseCategory,
)
from services import movement_serial
from auth_required import require_login, get_current_user_name

current_user = require_login()
current_user_name = get_current_user_name()

st.set_page_config(page_title="البحث الموحد", page_icon="🔍", layout="wide")
st.title("🔍 البحث الموحد في النظام")
st.info(f"👤 المستخدم: **{current_user_name}**")

st.markdown("""
**ابحث في كل شيء من مكان واحد:**
- 👥 العملاء والموردين
- 📦 الأصناف
- 🧾 الفواتير
- 💰 المدفوعات
- 💸 المصروفات
- 📝 القيود اليومية
""")

# ==========================================
# شريط البحث
# ==========================================
col_q, col_btn = st.columns([4, 1])
with col_q:
    query = st.text_input(
        "🔍 ابحث عن أي شيء...",
        placeholder="اسم عميل، باركود، رقم فاتورة، رقم مسلسل، مبلغ...",
        key="gs_query",
    )
with col_btn:
    st.write("")
    search_clicked = st.button("🔍 ابحث", type="primary", use_container_width=True)

st.markdown("---")

# ==========================================
# خيارات البحث المتقدم
# ==========================================
with st.expander("⚙️ خيارات البحث المتقدم", expanded=False):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        search_party = st.checkbox("العملاء والموردين", value=True, key="gs_party")
        search_items = st.checkbox("الأصناف", value=True, key="gs_items")
    with col_b:
        search_invoices = st.checkbox("الفواتير", value=True, key="gs_invoices")
        search_payments = st.checkbox("المدفوعات", value=True, key="gs_payments")
    with col_c:
        search_expenses = st.checkbox("المصروفات", value=True, key="gs_expenses")
        search_entries = st.checkbox("القيود اليومية", value=True, key="gs_entries")

db = SessionLocal()


# ==========================================
# دوال البحث
# ==========================================
def search_parties(q):
    """البحث في العملاء والموردين."""
    q_like = f"%{q}%"
    results = db.query(Party).filter(
        (Party.name.ilike(q_like)) |
        (Party.phone.ilike(q_like)) |
        (Party.address.ilike(q_like))
    ).limit(20).all()

    return [
        {
            "النوع": "عميل" if p.type == 'customer' else "مورد",
            "الاسم": p.name,
            "الهاتف": p.phone or "—",
            "العنوان": p.address or "—",
            "ID": p.id,
            "_action": f"👥 {p.name}",
        }
        for p in results
    ]


def search_items(q):
    """البحث في الأصناف."""
    q_like = f"%{q}%"
    results = db.query(Item).filter(
        (Item.name.ilike(q_like)) |
        (Item.barcode.ilike(q_like))
    ).limit(20).all()

    # خريطة التصنيفات
    cat_ids = list({r.category_id for r in results if r.category_id})
    cats_map = {}
    if cat_ids:
        cats_map = {
            c.id: c.name for c in db.query(Category).filter(
                Category.id.in_(cat_ids)
            ).all()
        }

    return [
        {
            "الاسم": it.name,
            "الباركود": it.barcode or "—",
            "التصنيف": cats_map.get(it.category_id, "بدون"),
            "سعر البيع": float(it.sell_price or 0),
            "سعر التكلفة": float(it.cost_price or 0),
            "النوع": "مدمج" if it.is_kit else "عادي",
            "ID": it.id,
            "_action": f"📦 {it.name}",
        }
        for it in results
    ]


def search_invoices(q):
    """البحث في الفواتير."""
    q_like = f"%{q}%"

    # البحث بالرقم أو برقم العميل أو المبلغ
    query = db.query(Invoice).filter(
        Invoice.invoice_number.ilike(q_like)
    )

    # لو الرقم رقمي، ابحث في المبلغ أيضاً
    try:
        amount_val = float(q)
        query = db.query(Invoice).filter(
            (Invoice.invoice_number.ilike(q_like)) |
            (Invoice.net_amount == amount_val)
        )
    except (ValueError, TypeError):
        pass

    results = query.order_by(Invoice.date.desc()).limit(20).all()

    # خريطة الأطراف
    party_ids = list({r.party_id for r in results if r.party_id})
    party_map = {}
    if party_ids:
        party_map = {
            p.id: p.name for p in db.query(Party).filter(
                Party.id.in_(party_ids)
            ).all()
        }

    return [
        {
            "المسلسل": inv.invoice_number,
            "التاريخ": inv.date.strftime("%Y-%m-%d") if inv.date else "—",
            "النوع": "بيع" if inv.type == 'sale' else "شراء",
            "الطرف": party_map.get(inv.party_id, "—"),
            "المبلغ": float(inv.net_amount or 0),
            "الحالة": inv.status,
            "ID": inv.id,
            "_action": f"🧾 {inv.invoice_number}",
        }
        for inv in results
    ]


def search_payments(q):
    """البحث في المدفوعات."""
    q_like = f"%{q}%"
    results = db.query(Payment).filter(
        (Payment.reference_number.ilike(q_like)) |
        (Payment.notes.ilike(q_like))
    ).order_by(Payment.date.desc()).limit(20).all()

    # خريطة الأطراف
    party_ids = list({r.party_id for r in results if r.party_id})
    party_map = {}
    if party_ids:
        party_map = {
            p.id: p.name for p in db.query(Party).filter(
                Party.id.in_(party_ids)
            ).all()
        }

    return [
        {
            "المسلسل": movement_serial("PAY", p.id),
            "التاريخ": p.date.strftime("%Y-%m-%d") if p.date else "—",
            "النوع": "قبض" if p.payment_type == 'receipt' else "صرف",
            "الطرف": party_map.get(p.party_id, "—"),
            "المبلغ": float(p.amount or 0),
            "المرجع": p.reference_number or "—",
            "ID": p.id,
            "_action": f"💰 {movement_serial('PAY', p.id)}",
        }
        for p in results
    ]


def search_expenses(q):
    """البحث في المصروفات."""
    q_like = f"%{q}%"
    results = db.query(Expense).filter(
        (Expense.description.ilike(q_like)) |
        (Expense.reference_number.ilike(q_like))
    ).order_by(Expense.date.desc()).limit(20).all()

    # خريطة التصنيفات
    cat_ids = list({r.category_id for r in results if r.category_id})
    cats_map = {}
    if cat_ids:
        cats_map = {
            c.id: c.name for c in db.query(ExpenseCategory).filter(
                ExpenseCategory.id.in_(cat_ids)
            ).all()
        }

    return [
        {
            "المسلسل": movement_serial("EXP", e.id),
            "التاريخ": e.date.strftime("%Y-%m-%d") if e.date else "—",
            "التصنيف": cats_map.get(e.category_id, "—"),
            "الوصف": (e.description or "")[:60],
            "المبلغ": float(e.amount or 0),
            "ID": e.id,
            "_action": f"💸 {movement_serial('EXP', e.id)}",
        }
        for e in results
    ]


def search_entries(q):
    """البحث في القيود اليومية."""
    q_like = f"%{q}%"
    results = db.query(JournalEntry).filter(
        JournalEntry.description.ilike(q_like)
    ).order_by(JournalEntry.date.desc()).limit(20).all()

    return [
        {
            "المسلسل": movement_serial("JE", e.id),
            "التاريخ": e.date.strftime("%Y-%m-%d") if e.date else "—",
            "البيان": (e.description or "")[:70],
            "النوع": e.reference_type or "—",
            "ID": e.id,
            "_action": f"📝 {movement_serial('JE', e.id)}",
        }
        for e in results
    ]


# ==========================================
# تنفيذ البحث
# ==========================================
if query and query.strip():
    q = query.strip()
    st.markdown(f"### 🔎 نتائج البحث عن: **`{q}`**")

    # ملخص النتائج
    summary_placeholder = st.empty()

    total_results = 0
    tabs_to_show = []

    # جمع النتائج في dict
    results_dict = {}

    if search_party:
        results_dict["👥 العملاء والموردين"] = search_parties(q)
        total_results += len(results_dict["👥 العملاء والموردين"])
    if search_items:
        results_dict["📦 الأصناف"] = search_items(q)
        total_results += len(results_dict["📦 الأصناف"])
    if search_invoices:
        results_dict["🧾 الفواتير"] = search_invoices(q)
        total_results += len(results_dict["🧾 الفواتير"])
    if search_payments:
        results_dict["💰 المدفوعات"] = search_payments(q)
        total_results += len(results_dict["💰 المدفوعات"])
    if search_expenses:
        results_dict["💸 المصروفات"] = search_expenses(q)
        total_results += len(results_dict["💸 المصروفات"])
    if search_entries:
        results_dict["📝 القيود اليومية"] = search_entries(q)
        total_results += len(results_dict["📝 القيود اليومية"])

    summary_placeholder.success(
        f"✅ تم العثور على **{total_results}** نتيجة في **{len([k for k,v in results_dict.items() if v])}** قسم."
    )

    if total_results == 0:
        st.warning("لم يتم العثور على أي نتائج.")
        st.info(
            "💡 **جرب:**\n"
            "- التأكد من الإملاء\n"
            "- استخدام كلمات أقل\n"
            "- البحث بالباركود بدل الاسم\n"
            "- البحث برقم الفاتورة أو المسلسل"
        )
    else:
        # تبويبات لكل قسم به نتائج
        non_empty_tabs = [(name, rows) for name, rows in results_dict.items() if rows]

        tab_labels = [f"{name} ({len(rows)})" for name, rows in non_empty_tabs]
        tabs = st.tabs(tab_labels)

        for tab, (section_name, rows) in zip(tabs, non_empty_tabs):
            with tab:
                display_data = []
                for r in rows:
                    row_copy = {k: v for k, v in r.items() if k not in ('ID', '_action')}
                    display_data.append(row_copy)

                df = pd.DataFrame(display_data)

                # تنسيق الأعمدة الرقمية
                column_config = {}
                for col in df.columns:
                    if col in ('المبلغ', 'سعر البيع', 'سعر التكلفة'):
                        column_config[col] = st.column_config.NumberColumn(col, format="%.2f")

                st.dataframe(
                    df, use_container_width=True, hide_index=True,
                    column_config=column_config,
                )

        st.markdown("---")
        st.caption(
            "💡 **للعرض الكامل أو التعديل:** انتقل إلى صفحة القسم المعنية. "
            "استخدم القائمة الجانبية."
        )
else:
    st.info("👆 اكتب كلمة بحث في الأعلى للبدء.")

    # اقتراحات سريعة
    st.markdown("---")
    st.markdown("### 💡 اقتراحات للبحث")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("""
        **👥 للعملاء:**
        - اسم العميل
        - رقم الهاتف
        - العنوان
        """)
    with col_b:
        st.markdown("""
        **📦 للأصناف:**
        - اسم الصنف
        - الباركود
        - نوع التصنيف
        """)
    with col_c:
        st.markdown("""
        **🧾 للحركات:**
        - `INV-000123` للفواتير
        - `PAY-000045` للمدفوعات
        - `CM-000012` لحركات الخزينة
        """)

db.close()