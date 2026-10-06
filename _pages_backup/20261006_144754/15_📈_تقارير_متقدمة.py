
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/15_📈_تقارير_متقدمة.py
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from database import SessionLocal
import models
from auth_required import require_login

# التحقق من تسجيل الدخول
current_user = require_login()

st.set_page_config(page_title="تقارير متقدمة", page_icon="📈", layout="wide")
st.title("📈 التقارير المتقدمة وتحليل الأداء")

st.info(f"👤 مرحباً **{current_user['full_name']}** | يتم عرض البيانات بناءً على جميع العمليات المسجلة.")

db = SessionLocal()

try:
    tab1, tab2, tab3 = st.tabs([
        "🏆 الأصناف الأكثر والأقل مبيعاً",
        "👑 تحليل العملاء",
        "💰 تحليل هوامش الربح"
    ])

    # ==========================================
    # التبويب 1: الأصناف الأكثر والأقل مبيعاً
    # ==========================================
    with tab1:
        st.subheader("🏆 الأصناف الأكثر مبيعاً (Top 10)")
        
        # استعلام الأصناف الأكثر مبيعاً
        top_items_query = db.query(
            models.Item.name,
            func.sum(models.InvoiceLine.quantity).label('total_qty'),
            func.sum(models.InvoiceLine.total).label('total_revenue')
        ).join(
            models.InvoiceLine, models.Item.id == models.InvoiceLine.item_id
        ).join(
            models.Invoice, models.InvoiceLine.invoice_id == models.Invoice.id
        ).filter(
            models.Invoice.type == 'sale',
            models.Invoice.status != 'cancelled'
        ).group_by(
            models.Item.name
        ).order_by(
            func.sum(models.InvoiceLine.quantity).desc()
        ).limit(10).all()

        if top_items_query:
            df_top = pd.DataFrame(top_items_query)
            df_top.columns = ['اسم الصنف', 'الكمية المباعة', 'إجمالي الإيرادات']
            
            fig = px.bar(
                df_top, x='اسم الصنف', y='الكمية المباعة', 
                title='أعلى 10 أصناف مبيعاً', color='الكمية المباعة',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_top, use_container_width=True)
        else:
            st.info("لا توجد بيانات مبيعات كافية.")

        st.markdown("---")
        st.subheader("🐢 الأصناف الراكدة (لم تباع منذ 30 يوماً)")
        
        # حساب الأصناف الراكدة
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        all_items = db.query(models.Item).filter(models.Item.is_kit == False).all()
        dead_stock = []
        
        for item in all_items:
            # حساب المخزون الحالي
            movements = db.query(models.InventoryMovement).filter(
                models.InventoryMovement.item_id == item.id
            ).all()
            current_stock = sum(m.quantity if m.type == 'in' else -m.quantity for m in movements)
            
            if current_stock > 0:
                # التحقق من آخر عملية بيع
                last_sale = db.query(models.InvoiceLine).join(
                    models.Invoice
                ).filter(
                    models.InvoiceLine.item_id == item.id,
                    models.Invoice.type == 'sale',
                    models.Invoice.date >= thirty_days_ago
                ).first()
                
                if not last_sale:
                    dead_stock.append({
                        'الصنف': item.name,
                        'المخزون الحالي': current_stock,
                        'قيمة المخزون الراكد': current_stock * item.cost_price,
                        'سعر البيع': item.sell_price
                    })
        
        if dead_stock:
            df_dead = pd.DataFrame(dead_stock)
            st.warning(f"⚠️ يوجد {len(dead_stock)} صنف راكد لم يُبع منذ أكثر من 30 يوماً!")
            st.dataframe(df_dead, use_container_width=True)
            
            total_dead_value = df_dead['قيمة المخزون الراكد'].sum()
            st.metric("إجمالي قيمة المخزون الراكد", f"{total_dead_value:,.2f} ج.م")
        else:
            st.success("✅ ممتاز! لا توجد أصناف راكدة.")

    # ==========================================
    # التبويب 2: تحليل العملاء
    # ==========================================
    with tab2:
        st.subheader("👑 أفضل العملاء (أعلى مشتريات)")
        
        top_customers_query = db.query(
            models.Party.name,
            func.count(models.Invoice.id).label('invoice_count'),
            func.sum(models.Invoice.net_amount).label('total_spent')
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

        if top_customers_query:
            df_customers = pd.DataFrame(top_customers_query)
            df_customers.columns = ['اسم العميل', 'عدد الفواتير', 'إجمالي المشتريات']
            
            fig_pie = px.pie(
                df_customers, values='إجمالي المشتريات', names='اسم العميل',
                title='توزيع المبيعات على أفضل 10 عملاء', hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            st.dataframe(df_customers, use_container_width=True)
        else:
            st.info("لا توجد بيانات عملاء كافية.")

    # ==========================================
    # التبويب 3: تحليل هوامش الربح
    # ==========================================
    with tab3:
        st.subheader("💰 تحليل هوامش الربح للأصناف المباعة")
        
        # هذا التقرير يحسب الربح الصافي لكل صنف بناءً على (سعر البيع - سعر التكلفة)
        profit_query = db.query(
            models.Item.name,
            func.sum(models.InvoiceLine.quantity).label('total_qty'),
            (models.Item.sell_price - models.Item.cost_price).label('unit_profit'),
            func.sum(models.InvoiceLine.quantity * (models.Item.sell_price - models.Item.cost_price)).label('total_profit')
        ).join(
            models.InvoiceLine, models.Item.id == models.InvoiceLine.item_id
        ).join(
            models.Invoice, models.InvoiceLine.invoice_id == models.Invoice.id
        ).filter(
            models.Invoice.type == 'sale',
            models.Invoice.status != 'cancelled',
            models.Item.is_kit == False
        ).group_by(
            models.Item.name, models.Item.sell_price, models.Item.cost_price
        ).order_by(
            func.sum(models.InvoiceLine.quantity * (models.Item.sell_price - models.Item.cost_price)).desc()
        ).all()

        if profit_query:
            df_profit = pd.DataFrame(profit_query)
            df_profit.columns = ['اسم الصنف', 'الكمية المباعة', 'ربح الوحدة', 'إجمالي الربح']
            
            # تنسيق الأرقام
            df_profit['ربح الوحدة'] = df_profit['ربح الوحدة'].apply(lambda x: f"{x:,.2f}")
            df_profit['إجمالي الربح'] = df_profit['إجمالي الربح'].apply(lambda x: f"{x:,.2f}")
            
            st.dataframe(df_profit, use_container_width=True)
            
            total_net_profit = sum(row['total_profit'] for row in profit_query)
            st.metric("إجمالي صافي الربح من المبيعات", f"{total_net_profit:,.2f} ج.م")
        else:
            st.info("لا توجد بيانات أرباح كافية.")

finally:
    db.close()