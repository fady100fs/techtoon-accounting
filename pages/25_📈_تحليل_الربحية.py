
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/25_📈_تحليل_الربحية.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import SessionLocal
import models
from services import (
    get_profitability_by_item, get_profitability_by_customer,
    get_profitability_by_category, get_monthly_profitability,
    compare_periods, get_top_profitable_items, get_profitability_summary
)
from auth_required import require_login, get_current_user_id, get_current_user_name
from form_manager import clear_form, show_clear_hint

# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لكل مفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "prof_"


# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="تحليل الربحية", page_icon="📈", layout="wide")
st.title("📈 تحليل الربحية المتقدم")

show_clear_hint()  # 💡 الحقول ستُفرَّغ تلقائياً بعد كل عملية

st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

# فلاتر التاريخ العامة
st.sidebar.subheader("📅 فلاتر التاريخ")
filter_type = st.sidebar.radio("نوع الفترة:", ["الشهر الحالي", "آخر 3 أشهر", "آخر 6 أشهر", "السنة الحالية", "مخصص"])

if filter_type == "الشهر الحالي":
    start_date = datetime.now().replace(day=1)
    end_date = datetime.now()
elif filter_type == "آخر 3 أشهر":
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
elif filter_type == "آخر 6 أشهر":
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
elif filter_type == "السنة الحالية":
    start_date = datetime.now().replace(month=1, day=1)
    end_date = datetime.now()
else:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.sidebar.date_input("من تاريخ:", value=datetime.now().replace(day=1))
    with col2:
        end_date = st.sidebar.date_input("إلى تاريخ:", value=datetime.now())

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    " الملخص الشامل",
    "📦 ربحية الأصناف",
    "👥 ربحية العملاء",
    "🗂️ ربحية التصنيفات",
    "📈 الربحية الشهرية",
    "⚖️ مقارنة الفترات"
])

# ==========================================
# التبويب 1: الملخص الشامل
# ==========================================
with tab1:
    st.subheader(" الملخص الشامل للربحية")
    
    summary = get_profitability_summary(start_date, end_date)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 إجمالي الإيرادات",
            f"{summary['revenue']:,.2f} ج.م"
        )
    
    with col2:
        st.metric(
            " إجمالي التكلفة",
            f"{summary['cost']:,.2f} ج.م"
        )
    
    with col3:
        st.metric(
            "💵 إجمالي الربح الإجمالي",
            f"{summary['gross_profit']:,.2f} ج.م",
            delta=f"{summary['gross_margin']:.1f}%"
        )
    
    with col4:
        st.metric(
            "📉 المصروفات",
            f"{summary['expenses']:,.2f} ج.م"
        )
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            " صافي الربح",
            f"{summary['net_profit']:,.2f} ج.م",
            delta=f"{summary['net_margin']:.1f}%"
        )
    
    with col2:
        st.metric(
            " هامش الربح الصافي",
            f"{summary['net_margin']:.1f}%"
        )
    
    st.markdown("---")
    
    # رسم بياني للملخص
    fig = go.Figure(data=[
        go.Bar(name='الإيرادات', x=[''], y=[summary['revenue']], marker_color='#10b981'),
        go.Bar(name='التكلفة', x=[''], y=[summary['cost']], marker_color='#ef4444'),
        go.Bar(name='الربح الإجمالي', x=[''], y=[summary['gross_profit']], marker_color='#3b82f6'),
        go.Bar(name='المصروفات', x=[''], y=[summary['expenses']], marker_color='#f59e0b'),
        go.Bar(name='صافي الربح', x=[''], y=[summary['net_profit']], marker_color='#8b5cf6')
    ])
    
    fig.update_layout(
        title='ملخص الربحية',
        barmode='group',
        yaxis_title='المبلغ (ج.م)',
        template='plotly_white'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# التبويب 2: ربحية الأصناف
# ==========================================
with tab2:
    st.subheader("📦 تحليل ربحية الأصناف")
    
    item_profitability = get_profitability_by_item(start_date, end_date)
    
    if item_profitability:
        df = pd.DataFrame(item_profitability)
        
        st.dataframe(df, use_container_width=True)
        
        # رسم بياني
        fig = px.scatter(
            df,
            x='revenue',
            y='profit_margin',
            size='profit',
            color='category',
            hover_name='item_name',
            title='ربحية الأصناف (الإيرادات vs هامش الربح)',
            labels={'revenue': 'الإيرادات (ج.م)', 'profit_margin': 'هامش الربح (%)', 'profit': 'الربح'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # أعلى الأصناف ربحية
        st.markdown("---")
        st.subheader(" أعلى 10 أصناف ربحية")
        
        top_items = get_top_profitable_items(limit=10, start_date=start_date, end_date=end_date)
        
        if top_items:
            df_top = pd.DataFrame(top_items)
            fig = px.bar(
                df_top,
                x='item_name',
                y='profit',
                color='profit_margin',
                title='أعلى الأصناف ربحية',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("لا توجد بيانات ربحية للأصناف في الفترة المحددة.")

# ==========================================
# التبويب 3: ربحية العملاء
# ==========================================
with tab3:
    st.subheader("👥 تحليل ربحية العملاء")
    
    customer_profitability = get_profitability_by_customer(start_date, end_date)
    
    if customer_profitability:
        df = pd.DataFrame(customer_profitability)
        
        st.dataframe(df, use_container_width=True)
        
        # رسم بياني دائري
        fig = px.pie(
            df.head(10),
            values='revenue',
            names='customer_name',
            title='توزيع الإيرادات على أفضل 10 عملاء'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # رسم بياني للربحية
        fig = px.bar(
            df.head(10),
            x='customer_name',
            y='profit',
            color='profit_margin',
            title='ربحية أفضل 10 عملاء',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("لا توجد بيانات ربحية للعملاء في الفترة المحددة.")

# ==========================================
# التبويب 4: ربحية التصنيفات
# ==========================================
with tab4:
    st.subheader("️ تحليل ربحية التصنيفات")
    
    category_profitability = get_profitability_by_category(start_date, end_date)
    
    if category_profitability:
        df = pd.DataFrame(category_profitability)
        
        st.dataframe(df, use_container_width=True)
        
        # رسم بياني
        fig = px.bar(
            df,
            x='category_name',
            y='profit',
            color='profit_margin',
            title='ربحية التصنيفات',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # رسم بياني دائري للإيرادات
        fig = px.pie(
            df,
            values='revenue',
            names='category_name',
            title='توزيع الإيرادات حسب التصنيف'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("لا توجد بيانات ربحية للتصنيفات في الفترة المحددة.")

# ==========================================
# التبويب 5: الربحية الشهرية
# ==========================================
with tab5:
    st.subheader("📈 الربحية الشهرية")
    
    year = st.number_input("السنة:", min_value=2020, max_value=2100, value=datetime.now().year, step=1)
    
    monthly_data = get_monthly_profitability(year)
    
    if monthly_data:
        df = pd.DataFrame(monthly_data)
        
        st.dataframe(df, use_container_width=True)
        
        # رسم بياني خطي
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['month_name'],
            y=df['revenue'],
            mode='lines+markers',
            name='الإيرادات',
            line=dict(color='#10b981', width=3)
        ))
        
        fig.add_trace(go.Scatter(
            x=df['month_name'],
            y=df['cost'],
            mode='lines+markers',
            name='التكلفة',
            line=dict(color='#ef4444', width=3)
        ))
        
        fig.add_trace(go.Scatter(
            x=df['month_name'],
            y=df['profit'],
            mode='lines+markers',
            name='الربح',
            line=dict(color='#3b82f6', width=3)
        ))
        
        fig.update_layout(
            title=f'الربحية الشهرية لسنة {year}',
            xaxis_title='الشهر',
            yaxis_title='المبلغ (ج.م)',
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"لا توجد بيانات ربحية لسنة {year}.")

# ==========================================
# التبويب 6: مقارنة الفترات
# ==========================================
with tab6:
    st.subheader("️ مقارنة فترتين")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📅 الفترة الأولى")
        p1_start = st.date_input("من تاريخ:", value=datetime.now().replace(month=1, day=1), key=f"{PFX}p1_start")
        p1_end = st.date_input("إلى تاريخ:", value=datetime.now(), key=f"{PFX}p1_end")
    
    with col2:
        st.markdown("### 📅 الفترة الثانية")
        p2_start = st.date_input("من تاريخ:", value=(datetime.now() - timedelta(days=365)).replace(month=1, day=1), key=f"{PFX}p2_start")
        p2_end = st.date_input("إلى تاريخ:", value=datetime.now() - timedelta(days=365), key=f"{PFX}p2_end")
    
    if st.button("📊 مقارنة الفترتين", type="primary"):
        comparison = compare_periods(p1_start, p1_end, p2_start, p2_end)
        
        st.markdown("---")
        st.subheader(" نتائج المقارنة")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### الفترة الأولى")
            st.metric("الإيرادات", f"{comparison['period1']['revenue']:,.2f} ج.م")
            st.metric("الربح", f"{comparison['period1']['profit']:,.2f} ج.م")
            st.metric("هامش الربح", f"{comparison['period1']['profit_margin']:.1f}%")
        
        with col2:
            st.markdown("### الفترة الثانية")
            st.metric("الإيرادات", f"{comparison['period2']['revenue']:,.2f} ج.م")
            st.metric("الربح", f"{comparison['period2']['profit']:,.2f} ج.م")
            st.metric("هامش الربح", f"{comparison['period2']['profit_margin']:.1f}%")
        
        st.markdown("---")
        st.subheader("📈 نسبة التغيير")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "تغيير الإيرادات",
                f"{comparison['revenue_change']:+.1f}%",
                delta=f"{comparison['period1']['revenue'] - comparison['period2']['revenue']:,.2f} ج.م"
            )
        
        with col2:
            st.metric(
                "تغيير الربح",
                f"{comparison['profit_change']:+.1f}%",
                delta=f"{comparison['period1']['profit'] - comparison['period2']['profit']:,.2f} ج.م"
            )
        
        # رسم بياني للمقارنة
        fig = go.Figure(data=[
            go.Bar(name='الفترة الأولى', x=['الإيرادات', 'الربح'], y=[comparison['period1']['revenue'], comparison['period1']['profit']], marker_color='#3b82f6'),
            go.Bar(name='الفترة الثانية', x=['الإيرادات', 'الربح'], y=[comparison['period2']['revenue'], comparison['period2']['profit']], marker_color='#10b981')
        ])
        
        fig.update_layout(
            title='مقارنة الفترتين',
            barmode='group',
            yaxis_title='المبلغ (ج.م)',
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)

db.close()