# pages/27__الموظفين_والرواتب.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify
render_sidebar()

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
from form_manager import clear_form, show_clear_hint

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="الموظفين والرواتب", page_icon="👥", layout="wide")
st.title("👥 إدارة الموظفين والرواتب")
show_clear_hint()   # ✅ تلميح
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")


# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لمفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "emp_"


db = SessionLocal()


def _delete_employee(emp_id):
    """حذف موظف + سجلات رواتبه + القيود."""
    db_local = SessionLocal()
    try:
        emp = db_local.query(Employee).filter(Employee.id == emp_id).first()
        if not emp:
            raise ValueError("الموظف غير موجود")

        salaries_count = db_local.query(SalaryRecord).filter(
            SalaryRecord.employee_id == emp_id
        ).count()
        if salaries_count > 0:
            raise ValueError(
                f"لا يمكن حذف الموظف: لديه {salaries_count} سجل راتب. "
                "استخدم 'منتهي الخدمة' بدلاً من الحذف."
            )

        db_local.delete(emp)
        db_local.commit()
    except Exception:
        db_local.rollback()
        raise
    finally:
        db_local.close()


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "➕ إضافة موظف",
    "📋 قائمة الموظفين",
    "💰 معالجة الرواتب",
    "📊 كشف الرواتب",
    "📈 تقارير الرواتب",
])


# ==========================================
# التبويب 1: إضافة موظف
# ==========================================
with tab1:
    st.subheader("➕ إضافة موظف جديد")

    col1, col2 = st.columns(2)
    with col1:
        employee_code = st.text_input(
            "كود الموظف:",
            placeholder="مثال: EMP001",
            key=f"{PFX}new_code",   # ✅
        )
        full_name = st.text_input(
            "الاسم الكامل:",
            placeholder="الاسم رباعي",
            key=f"{PFX}new_name",   # ✅
        )
        national_id = st.text_input(
            "الرقم القومي:",
            placeholder="14 رقم",
            key=f"{PFX}new_nid",   # ✅
        )
        phone = st.text_input(
            "رقم الهاتف:",
            placeholder="01xxxxxxxxx",
            key=f"{PFX}new_phone",   # ✅
        )
        email = st.text_input("البريد الإلكتروني:", key=f"{PFX}new_email")   # ✅
        address = st.text_area("العنوان:", key=f"{PFX}new_address")   # ✅

    with col2:
        job_title = st.text_input(
            "المسمى الوظيفي:",
            placeholder="مثال: محاسب",
            key=f"{PFX}new_title",   # ✅
        )
        department = st.selectbox(
            "القسم:",
            ["الإدارة", "المحاسبة", "المبيعات", "المخازن", "التسويق",
             "تقنية المعلومات", "أخرى"],
            key=f"{PFX}new_dept",   # ✅
        )
        hire_date = st.date_input(
            "تاريخ التعيين:",
            value=datetime.now().date(),
            key=f"{PFX}new_hire",   # ✅
        )
        basic_salary = st.number_input(
            "الراتب الأساسي:",
            min_value=0.0, step=500.0, format="%.2f",
            key=f"{PFX}new_basic",   # ✅
        )
        allowances = st.number_input(
            "البدلات:",
            min_value=0.0, step=100.0, format="%.2f",
            key=f"{PFX}new_allow",   # ✅
        )
        deductions = st.number_input(
            "الخصومات الثابتة:",
            min_value=0.0, step=50.0, format="%.2f",
            key=f"{PFX}new_deduct",   # ✅
        )
        social_insurance = st.number_input(
            "نسبة التأمينات (%):",
            min_value=0.0, max_value=100.0, value=11.0, step=0.5,
            format="%.1f", key=f"{PFX}new_insur",   # ✅
        )
        tax_rate = st.number_input(
            "نسبة الضريبة (%):",
            min_value=0.0, max_value=100.0, value=0.0, step=0.5,
            format="%.1f", key=f"{PFX}new_tax",   # ✅
        )
        bank_account = st.text_input("رقم الحساب البنكي:", key=f"{PFX}new_bank_acc")   # ✅
        bank_name = st.text_input("اسم البنك:", key=f"{PFX}new_bank_name")   # ✅
        notes = st.text_area("ملاحظات:", key=f"{PFX}new_notes")   # ✅

    if st.button("💾 إضافة الموظف", type="primary", use_container_width=True,
                 key=f"{PFX}new_save"):
        if not employee_code or not full_name or not job_title:
            st.error("❌ يرجى ملء الحقول الإلزامية.")
        elif basic_salary <= 0:
            st.error("❌ يرجى إدخال راتب أساسي صحيح.")
        else:
            try:
                hire_datetime = datetime.combine(hire_date, datetime.min.time())
                create_employee(
                    employee_code=employee_code,
                    full_name=full_name,
                    job_title=job_title,
                    hire_date=hire_datetime,
                    basic_salary=basic_salary,
                    national_id=national_id or None,
                    phone=phone or None,
                    email=email or None,
                    address=address or None,
                    department=department,
                    allowances=allowances,
                    deductions=deductions,
                    social_insurance=social_insurance,
                    tax_rate=tax_rate,
                    bank_account=bank_account or None,
                    bank_name=bank_name or None,
                    notes=notes or None,
                    created_by=current_user_id,
                )
                st.success(f"✅ تم إضافة الموظف '{full_name}'!")
                st.balloons()

                # ✅ تفريغ كل حقول النموذج
                clear_form(PFX)
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 2: قائمة الموظفين (مع التعديل والحذف)
# ==========================================
with tab2:
    st.subheader("📋 قائمة الموظفين")

    employees = db.query(Employee).all()

    if employees:
        summary = get_employees_summary()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("إجمالي الموظفين", summary["total_employees"])
        with col2:
            st.metric("الموظفين النشطين", summary["active_employees"])
        with col3:
            st.metric("إجمالي الرواتب الشهرية",
                      f"{summary['total_monthly_salaries']:,.2f} ج.م")

        st.markdown("---")

        data = []
        for emp in employees:
            data.append({
                "مسلسل": emp.employee_code,
                "الاسم": emp.full_name,
                "المسمى الوظيفي": emp.job_title,
                "القسم": emp.department or "-",
                "تاريخ التعيين": emp.hire_date.strftime("%Y-%m-%d"),
                "الراتب الأساسي": f"{emp.basic_salary:,.2f}",
                "الحالة": emp.status.value,
            })
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

        # =============== التعديل والحذف ===============
        if can_modify():
            st.markdown("---")
            st.subheader("⚙️ تعديل / حذف موظف")

            emp_ids = [e.id for e in employees]
            sel_id = st.selectbox(
                "اختر موظف:",
                options=emp_ids,
                format_func=lambda x: next(
                    (f"{e.employee_code} — {e.full_name}" for e in employees if e.id == x),
                    str(x)),
                key=f"{PFX}edit_select",   # ✅
            )

            if sel_id:
                sel_emp = next((e for e in employees if e.id == sel_id), None)

                with st.form(f"{PFX}edit_form_{sel_id}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        e_name = st.text_input(
                            "الاسم:",
                            value=sel_emp.full_name,
                            key=f"{PFX}edit_name_{sel_id}",   # ✅
                        )
                        e_title = st.text_input(
                            "المسمى الوظيفي:",
                            value=sel_emp.job_title,
                            key=f"{PFX}edit_title_{sel_id}",   # ✅
                        )
                        e_phone = st.text_input(
                            "الهاتف:",
                            value=sel_emp.phone or "",
                            key=f"{PFX}edit_phone_{sel_id}",   # ✅
                        )
                        e_email = st.text_input(
                            "البريد:",
                            value=sel_emp.email or "",
                            key=f"{PFX}edit_email_{sel_id}",   # ✅
                        )
                    with c2:
                        e_basic = st.number_input(
                            "الراتب الأساسي:",
                            min_value=0.0,
                            value=float(sel_emp.basic_salary or 0),
                            step=500.0, format="%.2f",
                            key=f"{PFX}edit_basic_{sel_id}",   # ✅
                        )
                        e_allow = st.number_input(
                            "البدلات:",
                            min_value=0.0,
                            value=float(sel_emp.allowances or 0),
                            step=100.0, format="%.2f",
                            key=f"{PFX}edit_allow_{sel_id}",   # ✅
                        )
                        e_deduct = st.number_input(
                            "الخصومات:",
                            min_value=0.0,
                            value=float(sel_emp.deductions or 0),
                            step=50.0, format="%.2f",
                            key=f"{PFX}edit_deduct_{sel_id}",   # ✅
                        )
                        e_status_options = [s.value for s in EmploymentStatus]
                        e_status_idx = e_status_options.index(sel_emp.status.value) \
                            if sel_emp.status.value in e_status_options else 0
                        e_status = st.selectbox(
                            "الحالة:",
                            options=e_status_options,
                            index=e_status_idx,
                            key=f"{PFX}edit_status_{sel_id}",   # ✅
                        )

                    e_notes = st.text_area(
                        "ملاحظات:",
                        value=sel_emp.notes or "",
                        height=60,
                        key=f"{PFX}edit_notes_{sel_id}",   # ✅
                    )

                    submitted = st.form_submit_button(
                        "💾 حفظ التعديلات", type="primary",
                    )

                if submitted:
                    try:
                        if not e_name.strip() or not e_title.strip():
                            st.error("❌ الاسم والمسمى مطلوبان.")
                        else:
                            sel_emp.full_name = e_name.strip()
                            sel_emp.job_title = e_title.strip()
                            sel_emp.phone = e_phone.strip() or None
                            sel_emp.email = e_email.strip() or None
                            sel_emp.basic_salary = e_basic
                            sel_emp.allowances = e_allow
                            sel_emp.deductions = e_deduct
                            sel_emp.notes = e_notes.strip() or None
                            new_status = next(
                                (s for s in EmploymentStatus if s.value == e_status),
                                sel_emp.status)
                            sel_emp.status = new_status
                            db.commit()
                            st.success("✅ تم التعديل!")

                            # ✅ تفريغ كل مفاتيح التعديل
                            clear_form(PFX)
                            st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ خطأ: {e}")

                # الحذف
                st.markdown("#### 🗑 حذف الموظف")
                sal_count = db.query(SalaryRecord).filter(
                    SalaryRecord.employee_id == sel_id
                ).count()

                if sal_count > 0:
                    st.error(f"⛔ لا يمكن حذف الموظف: لديه **{sal_count}** سجل راتب.")
                    st.info("💡 الحل: غيّر حالته إلى **'منتهي'** من قائمة التعديل.")
                else:
                    st.warning(f"⚠️ سيتم حذف الموظف **{sel_emp.full_name}** نهائيًا.")
                    confirm = st.checkbox(
                        "✅ أؤكد الحذف النهائي",
                        key=f"{PFX}confirm_del_{sel_id}",   # ✅
                    )
                    if st.button(
                        "🗑 حذف الموظف",
                        type="secondary",
                        disabled=not confirm,
                        use_container_width=True,
                        key=f"{PFX}del_btn_{sel_id}",   # ✅
                    ):
                        try:
                            _delete_employee(sel_id)
                            st.success("✅ تم الحذف.")

                            # ✅ تفريغ كل مفاتيح الصفحة
                            clear_form(PFX)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {e}")
        else:
            st.info("⛔ التعديل والحذف للمدير فقط.")

        # رسم بياني
        if summary["departments"]:
            fig = px.pie(values=list(summary["departments"].values()),
                          names=list(summary["departments"].keys()),
                          title="توزيع الموظفين حسب الأقسام")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("لا يوجد موظفون.")


# ==========================================
# التبويب 3: معالجة الرواتب
# ==========================================
with tab3:
    st.subheader("💰 معالجة رواتب الموظفين")

    active = db.query(Employee).filter(
        Employee.status == EmploymentStatus.ACTIVE
    ).all()

    if not active:
        st.info("لا يوجد موظفون نشطون.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            sel_emp_id = st.selectbox(
                "اختر الموظف:",
                options=[e.id for e in active],
                format_func=lambda x: next(
                    (f"{e.employee_code} - {e.full_name}" for e in active if e.id == x),
                    str(x)),
                key=f"{PFX}payroll_emp_sel",   # ✅
            )
            month = st.number_input(
                "الشهر:", min_value=1, max_value=12,
                value=datetime.now().month, step=1,
                key=f"{PFX}payroll_month",   # ✅
            )
            year = st.number_input(
                "السنة:", min_value=2020, max_value=2100,
                value=datetime.now().year, step=1,
                key=f"{PFX}payroll_year",   # ✅
            )
        with col2:
            overtime = st.number_input(
                "العمل الإضافي:", min_value=0.0, step=100.0,
                format="%.2f", key=f"{PFX}payroll_ot",   # ✅
            )
            bonus = st.number_input(
                "المكافأة:", min_value=0.0, step=500.0,
                format="%.2f", key=f"{PFX}payroll_bonus",   # ✅
            )
            other_ded = st.number_input(
                "خصومات أخرى:", min_value=0.0, step=50.0,
                format="%.2f", key=f"{PFX}payroll_od",   # ✅
            )

        if sel_emp_id:
            salary_data = calculate_monthly_salary(sel_emp_id, month, year,
                                                    overtime, bonus, other_ded)
            st.markdown("---")
            st.markdown("### 📊 تفاصيل الراتب")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("الأساسي", f"{salary_data['basic_salary']:,.2f}")
                st.metric("البدلات", f"{salary_data['allowances']:,.2f}")
                st.metric("إضافي", f"{salary_data['overtime']:,.2f}")
                st.metric("مكافأة", f"{salary_data['bonus']:,.2f}")
            with c2:
                st.metric("الإجمالي", f"{salary_data['gross_salary']:,.2f}")
                st.metric("تأمينات", f"{salary_data['social_insurance']:,.2f}")
                st.metric("ضريبة", f"{salary_data['tax']:,.2f}")
                st.metric("خصومات", f"{salary_data['other_deductions']:,.2f}")
            with c3:
                st.metric("إجمالي خصومات", f"{salary_data['total_deductions']:,.2f}")
                st.metric("صافي الراتب", f"{salary_data['net_salary']:,.2f}")

            payment_method = st.selectbox(
                "طريقة الدفع:",
                ["bank_transfer (تحويل بنكي)", "cash (نقدي)", "check (شيك)"],
                key=f"{PFX}payroll_pm",   # ✅
            )
            actual_method = payment_method.split(" ")[0]

            if st.button("💾 صرف الراتب", type="primary", use_container_width=True,
                         key=f"{PFX}payroll_save"):
                try:
                    process_monthly_salary(
                        employee_id=sel_emp_id,
                        month=month, year=year,
                        overtime=overtime, bonus=bonus,
                        other_deductions=other_ded,
                        payment_date=datetime.now(),
                        payment_method=actual_method,
                        created_by=current_user_id,
                    )
                    st.success(f"✅ تم صرف راتب {month}/{year}!")
                    st.balloons()

                    # ✅ تفريغ كل حقول النموذج
                    clear_form(PFX)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ {e}")


# ==========================================
# التبويب 4: كشف الرواتب
# ==========================================
with tab4:
    st.subheader("📊 كشف الرواتب الشهري")

    col1, col2 = st.columns(2)
    with col1:
        pm = st.number_input(
            "الشهر:", min_value=1, max_value=12,
            value=datetime.now().month, step=1,
            key=f"{PFX}slip_month",   # ✅
        )
    with col2:
        py = st.number_input(
            "السنة:", min_value=2020, max_value=2100,
            value=datetime.now().year, step=1,
            key=f"{PFX}slip_year",   # ✅
        )

    if st.button("📊 عرض الكشف", type="primary", key=f"{PFX}slip_show"):
        payroll_data = get_monthly_payroll(pm, py)
        if payroll_data["payroll"]:
            st.markdown(f"### 📄 كشف رواتب {pm}/{py}")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("إجمالي", f"{payroll_data['total_gross']:,.2f}")
            with c2:
                st.metric("خصومات", f"{payroll_data['total_deductions']:,.2f}")
            with c3:
                st.metric("صافي", f"{payroll_data['total_net']:,.2f}")
            st.dataframe(pd.DataFrame(payroll_data["payroll"]),
                         use_container_width=True, hide_index=True)
        else:
            st.info(f"لا توجد رواتب لـ {pm}/{py}.")


# ==========================================
# التبويب 5: تقارير الرواتب
# ==========================================
with tab5:
    st.subheader("📈 تقارير الرواتب")

    rt1, rt2 = st.tabs(["سجل موظف", "تحليل عام"])

    with rt1:
        all_emps = db.query(Employee).all()
        if all_emps:
            eid = st.selectbox(
                "اختر موظف:",
                options=[e.id for e in all_emps],
                format_func=lambda x: next(
                    (f"{e.employee_code} - {e.full_name}" for e in all_emps if e.id == x),
                    str(x)),
                key=f"{PFX}hist_emp",   # ✅
            )
            if eid:
                history = get_employee_salary_history(eid)
                if history:
                    st.dataframe(pd.DataFrame(history), use_container_width=True,
                                 hide_index=True)
                else:
                    st.info("لا توجد سجلات.")

    with rt2:
        records = db.query(SalaryRecord).all()
        if records:
            total_paid = sum(r.net_salary for r in records)
            total_gross = sum(r.gross_salary for r in records)
            total_ded = sum(r.total_deductions for r in records)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("المدفوع", f"{total_paid:,.2f}")
            with c2:
                st.metric("الإجمالي", f"{total_gross:,.2f}")
            with c3:
                st.metric("خصومات", f"{total_ded:,.2f}")
        else:
            st.info("لا توجد سجلات.")

db.close()