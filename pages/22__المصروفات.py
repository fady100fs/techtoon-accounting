# pages/22_💸_المصروفات.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify
render_sidebar()

import streamlit as st
import pandas as pd
import traceback
import re
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

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="حركات الخزينة", page_icon="💹", layout="wide")
st.title("💹 حركات الخزينة")
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()


# ==========================================
# دوال مساعدة
# ==========================================
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


def _get_movements(direction=None, start=None, end=None):
    q = db.query(models.JournalEntry).filter(
        models.JournalEntry.reference_type.in_(["revenue", "expense", "cash_movement"])
    )
    if start:
        q = q.filter(models.JournalEntry.date >= start)
    if end:
        q = q.filter(models.JournalEntry.date <= end)
    entries = q.order_by(models.JournalEntry.date.desc()).all()
    if direction:
        filtered = []
        for e in entries:
            d = _movement_direction(e)
            if d == direction:
                filtered.append(e)
        return filtered
    return entries


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
        "amount": amount,
        "direction": _movement_direction(entry),
    }


def _delete_movement(entry):
    db_local = SessionLocal()
    try:
        # ✅ فحص الفترة
        if entry.date:
            check_period_open(entry.date, entity="حذف حركة خزينة")

        db_local.query(models.JournalLine).filter(
            models.JournalLine.entry_id == entry.id
        ).delete(synchronize_session=False)
        db_local.delete(entry)
        db_local.commit()
    except Exception:
        db_local.rollback()
        raise
    finally:
        db_local.close()


def _update_movement(entry_id, new_amount, new_date, new_desc,
                     new_ref=None, new_notes=None):
    """يحدّث حركة خزينة: المبلغ + التاريخ + الوصف + الأسطر."""
    db_local = SessionLocal()
    try:
        entry = db_local.query(models.JournalEntry).filter(
            models.JournalEntry.id == entry_id
        ).first()
        if not entry:
            raise ValueError("الحركة غير موجودة")

        # ✅ فحص الفترة الحالية والجديدة
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
            raise ValueError("تعذّر تحديد أسطر القيد (خزينة/طرف مقابل)")

        direction = _movement_direction(entry)
        dir_label = "وارد" if direction == "in" else "صادر"

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
        "💰 الإيرادات": [],
        "👥 تحصيل من عملاء": [],
        "💵 قروض وسلف": [],
        "🏦 حقوق ملكية": [],
        "💸 مصروفات": [],
        "📦 الأصول": [],
        "🤝 الموردون": [],
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


def _extract_original_desc(description):
    """يستخرج الوصف الأصلي من نص القيد."""
    if not description:
        return ""
    parts = description.split(" — ", 1)
    head = parts[0]
    if ":" in head:
        head = head.split(":", 1)[1]
    head = re.sub(r"\s*\[.*?\]\s*$", "", head)
    return head.strip()


# ==========================================
# التبويبات
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "➕ تسجيل حركة جديدة",
    "📋 سجل الحركات",
    "⚙️ تعديل / حذف حركة",
    "📊 تقرير الخزينة",
])


# ==========================================
# التبويب 1: تسجيل حركة جديدة
# ==========================================
with tab1:
    st.subheader("➕ تسجيل حركة جديدة")
    st.caption("💡 بعد الحفظ، الحقول هتتفرّغ تلقائيًا.")

    cash_boxes = db.query(CashBox).filter(CashBox.is_active == True).all()
    if not cash_boxes:
        st.error("⚠️ لا توجد خزائن مفعّلة!")
        st.stop()

    box_opts = {b.id: f"{b.name} ({b.code})" for b in cash_boxes}
    selected_box_id = st.selectbox(
        "1️⃣ الخزينة:",
        options=list(box_opts.keys()),
        format_func=lambda x: box_opts[x],
        key="cm_box",
    )

    st.markdown("### 2️⃣ نوع الحركة")
    direction = st.radio(
        "الاتجاه:",
        ["in", "out"],
        format_func=lambda x: "💰 وارد (استلام نقدية)" if x == "in" else "💸 صادر (دفع نقدية)",
        horizontal=True, key="cm_dir",
    )

    st.markdown("### 3️⃣ الحساب المقابل (سبب الحركة)")
    counter_groups = _get_counter_account_groups()

    if not counter_groups:
        st.error("⚠️ لا توجد حسابات طرف مقابل!")
        st.stop()

    for group_name, accounts in counter_groups.items():
        with st.expander(f"{group_name} ({len(accounts)})", expanded=False):
            acc_opts = {a.id: f"{a.code} — {a.name}" for a in accounts}
            picked = st.radio(
                f"اختر من {group_name}:",
                options=list(acc_opts.keys()),
                format_func=lambda x: acc_opts[x],
                key=f"cm_acc_{group_name}",
                label_visibility="collapsed",
            )
            if st.button(f"✔️ اختيار من {group_name}", key=f"cm_pick_{group_name}"):
                st.session_state["cm_selected_account"] = picked

    selected_account_id = st.session_state.get("cm_selected_account")
    if selected_account_id:
        acc = db.query(Account).filter(Account.id == selected_account_id).first()
        if acc:
            st.success(f"✅ الحساب المختار: **{acc.code} — {acc.name}**")
    else:
        st.warning("👆 اختر حساب من القوائم أعلاه.")

    st.markdown("### 4️⃣ تفاصيل الحركة")

    col_d, col_t = st.columns(2)
    with col_d:
        cm_date = st.date_input("التاريخ:", value=datetime.now().date(), key="cm_date")
    with col_t:
        cm_time = st.time_input("الوقت:", value=datetime.now().time(), key="cm_time")

    amount = st.number_input(
        "المبلغ (ج.م):", min_value=0.01, step=100.0, value=100.0,
        format="%.2f", key="cm_amount",
    )
    description = st.text_area(
        "الوصف:", placeholder="مثال: نصيب الأخ في بضاعة أونلاين",
        key="cm_desc",
    )
    ref_no = st.text_input("رقم المرجع (اختياري):", key="cm_ref")
    notes = st.text_area("ملاحظات (اختياري):", key="cm_notes", height=60)

    if st.button("💾 حفظ الحركة", type="primary", use_container_width=True, key="cm_save"):
        if not selected_account_id:
            st.error("❌ اختر الحساب المقابل أولاً.")
        elif not description.strip():
            st.error("❌ يرجى إدخال الوصف.")
        elif amount <= 0:
            st.error("❌ المبلغ يجب أن يكون أكبر من صفر.")
        else:
            try:
                cm_dt = datetime.combine(cm_date, cm_time)

                # ✅ فحص الفترة قبل الحفظ
                check_period_open(cm_dt, entity="تسجيل حركة خزينة")

                if direction == "in":
                    _create_cash_movement(
                        cash_box_id=int(selected_box_id),
                        counter_account_id=int(selected_account_id),
                        amount=float(amount),
                        description=description.strip(),
                        direction="in",
                        reference_number=ref_no or None,
                        notes=notes or None,
                        created_by=current_user_id,
                        movement_date=cm_dt,
                    )
                else:
                    acc_obj = db.query(Account).filter(Account.id == selected_account_id).first()
                    if acc_obj.type == AccountType.EXPENSE:
                        cat = _get_or_create_category_for_account(db, acc_obj)
                        create_expense(
                            category_id=cat.id,
                            amount=float(amount),
                            description=description.strip(),
                            payment_method="cash",
                            cash_box_id=int(selected_box_id),
                            reference_number=ref_no or None,
                            notes=notes or None,
                            expense_date=cm_dt,
                            created_by=current_user_id,
                        )
                    else:
                        _create_cash_movement(
                            cash_box_id=int(selected_box_id),
                            counter_account_id=int(selected_account_id),
                            amount=float(amount),
                            description=description.strip(),
                            direction="out",
                            reference_number=ref_no or None,
                            notes=notes or None,
                            created_by=current_user_id,
                            movement_date=cm_dt,
                        )

                direction_label = "وارد" if direction == "in" else "صادر"
                st.success(f"✅ تم تسجيل حركة {direction_label} بمبلغ {amount:,.2f} ج.م")
                st.balloons()

                group_keys = [f"cm_acc_{g}" for g in counter_groups.keys()]
                pick_keys = [f"cm_pick_{g}" for g in counter_groups.keys()]
                queue_state_updates(
                    delete_keys=(
                        "cm_selected_account",
                        "cm_amount",
                        "cm_desc",
                        "cm_ref",
                        "cm_notes",
                        *group_keys,
                        *pick_keys,
                    ),
                    set_values={
                        "cm_amount": 100.0,
                        "cm_desc": "",
                        "cm_ref": "",
                        "cm_notes": "",
                    },
                )
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 2: سجل الحركات (عرض فقط)
# ==========================================
with tab2:
    st.subheader("📋 سجل حركات الخزينة")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_dir = st.selectbox("الاتجاه:", ["الكل", "وارد فقط", "صادر فقط"], key="lf_dir")
    with col_f2:
        start_filter = st.date_input("من تاريخ:",
                                     value=datetime.now().replace(day=1).date(), key="lf_start")
    with col_f3:
        end_filter = st.date_input("إلى تاريخ:",
                                    value=datetime.now().date(), key="lf_end")

    d = None
    if filter_dir == "وارد فقط":
        d = "in"
    elif filter_dir == "صادر فقط":
        d = "out"

    start_dt = datetime.combine(start_filter, datetime.min.time())
    end_dt = datetime.combine(end_filter, datetime.max.time())

    movements = _get_movements(direction=d, start=start_dt, end=end_dt)

    if movements:
        rows = []
        total_in = 0.0
        total_out = 0.0
        for m in movements:
            det = _movement_details(m)
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
                "الطرف المقابل": f"{det['counter_acc'].code} — {det['counter_acc'].name}" if det["counter_acc"] else "—",
                "المبلغ": det["amount"],
                "الوصف": m.description or "—",
            })
        df = pd.DataFrame(rows)
        st.dataframe(
            df.drop(columns=["ID"]), use_container_width=True, hide_index=True,
            column_config={
                "المسلسل": st.column_config.TextColumn("المسلسل", width="small"),
                "المبلغ": st.column_config.NumberColumn("المبلغ", format="%.2f"),
            },
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("إجمالي الوارد", f"{total_in:,.2f} ج.م")
        with c2:
            st.metric("إجمالي الصادر", f"{total_out:,.2f} ج.م")
        with c3:
            st.metric("الصافي", f"{total_in - total_out:,.2f} ج.م")

        st.info("💡 للتعديل أو الحذف، انتقل إلى تبويب **⚙️ تعديل / حذف حركة**.")
    else:
        st.info("لا توجد حركات في الفترة المحددة.")


# ==========================================
# التبويب 3: تعديل / حذف حركة
# ==========================================
with tab3:
    st.subheader("⚙️ تعديل / حذف حركة خزينة")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        edit_dir = st.selectbox("الاتجاه:", ["الكل", "وارد فقط", "صادر فقط"], key="ef_dir")
    with col_f2:
        edit_start = st.date_input("من تاريخ:",
                                   value=(datetime.now().replace(day=1)).date(), key="ef_start")
    with col_f3:
        edit_end = st.date_input("إلى تاريخ:",
                                 value=datetime.now().date(), key="ef_end")

    d_edit = None
    if edit_dir == "وارد فقط":
        d_edit = "in"
    elif edit_dir == "صادر فقط":
        d_edit = "out"

    edit_start_dt = datetime.combine(edit_start, datetime.min.time())
    edit_end_dt = datetime.combine(edit_end, datetime.max.time())

    edit_movements = _get_movements(direction=d_edit, start=edit_start_dt, end=edit_end_dt)

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

        selected_m_id = st.selectbox(
            "اختر الحركة (بالمسلسل):",
            options=list(m_opts.keys()),
            format_func=lambda x: m_opts[x],
            key="edit_m_select",
        )

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
                    st.metric("الاتجاه",
                              "💰 وارد" if det["direction"] == "in" else "💸 صادر")
                with c2:
                    st.metric("المبلغ الحالي", f"{det['amount']:,.2f} ج.م")
                with c3:
                    st.metric("التاريخ",
                              entry.date.strftime("%Y-%m-%d") if entry.date else "—")

                st.write(f"**الخزينة:** {det['cash_acc'].name if det['cash_acc'] else '—'}")
                if det["counter_acc"]:
                    st.write(f"**الطرف المقابل:** {det['counter_acc'].code} — {det['counter_acc'].name}")
                else:
                    st.write("**الطرف المقابل:** —")

                original_desc = _extract_original_desc(entry.description or "")

                st.markdown("---")
                st.markdown("### ✏️ تعديل البيانات")
                st.warning(
                    "⚠️ يمكنك تعديل **المبلغ، التاريخ، الوصف، والملاحظات**. "
                    "لتغيير **الاتجاه** أو **الحساب المقابل** → احذف وأعد الإنشاء."
                )

                with st.form(f"edit_m_form_{entry.id}"):
                    new_amount = st.number_input(
                        "المبلغ الجديد (ج.م):",
                        min_value=0.01,
                        value=float(det["amount"]),
                        step=100.0, format="%.2f",
                    )

                    col_d, col_t = st.columns(2)
                    with col_d:
                        new_date = st.date_input(
                            "التاريخ:",
                            value=entry.date.date() if entry.date else datetime.now().date(),
                        )
                    with col_t:
                        new_time = st.time_input(
                            "الوقت:",
                            value=entry.date.time() if entry.date else datetime.now().time(),
                        )

                    new_desc = st.text_area(
                        "الوصف:",
                        value=original_desc,
                        height=68,
                    )

                    new_notes = st.text_area(
                        "ملاحظات إضافية (اختياري):",
                        value="",
                        height=68,
                        help="ستُضاف إلى نهاية الوصف بين [ ]",
                    )

                    submitted = st.form_submit_button(
                        "💾 حفظ التعديلات", type="primary", use_container_width=True,
                    )

                if submitted:
                    if not new_desc.strip():
                        st.error("❌ الوصف مطلوب.")
                    elif new_amount <= 0:
                        st.error("❌ المبلغ يجب أن يكون أكبر من صفر.")
                    else:
                        try:
                            new_dt = datetime.combine(new_date, new_time)
                            _update_movement(
                                entry_id=entry.id,
                                new_amount=float(new_amount),
                                new_date=new_dt,
                                new_desc=new_desc.strip(),
                                new_notes=new_notes.strip() or None,
                            )
                            st.success(f"✅ تم تحديث الحركة `{serial}` بنجاح!")
                            queue_state_updates(delete_keys=("edit_m_select",))
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ خطأ: {e}")
                            st.code(traceback.format_exc())

                st.markdown("---")
                st.markdown("### 🗑 حذف الحركة")

                if can_modify():
                    st.error(f"⚠️ سيتم حذف الحركة `{serial}` نهائيًا مع قيودها المحاسبية.")
                    confirm = st.checkbox("✅ أؤكد الحذف النهائي",
                                           key=f"confirm_del_m_{entry.id}")
                    if st.button(
                        "🗑 حذف الحركة",
                        type="secondary",
                        disabled=not confirm,
                        use_container_width=True,
                        key=f"del_m_btn_{entry.id}",
                    ):
                        try:
                            _delete_movement(entry)
                            st.success(f"✅ تم حذف الحركة `{serial}`.")
                            queue_state_updates(delete_keys=("edit_m_select",))
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
        rep_start = st.date_input("من تاريخ:",
                                  value=datetime.now().replace(day=1).date(),
                                  key="rep_start")
    with col2:
        rep_end = st.date_input("إلى تاريخ:",
                                value=datetime.now().date(), key="rep_end")

    if st.button("📊 عرض التقرير", type="primary", key="show_report"):
        s = datetime.combine(rep_start, datetime.min.time())
        e = datetime.combine(rep_end, datetime.max.time())

        movements = _get_movements(start=s, end=e)
        total_in = sum(
            _movement_details(m)["amount"] for m in movements
            if _movement_details(m)["direction"] == "in"
        )
        total_out = sum(
            _movement_details(m)["amount"] for m in movements
            if _movement_details(m)["direction"] == "out"
        )
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