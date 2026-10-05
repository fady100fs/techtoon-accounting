# pages/22_💸_المصروفات.py
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
from models import ExpenseCategory, Expense, CashBox, Account
from services import (
    create_expense_category, create_expense, get_expenses_summary,
    delete_expense,
    get_expense_categories, get_expense_category_by_id,
    update_expense_category, delete_expense_category,
    deactivate_expense_category, activate_expense_category,
    get_expense_category_usage,
)
from auth_required import require_login, get_current_user_id, get_current_user_name
from sidebar import can_modify

# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="المصروفات", page_icon="💸", layout="wide")
st.title("💸 إدارة المصروفات التشغيلية")
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

tab1, tab2, tab3, tab4 = st.tabs([
    "➕ تسجيل مصروف جديد",
    "📋 سجل المصروفات",
    "🗂️ إدارة تصنيفات المصروفات",
    "📊 تقرير المصروفات"
])

# ==========================================
# التبويب 1: تسجيل مصروف جديد
# ==========================================
with tab1:
    st.subheader("➕ تسجيل مصروف جديد")

    # جلب التصنيفات النشطة
    categories = get_expense_categories(include_inactive=False)

    if not categories:
        st.warning(
            "⚠️ لا توجد تصنيفات مصروفات! "
            "يرجى إضافتها أولاً من تبويب **'🗂️ إدارة تصنيفات المصروفات'**."
        )
        st.stop()

    # التاريخ والوقت
    st.markdown("### 📅 تاريخ ووقت المصروف")
    col_date, col_time = st.columns(2)
    with col_date:
        expense_date = st.date_input("التاريخ:", value=datetime.now().date(),
                                     key="expense_date")
    with col_time:
        expense_time = st.time_input("الوقت:", value=datetime.now().time(),
                                     key="expense_time")

    # التصنيف
    category_dict = {cat.id: cat.name for cat in categories}
    selected_category_id = st.selectbox(
        "تصنيف المصروف:",
        options=list(category_dict.keys()),
        format_func=lambda x: category_dict[x]
    )

    # المبلغ والوصف
    amount = st.number_input("مبلغ المصروف:", min_value=0.01, step=100.0,
                             format="%.2f")
    description = st.text_area("وصف المصروف:",
                               placeholder="مثال: فاتورة كهرباء شهر يناير...")

    # طريقة الدفع
    payment_method = st.selectbox(
        "طريقة الدفع:",
        ["cash (نقدي)", "bank_transfer (تحويل بنكي)", "check (شيك)"]
    )
    actual_method = payment_method.split(" ")[0]

    # الخزينة
    cash_boxes = db.query(CashBox).filter(CashBox.is_active == True).all()
    if not cash_boxes:
        st.error("❌ لا توجد خزائن متاحة! أضف خزينة أولاً.")
        st.stop()

    cash_box_dict = {box.id: f"{box.name} ({box.code})" for box in cash_boxes}
    selected_cash_box_id = st.selectbox(
        "الخزينة/الحساب:",
        options=list(cash_box_dict.keys()),
        format_func=lambda x: cash_box_dict[x]
    )

    reference_number = st.text_input("رقم المرجع (اختياري):",
                                     placeholder="رقم الفاتورة أو الشيك...")
    notes = st.text_area("ملاحظات (اختياري):")

    if st.button("💾 حفظ المصروف", type="primary"):
        if not description:
            st.error("يرجى إدخال وصف المصروف")
        elif amount <= 0:
            st.error("يرجى إدخال مبلغ صحيح")
        else:
            try:
                expense_datetime = datetime.combine(expense_date, expense_time)
                create_expense(
                    category_id=selected_category_id,
                    amount=amount,
                    description=description,
                    payment_method=actual_method,
                    cash_box_id=selected_cash_box_id,
                    reference_number=reference_number if reference_number else None,
                    notes=notes if notes else None,
                    expense_date=expense_datetime,
                    created_by=current_user_id
                )
                st.success(f"✅ تم تسجيل المصروف بنجاح! (بواسطة: {current_user_name})")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 2: سجل المصروفات
# ==========================================
with tab2:
    st.subheader("📋 سجل المصروفات")

    all_cats_for_filter = get_expense_categories(include_inactive=True)

    # فلاتر
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_category = st.selectbox(
            "تصفية حسب التصنيف:",
            options=["الكل"] + [cat.name for cat in all_cats_for_filter]
        )
    with col2:
        start_date = st.date_input("من تاريخ:",
                                   value=datetime.now().replace(day=1).date())
    with col3:
        end_date = st.date_input("إلى تاريخ:", value=datetime.now().date())

    # جلب المصروفات
    query = db.query(Expense).join(ExpenseCategory).filter(
        Expense.date >= datetime.combine(start_date, datetime.min.time()),
        Expense.date <= datetime.combine(end_date, datetime.max.time())
    )

    if filter_category != "الكل":
        category = db.query(ExpenseCategory).filter(
            ExpenseCategory.name == filter_category
        ).first()
        if category:
            query = query.filter(Expense.category_id == category.id)

    expenses = query.order_by(Expense.date.desc()).all()

    if expenses:
        # نجهز خرائط للأسماء
        cat_map = {c.id: c.name for c in all_cats_for_filter}
        box_map = {b.id: b.name for b in db.query(CashBox).all()}

        data = []
        for exp in expenses:
            data.append({
                "ID": exp.id,
                "التاريخ": exp.date.strftime("%Y-%m-%d %H:%M"),
                "التصنيف": cat_map.get(exp.category_id, "—"),
                "المبلغ": f"{exp.amount:,.2f} ج.م",
                "الوصف": exp.description or "—",
                "طريقة الدفع": exp.payment_method or "—",
                "الخزينة": box_map.get(exp.cash_box_id, "—"),
                "رقم المرجع": exp.reference_number or "—"
            })

        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ملخص
        total = sum(exp.amount for exp in expenses)
        st.metric("إجمالي المصروفات", f"{total:,.2f} ج.م")

        st.markdown("---")
        st.subheader("⚙️ حذف مصروف")

        expense_ids = [exp.id for exp in expenses]
        selected_expense_id = st.selectbox(
            "اختر مصروفاً للحذف:",
            options=expense_ids,
            format_func=lambda x: next((
                f"{exp.date.strftime('%Y-%m-%d')} - {exp.amount:,.2f} ج.م - {exp.description}"
                for exp in expenses if exp.id == x
            ), x)
        )

        confirm_del = st.checkbox("تأكيد الحذف؟ (سيتم حذف القيد المحاسبي المرتبط)",
                                  key="confirm_del_exp")
        if selected_expense_id and st.button(
            "🗑️ حذف المصروف", type="secondary", disabled=not confirm_del
        ):
            try:
                delete_expense(selected_expense_id)
                st.success("✅ تم حذف المصروف بنجاح!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
    else:
        st.info("لا توجد مصروفات في الفترة المحددة.")


# ==========================================
# التبويب 3: إدارة تصنيفات المصروفات
# ==========================================
with tab3:
    st.subheader("🗂️ إدارة تصنيفات المصروفات")

    # جلب التصنيفات (نشطة + معطلة)
    all_categories = get_expense_categories(include_inactive=True)

    # الحسابات المتاحة (نوعها مصروفات)
    expense_accounts = db.query(Account).filter(
        Account.type == models.AccountType.EXPENSE
    ).all()
    acc_opts = {a.id: f"{a.code} — {a.name}" for a in expense_accounts}

    # ---------------- 3.1) إضافة تصنيف جديد ----------------
    with st.expander("➕ إضافة تصنيف مصروفات جديد", expanded=not all_categories):
        st.markdown("""
        💡 **ملاحظة:** كل تصنيف يجب أن يرتبط بحساب في شجرة الحسابات تحت نوع "مصروفات".
        لو مش عارف أي حساب تختار، استخدم الحساب الرئيسي للمصروفات.
        """)

        if not acc_opts:
            st.error(
                "⚠️ لا توجد حسابات مصروفات في شجرة الحسابات! "
                "أضف حساب من نوع 'مصروفات' أولاً من صفحة 'شجرة الحسابات'."
            )
        else:
            with st.form("add_expcat_form", clear_on_submit=True):
                new_name = st.text_input("اسم التصنيف:",
                                         placeholder="مثال: إيجار، كهرباء، رواتب...")
                new_desc = st.text_area("الوصف (اختياري):", height=60)
                new_acc_id = st.selectbox(
                    "الحساب المحاسبي المرتبط:",
                    options=list(acc_opts.keys()),
                    format_func=lambda x: acc_opts[x],
                )
                submitted = st.form_submit_button("💾 إنشاء التصنيف", type="primary")

            if submitted:
                try:
                    if not new_name.strip():
                        st.error("❌ يرجى إدخال اسم التصنيف.")
                    else:
                        create_expense_category(
                            name=new_name.strip(),
                            description=new_desc.strip() if new_desc else None,
                            account_id=int(new_acc_id),
                            created_by=current_user_id,
                        )
                        st.success(f"✅ تم إنشاء التصنيف '{new_name}' بنجاح!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

    st.markdown("---")

    # ---------------- 3.2) قائمة التصنيفات ----------------
    st.markdown("### 📋 قائمة التصنيفات الحالية")

    if not all_categories:
        st.info("لا توجد تصنيفات بعد. أضف أول تصنيف من الأعلى.")
    else:
        # جدول العرض
        rows = []
        for cat in all_categories:
            account = db.query(Account).filter(
                Account.id == cat.account_id
            ).first()
            usage = get_expense_category_usage(cat.id)
            rows.append({
                "ID": cat.id,
                "الاسم": cat.name,
                "الوصف": cat.description or "—",
                "الحساب": f"{account.code} — {account.name}" if account else "—",
                "عدد المصروفات": usage["count"],
                "الإجمالي": f"{usage['total']:,.2f} ج.م",
                "الحالة": "✅ نشط" if cat.is_active else "⛔ معطل",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ---------------- 3.3) اختيار تصنيف للتعديل ----------------
        st.markdown("### ✏️ تعديل تصنيف")

        cat_options = {f"#{c.id} — {c.name}": c.id for c in all_categories}
        selected_label = st.selectbox(
            "اختر التصنيف:",
            options=list(cat_options.keys()),
            key="edit_expcat_select",
        )
        selected_id = cat_options[selected_label]
        selected_cat = next(c for c in all_categories if c.id == selected_id)

        # إحصائيات التصنيف المختار
        usage = get_expense_category_usage(selected_id)
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("عدد المصروفات", usage["count"])
        with col_s2:
            st.metric("إجمالي المصروفات", f"{usage['total']:,.2f} ج.م")
        with col_s3:
            st.metric("الحالة", "✅ نشط" if selected_cat.is_active else "⛔ معطل")

        # نموذج التعديل
        with st.form("edit_expcat_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                edit_name = st.text_input("الاسم:", value=selected_cat.name)
            with col_b:
                current_acc_idx = 0
                if acc_opts and selected_cat.account_id in acc_opts:
                    current_acc_idx = list(acc_opts.keys()).index(selected_cat.account_id)
                edit_acc = st.selectbox(
                    "الحساب:",
                    options=list(acc_opts.keys()) if acc_opts else [selected_cat.account_id],
                    format_func=lambda x: acc_opts.get(x, "—"),
                    index=current_acc_idx,
                )
            edit_desc = st.text_area(
                "الوصف:", value=selected_cat.description or "", height=60
            )
            edit_active = st.checkbox("نشط", value=bool(selected_cat.is_active))

            save_edit = st.form_submit_button("💾 حفظ التعديلات", type="primary")

        if save_edit:
            try:
                if not edit_name.strip():
                    st.error("❌ الاسم مطلوب.")
                else:
                    update_expense_category(
                        category_id=selected_id,
                        name=edit_name.strip(),
                        description=edit_desc.strip() if edit_desc else None,
                        account_id=int(edit_acc),
                        is_active=edit_active,
                    )
                    st.success(f"✅ تم تحديث '{edit_name}' بنجاح!")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

        st.markdown("---")

        # ---------------- 3.4) تنشيط/تعطيل ----------------
        st.markdown("### 🔄 تنشيط / تعطيل")

        col_act, col_deact = st.columns(2)
        with col_act:
            if not selected_cat.is_active:
                if st.button(f"✅ تنشيط '{selected_cat.name}'",
                             use_container_width=True, key="act_cat_btn"):
                    try:
                        activate_expense_category(selected_id)
                        st.success("✅ تم التنشيط.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")
            else:
                st.caption("التصنيف نشط بالفعل.")
        with col_deact:
            if selected_cat.is_active:
                if st.button(f"⛔ تعطيل '{selected_cat.name}'",
                             use_container_width=True, key="deact_cat_btn"):
                    try:
                        deactivate_expense_category(selected_id)
                        st.success("✅ تم التعطيل.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")
            else:
                st.caption("التصنيف معطل بالفعل.")

        st.markdown("---")

        # ---------------- 3.5) حذف التصنيف ----------------
        if can_modify():
            st.markdown("### 🗑️ حذف التصنيف")

            if usage["count"] > 0:
                st.warning(
                    f"⚠️ هذا التصنيف مرتبط بـ **{usage['count']} مصروف** "
                    f"(إجمالي {usage['total']:,.2f} ج.م). "
                    "خيارين:"
                )
                st.markdown("""
                - **الحذف القسري** → يحذف التصنيف + كل المصروفات المرتبطة + القيود المحاسبية.
                - **التعطيل** (الأنصح) → يخفي التصنيف من القوائم لكن المصروفات تفضل محفوظة.
                """)

                force_del = st.checkbox(
                    "🗑️ أوافق على الحذف القسري (سيُحذف كل شيء متعلق بهذا التصنيف!)",
                    key="force_del_cat_checkbox",
                )
                if st.button(
                    "🗑️ حذف قسري",
                    type="secondary",
                    disabled=not force_del,
                    use_container_width=True,
                    key="force_del_cat_btn",
                ):
                    try:
                        delete_expense_category(selected_id, force=True)
                        st.success("✅ تم الحذف القسري بنجاح.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")
            else:
                st.info("✅ التصنيف غير مرتبط بأي مصروفات — الحذف آمن.")
                confirm = st.checkbox("تأكيد الحذف", key="confirm_del_cat_checkbox")
                if st.button(
                    "🗑️ حذف التصنيف",
                    type="secondary",
                    disabled=not confirm,
                    use_container_width=True,
                    key="del_cat_btn",
                ):
                    try:
                        delete_expense_category(selected_id, force=False)
                        st.success("✅ تم الحذف.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")
        else:
            st.info("⛔ حذف التصنيفات متاح للمدير فقط.")


# ==========================================
# التبويب 4: تقرير المصروفات
# ==========================================
with tab4:
    st.subheader("📊 تقرير المصروفات")

    col1, col2 = st.columns(2)
    with col1:
        report_start = st.date_input(
            "من تاريخ:",
            value=datetime.now().replace(day=1).date(),
            key="report_start",
        )
    with col2:
        report_end = st.date_input(
            "إلى تاريخ:", value=datetime.now().date(), key="report_end"
        )

    if st.button("📊 عرض التقرير", type="primary"):
        start_dt = datetime.combine(report_start, datetime.min.time())
        end_dt = datetime.combine(report_end, datetime.max.time())

        summary = get_expenses_summary(start_dt, end_dt)

        st.markdown(f"### 💰 إجمالي المصروفات: {summary['total']:,.2f} ج.م")

        if summary["by_category"]:
            chart_data = pd.DataFrame(summary["by_category"])
            chart_data.columns = ["التصنيف", "المبلغ"]
            st.bar_chart(chart_data.set_index("التصنيف"))

            st.markdown("---")
            st.subheader("تفاصيل المصروفات حسب التصنيف")
            for _, row in chart_data.iterrows():
                pct = (
                    (row["المبلغ"] / summary["total"] * 100)
                    if summary["total"] > 0
                    else 0
                )
                st.write(f"**{row['التصنيف']}:** {row['المبلغ']:,.2f} ج.م ({pct:.1f}%)")
        else:
            st.info("لا توجد مصروفات في الفترة المحددة.")

db.close()