
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/22_💸_المصروفات.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from models import ExpenseCategory, Expense, CashBox
from services import create_expense_category, create_expense, get_expenses_summary, delete_expense
from auth_required import require_login, get_current_user_id, get_current_user_name
from sqlalchemy import func

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
    " تقرير المصروفات"
])

# ==========================================
# التبويب 1: تسجيل مصروف جديد
# ==========================================
with tab1:
    st.subheader("➕ تسجيل مصروف جديد")
    
    # التاريخ والوقت
    st.markdown("### 📅 تاريخ ووقت المصروف")
    col_date, col_time = st.columns(2)
    with col_date:
        expense_date = st.date_input("التاريخ:", value=datetime.now().date(), key="expense_date")
    with col_time:
        expense_time = st.time_input("الوقت:", value=datetime.now().time(), key="expense_time")
    
    # تصنيف المصروف
    categories = db.query(ExpenseCategory).filter(ExpenseCategory.is_active == True).all()
    if not categories:
        st.warning("⚠️ لا توجد تصنيفات مصروفات! يرجى إضافة تصنيفات أولاً من تبويب 'إدارة تصنيفات المصروفات'")
        st.stop()
    
    category_dict = {cat.id: cat.name for cat in categories}
    selected_category_id = st.selectbox(
        "تصنيف المصروف:",
        options=list(category_dict.keys()),
        format_func=lambda x: category_dict[x]
    )
    
    # المبلغ والوصف
    amount = st.number_input("مبلغ المصروف:", min_value=0.01, step=100.0, format="%.2f")
    description = st.text_area("وصف المصروف:", placeholder="مثال: فاتورة كهرباء شهر يناير...")
    
    # طريقة الدفع والخزينة
    payment_method = st.selectbox(
        "طريقة الدفع:",
        ["cash (نقدي)", "bank_transfer (تحويل بنكي)", "check (شيك)"]
    )
    actual_method = payment_method.split(" ")[0]
    
    cash_boxes = db.query(CashBox).filter(CashBox.is_active == True).all()
    cash_box_dict = {box.id: f"{box.name} ({box.code})" for box in cash_boxes}
    
    if cash_boxes:
        selected_cash_box_id = st.selectbox(
            "الخزينة/الحساب:",
            options=list(cash_box_dict.keys()),
            format_func=lambda x: cash_box_dict[x]
        )
    else:
        st.error("❌ لا توجد خزائن متاحة!")
        st.stop()
    
    reference_number = st.text_input("رقم المرجع (اختياري):", placeholder="رقم الفاتورة أو الشيك...")
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
    
    # فلاتر
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_category = st.selectbox(
            "تصفية حسب التصنيف:",
            options=["الكل"] + [cat.name for cat in categories]
        )
    with col2:
        start_date = st.date_input("من تاريخ:", value=datetime.now().replace(day=1).date())
    with col3:
        end_date = st.date_input("إلى تاريخ:", value=datetime.now().date())
    
    # جلب المصروفات
    query = db.query(Expense).join(ExpenseCategory).filter(
        Expense.date >= datetime.combine(start_date, datetime.min.time()),
        Expense.date <= datetime.combine(end_date, datetime.max.time())
    )
    
    if filter_category != "الكل":
        category = db.query(ExpenseCategory).filter(ExpenseCategory.name == filter_category).first()
        if category:
            query = query.filter(Expense.category_id == category.id)
    
    expenses = query.order_by(Expense.date.desc()).all()
    
    if expenses:
        data = []
        for exp in expenses:
            cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == exp.category_id).first()
            cash_box = db.query(CashBox).filter(CashBox.id == exp.cash_box_id).first()
            
            data.append({
                "ID": exp.id,
                "التاريخ": exp.date.strftime("%Y-%m-%d %H:%M"),
                "التصنيف": cat.name if cat else "-",
                "المبلغ": f"{exp.amount:,.2f} ج.م",
                "الوصف": exp.description,
                "طريقة الدفع": exp.payment_method,
                "الخزينة": cash_box.name if cash_box else "-",
                "رقم المرجع": exp.reference_number or "-"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
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
        
        if selected_expense_id and st.button("🗑️ حذف المصروف", type="secondary"):
            if st.checkbox("تأكيد الحذف؟ (سيتم حذف القيد المحاسبي المرتبط)"):
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
    
    sub_tab1, sub_tab2 = st.tabs(["➕ إضافة تصنيف", "📋 قائمة التصنيفات"])
    
    with sub_tab1:
        st.markdown("### 📝 إضافة تصنيف مصروفات جديد")
        
        st.info("""
        💡 **ملاحظة:**
        كل تصنيف يجب أن يرتبط بحساب في شجرة الحسابات تحت حساب "المصروفات".
        سيتم إنشاء الحساب تلقائياً إذا لم يكن موجوداً.
        """)
        
        category_name = st.text_input("اسم التصنيف:", placeholder="مثال: إيجار، كهرباء، رواتب...")
        category_description = st.text_area("الوصف (اختياري):")
        
        if st.button(" إنشاء التصنيف", type="primary"):
            if not category_name:
                st.error("يرجى إدخال اسم التصنيف")
            else:
                try:
                    # البحث عن حساب المصروفات أو إنشاء حساب فرعي
                    expenses_account = db.query(models.Account).filter(
                        models.Account.code == "5000"
                    ).first()
                    
                    if not expenses_account:
                        st.error("حساب المصروفات الرئيسي غير موجود في شجرة الحسابات!")
                    else:
                        # إنشاء حساب فرعي
                        account_code = f"5{db.query(models.Account).filter(models.Account.code.like('5%')).count() + 1:03d}"
                        new_account = models.Account(
                            code=account_code,
                            name=category_name,
                            type=models.AccountType.EXPENSE,
                            parent_id=expenses_account.id
                        )
                        db.add(new_account)
                        db.commit()
                        
                        create_expense_category(
                            name=category_name,
                            description=category_description if category_description else None,
                            account_id=new_account.id,
                            created_by=current_user_id
                        )
                        
                        st.success(f"✅ تم إنشاء التصنيف '{category_name}' بنجاح!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
    
    with sub_tab2:
        st.markdown("### 📋 قائمة تصنيفات المصروفات")
        
        all_categories = db.query(ExpenseCategory).all()
        
        if all_categories:
            data = []
            for cat in all_categories:
                account = db.query(models.Account).filter(models.Account.id == cat.account_id).first()
                expenses_count = db.query(Expense).filter(Expense.category_id == cat.id).count()
                total_expenses = db.query(Expense).filter(Expense.category_id == cat.id).with_entities(
                    func.sum(Expense.amount)
                ).scalar() or 0.0
                
                data.append({
                    "ID": cat.id,
                    "الاسم": cat.name,
                    "الوصف": cat.description or "-",
                    "الحساب المرتبط": account.name if account else "-",
                    "عدد المصروفات": expenses_count,
                    "إجمالي المصروفات": f"{total_expenses:,.2f} ج.م",
                    "الحالة": "✅ نشط" if cat.is_active else "⛔ معطل"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            
            st.markdown("---")
            st.subheader("⚙️ تعديل/حذف تصنيف")
            
            category_ids = [cat.id for cat in all_categories]
            selected_category_id = st.selectbox(
                "اختر تصنيفاً:",
                options=category_ids,
                format_func=lambda x: next((cat.name for cat in all_categories if cat.id == x), x)
            )
            
            if selected_category_id:
                selected_category = db.query(ExpenseCategory).filter(
                    ExpenseCategory.id == selected_category_id
                ).first()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**تعديل التصنيف:**")
                    new_name = st.text_input("الاسم الجديد:", value=selected_category.name, key=f"edit_cat_name_{selected_category_id}")
                    new_description = st.text_area("الوصف الجديد:", value=selected_category.description or "", key=f"edit_cat_desc_{selected_category_id}")
                    new_is_active = st.checkbox("نشط", value=selected_category.is_active, key=f"edit_cat_active_{selected_category_id}")
                    
                    if st.button("💾 حفظ التعديلات", type="primary"):
                        try:
                            selected_category.name = new_name
                            selected_category.description = new_description if new_description else None
                            selected_category.is_active = new_is_active
                            
                            # تحديث اسم الحساب المرتبط
                            account = db.query(models.Account).filter(models.Account.id == selected_category.account_id).first()
                            if account:
                                account.name = new_name
                            
                            db.commit()
                            st.success("✅ تم تحديث التصنيف بنجاح!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ خطأ: {e}")
                
                with col2:
                    st.markdown("**حذف التصنيف:**")
                    expenses_count = db.query(Expense).filter(Expense.category_id == selected_category_id).count()
                    
                    if expenses_count > 0:
                        st.error(f"⛔ لا يمكن حذف هذا التصنيف! له {expenses_count} مصروف مرتبط.")
                        st.info("💡 الحل: عطّل التصنيف بدلاً من حذفه")
                    else:
                        st.warning("⚠️ سيتم حذف التصنيف نهائياً!")
                        if st.button("🗑️ حذف التصنيف", type="secondary"):
                            if st.checkbox("تأكيد الحذف؟"):
                                try:
                                    # حذف الحساب المرتبط
                                    account = db.query(models.Account).filter(models.Account.id == selected_category.account_id).first()
                                    if account:
                                        db.delete(account)
                                    
                                    db.delete(selected_category)
                                    db.commit()
                                    st.success("✅ تم حذف التصنيف بنجاح!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ خطأ: {e}")
        else:
            st.info("لا توجد تصنيفات مصروفات.")

# ==========================================
# التبويب 4: تقرير المصروفات
# ==========================================
with tab4:
    st.subheader("📊 تقرير المصروفات")
    
    col1, col2 = st.columns(2)
    with col1:
        report_start = st.date_input("من تاريخ:", value=datetime.now().replace(day=1).date(), key="report_start")
    with col2:
        report_end = st.date_input("إلى تاريخ:", value=datetime.now().date(), key="report_end")
    
    if st.button("📊 عرض التقرير", type="primary"):
        start_dt = datetime.combine(report_start, datetime.min.time())
        end_dt = datetime.combine(report_end, datetime.max.time())
        
        summary = get_expenses_summary(start_dt, end_dt)
        
        st.markdown(f"### 💰 إجمالي المصروفات: {summary['total']:,.2f} ج.م")
        
        if summary['by_category']:
            chart_data = pd.DataFrame(summary['by_category'])
            chart_data.columns = ['التصنيف', 'المبلغ']
            
            st.bar_chart(chart_data.set_index('التصنيف'))
            
            st.markdown("---")
            st.subheader("تفاصيل المصروفات حسب التصنيف")
            
            for idx, row in chart_data.iterrows():
                percentage = (row['المبلغ'] / summary['total'] * 100) if summary['total'] > 0 else 0
                st.write(f"**{row['التصنيف']}:** {row['المبلغ']:,.2f} ج.م ({percentage:.1f}%)")

db.close()