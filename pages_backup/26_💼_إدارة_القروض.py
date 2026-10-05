# pages/26_💼_إدارة_القروض.py
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

# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="إدارة القروض", page_icon="💼", layout="wide")
st.title("💼 إدارة القروض والتمويل")

st.info(f" المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "➕ إضافة قرض جديد",
    "📋 قائمة القروض",
    "💳 سداد الأقساط",
    "📊 جدول الأقساط",
    "⚠️ الأقساط المتأخرة"
])

# ==========================================
# التبويب 1: إضافة قرض جديد
# ==========================================
with tab1:
    st.subheader("➕ إضافة قرض جديد")
    
    st.info("""
    💡 **أنواع القروض:**
    - **قرض مستلم:** قرض من بنك أو مؤسسة مالية (يُضاف كالتزام)
    - **قرض ممنوح:** قرض لعميل أو موظف (يُضاف كأصل)
    """)
    
    loan_type = st.radio(
        "نوع القرض:",
        [LoanType.RECEIVED.value, LoanType.GIVEN.value],
        horizontal=True
    )
    actual_type = LoanType.RECEIVED if loan_type == LoanType.RECEIVED.value else LoanType.GIVEN
    
    col1, col2 = st.columns(2)
    
    with col1:
        borrower_name = st.text_input(
            "اسم المقترض/المُقرض:",
            placeholder="مثال: بنك الأهلي، محمد أحمد..."
        )
        borrower_type = st.selectbox(
            "نوع المقترض:",
            ["bank (بنك)", "customer (عميل)", "employee (موظف)", "other (أخرى)"]
        )
        principal_amount = st.number_input(
            "المبلغ الأصلي:",
            min_value=1000.0,
            step=10000.0,
            format="%.2f"
        )
        annual_interest_rate = st.number_input(
            "نسبة الفائدة السنوية (%):",
            min_value=0.0,
            max_value=100.0,
            value=12.0,
            step=0.5,
            format="%.2f"
        )
    
    with col2:
        loan_date = st.date_input(
            "تاريخ القرض:",
            value=datetime.now().date()
        )
        term_months = st.number_input(
            "مدة القرض (أشهر):",
            min_value=1,
            max_value=360,
            value=12,
            step=1
        )
        
        # حساب القسط الشهري تلقائياً
        if principal_amount > 0 and term_months > 0:
            monthly_payment, total_interest = calculate_loan_installments(
                principal_amount, annual_interest_rate, term_months
            )
            st.success(f"💰 القسط الشهري: **{monthly_payment:,.2f} ج.م**")
            st.info(f"📊 إجمالي الفوائد: **{total_interest:,.2f} ج.م**")
            st.info(f"💵 المبلغ الإجمالي: **{principal_amount + total_interest:,.2f} ج.م**")
        else:
            monthly_payment = 0
            total_interest = 0
        
        # اختيار الخزينة
        cash_boxes = db.query(CashBox).filter(CashBox.is_active == True).all()
        cash_box_dict = {box.id: f"{box.name} ({box.code})" for box in cash_boxes}
        
        if cash_boxes:
            selected_cash_box_id = st.selectbox(
                "الخزينة/الحساب:",
                options=list(cash_box_dict.keys()),
                format_func=lambda x: cash_box_dict[x]
            )
        else:
            st.warning("⚠️ لا توجد خزائن متاحة!")
            selected_cash_box_id = None
        
        notes = st.text_area("ملاحظات (اختياري):")
    
    if st.button("💾 إنشاء القرض", type="primary"):
        if not borrower_name:
            st.error("يرجى إدخال اسم المقترض/المُقرض")
        elif principal_amount <= 0:
            st.error("يرجى إدخال مبلغ صحيح")
        elif term_months <= 0:
            st.error("يرجى إدخال مدة صحيحة")
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
                    created_by=current_user_id
                )
                
                st.success(f"✅ تم إنشاء القرض بنجاح!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

# ==========================================
# التبويب 2: قائمة القروض
# ==========================================
with tab2:
    st.subheader("📋 قائمة القروض")
    
    loan_type_filter = st.radio(
        "تصفية حسب النوع:",
        ["الكل", LoanType.RECEIVED.value, LoanType.GIVEN.value],
        horizontal=True
    )
    
    if loan_type_filter == "الكل":
        summary = get_loans_summary()
    else:
        actual_filter = LoanType.RECEIVED if loan_type_filter == LoanType.RECEIVED.value else LoanType.GIVEN
        summary = get_loans_summary(actual_filter)
    
    loans = summary['loans']
    
    if loans:
        # إحصائيات
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
        
        # جدول القروض
        data = []
        for loan in loans:
            data.append({
                "رقم القرض": loan.loan_number,
                "النوع": loan.loan_type.value,
                "المقترض/المُقرض": loan.borrower_name,
                "تاريخ القرض": loan.loan_date.strftime("%Y-%m-%d"),
                "تاريخ الاستحقاق": loan.maturity_date.strftime("%Y-%m-%d"),
                "المبلغ الأصلي": f"{loan.principal_amount:,.2f}",
                "الفائدة %": f"{loan.interest_rate:.1f}%",
                "القسط الشهري": f"{loan.installment_amount:,.2f}",
                "المدفوع": f"{loan.paid_amount:,.2f}",
                "المتبقي": f"{loan.remaining_amount:,.2f}",
                "الحالة": loan.status.value
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        # رسم بياني
        fig = px.pie(
            df,
            values='المتبقي',
            names='المقترض/المُقرض',
            title='توزيع القروض المتبقية'
        )
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
            options=[loan.id for loan in active_loans],
            format_func=lambda x: next(
                (f"{loan.loan_number} - {loan.borrower_name} ({loan.loan_type.value})" 
                 for loan in active_loans if loan.id == x),
                x
            )
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
                LoanInstallment.status == 'pending'
            ).order_by(LoanInstallment.installment_number).all()
            
            if pending_installments:
                for inst in pending_installments:
                    is_overdue = inst.due_date < datetime.now()
                    
                    if is_overdue:
                        st.error(f"⚠️ قسط #{inst.installment_number} - مستحق في {inst.due_date.strftime('%Y-%m-%d')} - مبلغ: {inst.total_amount:,.2f} ج.م")
                    else:
                        st.info(f" قسط #{inst.installment_number} - مستحق في {inst.due_date.strftime('%Y-%m-%d')} - مبلغ: {inst.total_amount:,.2f} ج.م")
                    
                    if st.button(f"💳 سداد القسط #{inst.installment_number}", key=f"pay_{inst.id}"):
                        cash_boxes = db.query(CashBox).filter(CashBox.is_active == True).all()
                        if cash_boxes:
                            cash_box_options = {box.id: f"{box.name}" for box in cash_boxes}
                            selected_cb = st.selectbox(
                                "اختر الخزينة:",
                                options=list(cash_box_options.keys()),
                                format_func=lambda x: cash_box_options[x],
                                key=f"cb_{inst.id}"
                            )
                            
                            if st.button("✅ تأكيد السداد", key=f"confirm_{inst.id}"):
                                try:
                                    pay_loan_installment(
                                        installment_id=inst.id,
                                        payment_date=datetime.now(),
                                        cash_box_id=selected_cb,
                                        created_by=current_user_id
                                    )
                                    st.success(f"✅ تم سداد القسط #{inst.installment_number} بنجاح!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ خطأ: {e}")
            else:
                st.success("✅ جميع الأقساط مسددة!")
    
    st.markdown("---")
    st.subheader("📋 سجل الأقساط المسددة")
    
    paid_installments = db.query(LoanInstallment).filter(
        LoanInstallment.status == 'paid'
    ).order_by(LoanInstallment.paid_date.desc()).limit(20).all()
    
    if paid_installments:
        data = []
        for inst in paid_installments:
            loan = db.query(Loan).filter(Loan.id == inst.loan_id).first()
            data.append({
                "رقم القرض": loan.loan_number if loan else "-",
                "المقترض": loan.borrower_name if loan else "-",
                "رقم القسط": inst.installment_number,
                "المبلغ": f"{inst.total_amount:,.2f} ج.م",
                "تاريخ السداد": inst.paid_date.strftime("%Y-%m-%d") if inst.paid_date else "-"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد أقساط مسددة.")

# ==========================================
# التبويب 4: جدول الأقساط
# ==========================================
with tab4:
    st.subheader("📊 جدول الأقساط التفصيلي")
    
    all_loans = db.query(Loan).all()
    
    if not all_loans:
        st.info("لا توجد قروض مسجلة.")
    else:
        selected_loan_id = st.selectbox(
            "اختر قرضاً:",
            options=[loan.id for loan in all_loans],
            format_func=lambda x: next(
                (f"{loan.loan_number} - {loan.borrower_name}" for loan in all_loans if loan.id == x),
                x
            )
        )
        
        if selected_loan_id:
            schedule_data = get_loan_schedule(selected_loan_id)
            
            if schedule_data:
                loan = schedule_data['loan']
                schedule = schedule_data['schedule']
                
                st.markdown(f"### 📄 قرض: {loan.loan_number} - {loan.borrower_name}")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("المبلغ الأصلي", f"{loan.principal_amount:,.2f}")
                with col2:
                    st.metric("إجمالي الفوائد", f"{loan.total_interest:,.2f}")
                with col3:
                    st.metric("القسط الشهري", f"{loan.installment_amount:,.2f}")
                with col4:
                    st.metric("عدد الأقساط", loan.term_months)
                
                st.markdown("---")
                
                if schedule:
                    df_schedule = pd.DataFrame(schedule)
                    df_schedule.columns = ['ID', 'رقم القسط', 'تاريخ الاستحقاق', 'الأصل', 'الفائدة', 'الإجمالي', 'المدفوع', 'تاريخ الدفع', 'الحالة']
                    
                    # تنسيق التواريخ
                    df_schedule['تاريخ الاستحقاق'] = pd.to_datetime(df_schedule['تاريخ الاستحقاق']).dt.strftime('%Y-%m-%d')
                    df_schedule['تاريخ الدفع'] = df_schedule['تاريخ الدفع'].apply(
                        lambda x: pd.to_datetime(x).strftime('%Y-%m-%d') if pd.notna(x) else '-'
                    )
                    
                    st.dataframe(df_schedule, use_container_width=True)
                    
                    # رسم بياني
                    fig = go.Figure()
                    
                    fig.add_trace(go.Bar(
                        x=df_schedule['رقم القسط'],
                        y=df_schedule['الأصل'],
                        name='الأصل',
                        marker_color='#3b82f6'
                    ))
                    
                    fig.add_trace(go.Bar(
                        x=df_schedule['رقم القسط'],
                        y=df_schedule['الفائدة'],
                        name='الفائدة',
                        marker_color='#f59e0b'
                    ))
                    
                    fig.update_layout(
                        title='توزيع الأقساط (أصل + فائدة)',
                        xaxis_title='رقم القسط',
                        yaxis_title='المبلغ (ج.م)',
                        barmode='stack',
                        template='plotly_white'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)

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
                "رقم القرض": item['loan_number'],
                "المقترض/المُقرض": item['borrower'],
                "النوع": item['loan_type'],
                "رقم القسط": item['installment_number'],
                "تاريخ الاستحقاق": item['due_date'].strftime("%Y-%m-%d"),
                "المبلغ": f"{item['amount']:,.2f} ج.م",
                "أيام التأخير": item['days_overdue']
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        total_overdue = sum(item['amount'] for item in overdue_list)
        st.error(f" إجمالي المبالغ المتأخرة: **{total_overdue:,.2f} ج.م**")
    else:
        st.success("✅ لا توجد أقساط متأخرة!")

db.close()