import streamlit as st
import database as db
import pandas as pd
from datetime import datetime

def show():
    st.title("🛒 الفواتير")
    
    # Search & Filter
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("🔍 بحث", placeholder="رقم الفاتورة أو اسم العميل")
    with col2:
        inv_type = st.selectbox("النوع", ["الكل", "sales", "purchase", "sales_return", "purchase_return"])
    with col3:
        st.write("")  # spacer
    
    # Build query
    query = """
        SELECT i.id, i.invoice_number, i.date, i.type, COALESCE(p.name,'') as party, 
               i.total, i.paid_amount, i.status
        FROM invoices i LEFT JOIN parties p ON i.party_id=p.id
    """
    params = []
    conditions = []
    
    if search:
        conditions.append("(i.invoice_number ILIKE %s OR p.name ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    if inv_type != "الكل":
        conditions.append("i.type=%s")
        params.append(inv_type)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY i.date DESC LIMIT 100"
    
    try:
        cols, rows = db.execute_query(query, tuple(params), fetch=True)
        if rows:
            df = pd.DataFrame(rows, columns=cols)
            
            # Display table
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Actions
            st.markdown("### إجراءات")
            selected_id = st.selectbox("اختر فاتورة", [r[0] for r in rows], 
                                       format_func=lambda x: f"#{x} - {[r[1] for r in rows if r[0]==x][0]}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👁️ عرض التفاصيل"):
                    show_details(selected_id)
            with col2:
                if st.button("🗑️ حذف", type="secondary"):
                    delete_invoice(selected_id)
        else:
            st.info("لا توجد فواتير")
    except Exception as e:
        st.error(f"خطأ: {e}")
    
    # New invoice button
    st.markdown("---")
    if st.button("➕ فاتورة جديدة"):
        st.session_state.show_new_invoice = True
    
    if st.session_state.get("show_new_invoice"):
        new_invoice_form()

def show_details(invoice_id):
    try:
        # Header
        cols, rows = db.execute_query(
            "SELECT i.invoice_number, i.date, i.type, COALESCE(p.name,''), i.total, i.paid_amount, i.status, i.notes "
            "FROM invoices i LEFT JOIN parties p ON i.party_id=p.id WHERE i.id=%s",
            (invoice_id,), fetch=True
        )
        if rows:
            r = rows[0]
            st.markdown(f"### الفاتورة: {r[0]}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**التاريخ:** {r[1]}")
                st.write(f"**النوع:** {r[2]}")
            with col2:
                st.write(f"**العميل:** {r[3]}")
                st.write(f"**الحالة:** {r[6]}")
            with col3:
                st.write(f"**الإجمالي:** {r[4]:.2f}")
                st.write(f"**المدفوع:** {r[5]:.2f}")
            
            # Lines
            st.markdown("#### الأصناف")
            cols2, rows2 = db.execute_query(
                "SELECT i.name, il.quantity, il.price, il.total "
                "FROM invoice_lines il JOIN items i ON il.item_id=i.id WHERE il.invoice_id=%s",
                (invoice_id,), fetch=True
            )
            if rows2:
                df = pd.DataFrame(rows2, columns=["الصنف", "الكمية", "السعر", "الإجمالي"])
                st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"خطأ: {e}")

def delete_invoice(invoice_id):
    st.warning(f"⚠️ سيتم حذف الفاتورة #{invoice_id} وكل تفاصيلها!")
    if st.button("تأكيد الحذف", type="primary"):
        try:
            # Delete in correct order
            db.execute_query("DELETE FROM invoice_lines WHERE invoice_id=%s", (invoice_id,))
            db.execute_query("DELETE FROM invoice_payments WHERE invoice_id=%s", (invoice_id,))
            db.execute_query("DELETE FROM payments WHERE invoice_id=%s", (invoice_id,))
            db.execute_query("DELETE FROM inventory_movements WHERE reference_id=%s AND reference_type='invoice'", (invoice_id,))
            db.execute_query("DELETE FROM invoices WHERE id=%s", (invoice_id,))
            st.success("✅ تم حذف الفاتورة بنجاح")
            st.rerun()
        except Exception as e:
            st.error(f"خطأ: {e}")

def new_invoice_form():
    st.markdown("### ➕ فاتورة جديدة")
    
    with st.form("new_invoice"):
        col1, col2 = st.columns(2)
        with col1:
            # Get parties
            _, parties = db.execute_query("SELECT id, name FROM parties WHERE is_active=TRUE ORDER BY name", fetch=True)
            party_options = {p[1]: p[0] for p in parties} if parties else {}
            party = st.selectbox("العميل/المورد", list(party_options.keys()) if party_options else ["لا يوجد"])
            
            inv_type = st.selectbox("النوع", ["sales", "purchase"])
            inv_date = st.date_input("التاريخ", datetime.now())
        
        with col2:
            # Get items
            _, items = db.execute_query("SELECT id, name FROM items WHERE is_active=TRUE ORDER BY name", fetch=True)
            item_options = {i[1]: i[0] for i in items} if items else {}
            
            status = st.selectbox("الحالة", ["draft", "confirmed", "paid"])
            notes = st.text_area("ملاحظات")
        
        # Invoice lines
        st.markdown("#### الأصناف")
        num_lines = st.number_input("عدد الأصناف", 1, 20, 1)
        lines = []
        
        for i in range(num_lines):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                item_name = st.selectbox(f"الصنف {i+1}", list(item_options.keys()) if item_options else [], key=f"item_{i}")
            with col2:
                qty = st.number_input(f"الكمية", 0.0, 999999.0, 1.0, key=f"qty_{i}")
            with col3:
                price = st.number_input(f"السعر", 0.0, 999999.0, 0.0, key=f"price_{i}")
            
            if item_name and item_name in item_options:
                lines.append({
                    "item_id": item_options[item_name],
                    "quantity": qty,
                    "price": price,
                    "total": qty * price
                })
        
        total = sum(l["total"] for l in lines)
        st.markdown(f"**الإجمالي: {total:,.2f}**")
        
        submitted = st.form_submit_button("💾 حفظ الفاتورة")
        
        if submitted:
            if not party_options:
                st.error("❌ لا يوجد عملاء. أضف عميلاً أولاً.")
            elif not lines:
                st.error("❌ أضف صنفاً واحداً على الأقل")
            else:
                try:
                    # Generate invoice number
                    inv_num = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    party_id = party_options.get(party)
                    
                    # Insert invoice
                    _, result = db.execute_query(
                        "INSERT INTO invoices (invoice_number, date, party_id, type, total, paid_amount, status, currency_id, notes) "
                        "VALUES (%s, %s, %s, %s, %s, 0, %s, 1, %s) RETURNING id",
                        (inv_num, inv_date, party_id, inv_type, total, status, notes), fetch=True
                    )
                    invoice_id = result[0][0]
                    
                    # Insert lines
                    for line in lines:
                        db.execute_query(
                            "INSERT INTO invoice_lines (invoice_id, item_id, quantity, price, total, discount) "
                            "VALUES (%s, %s, %s, %s, %s, 0)",
                            (invoice_id, line["item_id"], line["quantity"], line["price"], line["total"])
                        )
                    
                    st.success(f"✅ تم حفظ الفاتورة: {inv_num}")
                    st.session_state.show_new_invoice = False
                    st.rerun()
                except Exception as e:
<<<<<<< HEAD
                    st.error(f"خطأ: {e}")

=======
                    st.error(f"خطأ: {e}")

>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
