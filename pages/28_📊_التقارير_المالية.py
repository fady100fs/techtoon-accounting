
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/28_📊_التقارير_المالية.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import SessionLocal
import models
from services import (
    get_income_statement, get_balance_sheet, get_trial_balance,
    get_cash_flow_statement, get_financial_ratios,
    create_budget, get_budget_vs_actual
)
from auth_required import require_login, get_current_user_id, get_current_user_name
from form_manager import clear_form, show_clear_hint

# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لكل مفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "fin_rep_"


# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="التقارير المالية", page_icon="", layout="wide")
st.title(" التقارير المالية المتقدمة")

show_clear_hint()  # 💡 الحقول ستُفرَّغ تلقائياً بعد كل عملية

st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 قائمة الدخل",
    "⚖️ الميزانية العمومية",
    "📋 ميزان المراجعة",
    "💰 التدفقات النقدية",
    "📊 النسب المالية",
    " الموازنات"
])

# ==========================================
# التبويب 1: قائمة الدخل
# ==========================================
with tab1:
    st.subheader("📈 قائمة الدخل")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من تاريخ:", value=datetime.now().replace(month=1, day=1))
    with col2:
        end_date = st.date_input("إلى تاريخ:", value=datetime.now())
    
    if st.button(" عرض قائمة الدخل", type="primary"):
        income_data = get_income_statement(start_date, end_date)
        
        st.markdown("---")
        st.markdown("### 📄 قائمة الدخل")
        st.markdown(f"**الفترة:** من {start_date.strftime('%Y-%m-%d')} إلى {end_date.strftime('%Y-%m-%d')}")
        
        # عرض البيانات
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💰 الإيرادات والتكاليف")
            st.metric("إجمالي الإيرادات", f"{income_data['revenue']:,.2f} ج.م")
            st.metric("تكلفة المبيعات", f"{income_data['cogs']:,.2f} ج.م")
            st.metric("الربح الإجمالي", f"{income_data['gross_profit']:,.2f} ج.م", 
                     delta=f"{income_data['gross_margin']:.1f}%")
        
        with col2:
            st.markdown("### 💸 المصروفات")
            st.metric("المصروفات التشغيلية", f"{income_data['operating_expenses']:,.2f} ج.م")
            st.metric("مصروفات الرواتب", f"{income_data['salary_expenses']:,.2f} ج.م")
            st.metric("مصروفات الإهلاك", f"{income_data['depreciation_expenses']:,.2f} ج.م")
            st.metric("إجمالي المصروفات", f"{income_data['total_expenses']:,.2f} ج.م")
        
        st.markdown("---")
        
        # صافي الربح
        if income_data['net_profit'] > 0:
            st.success(f"### ✅ صافي الربح: {income_data['net_profit']:,.2f} ج.م ({income_data['net_margin']:.1f}%)")
        else:
            st.error(f"### ❌ صافي الخسارة: {income_data['net_profit']:,.2f} ج.م ({income_data['net_margin']:.1f}%)")
        
        # رسم بياني
        fig = go.Figure(data=[
            go.Bar(name='الإيرادات', x=[''], y=[income_data['revenue']], marker_color='#10b981'),
            go.Bar(name='التكاليف', x=[''], y=[income_data['cogs']], marker_color='#ef4444'),
            go.Bar(name='الربح الإجمالي', x=[''], y=[income_data['gross_profit']], marker_color='#3b82f6'),
            go.Bar(name='المصروفات', x=[''], y=[income_data['total_expenses']], marker_color='#f59e0b'),
            go.Bar(name='صافي الربح', x=[''], y=[income_data['net_profit']], marker_color='#8b5cf6')
        ])
        
        fig.update_layout(
            title='قائمة الدخل',
            barmode='group',
            yaxis_title='المبلغ (ج.م)',
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# التبويب 2: الميزانية العمومية
# ==========================================
with tab2:
    st.subheader("⚖️ الميزانية العمومية")
    
    as_of_date = st.date_input("تاريخ الميزانية:", value=datetime.now())
    
    if st.button(" عرض الميزانية العمومية", type="primary"):
        balance_data = get_balance_sheet(as_of_date)
        
        st.markdown("---")
        st.markdown("### 📄 الميزانية العمومية")
        st.markdown(f"**بتاريخ:** {as_of_date.strftime('%Y-%m-%d')}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 📈 الأصول")
            for asset_name, asset_value in balance_data['assets'].items():
                st.write(f"**{asset_name}:** {asset_value:,.2f} ج.م")
            st.markdown("---")
            st.metric("إجمالي الأصول", f"{balance_data['total_assets']:,.2f} ج.م")
        
        with col2:
            st.markdown("### 📉 الخصوم")
            for liab_name, liab_value in balance_data['liabilities'].items():
                st.write(f"**{liab_name}:** {liab_value:,.2f} ج.م")
            st.markdown("---")
            st.metric("إجمالي الخصوم", f"{balance_data['total_liabilities']:,.2f} ج.م")
        
        with col3:
            st.markdown("### 👑 حقوق الملكية")
            for eq_name, eq_value in balance_data['equity'].items():
                st.write(f"**{eq_name}:** {eq_value:,.2f} ج.م")
            st.markdown("---")
            st.metric("إجمالي حقوق الملكية", f"{balance_data['total_equity']:,.2f} ج.م")
        
        st.markdown("---")
        
        # التحقق من التوازن
        difference = balance_data['total_assets'] - (balance_data['total_liabilities'] + balance_data['total_equity'])
        
        if abs(difference) < 0.01:
            st.success("✅ الميزانية متوازنة!")
        else:
            st.error(f"️ الميزانية غير متوازنة! الفرق: {difference:,.2f} ج.م")
        
        # رسم بياني
        fig = go.Figure(data=[
            go.Pie(
                labels=['الأصول', 'الخصوم', 'حقوق الملكية'],
                values=[balance_data['total_assets'], balance_data['total_liabilities'], balance_data['total_equity']],
                marker_colors=['#10b981', '#ef4444', '#3b82f6']
            )
        ])
        
        fig.update_layout(title='توزيع الميزانية العمومية')
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# التبويب 3: ميزان المراجعة
# ==========================================
with tab3:
    st.subheader("📋 ميزان المراجعة")
    
    col1, col2 = st.columns(2)
    with col1:
        tb_start = st.date_input("من تاريخ:", value=datetime.now().replace(month=1, day=1), key=f"{PFX}tb_start")
    with col2:
        tb_end = st.date_input("إلى تاريخ:", value=datetime.now(), key=f"{PFX}tb_end")
    
    if st.button("📊 عرض ميزان المراجعة", type="primary"):
        trial_balance = get_trial_balance(tb_start, tb_end)
        
        st.markdown("---")
        st.markdown("### 📄 ميزان المراجعة")
        st.markdown(f"**الفترة:** من {tb_start.strftime('%Y-%m-%d')} إلى {tb_end.strftime('%Y-%m-%d')}")
        
        if trial_balance['accounts']:
            df = pd.DataFrame(trial_balance['accounts'])
            st.dataframe(df, use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("إجمالي المدين", f"{trial_balance['total_debit']:,.2f} ج.م")
            with col2:
                st.metric("إجمالي الدائن", f"{trial_balance['total_credit']:,.2f} ج.م")
            with col3:
                st.metric("الفرق", f"{trial_balance['difference']:,.2f} ج.م")
            
            if abs(trial_balance['difference']) < 0.01:
                st.success("✅ ميزان المراجعة متوازن!")
            else:
                st.error("⚠️ ميزان المراجعة غير متوازن!")
        else:
            st.info("لا توجد قيود في الفترة المحددة.")

# ==========================================
# التبويب 4: التدفقات النقدية
# ==========================================
with tab4:
    st.subheader("💰 قائمة التدفقات النقدية")
    
    col1, col2 = st.columns(2)
    with col1:
        cf_start = st.date_input("من تاريخ:", value=datetime.now().replace(month=1, day=1), key=f"{PFX}cf_start")
    with col2:
        cf_end = st.date_input("إلى تاريخ:", value=datetime.now(), key=f"{PFX}cf_end")
    
    if st.button("📊 عرض التدفقات النقدية", type="primary"):
        cash_flow = get_cash_flow_statement(cf_start, cf_end)
        
        st.markdown("---")
        st.markdown("### 📄 قائمة التدفقات النقدية")
        st.markdown(f"**الفترة:** من {cf_start.strftime('%Y-%m-%d')} إلى {cf_end.strftime('%Y-%m-%d')}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💵 التدفقات الداخلة")
            st.metric("من العمليات", f"{cash_flow['cash_from_operations']:,.2f} ج.م")
            st.metric("من الاستثمار", f"{cash_flow['cash_from_investing']:,.2f} ج.م")
            st.metric("من التمويل", f"{cash_flow['cash_from_financing']:,.2f} ج.م")
        
        with col2:
            st.markdown("### 💸 التدفقات الخارجة")
            st.metric("للعمليات", f"{cash_flow['cash_to_operations']:,.2f} ج.م")
        
        st.markdown("---")
        
        if cash_flow['net_cash_flow'] > 0:
            st.success(f"### ✅ صافي التدفق النقدي: {cash_flow['net_cash_flow']:,.2f} ج.م")
        else:
            st.error(f"### ❌ صافي التدفق النقدي: {cash_flow['net_cash_flow']:,.2f} ج.م")
        
        # رسم بياني
        fig = go.Figure(data=[
            go.Bar(name='التدفقات الداخلة', x=['العمليات', 'الاستثمار', 'التمويل'], 
                   y=[cash_flow['cash_from_operations'], cash_flow['cash_from_investing'], cash_flow['cash_from_financing']],
                   marker_color='#10b981'),
            go.Bar(name='التدفقات الخارجة', x=['العمليات'], 
                   y=[cash_flow['cash_to_operations']],
                   marker_color='#ef4444')
        ])
        
        fig.update_layout(
            title='التدفقات النقدية',
            barmode='group',
            yaxis_title='المبلغ (ج.م)',
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# التبويب 5: النسب المالية
# ==========================================
with tab5:
    st.subheader("📊 النسب المالية")
    
    col1, col2 = st.columns(2)
    with col1:
        ratio_start = st.date_input("من تاريخ:", value=datetime.now().replace(month=1, day=1), key=f"{PFX}ratio_start")
    with col2:
        ratio_end = st.date_input("إلى تاريخ:", value=datetime.now(), key=f"{PFX}ratio_end")
    
    if st.button("📊 حساب النسب المالية", type="primary"):
        ratios = get_financial_ratios(ratio_start, ratio_end)
        
        st.markdown("---")
        st.markdown("###  النسب المالية")
        st.markdown(f"**الفترة:** من {ratio_start.strftime('%Y-%m-%d')} إلى {ratio_end.strftime('%Y-%m-%d')}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 💧 نسب السيولة")
            st.metric("نسبة السيولة الحالية", f"{ratios['current_ratio']:.2f}")
            st.info("المثالي: 1.5 - 3.0")
        
        with col2:
            st.markdown("### 📈 نسب الربحية")
            st.metric("هامش الربح", f"{ratios['profit_margin']:.1f}%")
            st.metric("الإيرادات", f"{ratios['revenue']:,.2f} ج.م")
            st.metric("صافي الربح", f"{ratios['net_profit']:,.2f} ج.م")
        
        with col3:
            st.markdown("### ⚙️ نسب الكفاءة")
            st.metric("معدل دوران المخزون", f"{ratios['inventory_turnover']:.2f}")
            st.info("المثالي: 4 - 6 مرات سنوياً")
        
        # رسم بياني
        fig = go.Figure(data=[
            go.Indicator(
                mode="gauge+number+delta",
                value=ratios['current_ratio'],
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "نسبة السيولة الحالية"},
                delta={'reference': 2.0},
                gauge={
                    'axis': {'range': [None, 5]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 1], 'color': "red"},
                        {'range': [1, 2], 'color': "yellow"},
                        {'range': [2, 3], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 1.5
                    }
                }
            )
        ])
        
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# التبويب 6: الموازنات
# ==========================================
with tab6:
    st.subheader("📅 الموازنات التقديرية")
    
    budget_tab1, budget_tab2 = st.tabs(["➕ إضافة موازنة", "📊 مقارنة الموازنة بالفعلي"])
    
    with budget_tab1:
        st.markdown("### ➕ إضافة موازنة شهرية")
        
        # اختيار الحساب
        accounts = db.query(models.Account).all()
        account_dict = {acc.id: f"{acc.code} - {acc.name}" for acc in accounts}
        
        selected_account_id = st.selectbox(
            "اختر الحساب:",
            options=list(account_dict.keys()),
            format_func=lambda x: account_dict[x]
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            budget_month = st.number_input("الشهر:", min_value=1, max_value=12, value=datetime.now().month)
        with col2:
            budget_year = st.number_input("السنة:", min_value=2020, max_value=2100, value=datetime.now().year)
        with col3:
            budget_amount = st.number_input("المبلغ الموازن:", min_value=0.0, step=1000.0, format="%.2f")
        
        budget_notes = st.text_area("ملاحظات:")
        
        if st.button("💾 حفظ الموازنة", type="primary"):
            if not selected_account_id or budget_amount <= 0:
                st.error("يرجى اختيار الحساب وإدخال مبلغ صحيح")
            else:
                try:
                    create_budget(
                        account_id=selected_account_id,
                        month=budget_month,
                        year=budget_year,
                        budgeted_amount=budget_amount,
                        notes=budget_notes if budget_notes else None,
                        created_by=current_user_id
                    )
                    st.success("✅ تم حفظ الموازنة بنجاح!")
                    clear_form(PFX)  # ✅ تفريغ الحقول
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
    
    with budget_tab2:
        st.markdown("###  مقارنة الموازنة بالفعلي")
        
        col1, col2 = st.columns(2)
        with col1:
            compare_month = st.number_input("الشهر:", min_value=1, max_value=12, value=datetime.now().month, key=f"{PFX}compare_month")
        with col2:
            compare_year = st.number_input("السنة:", min_value=2020, max_value=2100, value=datetime.now().year, key=f"{PFX}compare_year")
        
        if st.button("📊 عرض المقارنة", type="primary"):
            comparison = get_budget_vs_actual(compare_month, compare_year)
            
            if comparison:
                df = pd.DataFrame(comparison)
                st.dataframe(df, use_container_width=True)
                
                # رسم بياني
                fig = go.Figure(data=[
                    go.Bar(name='الموازنة', x=df['account_name'], y=df['budgeted'], marker_color='#3b82f6'),
                    go.Bar(name='الفعلي', x=df['account_name'], y=df['actual'], marker_color='#10b981')
                ])
                
                fig.update_layout(
                    title=f'مقارنة الموازنة بالفعلي - شهر {compare_month}/{compare_year}',
                    barmode='group',
                    yaxis_title='المبلغ (ج.م)',
                    template='plotly_white'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("لا توجد موازنات مسجلة لهذا الشهر.")

db.close()