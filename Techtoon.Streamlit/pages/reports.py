import streamlit as st
import database as db
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

def show():
    st.title("📈 التقارير")
    
    report_type = st.selectbox("نوع التقرير", [
        "تقرير المبيعات",
        "تقرير الجرد",
        "كشف حساب",
        "تقرير المصروفات"
    ])
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("من", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("إلى", datetime.now())
    
    if st.button("📊 توليد التقرير"):
        if report_type == "تقرير المبيعات":
            sales_report(start_date, end_date)
        elif report_type == "تقرير الجرد":
            inventory_report()
        elif report_type == "كشف حساب":
            party_statement()
        elif report_type == "تقرير المصروفات":
            expenses_report(start_date, end_date)

def sales_report(start, end):
    st.markdown("### 📊 تقرير المبيعات")
    
    try:
        _, rows = db.execute_query(
            "SELECT i.invoice_number, i.date, COALESCE(p.name,''), i.total, i.paid_amount, i.status "
            "FROM invoices i LEFT JOIN parties p ON i.party_id=p.id "
            "WHERE i.type=%s AND i.date BETWEEN %s AND %s AND i.status<>%s "
            "ORDER BY i.date",
            ("sales", start, end + timedelta(days=1), "cancelled"), fetch=True
        )
        
        if rows:
            df = pd.DataFrame(rows, columns=["رقم الفاتورة", "التاريخ", "العميل", "الإجمالي", "المدفوع", "الحالة"])
            
            total = df["الإجمالي"].sum()
            paid = df["المدفوع"].sum()
            remaining = total - paid
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("الإجمالي", f"{total:,.2f}")
            with col2:
                st.metric("المحصل", f"{paid:,.2f}")
            with col3:
                st.metric("المتبقي", f"{remaining:,.2f}")
            
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Chart
            df["التاريخ"] = pd.to_datetime(df["التاريخ"]).dt.date
            daily = df.groupby("التاريخ")["الإجمالي"].sum().reset_index()
            fig = px.bar(daily, x="التاريخ", y="الإجمالي", title="المبيعات اليومية")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد مبيعات في هذه الفترة")
    except Exception as e:
        st.error(f"خطأ: {e}")

def inventory_report():
    st.markdown("### 📦 تقرير الجرد")
    
    try:
        _, rows = db.execute_query(
            "SELECT i.name, i.barcode, i.opening_quantity, COALESCE(i.avg_cost_price, i.cost_price, 0), i.sell_price, i.min_stock "
            "FROM items i WHERE i.is_active=TRUE AND i.is_kit IS NOT TRUE ORDER BY i.name",
            fetch=True
        )
        
        if rows:
            df = pd.DataFrame(rows, columns=["الصنف", "الباركود", "الكمية", "التكلفة", "سعر البيع", "الحد الأدنى"])
            df["قيمة المخزون"] = df["الكمية"] * df["التكلفة"]
            
            total_value = df["قيمة المخزون"].sum()
            st.metric("إجمالي قيمة المخزون", f"{total_value:,.2f}")
            
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("لا توجد أصناف")
    except Exception as e:
        st.error(f"خطأ: {e}")

def party_statement():
    st.markdown("### 📋 كشف حساب")
    
    try:
        _, parties = db.execute_query("SELECT id, name FROM parties WHERE is_active=TRUE ORDER BY name", fetch=True)
        if parties:
            party_options = {p[1]: p[0] for p in parties}
            party_name = st.selectbox("اختر الجهة", list(party_options.keys()))
            party_id = party_options[party_name]
            
            _, inv_rows = db.execute_query(
                "SELECT date, invoice_number, total, paid_amount FROM invoices WHERE party_id=%s ORDER BY date",
                (party_id,), fetch=True
            )
            _, pay_rows = db.execute_query(
                "SELECT date, reference_number, amount FROM payments WHERE party_id=%s ORDER BY date",
                (party_id,), fetch=True
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### الفواتير")
                if inv_rows:
                    df = pd.DataFrame(inv_rows, columns=["التاريخ", "رقم الفاتورة", "الإجمالي", "المدفوع"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("لا توجد فواتير")
            
            with col2:
                st.markdown("#### المدفوعات")
                if pay_rows:
                    df = pd.DataFrame(pay_rows, columns=["التاريخ", "المرجع", "المبلغ"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("لا توجد مدفوعات")
    except Exception as e:
        st.error(f"خطأ: {e}")

def expenses_report(start, end):
    st.markdown("### 💸 تقرير المصروفات")
    
    try:
        _, rows = db.execute_query(
            "SELECT e.date, ec.name, e.amount, e.notes FROM expenses e "
            "LEFT JOIN expense_categories ec ON e.category_id=ec.id "
            "WHERE e.date BETWEEN %s AND %s ORDER BY e.date",
            (start, end + timedelta(days=1)), fetch=True
        )
        
        if rows:
            df = pd.DataFrame(rows, columns=["التاريخ", "الفئة", "المبلغ", "ملاحظات"])
            total = df["المبلغ"].sum()
            st.metric("إجمالي المصروفات", f"{total:,.2f}")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("لا توجد مصروفات في هذه الفترة")
    except Exception as e:
        st.error(f"خطأ: {e}")
