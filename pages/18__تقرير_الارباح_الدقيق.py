
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/18_💰_تقرير_الارباح_الدقيق.py
import streamlit as st
import pandas as pd
from sqlalchemy import func
from database import SessionLocal
import models
from models import CostHistory
from auth_required import require_login
from form_manager import clear_form, show_clear_hint

# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لكل مفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "profit_"


# التحقق من تسجيل الدخول
current_user = require_login()

st.set_page_config(page_title="تقرير الأرباح الدقيق", page_icon="💰", layout="wide")
st.title("💰 تقرير الأرباح والخسائر الدقيق")

show_clear_hint()  # 💡 الحقول ستُفرَّغ تلقائياً بعد كل عملية

st.info(f" مرحباً **{current_user['full_name']}** | التقرير يعتمد على فواتير الشراء والبيع الفعلية")

db = SessionLocal()

try:
    tab1, tab2, tab3 = st.tabs([
        "📊 ملخص الأرباح",
        "📦 أرباح الأصناف",
        "📈 سجل تكاليف الشراء"
    ])
    
    # ==========================================
    # التبويب 1: ملخص الأرباح
    # ==========================================
    with tab1:
        st.subheader("📊 ملخص الأرباح والخسائر")
        
        # إجمالي المبيعات
        total_sales = db.query(func.sum(models.InvoiceLine.total)).join(
            models.Invoice
        ).filter(
            models.Invoice.type == 'sale',
            models.Invoice.status != 'cancelled'
        ).scalar() or 0.0
        
        # إجمالي التكلفة (من CostHistory)
        total_cost = db.query(func.sum(CostHistory.total_cost)).scalar() or 0.0
        
        # الربح الإجمالي
        gross_profit = total_sales - total_cost
        profit_margin = (gross_profit / total_sales * 100) if total_sales > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("إجمالي المبيعات", f"{total_sales:,.2f} ج.م")
        with col2:
            st.metric("إجمالي التكلفة", f"{total_cost:,.2f} ج.م")
        with col3:
            st.metric("صافي الربح", f"{gross_profit:,.2f} ج.م", delta=f"{profit_margin:.1f}%")
        with col4:
            st.metric("هامش الربح", f"{profit_margin:.1f}%")
        
        st.markdown("---")
        
        # رسم بياني
        import plotly.graph_objects as go
        
        fig = go.Figure(data=[
            go.Bar(name='المبيعات', x=['الإجمالي'], y=[total_sales], marker_color='green'),
            go.Bar(name='التكلفة', x=['الإجمالي'], y=[total_cost], marker_color='red'),
            go.Bar(name='الربح', x=['الإجمالي'], y=[gross_profit], marker_color='blue')
        ])
        
        fig.update_layout(
            title='ملخص الأرباح والخسائر',
            barmode='group',
            yaxis_title='المبلغ (ج.م)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # ==========================================
    # التبويب 2: أرباح الأصناف
    # ==========================================
    with tab2:
        st.subheader("📦 تحليل أرباح كل صنف")
        
        items = db.query(models.Item).filter(models.Item.is_kit == False).all()
        
        if items:
            data = []
            for item in items:
                # المبيعات
                sales = db.query(models.InvoiceLine).join(
                    models.Invoice
                ).filter(
                    models.InvoiceLine.item_id == item.id,
                    models.Invoice.type == 'sale',
                    models.Invoice.status != 'cancelled'
                ).all()
                
                total_sales_qty = sum(s.quantity for s in sales)
                total_sales_revenue = sum(s.total for s in sales)
                
                # المشتريات
                purchases = db.query(CostHistory).filter(
                    CostHistory.item_id == item.id
                ).all()
                
                total_purchase_qty = sum(p.quantity for p in purchases)
                total_purchase_cost = sum(p.total_cost for p in purchases)
                
                # الربح
                profit = total_sales_revenue - total_purchase_cost
                profit_margin = (profit / total_sales_revenue * 100) if total_sales_revenue > 0 else 0
                
                data.append({
                    'الصنف': item.name,
                    'الكمية المباعة': total_sales_qty,
                    'إجمالي المبيعات': total_sales_revenue,
                    'الكمية المشتراة': total_purchase_qty,
                    'إجمالي التكلفة': total_purchase_cost,
                    'الربح': profit,
                    'هامش الربح %': f"{profit_margin:.1f}%",
                    'متوسط سعر الشراء': item.avg_cost_price,
                    'آخر سعر شراء': item.cost_price,
                    'سعر البيع الاسترشادي': item.sell_price
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            
            # تصدير
            if st.button(" تصدير التقرير إلى Excel"):
                filename = "Profit_Report.xlsx"
                df.to_excel(filename, index=False, engine='xlsxwriter')
                with open(filename, "rb") as file:
                    st.download_button(
                        label="⬇️ تحميل Excel",
                        data=file,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.info("لا توجد أصناف.")
    
    # ==========================================
    # التبويب 3: سجل تكاليف الشراء
    # ==========================================
    with tab3:
        st.subheader("📈 سجل تكاليف الشراء لكل صنف")
        
        items = db.query(models.Item).filter(models.Item.is_kit == False).all()
        
        if items:
            selected_item = st.selectbox("اختر صنف:", [item.name for item in items])
            
            if selected_item:
                item = db.query(models.Item).filter(models.Item.name == selected_item).first()
                
                if item:
                    cost_records = db.query(CostHistory).filter(
                        CostHistory.item_id == item.id
                    ).order_by(CostHistory.purchase_date.desc()).all()
                    
                    if cost_records:
                        data = []
                        for record in cost_records:
                            supplier = db.query(models.Party).filter(
                                models.Party.id == record.supplier_id
                            ).first()
                            
                            data.append({
                                'التاريخ': record.purchase_date.strftime('%Y-%m-%d %H:%M'),
                                'المورد': supplier.name if supplier else 'غير محدد',
                                'الكمية': record.quantity,
                                'سعر الشراء': record.purchase_price,
                                'التكلفة الإجمالية': record.total_cost
                            })
                        
                        df_cost = pd.DataFrame(data)
                        st.dataframe(df_cost, use_container_width=True)
                        
                        st.markdown("---")
                        st.write(f"**متوسط سعر الشراء:** {item.avg_cost_price:,.2f} ج.م")
                        st.write(f"**آخر سعر شراء:** {item.cost_price:,.2f} ج.م")
                        st.write(f"**سعر البيع الاسترشادي:** {item.sell_price:,.2f} ج.م")
                    else:
                        st.info("لا توجد سجلات شراء لهذا الصنف.")
        else:
            st.info("لا توجد أصناف.")

finally:
    db.close()