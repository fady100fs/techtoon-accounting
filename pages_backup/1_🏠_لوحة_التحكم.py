# pages/1_🏠_لوحة_التحكم.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sqlalchemy import func
from database import SessionLocal
import models
from models import ExpenseCategory, Expense, CashBox
from auth_required import require_login, get_current_user_id, get_current_user_name

# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="لوحة التحكم", page_icon="🏠", layout="wide")

# CSS عصري
st.markdown("""
<style>
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .kpi-card.success {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    
    .kpi-card.warning {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    
    .kpi-card.info {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    
    .kpi-value {
        font-size: 32px;
        font-weight: bold;
        margin: 10px 0;
    }
    
    .kpi-label {
        font-size: 14px;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏠 لوحة التحكم التنفيذية")
st.info(f"👤 مرحباً **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

try:
    # ==========================================
    # 1. مؤشرات الأداء الرئيسية (KPIs)
    # ==========================================
    st.subheader("📊 مؤشرات الأداء الرئيسية")
    
    # حساب الإحصائيات
    today = datetime.now()
    this_month_start = today.replace(day=1)
    last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    
    # المبيعات
    total_sales = db.query(func.sum(models.Invoice.net_amount)).filter(
        models.Invoice.type == 'sale',
        models.Invoice.status != 'cancelled'
    ).scalar() or 0.0
    
    monthly_sales = db.query(func.sum(models.Invoice.net_amount)).filter(
        models.Invoice.type == 'sale',
        models.Invoice.status != 'cancelled',
        models.Invoice.date >= this_month_start
    ).scalar() or 0.0
    
    # المشتريات
    total_purchases = db.query(func.sum(models.Invoice.net_amount)).filter(
        models.Invoice.type == 'purchase',
        models.Invoice.status != 'cancelled'
    ).scalar() or 0.0
    
    # المصروفات
    total_expenses = db.query(func.sum(Expense.amount)).scalar() or 0.0
    
    # عدد الفواتير
    total_invoices = db.query(models.Invoice).filter(
        models.Invoice.status != 'cancelled'
    ).count()
    
    # عدد العملاء
    total_customers = db.query(models.Party).filter(
        models.Party.type == 'customer'
    ).count()
    
    # عدد الأصناف
    total_items = db.query(models.Item).filter(
        models.Item.is_kit == False
    ).count()
    
    # عرض KPIs
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="kpi-card success">
            <div style="font-size: 40px;">💰</div>
            <div class="kpi-value">{total_sales:,.0f}</div>
            <div class="kpi-label">إجمالي المبيعات (ج.م)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="kpi-card info">
            <div style="font-size: 40px;">📈</div>
            <div class="kpi-value">{monthly_sales:,.0f}</div>
            <div class="kpi-label">مبيعات الشهر (ج.م)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="kpi-card warning">
            <div style="font-size: 40px;">💸</div>
            <div class="kpi-value">{total_expenses:,.0f}</div>
            <div class="kpi-label">إجمالي المصروفات (ج.م)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div style="font-size: 40px;">🧾</div>
            <div class="kpi-value">{total_invoices}</div>
            <div class="kpi-label">عدد الفواتير</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="kpi-card success">
            <div style="font-size: 40px;"></div>
            <div class="kpi-value">{total_customers}</div>
            <div class="kpi-label">عدد العملاء</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==========================================
    # 2. الرسوم البيانية
    # ==========================================
    st.subheader("📈 التحليلات والرسوم البيانية")
    
    chart_tab1, chart_tab2, chart_tab3, chart_tab4 = st.tabs([
        "📊 المبيعات الشهرية",
        "🏆 أفضل العملاء",
        "💸 تحليل المصروفات",
        "📦 حالة المخزون"
    ])
    
    with chart_tab1:
        st.markdown("### 📊 المبيعات الشهرية")
        
        # جلب بيانات المبيعات الشهرية
        sales_by_month = db.query(
            func.strftime('%Y-%m', models.Invoice.date).label('month'),
            func.sum(models.Invoice.net_amount).label('total')
        ).filter(
            models.Invoice.type == 'sale',
            models.Invoice.status != 'cancelled'
        ).group_by(
            func.strftime('%Y-%m', models.Invoice.date)
        ).order_by(
            func.strftime('%Y-%m', models.Invoice.date)
        ).all()
        
        if sales_by_month:
            df_sales = pd.DataFrame(sales_by_month)
            df_sales.columns = ['الشهر', 'المبيعات']
            
            fig = px.bar(
                df_sales,
                x='الشهر',
                y='المبيعات',
                title='المبيعات الشهرية',
                color_discrete_sequence=['#667eea']
            )
            fig.update_layout(
                xaxis_title='الشهر',
                yaxis_title='المبيعات (ج.م)',
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد بيانات مبيعات")
    
    with chart_tab2:
        st.markdown("### 🏆 أفضل 10 عملاء")
        
        top_customers = db.query(
            models.Party.name,
            func.sum(models.Invoice.net_amount).label('total')
        ).join(
            models.Invoice, models.Party.id == models.Invoice.party_id
        ).filter(
            models.Invoice.type == 'sale',
            models.Invoice.status != 'cancelled'
        ).group_by(
            models.Party.name
        ).order_by(
            func.sum(models.Invoice.net_amount).desc()
        ).limit(10).all()
        
        if top_customers:
            df_customers = pd.DataFrame(top_customers)
            df_customers.columns = ['العميل', 'المبيعات']
            
            fig = px.pie(
                df_customers,
                values='المبيعات',
                names='العميل',
                title='توزيع المبيعات على أفضل 10 عملاء'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد بيانات عملاء")
    
    with chart_tab3:
        st.markdown("### 💸 تحليل المصروفات حسب التصنيف")
        
        expenses_by_category = db.query(
            ExpenseCategory.name,
            func.sum(Expense.amount).label('total')
        ).join(
            Expense, ExpenseCategory.id == Expense.category_id
        ).group_by(
            ExpenseCategory.name
        ).all()
        
        if expenses_by_category:
            df_expenses = pd.DataFrame(expenses_by_category)
            df_expenses.columns = ['التصنيف', 'المبلغ']
            
            fig = px.bar(
                df_expenses,
                x='التصنيف',
                y='المبلغ',
                title='المصروفات حسب التصنيف',
                color_discrete_sequence=['#f5576c']
            )
            fig.update_layout(
                xaxis_title='التصنيف',
                yaxis_title='المبلغ (ج.م)',
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد مصروفات مسجلة")
    
    with chart_tab4:
        st.markdown("### 📦 حالة المخزون")
        
        items = db.query(models.Item).filter(
            models.Item.is_kit == False
        ).all()
        
        if items:
            low_stock_count = 0
            for item in items:
                movements = db.query(models.InventoryMovement).filter(
                    models.InventoryMovement.item_id == item.id
                ).all()
                current_stock = sum(m.quantity if m.type == 'in' else -m.quantity for m in movements)
                
                if current_stock <= item.min_stock:
                    low_stock_count += 1
            
            good_stock = len(items) - low_stock_count
            
            fig = go.Figure(data=[
                go.Pie(
                    labels=['مخزون جيد', 'تحت الحد الأدنى'],
                    values=[good_stock, low_stock_count],
                    marker_colors=['#11998e', '#f5576c']
                )
            ])
            fig.update_layout(title='حالة المخزون')
            st.plotly_chart(fig, use_container_width=True)
            
            st.info(f" إجمالي الأصناف: {len(items)} | ⚠️ تحت الحد الأدنى: {low_stock_count}")
        else:
            st.info("لا توجد أصناف في المخزون")
    
    st.markdown("---")
    
    # ==========================================
    # 3. آخر العمليات
    # ==========================================
    st.subheader("📋 آخر العمليات")
    
    last_tab1, last_tab2, last_tab3 = st.tabs([
        "🧾 آخر الفواتير",
        "💰 آخر المدفوعات",
        "💸 آخر المصروفات"
    ])
    
    with last_tab1:
        recent_invoices = db.query(models.Invoice).order_by(
            models.Invoice.date.desc()
        ).limit(5).all()
        
        if recent_invoices:
            data = []
            for inv in recent_invoices:
                party = db.query(models.Party).filter(models.Party.id == inv.party_id).first()
                data.append({
                    "رقم الفاتورة": inv.invoice_number,
                    "التاريخ": inv.date.strftime("%Y-%m-%d %H:%M"),
                    "النوع": "بيع" if inv.type == 'sale' else "شراء",
                    "العميل/المورد": party.name if party else "-",
                    "المبلغ": f"{inv.net_amount:,.2f} ج.م",
                    "الحالة": inv.status
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("لا توجد فواتير")
    
    with last_tab2:
        recent_payments = db.query(models.Payment).order_by(
            models.Payment.date.desc()
        ).limit(5).all()
        
        if recent_payments:
            data = []
            for pay in recent_payments:
                party = db.query(models.Party).filter(models.Party.id == pay.party_id).first()
                data.append({
                    "التاريخ": pay.date.strftime("%Y-%m-%d %H:%M"),
                    "النوع": "قبض" if pay.payment_type == 'receipt' else "صرف",
                    "العميل/المورد": party.name if party else "-",
                    "المبلغ": f"{pay.amount:,.2f} ج.م",
                    "الطريقة": pay.payment_method
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("لا توجد مدفوعات")
    
    with last_tab3:
        recent_expenses = db.query(Expense).order_by(
            Expense.date.desc()
        ).limit(5).all()
        
        if recent_expenses:
            data = []
            for exp in recent_expenses:
                cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == exp.category_id).first()
                data.append({
                    "التاريخ": exp.date.strftime("%Y-%m-%d %H:%M"),
                    "التصنيف": cat.name if cat else "-",
                    "المبلغ": f"{exp.amount:,.2f} ج.م",
                    "الوصف": exp.description
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("لا توجد مصروفات")

finally:
    db.close()