
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/29_📅_الإغلاق_المحاسبي.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import SessionLocal
import models
from models import AccountingPeriod, PeriodStatus
from services import (
    create_accounting_period, get_all_periods, close_accounting_period,
    reopen_accounting_period, get_period_summary, check_period_integrity,
    get_period_for_date
)
from auth_required import require_login, get_current_user_id, get_current_user_name
from form_manager import clear_form, show_clear_hint

# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لكل مفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "close_"


# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="الإغلاق المحاسبي", page_icon="📅", layout="wide")
st.title("📅 الإغلاق المحاسبي")

show_clear_hint()  # 💡 الحقول ستُفرَّغ تلقائياً بعد كل عملية

st.info(f" المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

tab1, tab2, tab3, tab4 = st.tabs([
    "➕ إنشاء فترة محاسبية",
    "📋 قائمة الفترات",
    "🔒 إغلاق فترة",
    "📊 تقرير الإغلاق"
])

# ==========================================
# التبويب 1: إنشاء فترة محاسبية
# ==========================================
with tab1:
    st.subheader("➕ إنشاء فترة محاسبية جديدة")
    
    st.info("""
    💡 **الفترات المحاسبية:**
    - تُستخدم لتنظيم العمليات المالية حسب الفترات الزمنية
    - يمكن إغلاق الفترة لمنع التعديل على البيانات القديمة
    - يمكن إنشاء فترات شهرية أو سنوية
    """)
    
    period_name = st.text_input("اسم الفترة:", placeholder="مثال: يناير 2024, السنة المالية 2024...")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("تاريخ البداية:", value=datetime.now().replace(day=1))
    with col2:
        end_date = st.date_input("تاريخ النهاية:", value=(datetime.now().replace(day=1) + timedelta(days=31)).replace(day=1) - timedelta(days=1))
    
    is_fiscal_year = st.checkbox("سنة مالية كاملة", value=False)
    
    if st.button("💾 إنشاء الفترة", type="primary"):
        if not period_name:
            st.error("يرجى إدخال اسم الفترة")
        elif start_date >= end_date:
            st.error("تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
        else:
            try:
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())
                
                create_accounting_period(
                    period_name=period_name,
                    start_date=start_datetime,
                    end_date=end_datetime,
                    is_fiscal_year=is_fiscal_year,
                    created_by=current_user_id
                )
                
                st.success(f"✅ تم إنشاء الفترة '{period_name}' بنجاح!")
                st.balloons()
                clear_form(PFX)  # ✅ تفريغ الحقول
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

# ==========================================
# التبويب 2: قائمة الفترات
# ==========================================
with tab2:
    st.subheader("📋 قائمة الفترات المحاسبية")
    
    periods = get_all_periods()
    
    if periods:
        data = []
        for period in periods:
            summary = get_period_summary(period.id)
            
            data.append({
                "الفترة": period.period_name,
                "البداية": period.start_date.strftime("%Y-%m-%d"),
                "النهاية": period.end_date.strftime("%Y-%m-%d"),
                "الحالة": period.status.value,
                "عدد الفواتير": summary['invoices_count'] if summary else 0,
                "المبيعات": f"{summary['total_sales']:,.2f}" if summary else "0.00",
                "المصروفات": f"{summary['total_expenses']:,.2f}" if summary else "0.00"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد فترات محاسبية مسجلة.")

# ==========================================
# التبويب 3: إغلاق فترة
# ==========================================
with tab3:
    st.subheader("🔒 إغلاق فترة محاسبية")
    
    st.warning("""
    ️ **تنبيه مهم:**
    - إغلاق الفترة يمنع إضافة أو تعديل البيانات في هذه الفترة
    - سيتم ترحيل الأرباح والخسائر إلى الأرباح المحتجزة
    - يمكن إعادة فتح الفترة إذا لزم الأمر
    """)
    
    open_periods = db.query(AccountingPeriod).filter(
        AccountingPeriod.status == PeriodStatus.OPEN
    ).all()
    
    if not open_periods:
        st.info("لا توجد فترات مفتوحة للإغلاق.")
    else:
        selected_period_id = st.selectbox(
            "اختر فترة للإغلاق:",
            options=[p.id for p in open_periods],
            format_func=lambda x: next((p.period_name for p in open_periods if p.id == x), x)
        )
        
        if selected_period_id:
            selected_period = db.query(AccountingPeriod).filter(
                AccountingPeriod.id == selected_period_id
            ).first()
            
            # عرض ملخص الفترة
            summary = get_period_summary(selected_period_id)
            
            if summary:
                st.markdown("### 📊 ملخص الفترة")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("عدد الفواتير", summary['invoices_count'])
                with col2:
                    st.metric("المبيعات", f"{summary['total_sales']:,.2f} ج.م")
                with col3:
                    st.metric("المشتريات", f"{summary['total_purchases']:,.2f} ج.م")
                with col4:
                    st.metric("المصروفات", f"{summary['total_expenses']:,.2f} ج.م")
                
                st.markdown("---")
                
                # التحقق من سلامة الفترة
                integrity = check_period_integrity(selected_period_id)
                
                if integrity:
                    if integrity['issues']:
                        st.error("⚠️ **مشاكل يجب حلها قبل الإغلاق:**")
                        for issue in integrity['issues']:
                            st.write(f"- {issue}")
                    else:
                        st.success("✅ الفترة جاهزة للإغلاق!")
                
                closing_notes = st.text_area("ملاحظات الإغلاق (اختياري):")
                
                if st.button("🔒 إغلاق الفترة", type="primary"):
                    if integrity and integrity['issues']:
                        st.error("⚠️ يرجى حل المشاكل المذكورة أعلاه قبل الإغلاق!")
                    else:
                        try:
                            result = close_accounting_period(
                                period_id=selected_period_id,
                                closing_notes=closing_notes if closing_notes else None,
                                closed_by=current_user_id
                            )
                            
                            st.success(f"✅ تم إغلاق الفترة '{result['period'].period_name}' بنجاح!")
                            st.info(f"صافي الربح/الخسارة: {result['net_profit']:,.2f} ج.م")
                            st.balloons()
                            clear_form(PFX)  # ✅ تفريغ الحقول
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ خطأ: {e}")

# ==========================================
# التبويب 4: تقرير الإغلاق
# ==========================================
with tab4:
    st.subheader("📊 تقرير الإغلاق المحاسبي")
    
    closed_periods = db.query(AccountingPeriod).filter(
        AccountingPeriod.status == PeriodStatus.CLOSED
    ).all()
    
    if not closed_periods:
        st.info("لا توجد فترات مغلقة.")
    else:
        selected_period_id = st.selectbox(
            "اختر فترة مغلقة:",
            options=[p.id for p in closed_periods],
            format_func=lambda x: next((p.period_name for p in closed_periods if p.id == x), x)
        )
        
        if selected_period_id:
            period = db.query(AccountingPeriod).filter(
                AccountingPeriod.id == selected_period_id
            ).first()
            
            st.markdown(f"### 📄 تقرير إغلاق فترة: {period.period_name}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**تاريخ البداية:** {period.start_date.strftime('%Y-%m-%d')}")
                st.write(f"**تاريخ النهاية:** {period.end_date.strftime('%Y-%m-%d')}")
            with col2:
                st.write(f"**تاريخ الإغلاق:** {period.closing_date.strftime('%Y-%m-%d %H:%M') if period.closing_date else '-'}")
                st.write(f"**تم الإغلاق بواسطة:** {period.closed_by}")
            
            if period.closing_notes:
                st.markdown(f"**ملاحظات الإغلاق:** {period.closing_notes}")
            
            st.markdown("---")
            
            # عرض القيود المحاسبية في الفترة
            journal_entries = db.query(models.JournalEntry).filter(
                models.JournalEntry.period_id == selected_period_id
            ).order_by(models.JournalEntry.date).all()
            
            if journal_entries:
                st.markdown("### 📝 القيود المحاسبية في الفترة")
                
                data = []
                for entry in journal_entries:
                    data.append({
                        "التاريخ": entry.date.strftime("%Y-%m-%d %H:%M"),
                        "الوصف": entry.description,
                        "النوع": entry.reference_type,
                        "رقم المرجع": entry.reference_id or "-"
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
                
                st.write(f"**إجمالي القيود:** {len(journal_entries)}")
            else:
                st.info("لا توجد قيود محاسبية في هذه الفترة.")

db.close()