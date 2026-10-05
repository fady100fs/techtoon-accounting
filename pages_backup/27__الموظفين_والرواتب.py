# pages/27_👥_الموظفين_والرواتب.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from database import SessionLocal
import models
from models import Employee, SalaryRecord, EmploymentStatus
from services import (
    create_employee, calculate_monthly_salary, process_monthly_salary,
    get_employee_salary_history, get_monthly_payroll, get_employees_summary
)
from auth_required import require_login, get_current_user_id, get_current_user_name

# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="الموظفين والرواتب", page_icon="👥", layout="wide")
st.title("👥 إدارة الموظفين والرواتب")

st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "➕ إضافة موظف",
    " قائمة الموظفين",
    "💰 معالجة الرواتب",
    "📊 كشف الرواتب",
    "📈 تقارير الرواتب"
])

# ==========================================
# التبويب 1: إضافة موظف
# ==========================================
with tab1:
    st.subheader("➕ إضافة موظف جديد")
    
    col1, col2 = st.columns(2)
    
    with col1:
        employee_code = st.text_input("كود الموظف:", placeholder="مثال: EMP001")
        full_name = st.text_input("الاسم الكامل:", placeholder="الاسم رباعي")
        national_id = st.text_input("الرقم القومي:", placeholder="14 رقم")
        phone = st.text_input("رقم الهاتف:", placeholder="01xxxxxxxxx")
        email = st.text_input("البريد الإلكتروني:")
        address = st.text_area("العنوان:")
    
    with col2:
        job_title = st.text_input("المسمى الوظيفي:", placeholder="مثال: محاسب، مبيعات...")
        department = st.selectbox("القسم:", ["الإدارة", "المحاسبة", "المبيعات", "المخازن", "التسويق", "تقنية المعلومات", "أخرى"])
        hire_date = st.date_input("تاريخ التعيين:", value=datetime.now().date())
        basic_salary = st.number_input("الراتب الأساسي:", min_value=0.0, step=500.0, format="%.2f")
        allowances = st.number_input("البدلات:", min_value=0.0, step=100.0, format="%.2f")
        deductions = st.number_input("الخصومات الثابتة:", min_value=0.0, step=50.0, format="%.2f")
        social_insurance = st.number_input("نسبة التأمينات (%):", min_value=0.0, max_value=100.0, value=11.0, step=0.5, format="%.1f")
        tax_rate = st.number_input("نسبة الضريبة (%):", min_value=0.0, max_value=100.0, value=0.0, step=0.5, format="%.1f")
        bank_account = st.text_input("رقم الحساب البنكي:")
        bank_name = st.text_input("اسم البنك:")
        notes = st.text_area("ملاحظات:")
    
    if st.button("💾 إضافة الموظف", type="primary"):
        if not employee_code or not full_name or not job_title:
            st.error("يرجى ملء الحقول الإلزامية (كود الموظف، الاسم، المسمى الوظيفي)")
        elif basic_salary <= 0:
            st.error("يرجى إدخال راتب أساسي صحيح")
        else:
            try:
                hire_datetime = datetime.combine(hire_date, datetime.min.time())
                
                create_employee(
                    employee_code=employee_code,
                    full_name=full_name,
                    job_title=job_title,
                    hire_date=hire_datetime,
                    basic_salary=basic_salary,
                    national_id=national_id if national_id else None,
                    phone=phone if phone else None,
                    email=email if email else None,
                    address=address if address else None,
                    department=department,
                    allowances=allowances,
                    deductions=deductions,
                    social_insurance=social_insurance,
                    tax_rate=tax_rate,
                    bank_account=bank_account if bank_account else None,
                    bank_name=bank_name if bank_name else None,
                    notes=notes if notes else None,
                    created_by=current_user_id
                )
                
                st.success(f"✅ تم إضافة الموظف '{full_name}' بنجاح!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

# ==========================================
# التبويب 2: قائمة الموظفين
# ==========================================
with tab2:
    st.subheader("📋 قائمة الموظفين")
    
    employees = db.query(Employee).all()
    
    if employees:
        # إحصائيات
        summary = get_employees_summary()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("إجمالي الموظفين", summary['total_employees'])
        with col2:
            st.metric("الموظفين النشطين", summary['active_employees'])
        with col3:
            st.metric("إجمالي الرواتب الشهرية", f"{summary['total_monthly_salaries']:,.2f} ج.م")
        
        st.markdown("---")
        
        # جدول الموظفين
        data = []
        for emp in employees:
            data.append({
                "الكود": emp.employee_code,
                "الاسم": emp.full_name,
                "المسمى الوظيفي": emp.job_title,
                "القسم": emp.department or "-",
                "تاريخ التعيين": emp.hire_date.strftime("%Y-%m-%d"),
                "الراتب الأساسي": f"{emp.basic_salary:,.2f}",
                "البدلات": f"{emp.allowances:,.2f}",
                "الحالة": emp.status.value
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        # رسم بياني للتوزيع حسب القسم
        if summary['departments']:
            fig = px.pie(
                values=list(summary['departments'].values()),
                names=list(summary['departments'].keys()),
                title='توزيع الموظفين حسب الأقسام'
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("لا يوجد موظفون مسجلون.")

# ==========================================
# التبويب 3: معالجة الرواتب
# ==========================================
with tab3:
    st.subheader("💰 معالجة رواتب الموظفين")
    
    active_employees = db.query(Employee).filter(Employee.status == EmploymentStatus.ACTIVE).all()
    
    if not active_employees:
        st.info("لا يوجد موظفون نشطون.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            selected_employee_id = st.selectbox(
                "اختر الموظف:",
                options=[emp.id for emp in active_employees],
                format_func=lambda x: next((f"{emp.employee_code} - {emp.full_name}" for emp in active_employees if emp.id == x), x)
            )
            
            month = st.number_input("الشهر:", min_value=1, max_value=12, value=datetime.now().month, step=1)
            year = st.number_input("السنة:", min_value=2020, max_value=2100, value=datetime.now().year, step=1)
        
        with col2:
            overtime = st.number_input("العمل الإضافي:", min_value=0.0, step=100.0, format="%.2f")
            bonus = st.number_input("المكافأة:", min_value=0.0, step=500.0, format="%.2f")
            other_deductions = st.number_input("خصومات أخرى:", min_value=0.0, step=50.0, format="%.2f")
        
        if selected_employee_id:
            # حساب الراتب
            salary_data = calculate_monthly_salary(
                selected_employee_id, month, year, overtime, bonus, other_deductions
            )
            
            st.markdown("---")
            st.markdown("### 📊 تفاصيل الراتب")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("الراتب الأساسي", f"{salary_data['basic_salary']:,.2f} ج.م")
                st.metric("البدلات", f"{salary_data['allowances']:,.2f} ج.م")
                st.metric("العمل الإضافي", f"{salary_data['overtime']:,.2f} ج.م")
                st.metric("المكافأة", f"{salary_data['bonus']:,.2f} ج.م")
            
            with col2:
                st.metric("إجمالي الراتب", f"{salary_data['gross_salary']:,.2f} ج.م")
                st.metric("التأمينات", f"{salary_data['social_insurance']:,.2f} ج.م")
                st.metric("الضريبة", f"{salary_data['tax']:,.2f} ج.م")
                st.metric("خصومات أخرى", f"{salary_data['other_deductions']:,.2f} ج.م")
            
            with col3:
                st.metric("إجمالي الخصومات", f"{salary_data['total_deductions']:,.2f} ج.م")
                st.metric("صافي الراتب", f"{salary_data['net_salary']:,.2f} ج.م")
            
            st.markdown("---")
            
            payment_method = st.selectbox("طريقة الدفع:", ["bank_transfer (تحويل بنكي)", "cash (نقدي)", "check (شيك)"])
            actual_method = payment_method.split(" ")[0]
            
            if st.button(" صرف الراتب", type="primary"):
                try:
                    process_monthly_salary(
                        employee_id=selected_employee_id,
                        month=month,
                        year=year,
                        overtime=overtime,
                        bonus=bonus,
                        other_deductions=other_deductions,
                        payment_date=datetime.now(),
                        payment_method=actual_method,
                        created_by=current_user_id
                    )
                    
                    st.success(f"✅ تم صرف راتب شهر {month}/{year} بنجاح!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

# ==========================================
# التبويب 4: كشف الرواتب
# ==========================================
with tab4:
    st.subheader("📊 كشف الرواتب الشهري")
    
    col1, col2 = st.columns(2)
    with col1:
        payroll_month = st.number_input("الشهر:", min_value=1, max_value=12, value=datetime.now().month, step=1, key="payroll_month")
    with col2:
        payroll_year = st.number_input("السنة:", min_value=2020, max_value=2100, value=datetime.now().year, step=1, key="payroll_year")
    
    if st.button("📊 عرض كشف الرواتب", type="primary"):
        payroll_data = get_monthly_payroll(payroll_month, payroll_year)
        
        if payroll_data['payroll']:
            st.markdown(f"### 📄 كشف رواتب شهر {payroll_month}/{payroll_year}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("إجمالي الرواتب", f"{payroll_data['total_gross']:,.2f} ج.م")
            with col2:
                st.metric("إجمالي الخصومات", f"{payroll_data['total_deductions']:,.2f} ج.م")
            with col3:
                st.metric("صافي الرواتب", f"{payroll_data['total_net']:,.2f} ج.م")
            
            st.markdown("---")
            
            df = pd.DataFrame(payroll_data['payroll'])
            st.dataframe(df, use_container_width=True)
            
            # تصدير
            if st.button("📤 تصدير الكشف إلى Excel"):
                df.to_excel(f"payroll_{payroll_month}_{payroll_year}.xlsx", index=False)
                with open(f"payroll_{payroll_month}_{payroll_year}.xlsx", "rb") as file:
                    st.download_button(
                        label="⬇️ تحميل الكشف",
                        data=file,
                        file_name=f"payroll_{payroll_month}_{payroll_year}.xlsx"
                    )
        else:
            st.info(f"لا توجد رواتب مسجلة لشهر {payroll_month}/{payroll_year}.")

# ==========================================
# التبويب 5: تقارير الرواتب
# ==========================================
with tab5:
    st.subheader("📈 تقارير الرواتب")
    
    report_tab1, report_tab2 = st.tabs(["سجل رواتب الموظف", "تحليل الرواتب"])
    
    with report_tab1:
        st.markdown("### 📋 سجل رواتب الموظف")
        
        all_employees = db.query(Employee).all()
        
        if all_employees:
            selected_emp_id = st.selectbox(
                "اختر موظفاً:",
                options=[emp.id for emp in all_employees],
                format_func=lambda x: next((f"{emp.employee_code} - {emp.full_name}" for emp in all_employees if emp.id == x), x)
            )
            
            if selected_emp_id:
                history = get_employee_salary_history(selected_emp_id)
                
                if history:
                    df = pd.DataFrame(history)
                    st.dataframe(df, use_container_width=True)
                    
                    # رسم بياني
                    fig = px.line(
                        df,
                        x='year',
                        y='net_salary',
                        title='تطور صافي الراتب',
                        markers=True
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("لا توجد سجلات رواتب لهذا الموظف.")
        else:
            st.info("لا يوجد موظفون.")
    
    with report_tab2:
        st.markdown("### 📊 تحليل الرواتب")
        
        all_salary_records = db.query(SalaryRecord).all()
        
        if all_salary_records:
            total_paid = sum(r.net_salary for r in all_salary_records)
            total_gross = sum(r.gross_salary for r in all_salary_records)
            total_deductions = sum(r.total_deductions for r in all_salary_records)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("إجمالي الرواتب المدفوعة", f"{total_paid:,.2f} ج.م")
            with col2:
                st.metric("إجمالي الرواتب الإجمالية", f"{total_gross:,.2f} ج.م")
            with col3:
                st.metric("إجمالي الخصومات", f"{total_deductions:,.2f} ج.م")
            
            # رسم بياني
            fig = go.Figure(data=[
                go.Bar(name='الرواتب الإجمالية', x=[''], y=[total_gross], marker_color='#10b981'),
                go.Bar(name='الخصومات', x=[''], y=[total_deductions], marker_color='#ef4444'),
                go.Bar(name='صافي الرواتب', x=[''], y=[total_paid], marker_color='#3b82f6')
            ])
            
            fig.update_layout(
                title='ملخص الرواتب',
                barmode='group',
                template='plotly_white'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد سجلات رواتب.")

db.close()