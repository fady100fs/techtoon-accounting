
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/30_🏢_مراكز_التكلفة.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import SessionLocal
import models
from models import CostCenter, CostAllocation, CostCenterTransaction, Account
from services import (
    create_cost_center, get_cost_centers_tree, allocate_cost_to_center,
    get_cost_center_report, get_all_cost_centers_summary,
    transfer_between_cost_centers
)
from auth_required import require_login, get_current_user_id, get_current_user_name

# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="مراكز التكلفة", page_icon="🏢", layout="wide")
st.title("🏢 إدارة مراكز التكلفة")

st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "➕ إضافة مركز تكلفة",
    "📋 قائمة مراكز التكلفة",
    "💰 تخصيص تكلفة",
    "📊 تقارير مراكز التكلفة",
    "🔄 التحويلات بين المراكز"
])

# ==========================================
# التبويب 1: إضافة مركز تكلفة
# ==========================================
with tab1:
    st.subheader("➕ إضافة مركز تكلفة جديد")
    
    st.info("""
    💡 **مراكز التكلفة:**
    - وحدات داخل المنظمة تُخصص لها التكاليف
    - تساعد في تتبع المصروفات حسب الأقسام
    - أمثلة: قسم المبيعات، قسم الإنتاج، قسم التسويق
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        center_code = st.text_input("كود المركز:", placeholder="مثال: CC001, SALES, PROD...")
        center_name = st.text_input("اسم المركز:", placeholder="مثال: قسم المبيعات، قسم الإنتاج...")
        manager_name = st.text_input("اسم المسؤول:", placeholder="اسم مدير المركز")
        description = st.text_area("الوصف:")
    
    with col2:
        # اختيار المركز الأب
        all_centers = db.query(CostCenter).filter(CostCenter.is_active == True).all()
        parent_options = {"بدون (مركز رئيسي)": None}
        for c in all_centers:
            parent_options[c.name] = c.id
        
        selected_parent = st.selectbox(
            "المركز الأب (اختياري):",
            options=list(parent_options.values()),
            format_func=lambda x: next((k for k, v in parent_options.items() if v == x), "بدون")
        )
        
        budget_limit = st.number_input("حد الميزانية (اختياري):", min_value=0.0, step=10000.0, format="%.2f")
        notes = st.text_area("ملاحظات:")
    
    if st.button("💾 إنشاء مركز التكلفة", type="primary"):
        if not center_code or not center_name:
            st.error("يرجى إدخال الكود والاسم")
        else:
            try:
                create_cost_center(
                    code=center_code,
                    name=center_name,
                    description=description if description else None,
                    manager_name=manager_name if manager_name else None,
                    parent_id=selected_parent,
                    budget_limit=budget_limit if budget_limit > 0 else None,
                    notes=notes if notes else None,
                    created_by=current_user_id
                )
                
                st.success(f"✅ تم إنشاء مركز التكلفة '{center_name}' بنجاح!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

# ==========================================
# التبويب 2: قائمة مراكز التكلفة
# ==========================================
with tab2:
    st.subheader("📋 قائمة مراكز التكلفة")
    
    centers = db.query(CostCenter).all()
    
    if centers:
        # عرض الشجرة
        tree = get_cost_centers_tree()
        
        st.markdown("### 🌳 شجرة مراكز التكلفة")
        
        for node in tree:
            with st.expander(f" {node['code']} - {node['name']}", expanded=True):
                st.write(f"**المسؤول:** {node['manager'] or '-'}")
                st.write(f"**الميزانية:** {node['budget_limit']:,.2f} ج.م" if node['budget_limit'] else "**الميزانية:** غير محددة")
                
                if node['children']:
                    st.markdown("**المراكز الفرعية:**")
                    for child in node['children']:
                        st.write(f"  - 📄 {child['code']} - {child['name']}")
        
        st.markdown("---")
        
        # جدول شامل
        st.markdown("### 📊 جدول مراكز التكلفة")
        
        data = []
        for center in centers:
            parent = db.query(CostCenter).filter(CostCenter.id == center.parent_id).first()
            transactions_count = db.query(CostCenterTransaction).filter(
                CostCenterTransaction.cost_center_id == center.id
            ).count()
            
            data.append({
                "الكود": center.code,
                "الاسم": center.name,
                "المركز الأب": parent.name if parent else "-",
                "المسؤول": center.manager_name or "-",
                "الميزانية": f"{center.budget_limit:,.2f}" if center.budget_limit else "-",
                "عدد المعاملات": transactions_count,
                "الحالة": "✅ نشط" if center.is_active else "⛔ معطل"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد مراكز تكلفة مسجلة.")

# ==========================================
# التبويب 3: تخصيص تكلفة
# ==========================================
with tab3:
    st.subheader(" تخصيص تكلفة لمركز تكلفة")
    
    active_centers = db.query(CostCenter).filter(CostCenter.is_active == True).all()
    
    if not active_centers:
        st.warning("⚠️ لا توجد مراكز تكلفة نشطة!")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            selected_center_id = st.selectbox(
                "اختر مركز التكلفة:",
                options=[c.id for c in active_centers],
                format_func=lambda x: next((f"{c.code} - {c.name}" for c in active_centers if c.id == x), x)
            )
            
            # اختيار الحساب
            expense_accounts = db.query(Account).filter(Account.type == models.AccountType.EXPENSE).all()
            account_dict = {acc.id: f"{acc.code} - {acc.name}" for acc in expense_accounts}
            
            selected_account_id = st.selectbox(
                "اختر حساب المصروف:",
                options=list(account_dict.keys()),
                format_func=lambda x: account_dict[x]
            )
        
        with col2:
            allocation_date = st.date_input("التاريخ:", value=datetime.now().date())
            amount = st.number_input("المبلغ:", min_value=0.01, step=100.0, format="%.2f")
            description = st.text_area("الوصف:", placeholder="وصف التكلفة...")
        
        if st.button("💾 تخصيص التكلفة", type="primary"):
            if not description:
                st.error("يرجى إدخال وصف التكلفة")
            elif amount <= 0:
                st.error("يرجى إدخال مبلغ صحيح")
            else:
                try:
                    allocation_datetime = datetime.combine(allocation_date, datetime.min.time())
                    
                    allocate_cost_to_center(
                        cost_center_id=selected_center_id,
                        account_id=selected_account_id,
                        amount=amount,
                        description=description,
                        allocation_date=allocation_datetime,
                        created_by=current_user_id
                    )
                    
                    st.success(f"✅ تم تخصيص التكلفة بنجاح!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

# ==========================================
# التبويب 4: تقارير مراكز التكلفة
# ==========================================
with tab4:
    st.subheader("📊 تقارير مراكز التكلفة")
    
    report_type = st.radio("نوع التقرير:", ["تقرير مركز واحد", "ملخص جميع المراكز"], horizontal=True)
    
    if report_type == "تقرير مركز واحد":
        all_centers = db.query(CostCenter).all()
        
        if not all_centers:
            st.info("لا توجد مراكز تكلفة.")
        else:
            selected_center_id = st.selectbox(
                "اختر مركز التكلفة:",
                options=[c.id for c in all_centers],
                format_func=lambda x: next((f"{c.code} - {c.name}" for c in all_centers if c.id == x), x)
            )
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("من تاريخ:", value=datetime.now().replace(day=1))
            with col2:
                end_date = st.date_input("إلى تاريخ:", value=datetime.now())
            
            if st.button("📊 عرض التقرير", type="primary"):
                start_dt = datetime.combine(start_date, datetime.min.time())
                end_dt = datetime.combine(end_date, datetime.max.time())
                
                report = get_cost_center_report(selected_center_id, start_dt, end_dt)
                
                if report:
                    center = report['cost_center']
                    
                    st.markdown(f"### 📄 تقرير: {center.name} ({center.code})")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("إجمالي المصروفات", f"{report['total_expenses']:,.2f} ج.م")
                    with col2:
                        st.metric("إجمالي الإيرادات", f"{report['total_revenues']:,.2f} ج.م")
                    with col3:
                        st.metric("صافي المبلغ", f"{report['net_amount']:,.2f} ج.م")
                    
                    if center.budget_limit:
                        usage_pct = (report['total_expenses'] / center.budget_limit * 100)
                        st.progress(min(usage_pct / 100, 1.0))
                        st.write(f"**نسبة الاستخدام:** {usage_pct:.1f}% من الميزانية")
                    
                    st.markdown("---")
                    st.markdown("### 📝 المعاملات")
                    
                    if report['transactions']:
                        data = []
                        for t in report['transactions']:
                            data.append({
                                "التاريخ": t.date.strftime("%Y-%m-%d"),
                                "الوصف": t.description,
                                "النوع": t.transaction_type,
                                "المبلغ": f"{t.amount:,.2f} ج.م"
                            })
                        
                        df = pd.DataFrame(data)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("لا توجد معاملات في هذه الفترة.")
                    
                    # رسم بياني
                    if report['children']:
                        fig = px.pie(
                            pd.DataFrame(report['children']),
                            values='total',
                            names='name',
                            title='توزيع التكاليف على المراكز الفرعية'
                        )
                        st.plotly_chart(fig, use_container_width=True)
    
    else:
        # ملخص جميع المراكز
        col1, col2 = st.columns(2)
        with col1:
            summary_start = st.date_input("من تاريخ:", value=datetime.now().replace(day=1), key="summary_start")
        with col2:
            summary_end = st.date_input("إلى تاريخ:", value=datetime.now(), key="summary_end")
        
        if st.button("📊 عرض الملخص", type="primary"):
            summary_start_dt = datetime.combine(summary_start, datetime.min.time())
            summary_end_dt = datetime.combine(summary_end, datetime.max.time())
            
            summary = get_all_cost_centers_summary(summary_start_dt, summary_end_dt)
            
            if summary:
                df = pd.DataFrame(summary)
                st.dataframe(df, use_container_width=True)
                
                # رسم بياني
                fig = px.bar(
                    df,
                    x='name',
                    y='total_spent',
                    color='usage_percentage',
                    title='إجمالي المصروفات حسب مركز التكلفة',
                    color_continuous_scale='RdYlGn_r'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # إجمالي
                total_spent = sum(s['total_spent'] for s in summary)
                st.metric("إجمالي مصروفات جميع المراكز", f"{total_spent:,.2f} ج.م")

# ==========================================
# التبويب 5: التحويلات بين المراكز
# ==========================================
with tab5:
    st.subheader("🔄 التحويلات بين مراكز التكلفة")
    
    active_centers = db.query(CostCenter).filter(CostCenter.is_active == True).all()
    
    if len(active_centers) < 2:
        st.warning("️ يجب وجود مركزين نشطين على الأقل!")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            from_center_id = st.selectbox(
                "من مركز:",
                options=[c.id for c in active_centers],
                format_func=lambda x: next((f"{c.code} - {c.name}" for c in active_centers if c.id == x), x)
            )
        
        with col2:
            to_center_id = st.selectbox(
                "إلى مركز:",
                options=[c.id for c in active_centers],
                format_func=lambda x: next((f"{c.code} - {c.name}" for c in active_centers if c.id == x), x)
            )
        
        transfer_date = st.date_input("تاريخ التحويل:", value=datetime.now().date())
        transfer_amount = st.number_input("مبلغ التحويل:", min_value=0.01, step=100.0, format="%.2f")
        transfer_description = st.text_area("وصف التحويل:")
        
        if st.button("🔄 تنفيذ التحويل", type="primary"):
            if from_center_id == to_center_id:
                st.error("❌ لا يمكن التحويل بين نفس المركز!")
            elif transfer_amount <= 0:
                st.error("❌ يرجى إدخال مبلغ صحيح!")
            elif not transfer_description:
                st.error("❌ يرجى إدخال وصف التحويل!")
            else:
                try:
                    transfer_datetime = datetime.combine(transfer_date, datetime.min.time())
                    
                    result = transfer_between_cost_centers(
                        from_center_id=from_center_id,
                        to_center_id=to_center_id,
                        amount=transfer_amount,
                        description=transfer_description,
                        transfer_date=transfer_datetime,
                        created_by=current_user_id
                    )
                    
                    st.success(f"✅ تم التحويل بنجاح: {transfer_amount:,.2f} ج.م من {result['from']} إلى {result['to']}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
        
        st.markdown("---")
        st.markdown("### 📋 سجل التحويلات")
        
        transfers = db.query(CostCenterTransaction).filter(
            CostCenterTransaction.transaction_type.in_(['transfer_in', 'transfer_out'])
        ).order_by(CostCenterTransaction.date.desc()).limit(20).all()
        
        if transfers:
            data = []
            for t in transfers:
                center = db.query(CostCenter).filter(CostCenter.id == t.cost_center_id).first()
                data.append({
                    "التاريخ": t.date.strftime("%Y-%m-%d"),
                    "المركز": center.name if center else "-",
                    "النوع": "وارد" if t.transaction_type == 'transfer_in' else "صادر",
                    "المبلغ": f"{t.amount:,.2f} ج.م",
                    "الوصف": t.description
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("لا توجد تحويلات مسجلة.")

db.close()