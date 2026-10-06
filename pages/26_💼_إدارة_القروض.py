# pages/26_💼_إدارة_القروض.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify, require_modify
render_sidebar()

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from database import SessionLocal
import models
from models import Loan, LoanInstallment, LoanType, LoanStatus, CashBox
from services import (
    create_loan, pay_loan_installment, get_loans_summary,
    get_loan_schedule, check_overdue_installments,
    calculate_loan_installments
)
from auth_required import require_login, get_current_user_id, get_current_user_name

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="إدارة القروض", page_icon="💼", layout="wide")
st.title("💼 إدارة القروض والتمويل")
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()


def _delete_loan(loan_id):
    """حذف قرض + كل الأقساط + القيود المحاسبية."""
    db_local = SessionLocal()
    try:
        loan = db_local.query(Loan).filter(Loan.id == loan_id).first()
        if not loan:
            raise ValueError("القرض غير موجود")

        # حذف الأقساط
        db_local.query(LoanInstallment).filter(LoanInstallment.loan_id == loan_id).delete()

        # حذف القيود المحاسبية المرتبطة
        je_ids = [r[0] for r in db_local.query(models.JournalEntry.id).filter(
            models.JournalEntry.reference_id == loan_id,
            models.JournalEntry.reference_type.in_(["loan", "loan_payment"]),
        ).all()]
        if je_ids:
            db_local.query(models.JournalLine).filter(
                models.JournalLine.entry_id.in_(je_ids)
            ).delete(synchronize_session=False)
            db_local.query(models.JournalEntry).filter(
                models.JournalEntry.id.in_(je_ids)
            ).delete(synchronize_session=False)

        db_local.delete(loan)
        db_local.commit()
    except Exception:
        db_local.rollback()
        raise
    finally:
        db_local.close()


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "➕ إضافة قرض جديد",
    "📋 قائمة القروض",
    "💳 سداد الأقساط",
    "📊 جدول الأقساط",
    "⚠️ الأقساط المتأخرة",
])


# ==========================================
# التبويب 1: إضافة قرض جديد
# ==========================================
with tab1:
    st.subheader("➕ إضافة قرض جديد")
    st.caption("💡 بعد الحفظ، الحقول هتتفرّغ تلقائيًا.")

    loan_type = st.radio(
        "نوع القرض:",
        [LoanType.RECEIVED.value, LoanType.GIVEN.value],
        horizontal=True,
        key="new_loan_type",
    )
    actual_type = LoanType.RECEIVED if loan_type == LoanType.RECEIVED.value else LoanType.GIVEN

    col1, col2 = st.columns(2)

    with col1:
        borrower_name = st.text_input(
            "اسم المقترض/المُقرض:",
            placeholder="مثال: بنك الأهلي، محمد أحمد...",
            key="new_loan_borrower",
        )
        borrower_type = st.selectbox(
            "نوع المقترض:",
            ["bank (بنك)", "customer (عميل)", "employee (موظف)", "other (أخرى)"],
            key="new_loan_borrower_type",
        )
        principal_amount = st.number_input(
            "المبلغ الأصلي:",
            min_value=1000.0, step=10000.0, format="%.2f",
            key="new_loan_principal",
        )
        annual_interest_rate = st.number_input(
            "نسبة الفائدة السنوية (%):",
            min_value=0.0, max_value=100.0, value=12.0, step=0.5,
            format="%.2f", key="new_loan_rate",
        )

    with col2:
        loan_date = st.date_input("تاريخ القرض:", value=datetime.now().date(),
                                  key="new_loan_date")
        term_months = st.number_input(
            "مدة القرض (أشهر):", min_value=1, max_value=360, value=12, step=1,
            key="new_loan_term",
        )

        if principal_amount > 0 and term_months > 0:
            monthly_payment, total_interest = calculate_loan_installments(
                principal_amount, annual_interest_rate, term_months
            )
            st.success(f"💰 القسط الشهري: **{monthly_payment:,.2f} ج.م**")
            st.info(f"📊 إجمالي الفوائد: **{total_interest:,.2f} ج.م**")
        else:
            monthly_payment = 0
            total_interest = 0

        cash_boxes = db.query(CashBox).filter(CashBox.is_active == True).all()
        cash_box_dict = {box.id: f"{box.name} ({box.code})" for box in cash_boxes}
        if cash_boxes:
            selected_cash_box_id = st.selectbox(
                "الخزينة/الحساب:",
                options=list(cash_box_dict.keys()),
                format_func=lambda x: cash_box_dict[x],
                key="new_loan_box",
            )
        else:
            st.warning("⚠️ لا توجد خزائن متاحة!")
            selected_cash_box_id = None

        notes = st.text_area("ملاحظات (اختياري):", key="new_loan_notes")

    if st.button("💾 إنشاء القرض", type="primary", use_container_width=True):
        if not borrower_name:
            st.error("❌ يرجى إدخال اسم المقترض/المُقرض")
        elif principal_amount <= 0:
            st.error("❌ يرجى إدخال مبلغ صحيح")
        elif term_months <= 0:
            st.error("❌ يرجى إدخال مدة صحيحة")
        else:
            try:
                loan_datetime = datetime.combine(loan_date, datetime.min.time())
                create_loan(
                    loan_type=actual_type,
                    borrower_name=borrower_name,
                    borrower_type=borrower_type.split(" ")[0],
                    principal_amount=principal_amount,
                    annual_interest_rate=annual_interest_rate,
                    loan_date=loan_datetime,
                    term_months=term_months,
                    cash_box_id=selected_cash_box_id,
                    notes=notes if notes else None,
                    created_by=current_user_id,
                )
                st.success("✅ تم إنشاء القرض بنجاح!")
                st.balloons()

                # ✅ تفريغ كامل
                queue_state_updates(
                    delete_keys=(
                        "new_loan_borrower", "new_loan_principal", "new_loan_rate",
                        "new_loan_date", "new_loan_term", "new_loan_box", "new_loan_notes",
                        "new_loan_borrower_type",
                    ),
                    set_values={
                        "new_loan_borrower": "",
                        "new_loan_principal": 1000.0,
                        "new_loan_rate": 12.0,
                        "new_loan_term": 12,
                        "new_loan_notes": "",
                    },
                )
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 2: قائمة القروض (مع التعديل والحذف)
# ==========================================
with tab2:
    st.subheader("📋 قائمة القروض")

    loan_type_filter = st.radio(
        "تصفية حسب النوع:",
        ["الكل", LoanType.RECEIVED.value, LoanType.GIVEN.value],
        horizontal=True,
        key="filter_loan_type",
    )

    if loan_type_filter == "الكل":
        summary = get_loans_summary()
    else:
        actual_filter = LoanType.RECEIVED if loan_type_filter == LoanType.RECEIVED.value else LoanType.GIVEN
        summary = get_loans_summary(actual_filter)

    loans = summary["loans"]

    if loans:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("إجمالي المبلغ الأصلي", f"{summary['total_principal']:,.2f} ج.م")
        with col2:
            st.metric("إجمالي الفوائد", f"{summary['total_interest']:,.2f} ج.م")
        with col3:
            st.metric("إجمالي المدفوع", f"{summary['total_paid']:,.2f} ج.م")
        with col4:
            st.metric("إجمالي المتبقي", f"{summary['total_remaining']:,.2f} ج.م")

        st.markdown("---")

        data = []
        for loan in loans:
            data.append({
                "مسلسل": loan.loan_number,
                "النوع": loan.loan_type.value,
                "المقترض/المُقرض": loan.borrower_name,
                "تاريخ القرض": loan.loan_date.strftime("%Y-%m-%d"),
                "الأصلي": f"{loan.principal_amount:,.2f}",
                "المدفوع": f"{loan.paid_amount:,.2f}",
                "المتبقي": f"{loan.remaining_amount:,.2f}",
                "الحالة": loan.status.value,
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # =============== التعديل والحذف ===============
        if can_modify():
            st.markdown("---")
            st.subheader("⚙️ تعديل / حذف قرض")

            loan_ids = [l.id for l in loans]
            selected_loan_id = st.selectbox(
                "اختر قرض:",
                options=loan_ids,
                format_func=lambda x: next(
                    (f"{l.loan_number} — {l.borrower_name} ({l.principal_amount:,.2f})"
                     for l in loans if l.id == x),
                    str(x),
                ),
                key="sel_loan_edit",
            )

            if selected_loan_id:
                selected_loan = next((l for l in loans if l.id == selected_loan_id), None)

                # تفاصيل مختصرة
                st.markdown(f"### 📄 تفاصيل القرض: **{selected_loan.loan_number}**")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("المبلغ الأصلي", f"{selected_loan.principal_amount:,.2f}")
                with c2:
                    st.metric("المدفوع", f"{selected_loan.paid_amount:,.2f}")
                with c3:
                    st.metric("المتبقي", f"{selected_loan.remaining_amount:,.2f}")

                # ---------- التعديل ----------
                with st.form(f"edit_loan_form_{selected_loan_id}"):
                    new_borrower = st.text_input(
                        "اسم المقترض/المُقرض:",
                        value=selected_loan.borrower_name,
                    )
                    new_notes = st.text_area(
                        "ملاحظات:",
                        value=selected_loan.notes or "",
                        height=80,
                    )
                    edit_submitted = st.form_submit_button(
                        "💾 حفظ التعديلات", type="primary",
                    )

                if edit_submitted:
                    try:
                        if not new_borrower.strip():
                            st.error("❌ الاسم مطلوب.")
                        else:
                            selected_loan.borrower_name = new_borrower.strip()
                            selected_loan.notes = new_notes.strip() or None
                            db.commit()
                            st.success("✅ تم التعديل بنجاح!")
                            queue_state_updates(delete_keys=("sel_loan_edit",))
                            st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ خطأ: {e}")

                # ---------- الحذف ----------
                st.markdown("#### 🗑 حذف القرض")
                pending_inst = db.query(LoanInstallment).filter(
                    LoanInstallment.loan_id == selected_loan_id,
                    LoanInstallment.status == "pending",
                ).count()
                paid_inst = db.query(LoanInstallment).filter(
                    LoanInstallment.loan_id == selected_loan_id,
                    LoanInstallment.status == "paid",
                ).count()

                st.warning(
                    f"⚠️ الحذف سيمسح القرض + **{pending_inst + paid_inst}** قسط "
                    f"({paid_inst} مدفوع، {pending_inst} معلق) + القيود المحاسبية."
                )
                confirm_del = st.checkbox(
                    "✅ أؤكد الحذف النهائي",
                    key=f"confirm_del_loan_{selected_loan_id}",
                )
                if st.button(
                    "🗑 حذف القرض",
                    type="secondary",
                    disabled=not confirm_del,
                    use_container_width=True,
                    key=f"del_loan_btn_{selected_loan_id}",
                ):
                    try:
                        _delete_loan(selected_loan_id)
                        st.success("✅ تم حذف القرض بنجاح!")
                        queue_state_updates(delete_keys=("sel_loan_edit",))
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")
        else:
            st.info("⛔ التعديل والحذف للمدير فقط.")

        # رسم بياني
        fig = px.pie(df, values="المتبقي", names="المقترض/المُقرض",
                     title="توزيع القروض المتبقية")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("لا توجد قروض مسجلة.")


# ==========================================
# التبويب 3: سداد الأقساط
# ==========================================
with tab3:
    st.subheader("💳 سداد أقساط القروض")

    active_loans = db.query(Loan).filter(Loan.status == LoanStatus.ACTIVE).all()

    if not active_loans:
        st.info("لا توجد قروض نشطة.")
    else:
        selected_loan_id = st.selectbox(
            "اختر القرض:",
            options=[l.id for l in active_loans],
            format_func=lambda x: next(
                (f"{l.loan_number} - {l.borrower_name} ({l.loan_type.value})"
                 for l in active_loans if l.id == x), str(x),
            ),
            key="pay_loan_select",
        )

        if selected_loan_id:
            loan = db.query(Loan).filter(Loan.id == selected_loan_id).first()
            st.markdown(f"### 📄 تفاصيل القرض: {loan.loan_number}")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("المبلغ الأصلي", f"{loan.principal_amount:,.2f} ج.م")
            with col2:
                st.metric("المدفوع", f"{loan.paid_amount:,.2f} ج.م")
            with col3:
                st.metric("المتبقي", f"{loan.remaining_amount:,.2f} ج.م")

            st.markdown("---")
            st.markdown("### 💰 الأقساط المستحقة")

            pending_installments = db.query(LoanInstallment).filter(
                LoanInstallment.loan_id == loan.id,
                LoanInstallment.status == "pending",
            ).order_by(LoanInstallment.installment_number).all()

            if pending_installments:
                # قائمة الخزائن
                cash_boxes = db.query(CashBox).filter(CashBox.is_active == True).all()
                box_opts = {b.id: f"{b.name} ({b.code})" for b in cash_boxes}

                for inst in pending_installments:
                    is_overdue = inst.due_date < datetime.now()
                    if is_overdue:
                        st.error(f"⚠️ قسط #{inst.installment_number} - "
                                 f"مستحق في {inst.due_date.strftime('%Y-%m-%d')} - "
                                 f"مبلغ: {inst.total_amount:,.2f} ج.م")
                    else:
                        st.info(f"📌 قسط #{inst.installment_number} - "
                                f"مستحق في {inst.due_date.strftime('%Y-%m-%d')} - "
                                f"مبلغ: {inst.total_amount:,.2f} ج.م")

                    with st.expander(f"💳 سداد القسط #{inst.installment_number}", expanded=False):
                        if not cash_boxes:
                            st.error("لا توجد خزائن!")
                        else:
                            cb = st.selectbox(
                                "الخزينة:",
                                options=list(box_opts.keys()),
                                format_func=lambda x: box_opts[x],
                                key=f"cb_{inst.id}",
                            )
                            if st.button("✅ تأكيد السداد",
                                         key=f"confirm_pay_{inst.id}",
                                         type="primary"):
                                try:
                                    pay_loan_installment(
                                        installment_id=inst.id,
                                        payment_date=datetime.now(),
                                        cash_box_id=int(cb),
                                        created_by=current_user_id,
                                    )
                                    st.success(f"✅ تم سداد القسط #{inst.installment_number}!")
                                    queue_state_updates(
                                        delete_keys=(f"cb_{inst.id}",
                                                     f"confirm_pay_{inst.id}",
                                                     "pay_loan_select"),
                                    )
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ {e}")
            else:
                st.success("✅ جميع الأقساط مسددة!")

    st.markdown("---")
    st.subheader("📋 آخر الأقساط المسددة")

    paid_installments = db.query(LoanInstallment).filter(
        LoanInstallment.status == "paid"
    ).order_by(LoanInstallment.paid_date.desc()).limit(20).all()

    if paid_installments:
        data = []
        for inst in paid_installments:
            loan = db.query(Loan).filter(Loan.id == inst.loan_id).first()
            data.append({
                "مسلسل القرض": loan.loan_number if loan else "-",
                "المقترض": loan.borrower_name if loan else "-",
                "رقم القسط": inst.installment_number,
                "المبلغ": f"{inst.total_amount:,.2f} ج.م",
                "تاريخ السداد": inst.paid_date.strftime("%Y-%m-%d") if inst.paid_date else "-",
            })
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد أقساط مسددة.")


# ==========================================
# التبويب 4: جدول الأقساط
# ==========================================
with tab4:
    st.subheader("📊 جدول الأقساط التفصيلي")

    all_loans = db.query(Loan).all()
    if not all_loans:
        st.info("لا توجد قروض.")
    else:
        sel_id = st.selectbox(
            "اختر قرضاً:",
            options=[l.id for l in all_loans],
            format_func=lambda x: next(
                (f"{l.loan_number} - {l.borrower_name}" for l in all_loans if l.id == x),
                str(x)),
            key="schedule_loan_select",
        )
        if sel_id:
            schedule_data = get_loan_schedule(sel_id)
            if schedule_data:
                loan = schedule_data["loan"]
                schedule = schedule_data["schedule"]
                st.markdown(f"### 📄 قرض: {loan.loan_number} - {loan.borrower_name}")

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("المبلغ الأصلي", f"{loan.principal_amount:,.2f}")
                with c2:
                    st.metric("إجمالي الفوائد", f"{loan.total_interest:,.2f}")
                with c3:
                    st.metric("القسط الشهري", f"{loan.installment_amount:,.2f}")
                with c4:
                    st.metric("عدد الأقساط", loan.term_months)

                if schedule:
                    df_schedule = pd.DataFrame(schedule)
                    st.dataframe(df_schedule, use_container_width=True, hide_index=True)


# ==========================================
# التبويب 5: الأقساط المتأخرة
# ==========================================
with tab5:
    st.subheader("⚠️ الأقساط المتأخرة")

    overdue_list = check_overdue_installments()
    if overdue_list:
        st.warning(f"⚠️ يوجد **{len(overdue_list)}** قسط متأخر!")
        data = []
        for item in overdue_list:
            data.append({
                "مسلسل القرض": item["loan_number"],
                "المقترض": item["borrower"],
                "النوع": item["loan_type"],
                "رقم القسط": item["installment_number"],
                "تاريخ الاستحقاق": item["due_date"].strftime("%Y-%m-%d"),
                "المبلغ": f"{item['amount']:,.2f} ج.م",
                "أيام التأخير": item["days_overdue"],
            })
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

        total_overdue = sum(i["amount"] for i in overdue_list)
        st.error(f"إجمالي المبالغ المتأخرة: **{total_overdue:,.2f} ج.م**")
    else:
        st.success("✅ لا توجد أقساط متأخرة!")

db.close()