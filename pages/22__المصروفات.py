# pages/22_💸_المصروفات.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, can_modify
render_sidebar()

import streamlit as st
import pandas as pd
import traceback
import re
import math
from datetime import datetime

from database import SessionLocal
import models
from models import Account, AccountType, CashBox
from services import (
    create_expense, delete_expense, get_expenses_summary,
    get_expense_categories, create_expense_category,
    movement_serial,
)
from period_guard import check_period_open
from auth_required import require_login, get_current_user_id, get_current_user_name
from form_manager import clear_form, show_clear_hint

# ⭐ وصف اختياري — قيمة افتراضية آمنة
def _safe_desc(d, default="حركة خزينة"):
    if d is None or str(d).strip() == "":
        return default
    return str(d).strip()


current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

# ⭐ استقبال التنقل من شجرة الحسابات
try:
    from navigation_helper import consume_navigation_flags, show_navigation_banner
    _nav = consume_navigation_flags()
    show_navigation_banner(_nav, page_name="حركات الخزينة")
    _nav_filter_account = _nav.get("filter_expense_by_account") or _nav.get("filter_by_account")
    _nav_filter_party = _nav.get("filter_party_id")
    if _nav_filter_account:
        st.session_state["_cm_nav_account_id"] = _nav_filter_account
    if _nav_filter_party:
        st.session_state["_cm_nav_party_id"] = _nav_filter_party
except Exception:
    pass

st.set_page_config(page_title="حركات الخزينة", page_icon="💹", layout="wide")
st.title("💹 حركات الخزينة")
show_clear_hint()
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")


PFX = "cm_"


GROUP_COLORS = {
    "💰 الإيرادات": "#10b981",
    "👥 تحصيل من عملاء": "#3b82f6",
    "💵 قروض وسلف": "#8b5cf6",
    "🏦 حقوق ملكية": "#06b6d4",
    "💸 مصروفات": "#ef4444",
    "📦 الأصول": "#64748b",
    "🤝 الموردون": "#f59e0b",
}

ALL_GROUPS = list(GROUP_COLORS.keys())


db = SessionLocal()


ACCOUNTS_PER_ROW = 6
BTN_MIN_H = 120
BTN_FONT_SIZE = 12


def _inject_grid_css(all_accounts):
    css = ["<style>"]
    for acc, group_name in all_accounts:
        color = GROUP_COLORS.get(group_name, "#2563eb")
        container_sel = f'.st-key-{PFX}acc_btn_{acc.id}'
        css.append(f"""
        {container_sel} button {{
            background: {color} !important;
            color: #ffffff !important;
            border: 1.5px solid {color} !important;
            border-radius: 10px !important;
            padding: 8px 5px !important;
            min-height: {BTN_MIN_H}px !important;
            height: {BTN_MIN_H}px !important;
            width: 100% !important;
            font-weight: 700 !important;
            font-size: {BTN_FONT_SIZE}px !important;
            line-height: 1.25 !important;
            white-space: normal !important;
            word-break: break-word !important;
            overflow: visible !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            transition: all 0.15s ease !important;
            margin: 0 !important;
        }}
        {container_sel} button:hover {{
            filter: brightness(1.2) !important;
            transform: translateY(-1px);
            box-shadow: 0 5px 14px rgba(0,0,0,0.4) !important;
            border-color: #ffffff !important;
        }}
        {container_sel} button:focus {{ outline: none !important; }}
        {container_sel} button > div,
        {container_sel} button > div > p,
        {container_sel} button p,
        {container_sel} button span {{
            color: #ffffff !important;
            font-size: {BTN_FONT_SIZE}px !important;
            font-weight: 700 !important;
            line-height: 1.25 !important;
            margin: 0 !important;
            padding: 0 !important;
            white-space: normal !important;
            word-break: break-word !important;
            overflow: visible !important;
            text-align: center !important;
            width: 100% !important;
        }}
        {container_sel} button[kind="primary"],
        {container_sel} button[data-testid="stBaseButton-primary"] {{
            border: 3px solid #ffffff !important;
            box-shadow: 0 0 0 3px {color}, 0 0 18px rgba(255,255,255,0.7) !important;
            transform: scale(1.04);
        }}
        """)
    css.append("</style>")
    return "".join(css)


def _create_cash_movement(cash_box_id, counter_account_id, amount, description,
                          direction, reference_number=None, notes=None,
                          created_by=None, movement_date=None):
    db_local = SessionLocal()
    try:
        cash_box = db_local.query(CashBox).filter(CashBox.id == cash_box_id).first()
        if not cash_box:
            raise ValueError("الخزينة غير موجودة")
        counter_acc = db_local.query(Account).filter(Account.id == counter_account_id).first()
        if not counter_acc:
            raise ValueError("الحساب المقابل غير موجود")
        mov_date = movement_date or datetime.now()
        dir_label = "وارد" if direction == "in" else "صادر"
        desc = f"{dir_label}: {description} — {counter_acc.code} {counter_acc.name}"
        entry = models.JournalEntry(
            date=mov_date, description=desc[:250],
            reference_type="cash_movement", created_by=created_by,
        )
        db_local.add(entry)
        db_local.flush()
        if direction == "in":
            db_local.add(models.JournalLine(entry_id=entry.id, account_id=cash_box.account_id,
                                            debit=float(amount), credit=0.0))
            db_local.add(models.JournalLine(entry_id=entry.id, account_id=counter_account_id,
                                            debit=0.0, credit=float(amount)))
        else:
            db_local.add(models.JournalLine(entry_id=entry.id, account_id=counter_account_id,
                                            debit=float(amount), credit=0.0))
            db_local.add(models.JournalLine(entry_id=entry.id, account_id=cash_box.account_id,
                                            debit=0.0, credit=float(amount)))
        db_local.commit()
        return entry
    except Exception:
        db_local.rollback()
        raise
    finally:
        db_local.close()


def _get_or_create_category_for_account(db_local, account):
    cat = db_local.query(models.ExpenseCategory).filter(
        models.ExpenseCategory.account_id == account.id
    ).first()
    if not cat:
        cat = models.ExpenseCategory(
            name=account.name,
            description=f"تصنيف تلقائي للحساب {account.code}",
            account_id=account.id, is_active=True, created_at=datetime.now(),
        )
        db_local.add(cat)
        db_local.commit()
        db_local.refresh(cat)
    return cat


def _get_group_for_account(acc):
    if not acc:
        return None
    n = acc.name or ""
    if acc.type == AccountType.REVENUE:
        return "💰 الإيرادات"
    elif acc.type == AccountType.EXPENSE:
        return "💸 مصروفات"
    elif acc.type == AccountType.EQUITY:
        return "🏦 حقوق ملكية"
    elif acc.type == AccountType.LIABILITY:
        if "قرض" in n or "سلف" in n:
            return "💵 قروض وسلف"
        elif "مورد" in n:
            return "🤝 الموردون"
        else:
            return "💵 قروض وسلف"
    elif acc.type == AccountType.ASSET:
        if "عميل" in n or "مدينون" in n:
            return "👥 تحصيل من عملاء"
        else:
            return "📦 الأصول"
    return None


def _get_movements(direction=None, start=None, end=None,
                   counter_group=None, counter_search=None,
                   filter_account_id=None, filter_party_id=None):
    q = db.query(models.JournalEntry).filter(
        models.JournalEntry.reference_type.in_(["revenue", "expense", "cash_movement"])
    )
    if start:
        q = q.filter(models.JournalEntry.date >= start)
    if end:
        q = q.filter(models.JournalEntry.date <= end)
    entries = q.order_by(models.JournalEntry.date.desc()).all()
    result = []
    search_q = (counter_search or "").strip().lower()
    for e in entries:
        if direction:
            d = _movement_direction(e)
            if d != direction:
                continue
        det = _movement_details(e)
        if filter_account_id:
            try:
                f_acc_id = int(filter_account_id)
                entry_lines = db.query(models.JournalLine).filter(
                    models.JournalLine.entry_id == e.id,
                    models.JournalLine.account_id == f_acc_id
                ).first()
                if not entry_lines:
                    continue
            except Exception:
                pass
        if filter_party_id:
            try:
                f_party_id = int(filter_party_id)
                f_party = db.query(models.Party).filter(
                    models.Party.id == f_party_id
                ).first()
                if f_party and f_party.account_id:
                    entry_lines = db.query(models.JournalLine).filter(
                        models.JournalLine.entry_id == e.id,
                        models.JournalLine.account_id == f_party.account_id
                    ).first()
                    if not entry_lines:
                        continue
            except Exception:
                pass
        if counter_group and counter_group != "— الكل —":
            grp = _get_group_for_account(det.get("counter_acc"))
            if grp != counter_group:
                continue
        if search_q:
            counter_acc = det.get("counter_acc")
            code = (counter_acc.code or "").lower() if counter_acc else ""
            name = (counter_acc.name or "").lower() if counter_acc else ""
            desc = (e.description or "").lower()
            if (search_q not in code and search_q not in name and search_q not in desc):
                continue
        result.append(e)
    return result


def _movement_direction(entry):
    if entry.description and (entry.description.startswith("وارد") or entry.reference_type == "revenue"):
        return "in"
    return "out"


def _movement_details(entry):
    lines = db.query(models.JournalLine).filter(
        models.JournalLine.entry_id == entry.id
    ).all()
    cash_line = None
    counter_line = None
    for ln in lines:
        acc = db.query(Account).filter(Account.id == ln.account_id).first()
        if not acc:
            continue
        is_cashbox = db.query(CashBox).filter(CashBox.account_id == acc.id).first() is not None
        if is_cashbox:
            cash_line = (acc, ln)
        else:
            counter_line = (acc, ln)
    amount = 0.0
    if cash_line:
        amount = float(cash_line[1].debit or 0) or float(cash_line[1].credit or 0)
    return {
        "cash_acc": cash_line[0] if cash_line else None,
        "counter_acc": counter_line[0] if counter_line else None,
        "counter_acc_id": counter_line[0].id if counter_line else None,
        "amount": amount,
        "direction": _movement_direction(entry),
    }


# ═══════════════════════════════════════════════════════════
# ⭐ _delete_movement — مُصلَحة (إعادة تحميل الكائن في الجلسة الجديدة)
# ═══════════════════════════════════════════════════════════
def _delete_movement(entry):
    """حذف حركة خزينة — إعادة تحميل الكائن في الجلسة الجديدة."""
    db_local = SessionLocal()
    try:
        entry_id = entry.id
        entry_date = entry.date

        if entry_date:
            check_period_open(entry_date, entity="حذف حركة خزينة")

        # 1) حذف أسطر القيد أولاً
        db_local.query(models.JournalLine).filter(
            models.JournalLine.entry_id == entry_id
        ).delete(synchronize_session=False)

        # 2) ⭐ إعادة تحميل الكائن في الجلسة الجديدة قبل الحذف
        entry_local = db_local.query(models.JournalEntry).filter(
            models.JournalEntry.id == entry_id
        ).first()

        if entry_local:
            db_local.delete(entry_local)

        db_local.commit()
    except Exception:
        db_local.rollback()
        raise
    finally:
        db_local.close()


def _update_movement(entry_id, new_amount, new_date, new_desc,
                     new_counter_account_id=None,
                     new_ref=None, new_notes=None):
    db_local = SessionLocal()
    try:
        entry = db_local.query(models.JournalEntry).filter(
            models.JournalEntry.id == entry_id
        ).first()
        if not entry:
            raise ValueError("الحركة غير موجودة")
        if entry.date:
            check_period_open(entry.date, entity="تعديل حركة خزينة")
        check_period_open(new_date, entity="تعديل حركة خزينة")
        lines = db_local.query(models.JournalLine).filter(
            models.JournalLine.entry_id == entry.id
        ).all()
        cash_line = None
        counter_line = None
        for ln in lines:
            is_cash = db_local.query(CashBox).filter(
                CashBox.account_id == ln.account_id
            ).first() is not None
            if is_cash:
                cash_line = ln
            else:
                counter_line = ln
        if not cash_line or not counter_line:
            raise ValueError("تعذّر تحديد أسطر القيد")
        direction = _movement_direction(entry)
        dir_label = "وارد" if direction == "in" else "صادر"
        if new_counter_account_id and int(new_counter_account_id) != int(counter_line.account_id):
            new_acc = db_local.query(Account).filter(
                Account.id == int(new_counter_account_id)
            ).first()
            if not new_acc:
                raise ValueError("الحساب المقابل الجديد غير موجود")
            is_cash = db_local.query(CashBox).filter(
                CashBox.account_id == new_acc.id
            ).first() is not None
            if is_cash:
                raise ValueError("لا يمكن اختيار حساب خزينة كطرف مقابل")
            counter_line.account_id = int(new_counter_account_id)
        counter_acc = db_local.query(Account).filter(
            Account.id == counter_line.account_id
        ).first()
        counter_label = f"{counter_acc.code} {counter_acc.name}" if counter_acc else ""
        entry.date = new_date
        new_desc_full = f"{dir_label}: {new_desc.strip()}"
        if counter_label:
            new_desc_full += f" — {counter_label}"
        if new_notes and new_notes.strip():
            new_desc_full += f" [{new_notes.strip()}]"
        entry.description = new_desc_full[:250]
        if direction == "in":
            cash_line.debit = float(new_amount)
            cash_line.credit = 0.0
            counter_line.debit = 0.0
            counter_line.credit = float(new_amount)
        else:
            counter_line.debit = float(new_amount)
            counter_line.credit = 0.0
            cash_line.debit = 0.0
            cash_line.credit = float(new_amount)
        db_local.commit()
        return entry
    except Exception:
        db_local.rollback()
        raise
    finally:
        db_local.close()


def _get_counter_account_groups():
    accounts = db.query(Account).order_by(Account.code).all()
    cash_account_ids = [b.account_id for b in db.query(CashBox).all()]
    groups = {
        "💰 الإيرادات": [], "👥 تحصيل من عملاء": [], "💵 قروض وسلف": [],
        "🏦 حقوق ملكية": [], "💸 مصروفات": [], "📦 الأصول": [], "🤝 الموردون": [],
    }
    for acc in accounts:
        if acc.id in cash_account_ids:
            continue
        if acc.type == AccountType.REVENUE:
            groups["💰 الإيرادات"].append(acc)
        elif acc.type == AccountType.EXPENSE:
            groups["💸 مصروفات"].append(acc)
        elif acc.type == AccountType.EQUITY:
            groups["🏦 حقوق ملكية"].append(acc)
        elif acc.type == AccountType.LIABILITY:
            if "قرض" in (acc.name or "") or "سلف" in (acc.name or ""):
                groups["💵 قروض وسلف"].append(acc)
            elif "مورد" in (acc.name or ""):
                groups["🤝 الموردون"].append(acc)
            else:
                groups["💵 قروض وسلف"].append(acc)
        elif acc.type == AccountType.ASSET:
            if "عميل" in (acc.name or "") or "مدينون" in (acc.name or ""):
                groups["👥 تحصيل من عملاء"].append(acc)
            else:
                groups["📦 الأصول"].append(acc)
    return {k: v for k, v in groups.items() if v}


def _flatten_accounts(groups):
    flat = []
    order = ["💰 الإيرادات", "👥 تحصيل من عملاء", "💵 قروض وسلف",
             "🏦 حقوق ملكية", "💸 مصروفات", "📦 الأصول", "🤝 الموردون"]
    for group_name in order:
        if group_name in groups:
            for acc in groups[group_name]:
                flat.append((acc, group_name))
    return flat


def _filter_accounts(all_accounts, group_filter, search_query):
    result = []
    q = (search_query or "").strip().lower()
    for acc, grp in all_accounts:
        if group_filter and group_filter != "— الكل —" and grp != group_filter:
            continue
        if q:
            code = (acc.code or "").lower()
            name = (acc.name or "").lower()
            if q not in code and q not in name:
                continue
        result.append((acc, grp))
    return result


def _extract_original_desc(description):
    if not description:
        return ""
    parts = description.split(" — ", 1)
    head = parts[0]
    if ":" in head:
        head = head.split(":", 1)[1]
    head = re.sub(r"\s*\[.*?\]\s*$", "", head)
    return head.strip()


def _is_customer_account(acc):
    n = (acc.name or "") if acc else ""
    return ("عميل" in n) or ("مدينون" in n)


def _is_supplier_account(acc):
    n = (acc.name or "") if acc else ""
    return ("مورد" in n) or ("دائنون" in n)


tab1, tab2, tab3, tab4 = st.tabs([
    "➕ تسجيل حركة جديدة", "📋 سجل الحركات",
    "⚙️ تعديل / حذف حركة", "📊 تقرير الخزينة",
])


# ==========================================
# التبويب 1
# ==========================================
with tab1:
    st.subheader("➕ تسجيل حركة جديدة")
    cash_boxes = db.query(CashBox).filter(CashBox.is_active == True).all()
    if not cash_boxes:
        st.error("⚠️ لا توجد خزائن مفعّلة!")
        st.stop()
    box_opts = {b.id: f"{b.name} ({b.code})" for b in cash_boxes}
    selected_box_id = st.selectbox("1️⃣ الخزينة:", options=list(box_opts.keys()),
                                    format_func=lambda x: box_opts[x], key=f"{PFX}box")
    st.markdown("### 2️⃣ نوع الحركة")
    direction = st.radio("الاتجاه:", ["in", "out"],
                          format_func=lambda x: "💰 وارد" if x == "in" else "💸 صادر",
                          horizontal=True, key=f"{PFX}dir")
    st.markdown("### 3️⃣ الحساب المقابل")
    st.caption("💡 اضغط على مربع الحساب لاختياره.")
    counter_groups = _get_counter_account_groups()
    if not counter_groups:
        st.error("⚠️ لا توجد حسابات طرف مقابل!")
        st.stop()
    all_accounts = _flatten_accounts(counter_groups)
    st.markdown(_inject_grid_css(all_accounts), unsafe_allow_html=True)
    selected_account_id = st.session_state.get(f"{PFX}selected_account")
    total = len(all_accounts)
    num_rows = math.ceil(total / ACCOUNTS_PER_ROW)
    idx_global = 0
    for r in range(num_rows):
        cols = st.columns(ACCOUNTS_PER_ROW, gap="small")
        for c in range(ACCOUNTS_PER_ROW):
            with cols[c]:
                if idx_global < total:
                    acc, group_name = all_accounts[idx_global]
                    is_selected = (selected_account_id == acc.id)
                    label = f"{'✅ ' if is_selected else ''}{acc.code}\n{acc.name}"
                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(label, key=f"{PFX}acc_btn_{acc.id}",
                                 type=btn_type, use_container_width=True):
                        st.session_state[f"{PFX}selected_account"] = acc.id
                        st.rerun()
                    idx_global += 1
                else:
                    st.markdown(f'<div style="height:{BTN_MIN_H}px;"></div>', unsafe_allow_html=True)
    selected_account_id = st.session_state.get(f"{PFX}selected_account")
    linked_invoice_number = None
    linked_party_name = None
    if selected_account_id:
        acc = db.query(Account).filter(Account.id == selected_account_id).first()
        if acc:
            st.markdown("---")
            st.success(f"✅ **الحساب المختار:** `{acc.code}` — {acc.name}")
            is_customer = _is_customer_account(acc)
            is_supplier = _is_supplier_account(acc)
            if is_customer:
                st.markdown("### 🔗 ربط الحركة بعميل وفاتورة (اختياري)")
                customers = db.query(models.Party).filter(models.Party.type == 'customer').order_by(models.Party.name).all()
                if not customers:
                    st.warning("⚠️ لا يوجد عملاء مسجلين.")
                else:
                    party_opts = {p.id: p.name for p in customers}
                    linked_party_id = st.selectbox("اختر العميل:",
                                                    options=[None] + list(party_opts.keys()),
                                                    format_func=lambda x: "— بدون ربط —" if x is None else party_opts[x],
                                                    key=f"{PFX}linked_party")
                    if linked_party_id:
                        linked_party_name = party_opts.get(linked_party_id)
                        invoices = db.query(models.Invoice).filter(
                            models.Invoice.party_id == linked_party_id,
                            models.Invoice.type == 'sale'
                        ).order_by(models.Invoice.date.desc()).all()
                        if invoices:
                            status_map = {"paid": "✅ مدفوعة", "partial": "🟡 جزئية", "pending": "🔴 غير مدفوعة"}
                            inv_opts = {"— بدون ربط بفاتورة —": None}
                            for inv in invoices:
                                status_ar = status_map.get((inv.status or "").lower(), inv.status or "—")
                                net = float(inv.net_amount or 0)
                                inv_opts[f"{inv.invoice_number} — {net:,.2f} ج.م — {status_ar}"] = inv.invoice_number
                            selected_inv_label = st.selectbox("اختر الفاتورة (اختياري):",
                                                              options=list(inv_opts.keys()),
                                                              key=f"{PFX}linked_inv")
                            linked_invoice_number = inv_opts.get(selected_inv_label)
            elif is_supplier:
                st.markdown("### 🔗 ربط الحركة بمورد وفاتورة (اختياري)")
                suppliers = db.query(models.Party).filter(models.Party.type == 'supplier').order_by(models.Party.name).all()
                if not suppliers:
                    st.warning("⚠️ لا يوجد موردون مسجلون.")
                else:
                    party_opts = {p.id: p.name for p in suppliers}
                    linked_party_id = st.selectbox("اختر المورد:",
                                                    options=[None] + list(party_opts.keys()),
                                                    format_func=lambda x: "— بدون ربط —" if x is None else party_opts[x],
                                                    key=f"{PFX}linked_party")
                    if linked_party_id:
                        linked_party_name = party_opts.get(linked_party_id)
                        invoices = db.query(models.Invoice).filter(
                            models.Invoice.party_id == linked_party_id,
                            models.Invoice.type == 'purchase'
                        ).order_by(models.Invoice.date.desc()).all()
                        if invoices:
                            status_map = {"paid": "✅ مدفوعة", "partial": "🟡 جزئية", "pending": "🔴 غير مدفوعة"}
                            inv_opts = {"— بدون ربط بفاتورة —": None}
                            for inv in invoices:
                                status_ar = status_map.get((inv.status or "").lower(), inv.status or "—")
                                net = float(inv.net_amount or 0)
                                inv_opts[f"{inv.invoice_number} — {net:,.2f} ج.م — {status_ar}"] = inv.invoice_number
                            selected_inv_label = st.selectbox("اختر الفاتورة (اختياري):",
                                                              options=list(inv_opts.keys()),
                                                              key=f"{PFX}linked_inv")
                            linked_invoice_number = inv_opts.get(selected_inv_label)
    else:
        st.warning("👆 اضغط على مربع حساب لاختياره.")
    st.markdown("### 4️⃣ تفاصيل الحركة")
    col_d, col_t = st.columns(2)
    with col_d:
        cm_date = st.date_input("التاريخ:", value=datetime.now().date(), key=f"{PFX}date")
    with col_t:
        cm_time = st.time_input("الوقت:", value=datetime.now().time(), key=f"{PFX}time")
    amount = st.number_input("المبلغ (ج.م):", min_value=0.01, step=100.0, value=100.0,
                              format="%.2f", key=f"{PFX}amount")
    description = st.text_area("الوصف (اختياري):", placeholder="اتركه فارغاً ليُولَّد تلقائياً", key=f"{PFX}desc")
    ref_no = st.text_input("رقم المرجع (اختياري):", value=linked_invoice_number or "", key=f"{PFX}ref")
    notes = st.text_area("ملاحظات (اختياري):", key=f"{PFX}notes", height=60)
    if st.button("💾 حفظ الحركة", type="primary", use_container_width=True, key=f"{PFX}save"):
        if not selected_account_id:
            st.error("❌ اختر الحساب المقابل أولاً.")
        elif amount <= 0:
            st.error("❌ المبلغ يجب أن يكون أكبر من صفر.")
        else:
            try:
                cm_dt = datetime.combine(cm_date, cm_time)
                check_period_open(cm_dt, entity="تسجيل حركة خزينة")
                final_desc = description.strip() if description else ""
                if not final_desc:
                    if linked_invoice_number:
                        final_desc = f"مرتبط بالفاتورة {linked_invoice_number}"
                        if linked_party_name:
                            final_desc += f" — {linked_party_name}"
                    else:
                        final_desc = "حركة خزينة"
                final_ref = ref_no.strip() if ref_no and ref_no.strip() else None
                if not final_ref and linked_invoice_number:
                    final_ref = linked_invoice_number
                if direction == "in":
                    _create_cash_movement(
                        cash_box_id=int(selected_box_id),
                        counter_account_id=int(selected_account_id),
                        amount=float(amount), description=final_desc, direction="in",
                        reference_number=final_ref, notes=notes or None,
                        created_by=current_user_id, movement_date=cm_dt,
                    )
                else:
                    acc_obj = db.query(Account).filter(Account.id == selected_account_id).first()
                    if acc_obj.type == AccountType.EXPENSE:
                        cat = _get_or_create_category_for_account(db, acc_obj)
                        create_expense(
                            category_id=cat.id, amount=float(amount), description=final_desc,
                            payment_method="cash", cash_box_id=int(selected_box_id),
                            reference_number=final_ref, notes=notes or None,
                            expense_date=cm_dt, created_by=current_user_id,
                        )
                    else:
                        _create_cash_movement(
                            cash_box_id=int(selected_box_id),
                            counter_account_id=int(selected_account_id),
                            amount=float(amount), description=final_desc, direction="out",
                            reference_number=final_ref, notes=notes or None,
                            created_by=current_user_id, movement_date=cm_dt,
                        )
                direction_label = "وارد" if direction == "in" else "صادر"
                st.success(f"✅ تم تسجيل حركة {direction_label} بمبلغ {amount:,.2f} ج.م")
                st.balloons()
                clear_form(PFX)
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 2: سجل الحركات + حذف مباشر
# ==========================================
with tab2:
    st.subheader("📋 سجل حركات الخزينة")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_dir = st.selectbox("الاتجاه:", ["الكل", "وارد فقط", "صادر فقط"], key=f"{PFX}filter_dir")
    with col_f2:
        start_filter = st.date_input("من تاريخ:", value=datetime.now().replace(day=1).date(), key=f"{PFX}filter_start")
    with col_f3:
        end_filter = st.date_input("إلى تاريخ:", value=datetime.now().date(), key=f"{PFX}filter_end")
    col_f4, col_f5 = st.columns([1, 2])
    with col_f4:
        filter_counter_group = st.selectbox("📁 نوع الحساب المقابل:",
                                             options=["— الكل —"] + ALL_GROUPS,
                                             key=f"{PFX}filter_counter_grp")
    with col_f5:
        filter_search = st.text_input("🔎 بحث (كود/اسم الحساب أو الوصف):",
                                       placeholder="مثال: 5000 أو مصروفات أو إيجار",
                                       key=f"{PFX}filter_search")
    d = None
    if filter_dir == "وارد فقط":
        d = "in"
    elif filter_dir == "صادر فقط":
        d = "out"
    start_dt = datetime.combine(start_filter, datetime.min.time())
    end_dt = datetime.combine(end_filter, datetime.max.time())
    _nav_acc_id = st.session_state.get("_cm_nav_account_id")
    _nav_party_id = st.session_state.get("_cm_nav_party_id")
    if _nav_acc_id:
        _acc = db.query(Account).filter(Account.id == _nav_acc_id).first()
        if _acc:
            st.info(f"🎯 **مفلتر من شجرة الحسابات** على: `{_acc.code}` — {_acc.name}")
    movements = _get_movements(direction=d, start=start_dt, end=end_dt,
                                counter_group=filter_counter_group, counter_search=filter_search,
                                filter_account_id=_nav_acc_id, filter_party_id=_nav_party_id)
    st.caption(f"📊 عدد الحركات المطابقة: **{len(movements)}**")
    if movements:
        rows = []
        total_in = 0.0
        total_out = 0.0
        for m in movements:
            det = _movement_details(m)
            grp = _get_group_for_account(det.get("counter_acc")) or "—"
            if det["direction"] == "in":
                total_in += det["amount"]
            else:
                total_out += det["amount"]
            rows.append({
                "المسلسل": movement_serial("CM", m.id),
                "ID": m.id,
                "التاريخ": m.date.strftime("%Y-%m-%d %H:%M") if m.date else "—",
                "الاتجاه": "💰 وارد" if det["direction"] == "in" else "💸 صادر",
                "الخزينة": det["cash_acc"].name if det["cash_acc"] else "—",
                "النوع": grp,
                "الطرف المقابل": f"{det['counter_acc'].code} — {det['counter_acc'].name}" if det["counter_acc"] else "—",
                "المبلغ": det["amount"],
                "الوصف": m.description or "—",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True,
                     column_config={
                         "المسلسل": st.column_config.TextColumn("المسلسل", width="small"),
                         "المبلغ": st.column_config.NumberColumn("المبلغ", format="%.2f"),
                     })
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("إجمالي الوارد", f"{total_in:,.2f} ج.م")
        with c2:
            st.metric("إجمالي الصادر", f"{total_out:,.2f} ج.م")
        with c3:
            st.metric("الصافي", f"{total_in - total_out:,.2f} ج.م")
        st.markdown("---")
        # ⭐ حذف مباشر من السجل
        if can_modify():
            st.markdown("### 🗑 حذف حركة من السجل")
            del_opts = {}
            for m in movements:
                det = _movement_details(m)
                serial = movement_serial("CM", m.id)
                arrow = "💰" if det["direction"] == "in" else "💸"
                date_s = m.date.strftime("%Y-%m-%d %H:%M") if m.date else "—"
                desc_s = _extract_original_desc(m.description or "")[:50]
                counter_s = ""
                if det["counter_acc"]:
                    counter_s = f" — {det['counter_acc'].code} {det['counter_acc'].name}"
                del_opts[m.id] = f"{serial} — {arrow} — {det['amount']:,.2f} ج.م — {date_s}{counter_s} — {desc_s}"
            del_m_id = st.selectbox("اختر الحركة لحذفها:", options=list(del_opts.keys()),
                                     format_func=lambda x: del_opts[x], key=f"{PFX}log_del_select")
            if del_m_id:
                del_entry = db.query(models.JournalEntry).filter(
                    models.JournalEntry.id == del_m_id
                ).first()
                if del_entry:
                    det_del = _movement_details(del_entry)
                    del_serial = movement_serial("CM", del_entry.id)
                    with st.container(border=True):
                        dcol1, dcol2, dcol3 = st.columns(3)
                        with dcol1:
                            st.metric("الاتجاه", "💰 وارد" if det_del["direction"] == "in" else "💸 صادر")
                        with dcol2:
                            st.metric("المبلغ", f"{det_del['amount']:,.2f} ج.م")
                        with dcol3:
                            st.metric("التاريخ", del_entry.date.strftime("%Y-%m-%d") if del_entry.date else "—")
                        st.caption(f"**المسلسل:** `{del_serial}`")
                        if det_del["counter_acc"]:
                            st.caption(f"**الطرف المقابل:** {det_del['counter_acc'].code} — {det_del['counter_acc'].name}")
                        st.caption(f"**الوصف:** {(del_entry.description or '—')[:150]}")
                        st.warning(f"⚠️ سيتم حذف الحركة `{del_serial}` نهائياً مع قيودها المحاسبية.")
                        confirm_log = st.checkbox("✅ أؤكد الحذف النهائي من السجل",
                                                   key=f"{PFX}log_confirm_del_{del_m_id}")
                        if st.button("🗑 حذف نهائي", type="primary",
                                     disabled=not confirm_log,
                                     use_container_width=True,
                                     key=f"{PFX}log_del_btn_{del_m_id}"):
                            try:
                                _delete_movement(del_entry)
                                st.success(f"✅ تم حذف الحركة `{del_serial}` بنجاح!")
                                st.balloons()
                                st.session_state.pop(f"{PFX}log_confirm_del_{del_m_id}", None)
                                st.session_state.pop(f"{PFX}log_del_select", None)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ خطأ: {e}")
        else:
            st.info("⛔ **الحذف للمدير فقط.**")
        st.markdown("---")
        st.info("💡 للتعديل الكامل، انتقل إلى تبويب **⚙️ تعديل / حذف حركة**.")
    else:
        st.info("لا توجد حركات في الفترة المحددة.")


# ==========================================
# التبويب 3: تعديل / حذف حركة
# ==========================================
with tab3:
    st.subheader("⚙️ تعديل / حذف حركة خزينة")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        edit_dir = st.selectbox("الاتجاه:", ["الكل", "وارد فقط", "صادر فقط"], key=f"{PFX}ef_dir")
    with col_f2:
        edit_start = st.date_input("من تاريخ:", value=(datetime.now().replace(day=1)).date(), key=f"{PFX}ef_start")
    with col_f3:
        edit_end = st.date_input("إلى تاريخ:", value=datetime.now().date(), key=f"{PFX}ef_end")
    col_f4, col_f5 = st.columns([1, 2])
    with col_f4:
        edit_counter_group = st.selectbox("📁 نوع الحساب المقابل:",
                                           options=["— الكل —"] + ALL_GROUPS,
                                           key=f"{PFX}ef_counter_grp")
    with col_f5:
        edit_search = st.text_input("🔎 بحث (كود/اسم الحساب أو الوصف):",
                                     placeholder="مثال: 5000 أو مصروفات أو إيجار",
                                     key=f"{PFX}ef_search")
    d_edit = None
    if edit_dir == "وارد فقط":
        d_edit = "in"
    elif edit_dir == "صادر فقط":
        d_edit = "out"
    edit_start_dt = datetime.combine(edit_start, datetime.min.time())
    edit_end_dt = datetime.combine(edit_end, datetime.max.time())
    edit_movements = _get_movements(direction=d_edit, start=edit_start_dt, end=edit_end_dt,
                                     counter_group=edit_counter_group, counter_search=edit_search,
                                     filter_account_id=st.session_state.get("_cm_nav_account_id"),
                                     filter_party_id=st.session_state.get("_cm_nav_party_id"))
    st.caption(f"📊 عدد الحركات المطابقة: **{len(edit_movements)}**")
    if not edit_movements:
        st.info("لا توجد حركات في الفترة المحددة.")
    else:
        m_opts = {}
        for m in edit_movements:
            det = _movement_details(m)
            serial = movement_serial("CM", m.id)
            arrow = "💰" if det["direction"] == "in" else "💸"
            date_s = m.date.strftime("%Y-%m-%d") if m.date else "—"
            desc_s = _extract_original_desc(m.description or "")[:40]
            m_opts[m.id] = f"{serial} — {arrow} — {det['amount']:,.2f} ج.م — {date_s} — {desc_s}"
        selected_m_id = st.selectbox("اختر الحركة (بالمسلسل):", options=list(m_opts.keys()),
                                      format_func=lambda x: m_opts[x], key=f"{PFX}edit_select")
        if selected_m_id:
            entry = db.query(models.JournalEntry).filter(
                models.JournalEntry.id == selected_m_id
            ).first()
            if entry:
                det = _movement_details(entry)
                serial = movement_serial("CM", entry.id)
                st.markdown(f"### 📄 تفاصيل الحركة **`{serial}`**")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("الاتجاه", "💰 وارد" if det["direction"] == "in" else "💸 صادر")
                with c2:
                    st.metric("المبلغ الحالي", f"{det['amount']:,.2f} ج.م")
                with c3:
                    st.metric("التاريخ", entry.date.strftime("%Y-%m-%d") if entry.date else "—")
                st.write(f"**الخزينة:** {det['cash_acc'].name if det['cash_acc'] else '—'}")
                if det["counter_acc"]:
                    st.write(f"**الطرف المقابل:** {det['counter_acc'].code} — {det['counter_acc'].name}")
                original_desc = _extract_original_desc(entry.description or "")
                st.markdown("---")
                st.markdown("### ✏️ تعديل البيانات")
                counter_groups_edit = _get_counter_account_groups()
                all_accounts_edit = _flatten_accounts(counter_groups_edit)
                st.markdown("##### 🎯 الحساب المقابل (يمكن تغييره)")
                col_fg, col_fs = st.columns([1, 2])
                with col_fg:
                    inner_group_filter = st.selectbox("📁 نوع الحساب:",
                                                       options=["— الكل —"] + list(counter_groups_edit.keys()),
                                                       key=f"{PFX}inner_grp_{entry.id}")
                with col_fs:
                    inner_search = st.text_input("🔎 بحث الحساب:", placeholder="كود أو اسم",
                                                  key=f"{PFX}inner_search_{entry.id}")
                filtered = _filter_accounts(all_accounts_edit, inner_group_filter, inner_search)
                current_acc_id = det.get("counter_acc_id")
                current_present = any(acc.id == current_acc_id for acc, _ in filtered)
                if not current_present:
                    for acc, grp in all_accounts_edit:
                        if acc.id == current_acc_id:
                            filtered = [(acc, grp)] + filtered
                            break
                st.caption(f"📊 عدد الحسابات: **{len(filtered)}** من {len(all_accounts_edit)}")
                if not filtered:
                    st.warning("⚠️ لا توجد حسابات مطابقة.")
                    acc_options = {}
                else:
                    acc_options = {}
                    for _acc, _grp in filtered:
                        acc_options[f"{_acc.code} — {_acc.name}  ({_grp})"] = _acc.id
                option_labels = list(acc_options.keys())
                current_index = 0
                for i, lbl in enumerate(option_labels):
                    if acc_options[lbl] == current_acc_id:
                        current_index = i
                        break
                if option_labels:
                    selected_acc_label = st.selectbox("اختر الحساب المقابل:", options=option_labels,
                                                       index=current_index,
                                                       key=f"{PFX}edit_counter_{entry.id}")
                    new_counter_account_id = acc_options.get(selected_acc_label)
                else:
                    new_counter_account_id = current_acc_id
                    st.info("الحساب الحالي محفوظ.")
                st.markdown("---")
                st.markdown("##### 💰 المبلغ والتاريخ")
                new_amount = st.number_input("المبلغ الجديد (ج.م):", min_value=0.01,
                                              value=float(det["amount"]), step=100.0,
                                              format="%.2f", key=f"{PFX}edit_amount_{entry.id}")
                col_d, col_t = st.columns(2)
                with col_d:
                    new_date = st.date_input("التاريخ:",
                                              value=entry.date.date() if entry.date else datetime.now().date(),
                                              key=f"{PFX}edit_date_{entry.id}")
                with col_t:
                    new_time = st.time_input("الوقت:",
                                              value=entry.date.time() if entry.date else datetime.now().time(),
                                              key=f"{PFX}edit_time_{entry.id}")
                st.markdown("##### 📝 الوصف والملاحظات")
                new_desc = st.text_area("الوصف (اختياري):", value=original_desc, height=68,
                                         key=f"{PFX}edit_desc_{entry.id}")
                new_notes = st.text_area("ملاحظات إضافية (اختياري):", value="", height=68,
                                          key=f"{PFX}edit_notes_{entry.id}")
                if st.button("💾 حفظ التعديلات", type="primary", use_container_width=True,
                             key=f"{PFX}save_edit_{entry.id}"):
                    if new_amount <= 0:
                        st.error("❌ المبلغ يجب أن يكون أكبر من صفر.")
                    elif not new_counter_account_id:
                        st.error("❌ اختر الحساب المقابل.")
                    else:
                        try:
                            new_dt = datetime.combine(new_date, new_time)
                            final_new_desc = new_desc.strip() if new_desc else "حركة خزينة"
                            _update_movement(entry_id=entry.id, new_amount=float(new_amount),
                                              new_date=new_dt, new_desc=final_new_desc,
                                              new_counter_account_id=new_counter_account_id,
                                              new_notes=new_notes.strip() or None)
                            st.success(f"✅ تم تحديث الحركة `{serial}` بنجاح!")
                            clear_form(PFX)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ خطأ: {e}")
                            st.code(traceback.format_exc())
                st.markdown("---")
                st.markdown("### 🗑 حذف الحركة")
                if can_modify():
                    st.error(f"⚠️ سيتم حذف الحركة `{serial}` نهائيًا مع قيودها المحاسبية.")
                    confirm = st.checkbox("✅ أؤكد الحذف النهائي", key=f"{PFX}confirm_del_{entry.id}")
                    if st.button("🗑 حذف الحركة", type="secondary", disabled=not confirm,
                                 use_container_width=True, key=f"{PFX}del_btn_{entry.id}"):
                        try:
                            _delete_movement(entry)
                            st.success(f"✅ تم حذف الحركة `{serial}`.")
                            clear_form(PFX)
                            st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"❌ خطأ: {e}")
                else:
                    st.info("⛔ الحذف للمدير فقط.")


# ==========================================
# التبويب 4: تقرير الخزينة
# ==========================================
with tab4:
    st.subheader("📊 تقرير حركات الخزينة")
    col1, col2 = st.columns(2)
    with col1:
        rep_start = st.date_input("من تاريخ:", value=datetime.now().replace(day=1).date(), key=f"{PFX}rep_start")
    with col2:
        rep_end = st.date_input("إلى تاريخ:", value=datetime.now().date(), key=f"{PFX}rep_end")
    if st.button("📊 عرض التقرير", type="primary", key=f"{PFX}show_report"):
        s = datetime.combine(rep_start, datetime.min.time())
        e = datetime.combine(rep_end, datetime.max.time())
        movements = _get_movements(start=s, end=e)
        total_in = sum(_movement_details(m)["amount"] for m in movements
                        if _movement_details(m)["direction"] == "in")
        total_out = sum(_movement_details(m)["amount"] for m in movements
                         if _movement_details(m)["direction"] == "out")
        net = total_in - total_out
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("إجمالي الوارد", f"{total_in:,.2f} ج.م")
        with c2:
            st.metric("إجمالي الصادر", f"{total_out:,.2f} ج.م")
        with c3:
            st.metric("الصافي", f"{net:,.2f} ج.م",
                      delta="زيادة" if net >= 0 else "نقص",
                      delta_color="normal" if net >= 0 else "inverse")
        in_by_counter = {}
        out_by_counter = {}
        for m in movements:
            det = _movement_details(m)
            if not det["counter_acc"]:
                continue
            key = f"{det['counter_acc'].code} — {det['counter_acc'].name}"
            if det["direction"] == "in":
                in_by_counter[key] = in_by_counter.get(key, 0) + det["amount"]
            else:
                out_by_counter[key] = out_by_counter.get(key, 0) + det["amount"]
        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 💰 الوارد حسب المصدر")
            if in_by_counter:
                df = pd.DataFrame(list(in_by_counter.items()), columns=["المصدر", "المبلغ"])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.bar_chart(df.set_index("المصدر"))
            else:
                st.info("لا وارد.")
        with col_b:
            st.markdown("### 💸 الصادر حسب الجهة")
            if out_by_counter:
                df = pd.DataFrame(list(out_by_counter.items()), columns=["الجهة", "المبلغ"])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.bar_chart(df.set_index("الجهة"))
            else:
                st.info("لا صادر.")

db.close()