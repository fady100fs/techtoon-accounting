
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/13__التنبيهات.py
import streamlit as st
import pandas as pd
from alerts import get_all_alerts, get_low_stock_items, get_overdue_invoices, get_credit_limit_warnings
from auth_required import require_login
current_user = require_login()
st.set_page_config(page_title="التنبيهات", page_icon="", layout="wide")
st.title(" مركز التنبيهات")

# الحصول على جميع التنبيهات
alerts = get_all_alerts()

# حساب إجمالي التنبيهات
total_alerts = (
    len(alerts['low_stock']) + 
    len(alerts['overdue_invoices']) + 
    len(alerts['credit_warnings'])
)

# عرض ملخص التنبيهات
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("إجمالي التنبيهات", total_alerts)

with col2:
    st.metric("أصناف تحت الحد", len(alerts['low_stock']), 
              delta=f"{len(alerts['low_stock'])} تنبيه" if len(alerts['low_stock']) > 0 else None)

with col3:
    st.metric("فواتير متأخرة", len(alerts['overdue_invoices']),
              delta=f"{len(alerts['overdue_invoices'])} تنبيه" if len(alerts['overdue_invoices']) > 0 else None)

with col4:
    st.metric("تجاوز حد ائتمان", len(alerts['credit_warnings']),
              delta=f"{len(alerts['credit_warnings'])} تنبيه" if len(alerts['credit_warnings']) > 0 else None)

st.markdown("---")

tab1, tab2, tab3 = st.tabs([
    f"📦 أصناف تحت الحد ({len(alerts['low_stock'])})",
    f"📄 فواتير متأخرة ({len(alerts['overdue_invoices'])})",
    f"💳 تجاوز حد ائتمان ({len(alerts['credit_warnings'])})"
])

with tab1:
    st.subheader("أصناف وصلت للحد الأدنى أو أقل")
    
    if alerts['low_stock']:
        data = []
        for item_info in alerts['low_stock']:
            item = item_info['item']
            data.append({
                "الصنف": item.name,
                "الباركود": item.barcode or "-",
                "الرصيد الحالي": item_info['current_stock'],
                "الحد الأدنى": item_info['min_stock'],
                "النقص": item_info['shortage'],
                "سعر البيع": f"{item.sell_price:,.2f} ج.م"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.warning(f"⚠️ يوجد {len(alerts['low_stock'])} صنف يحتاج لإعادة تخزين!")
    else:
        st.success("✅ جميع الأصناف في المخزون بمستويات آمنة.")

with tab2:
    st.subheader("فواتير تجاوزت تاريخ الاستحقاق")
    
    if alerts['overdue_invoices']:
        data = []
        for inv_info in alerts['overdue_invoices']:
            inv = inv_info['invoice']
            party = inv_info['party']
            data.append({
                "رقم الفاتورة": inv.invoice_number,
                "العميل/المورد": party.name if party else "غير محدد",
                "تاريخ الفاتورة": inv.date.strftime("%Y-%m-%d") if inv.date else "-",
                "تاريخ الاستحقاق": inv.due_date.strftime("%Y-%m-%d") if inv.due_date else "-",
                "أيام التأخير": inv_info['days_overdue'],
                "المبلغ": f"{inv.net_amount:,.2f} ج.م"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        total_overdue = sum(inv_info['invoice'].net_amount for inv_info in alerts['overdue_invoices'])
        st.error(f" إجمالي المبالغ المتأخرة: {total_overdue:,.2f} ج.م")
    else:
        st.success("✅ لا توجد فواتير متأخرة.")

with tab3:
    st.subheader("عملاء تجاوزوا حد الائتمان")
    
    if alerts['credit_warnings']:
        data = []
        for warning in alerts['credit_warnings']:
            customer = warning['customer']
            data.append({
                "العميل": customer.name,
                "الرصيد المستحق": f"{warning['balance']:,.2f} ج.م",
                "حد الائتمان": f"{warning['credit_limit']:,.2f} ج.م",
                "المبلغ المتجاوز": f"{warning['excess']:,.2f} ج.م"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.error(f"⚠️ يوجد {len(alerts['credit_warnings'])} عميل تجاوز حد الائتمان!")
    else:
        st.success("✅ جميع العملاء ضمن حدود الائتمان.")