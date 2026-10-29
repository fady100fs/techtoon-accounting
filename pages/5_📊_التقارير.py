import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/5_📊_التقارير.py
import streamlit as st
import pandas as pd
from sqlalchemy import func
from database import SessionLocal
import models
from cache_helpers import get_items_with_stock

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

    # ✅ استعلامان فقط (بدل N+2)
    all_items = get_items_with_stock()
    items = [it for it in all_items if not it["is_kit"]]

    if items:
        data = []
        for it in items:
            data.append({
                "الصنف": it["name"],
                "الباركود": it["barcode"] or "-",
                "سعر التكلفة": it["cost_price"],
                "سعر البيع": it["sell_price"],
                "الرصيد الحالي": it["current_stock"],
                "الحد الأدنى": it["min_stock"],
                "الحالة": "⚠️ منخفض" if it["current_stock"] <= it["min_stock"] else "✅ جيد",
                "قيمة المخزون": it["current_stock"] * it["cost_price"],
            })

        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            total_value = df['قيمة المخزون'].sum()
            st.metric("إجمالي قيمة المخزون", f"{total_value:,.2f} ج.م")
        with c2:
            low_count = len(df[df['الحالة'] == "⚠️ منخفض"])
            st.metric("أصناف تحت الحد", low_count)
        with c3:
            st.metric("إجمالي الأصناف", len(df))

        st.markdown("---")

        if st.button("📤 تصدير تقرير المخزون إلى Excel", type="primary"):
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