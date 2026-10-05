# pages/5_📊_التقارير.py
import streamlit as st
import pandas as pd
from sqlalchemy import func
from database import SessionLocal
import models

from auth_required import require_login
current_user = require_login()
st.set_page_config(page_title="التقارير", page_icon="📊", layout="wide")
st.title("📊 التقارير المالية")

db = SessionLocal()

tab1, tab2 = st.tabs(["💰 الأرباح والخسائر", "📦 حالة المخزون"])

with tab1:
    st.subheader("تقرير الأرباح والخسائر (Profit & Loss)")
    
    revenues = db.query(func.sum(models.JournalLine.credit)).join(
        models.Account
    ).filter(
        models.Account.type == 'REVENUE',
        models.JournalLine.credit > 0
    ).scalar() or 0
    
    expenses = db.query(func.sum(models.JournalLine.debit)).join(
        models.Account
    ).filter(
        models.Account.type == 'EXPENSE',
        models.JournalLine.debit > 0
    ).scalar() or 0
    
    net_profit = revenues - expenses
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("إجمالي الإيرادات", f"{revenues:,.2f} ج.م")
    with col2:
        st.metric("إجمالي المصروفات", f"{expenses:,.2f} ج.م")
    with col3:
        st.metric("صافي الربح/الخسارة", f"{net_profit:,.2f} ج.م", delta=f"{net_profit:,.2f}")
    
    st.markdown("---")
    
    # زر تصدير Excel
    if st.button("📊 تصدير تقرير الأرباح والخسائر إلى Excel", type="primary"):
        try:
            from export_excel import export_profit_loss_to_excel
            excel_path = export_profit_loss_to_excel()
            st.success(f"تم التصدير: {excel_path}")
            
            with open(excel_path, "rb") as file:
                st.download_button(
                    label="⬇️ تحميل Excel",
                    data=file,
                    file_name=excel_path,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.error(f"خطأ في التصدير: {e}")

with tab2:
    st.subheader("تقرير المخزون")
    items = db.query(models.Item).filter(models.Item.is_kit == False).all()
    
    if items:
        data = []
        for item in items:
            movements = db.query(models.InventoryMovement).filter(
                models.InventoryMovement.item_id == item.id
            ).all()
            
            stock_in = sum(m.quantity for m in movements if m.type == 'in')
            stock_out = sum(m.quantity for m in movements if m.type == 'out')
            current_stock = stock_in - stock_out
            
            data.append({
                "الصنف": item.name,
                "سعر التكلفة": item.cost_price,
                "سعر البيع": item.sell_price,
                "الكمية الواردة": stock_in,
                "الكمية الصادرة": stock_out,
                "الرصيد الحالي": current_stock,
                "قيمة المخزون": current_stock * item.cost_price
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        total_value = df['قيمة المخزون'].sum()
        st.metric("إجمالي قيمة المخزون", f"{total_value:,.2f} ج.م")
        
        st.markdown("---")
        
        # زر تصدير Excel
        if st.button(" تصدير تقرير المخزون إلى Excel", type="primary"):
            try:
                from export_excel import export_inventory_to_excel
                excel_path = export_inventory_to_excel()
                st.success(f"تم التصدير: {excel_path}")
                
                with open(excel_path, "rb") as file:
                    st.download_button(
                        label="⬇️ تحميل Excel",
                        data=file,
                        file_name=excel_path,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"خطأ في التصدير: {e}")
    else:
        st.info("لا توجد أصناف في المخزون.")

db.close()