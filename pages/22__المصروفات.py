# pages/22_💸_المصروفات.py
# صفحة الإيرادات والمصروفات — تختار الحساب من شجرة الحسابات مباشرة
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

import streamlit as st
import pandas as pd
from datetime import datetime

from database import SessionLocal
import models
from models import Account, AccountType, CashBox
from services import (
    create_expense, delete_expense, get_expenses_summary,
    get_expense_categories, create_expense_category,
)
from auth_required import require_login, get_current_user_id, get_current_user_name
from sidebar import can_modify

# ==========================================
# التحقق من الدخول
# ==========================================
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="الإيرادات والمصروفات", page_icon="💹", layout="wide")
st.title("💹 إدارة الإيرادات والمصروفات")
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()


# ==========================================
# دوال مساعدة
# ==========================================
def _create_transaction_entry(account_id, amount, description, transaction_type,
                              cash_box_id, reference_number=None, notes=None,
                              created_by=None, transaction_date=None):
    """ينشئ قيد محاسبي لإيراد أو مصروف مباشرة من الحساب."""
    from datetime import datetime as _dt
    db = SessionLocal()
    try:
        cash_box = db.query(CashBox).filter(CashBox.id == cash_box_id).first()
        if not cash_box:
            raise ValueError("الخزينة غير موجودة")

        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise ValueError("الحساب غير موجود")

        entry_date = transaction_date or _dt.now()
        ref_type = "revenue" if transaction_type == "revenue" else "expense"

        entry = models.JournalEntry(
            date=entry_date,
            description=f"{'إيراد' if ref_type == 'revenue' else 'مصروف'}: {description}",
            reference_type=ref_type,
            created_by=created_by,
        )
        db.add(entry)
        db.flush()

        if ref_type == "expense":
            # مصروف: مدين الحساب، دائن الخزينة
            db.add(models.JournalLine(
                entry_id=entry.id, account_id=account_id,
                debit=float(amount), credit=0.0
            ))
            db.add(models.JournalLine(
                entry_id=entry.id, account_id=cash_box.account_id,
                debit=0.0, credit=float(amount)
            ))
        else:
            # إيراد: مدين الخزينة، دائن الحساب
            db.add(models.JournalLine(
                entry_id=entry.id, account_id=cash_box.account_id,
                debit=float(amount), credit=0.0
            ))
            db.add(models.JournalLine(
                entry_id=entry.id, account_id=account_id,
                debit=0.0, credit=float(amount)
            ))

        db.commit()
        return entry
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _get_transactions(transaction_type=None, start=None, end=None):
    """يرجع الحركات (إيرادات/مصروفات) من JournalEntry."""
    q = db.query(models.JournalEntry).filter(
        models.JournalEntry.reference_type.in_(["revenue", "expense"])
    )
    if transaction_type:
        q = q.filter(models.JournalEntry.reference_type == transaction_type)
    if start:
        q = q.filter(models.JournalEntry.date >= start)
    if end:
        q = q.filter(models.JournalEntry.date <= end)
    return q.order_by(models.JournalEntry.date.desc()).all()


def _transaction_details(entry):
    """يستخرج حساب الحركة + المبلغ."""
    lines = db.query(models.JournalLine).filter(
        models.JournalLine.entry_id == entry.id
    ).all()
    # القيد: سطرين — واحد debit والتاني credit
    main_account = None
    amount = 0.0
    for ln in lines:
        acc = db.query(Account).filter(Account.id == ln.account_id).first()
        if not acc:
            continue
        # للسطر اللي مش الخزينة
        is_cashbox = db.query(CashBox).filter(CashBox.account_id == acc.id).first() is not None
        if not is_cashbox:
            main_account = acc
            amount = float(ln.debit or 0) or float(ln.credit or 0)
    return main_account, amount


# ==========================================
# التبويبات
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "➕ تسجيل حركة جديدة",
    "📋 سجل الحركات",
    "🗂️ إدارة التصنيفات",
    "📊 تقرير الإيرادات والمصروفات",
])


# ==========================================
# التبويب 1: تسجيل حركة (إيراد أو مصروف)
# ==========================================
with tab1:
    st.subheader("➕ تسجيل حركة جديدة")

    # ✅ اختيار النوع
    transaction_type = st.radio(
        "نوع الحركة:",
        ["💰 إيراد", "💸 مصروف"],
        horizontal=True,
        key="trans_type",
    )
    is_revenue = "إيراد" in transaction_type

    # التاريخ والوقت
    st.markdown("### 📅 تاريخ ووقت الحركة")
    col_d, col_t = st.columns(2)
    with col_d:
        t_date = st.date_input("التاريخ:", value=datetime.now().date(), key="t_date")
    with col_t:
        t_time = st.time_input("الوقت:", value=datetime.now().time(), key="t_time")

    # ✅ اختيار الحساب من شجرة الحسابات
    target_type = AccountType.REVENUE if is_revenue else AccountType.EXPENSE
    accounts = db.query(Account).filter(Account.type == target_type).order_by(Account.code).all()

    if not accounts:
        st.error(
            f"⚠️ لا توجد حسابات من نوع '**{'إيرادات' if is_revenue else 'مصروفات'}**' "
            "في شجرة الحسابات! أضفها أولاً من صفحة 'شجرة الحسابات'."
        )
        st.stop()

    acc_opts = {a.id: f"{a.code} — {a.name}" for a in accounts}
    selected_account_id = st.selectbox(
        "الحساب (من شجرة الحسابات):",
        options=list(acc_opts.keys()),
        format_func=lambda x: acc_opts[x],
        key="t_account",
    )

    amount = st.number_input(
        "المبلغ (ج.م):", min_value=0.01, step=100.0, value=100.0,
        format="%.2f", key="t_amount",
    )
    description = st.text_area(
        "الوصف:",
        placeholder="مثال: فاتورة كهرباء يناير" if not is_revenue else "مثال: دفعة من عميل",
        key="t_desc",
    )

    # طريقة الدفع
    payment_method = st.selectbox(
        "طريقة الدفع:",
        ["cash (نقدي)", "bank_transfer (تحويل بنكي)", "check (شيك)"],
        key="t_method",
    )
    actual_method = payment_method.split(" ")[0]

    # الخزينة
    cash_boxes = db.query(CashBox).filter(CashBox.is_active == True).all()
    if not cash_boxes:
        st.error("❌ لا توجد خزائن مفعّلة! أضف خزينة أولاً.")
        st.stop()

    box_opts = {b.id: f"{b.name} ({b.code})" for b in cash_boxes}
    selected_box_id = st.selectbox(
        "الخزينة:", options=list(box_opts.keys()),
        format_func=lambda x: box_opts[x], key="t_box",
    )

    ref_no = st.text_input("رقم المرجع (اختياري):", key="t_ref")
    notes = st.text_area("ملاحظات (اختياري):", key="t_notes", height=60)

    if st.button("💾 حفظ الحركة", type="primary", use_container_width=True, key="save_trans"):
        if not description.strip():
            st.error("❌ يرجى إدخال الوصف.")
        elif amount <= 0:
            st.error("❌ المبلغ يجب أن يكون أكبر من صفر.")
        else:
            try:
                trans_dt = datetime.combine(t_date, t_time)

                # ✅ إنشاء القيد المحاسبي
                _create_transaction_entry(
                    account_id=int(selected_account_id),
                    amount=float(amount),
                    description=description.strip(),
                    transaction_type="revenue" if is_revenue else "expense",
                    cash_box_id=int(selected_box_id),
                    reference_number=ref_no or None,
                    notes=notes or None,
                    created_by=current_user_id,
                    transaction_date=trans_dt,
                )

                # ✅ لو مصروف: نسجل كمان في جدول Expense (للتوافق مع التقارير القديمة)
                if not is_revenue:
                    try:
                        # ننشئ تصنيف لو مش موجود بنفس اسم الحساب
                        acc_obj = db.query(Account).filter(Account.id == selected_account_id).first()
                        cat = db.query(models.ExpenseCategory).filter(
                            models.ExpenseCategory.name == acc_obj.name
                        ).first()
                        if not cat:
                            cat = models.ExpenseCategory(
                                name=acc_obj.name,
                                description=f"تصنيف تلقائي للحساب {acc_obj.code}",
                                account_id=acc_obj.id,
                                is_active=True,
                                created_at=datetime.now(),
                            )
                            db.add(cat)
                            db.commit()
                            db.refresh(cat)

                        create_expense(
                            category_id=cat.id,
                            amount=float(amount),
                            description=description.strip(),
                            payment_method=actual_method,
                            cash_box_id=int(selected_box_id),
                            reference_number=ref_no or None,
                            notes=notes or None,
                            expense_date=trans_dt,
                            created_by=current_user_id,
                        )
                    except Exception as ex:
                        # لو فشل تسجيل المصروف، مش مشكلة — القيد اتعمل بالفعل
                        pass

                label = "الإيراد" if is_revenue else "المصروف"
                st.success(f"✅ تم تسجيل {label} بمبلغ {amount:,.2f} ج.م بنجاح!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 2: سجل الحركات
# ==========================================
with tab2:
    st.subheader("📋 سجل الحركات")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_type = st.selectbox("النوع:", ["الكل", "إيرادات فقط", "مصروفات فقط"], key="f_type")
    with col_f2:
        start_filter = st.date_input("من تاريخ:", value=datetime.now().replace(day=1).date(), key="f_start")
    with col_f3:
        end_filter = st.date_input("إلى تاريخ:", value=datetime.now().date(), key="f_end")

    ttype = None
    if filter_type == "إيرادات فقط":
        ttype = "revenue"
    elif filter_type == "مصروفات فقط":
        ttype = "expense"

    start_dt = datetime.combine(start_filter, datetime.min.time())
    end_dt = datetime.combine(end_filter, datetime.max.time())

    transactions = _get_transactions(transaction_type=ttype, start=start_dt, end=end_dt)

    if transactions:
        rows = []
        total_revenue = 0.0
        total_expense = 0.0
        for t in transactions:
            acc, amt = _transaction_details(t)
            is_rev = t.reference_type == "revenue"
            if is_rev:
                total_revenue += amt
            else:
                total_expense += amt
            rows.append({
                "ID": t.id,
                "التاريخ": t.date.strftime("%Y-%m-%d %H:%M") if t.date else "—",
                "النوع": "💰 إيراد" if is_rev else "💸 مصروف",
                "الحساب": f"{acc.code} — {acc.name}" if acc else "—",
                "المبلغ": amt,
                "الوصف": t.description or "—",
            })

        df = pd.DataFrame(rows)
        st.dataframe(
            df, use_container_width=True, hide_index=True,
            column_config={"المبلغ": st.column_config.NumberColumn("المبلغ", format="%.2f")},
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("إجمالي الإيرادات", f"{total_revenue:,.2f} ج.م")
        with c2:
            st.metric("إجمالي المصروفات", f"{total_expense:,.2f} ج.م")
        with c3:
            net = total_revenue - total_expense
            st.metric("الصافي", f"{net:,.2f} ج.م",
                      delta="ربح" if net >= 0 else "خسارة",
                      delta_color="normal" if net >= 0 else "inverse")

        # حذف حركة
        if can_modify():
            st.markdown("---")
            st.markdown("### 🗑 حذف حركة")
            t_ids = [t.id for t in transactions]
            selected_t = st.selectbox(
                "اختر حركة للحذف:",
                options=t_ids,
                format_func=lambda x: next((
                    f"#{t.id} — {t.date.strftime('%Y-%m-%d')} — {t.description}"
                    for t in transactions if t.id == x
                ), x),
                key="del_t_select",
            )
            confirm = st.checkbox("تأكيد الحذف", key="confirm_del_t")
            if st.button("🗑 حذف الحركة", type="secondary", disabled=not confirm,
                         use_container_width=True, key="del_t_btn"):
                try:
                    # حذف القيد المحاسبي
                    entry = db.query(models.JournalEntry).filter(
                        models.JournalEntry.id == selected_t
                    ).first()
                    if entry:
                        db.query(models.JournalLine).filter(
                            models.JournalLine.entry_id == entry.id
                        ).delete(synchronize_session=False)
                        db.delete(entry)
                        db.commit()
                    st.success("✅ تم الحذف.")
                    st.rerun()
                except Exception as e:
                    db.rollback()
                    st.error(f"❌ خطأ: {e}")
    else:
        st.info("لا توجد حركات في الفترة المحددة.")


# ==========================================
# التبويب 3: إدارة التصنيفات
# ==========================================
with tab3:
    st.subheader("🗂️ إدارة تصنيفات المصروفات")
    st.caption("ملاحظة: هذه التصنيفات مرتبطة بالمصروفات فقط (للتقارير القديمة).")

    # التصنيفات
    all_cats = get_expense_categories(include_inactive=True)
    expense_accounts = db.query(Account).filter(
        Account.type == AccountType.EXPENSE
    ).order_by(Account.code).all()
    acc_opts = {a.id: f"{a.code} — {a.name}" for a in expense_accounts}

    # إضافة
    with st.expander("➕ إضافة تصنيف مصروفات جديد", expanded=not all_cats):
        if not acc_opts:
            st.error("⚠️ لا توجد حسابات مصروفات في شجرة الحسابات!")
        else:
            with st.form("add_cat_form", clear_on_submit=True):
                new_name = st.text_input("اسم التصنيف:", placeholder="مثال: إيجار، كهرباء...")
                new_desc = st.text_area("الوصف (اختياري):", height=60)
                new_acc_id = st.selectbox(
                    "الحساب المحاسبي:",
                    options=list(acc_opts.keys()),
                    format_func=lambda x: acc_opts[x],
                )
                sub = st.form_submit_button("💾 إنشاء التصنيف", type="primary")
            if sub:
                try:
                    if not new_name.strip():
                        st.error("❌ الاسم مطلوب.")
                    else:
                        create_expense_category(
                            name=new_name.strip(),
                            description=new_desc.strip() or None,
                            account_id=int(new_acc_id),
                            created_by=current_user_id,
                        )
                        st.success(f"✅ تم إنشاء '{new_name}'.")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

    st.markdown("---")

    # قائمة
    if all_cats:
        rows = []
        for c in all_cats:
            acc = db.query(Account).filter(Account.id == c.account_id).first()
            cnt = db.query(models.Expense).filter(models.Expense.category_id == c.id).count()
            rows.append({
                "ID": c.id, "الاسم": c.name,
                "الوصف": c.description or "—",
                "الحساب": f"{acc.code} — {acc.name}" if acc else "—",
                "عدد المصروفات": cnt,
                "الحالة": "✅ نشط" if c.is_active else "⛔ معطل",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد تصنيفات.")


# ==========================================
# التبويب 4: تقرير الإيرادات والمصروفات
# ==========================================
with tab4:
    st.subheader("📊 تقرير الإيرادات والمصروفات")

    col1, col2 = st.columns(2)
    with col1:
        rep_start = st.date_input("من تاريخ:", value=datetime.now().replace(day=1).date(),
                                  key="rep_start")
    with col2:
        rep_end = st.date_input("إلى تاريخ:", value=datetime.now().date(), key="rep_end")

    if st.button("📊 عرض التقرير", type="primary", key="show_report"):
        s = datetime.combine(rep_start, datetime.min.time())
        e = datetime.combine(rep_end, datetime.max.time())

        revs = _get_transactions("revenue", s, e)
        exps = _get_transactions("expense", s, e)

        total_r = sum(_transaction_details(t)[1] for t in revs)
        total_e = sum(_transaction_details(t)[1] for t in exps)
        net = total_r - total_e

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("إجمالي الإيرادات", f"{total_r:,.2f} ج.م")
        with c2:
            st.metric("إجمالي المصروفات", f"{total_e:,.2f} ج.م")
        with c3:
            st.metric("الصافي", f"{net:,.2f} ج.م",
                      delta="ربح" if net >= 0 else "خسارة",
                      delta_color="normal" if net >= 0 else "inverse")

        # تجميع حسب الحساب
        rev_by_acc = {}
        for t in revs:
            acc, amt = _transaction_details(t)
            key = f"{acc.code} — {acc.name}" if acc else "غير معروف"
            rev_by_acc[key] = rev_by_acc.get(key, 0) + amt

        exp_by_acc = {}
        for t in exps:
            acc, amt = _transaction_details(t)
            key = f"{acc.code} — {acc.name}" if acc else "غير معروف"
            exp_by_acc[key] = exp_by_acc.get(key, 0) + amt

        st.markdown("---")
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("### 💰 الإيرادات حسب الحساب")
            if rev_by_acc:
                df_r = pd.DataFrame(list(rev_by_acc.items()), columns=["الحساب", "المبلغ"])
                st.dataframe(df_r, use_container_width=True, hide_index=True)
                st.bar_chart(df_r.set_index("الحساب"))
            else:
                st.info("لا توجد إيرادات.")

        with col_b:
            st.markdown("### 💸 المصروفات حسب الحساب")
            if exp_by_acc:
                df_e = pd.DataFrame(list(exp_by_acc.items()), columns=["الحساب", "المبلغ"])
                st.dataframe(df_e, use_container_width=True, hide_index=True)
                st.bar_chart(df_e.set_index("الحساب"))
            else:
                st.info("لا توجد مصروفات.")


db.close()