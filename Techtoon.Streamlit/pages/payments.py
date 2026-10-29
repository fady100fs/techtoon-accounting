<<<<<<< HEAD
import streamlit as st
=======
﻿import streamlit as st
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
import database as db
import pandas as pd
from datetime import datetime

def show():
    st.title("💰 المدفوعات")
    
<<<<<<< HEAD
    search = st.text_input("🔍 بحث", placeholder="اسم الجهة/الحساب أو المرجع")
    
    query = """
        SELECT p.id, p.date, p.payment_type, COALESCE(pt.name,''), COALESCE(a.name,''), p.amount, p.payment_method, p.reference_number
        FROM payments p 
        LEFT JOIN parties pt ON p.party_id=pt.id
        LEFT JOIN accounts a ON p.account_id=a.id
    """
    params = []
    if search:
        query += " WHERE pt.name ILIKE %s OR a.name ILIKE %s OR p.reference_number ILIKE %s"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
=======
    search = st.text_input("🔍 بحث", placeholder="اسم الجهة أو المرجع")
    
    query = """
        SELECT p.id, p.date, p.payment_type, COALESCE(pt.name,'') as party, p.amount, p.payment_method, p.reference_number
        FROM payments p LEFT JOIN parties pt ON p.party_id=pt.id
    """
    params = []
    if search:
        query += " WHERE pt.name ILIKE %s OR p.reference_number ILIKE %s"
        params.extend([f"%{search}%", f"%{search}%"])
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
    query += " ORDER BY p.date DESC LIMIT 100"
    
    try:
        cols, rows = db.execute_query(query, tuple(params), fetch=True)
        if rows:
<<<<<<< HEAD
            df = pd.DataFrame(rows, columns=["ID", "التاريخ", "النوع", "الجهة", "الحساب", "المبلغ", "الطريقة", "المرجع"])
            df["الجهة/الحساب"] = df["الجهة"].fillna('') + df["الحساب"].fillna('')
            df = df.drop(columns=["الجهة", "الحساب"])
=======
            df = pd.DataFrame(rows, columns=cols)
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.markdown("### إجراءات")
            selected_id = st.selectbox("اختر", [r[0] for r in rows],
<<<<<<< HEAD
                                       format_func=lambda x: f"#{x} - {[r[3] or r[4] for r in rows if r[0]==x][0]} - {[r[5] for r in rows if r[0]==x][0]}")
=======
                                       format_func=lambda x: f"#{x} - {[r[3] for r in rows if r[0]==x][0]} - {[r[4] for r in rows if r[0]==x][0]}")
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
            
            if st.button("🗑️ حذف"):
                delete_payment(selected_id)
    except Exception as e:
        st.error(f"خطأ: {e}")
    
    st.markdown("---")
    if st.button("➕ سند قبض/صرف"):
        st.session_state.show_new_payment = True
    
    if st.session_state.get("show_new_payment"):
        payment_form()

def payment_form():
    st.markdown("### ➕ سند جديد")
    
    with st.form("payment_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            ptype = st.selectbox("النوع", ["receipt", "payment"],
                                 format_func=lambda x: "سند قبض" if x=="receipt" else "سند صرف")
            
<<<<<<< HEAD
            target_type = st.radio("نوع الجهة", ["عميل/مورد", "حساب (مصاريف بيت/إلخ)"])
            
            if target_type == "عميل/مورد":
                _, parties = db.execute_query("SELECT id, name FROM parties WHERE is_active=TRUE ORDER BY name", fetch=True)
                party_options = {p[1]: p[0] for p in parties} if parties else {}
                target_name = st.selectbox("الجهة *", list(party_options.keys()) if party_options else ["لا يوجد"])
                account_id = None
            else:
                _, accounts = db.execute_query("SELECT id, name FROM accounts WHERE is_active=TRUE ORDER BY name", fetch=True)
                account_options = {a[1]: a[0] for a in accounts} if accounts else {}
                target_name = st.selectbox("الحساب *", list(account_options.keys()) if account_options else ["لا يوجد"])
                party_options = {}
                account_id = account_options.get(target_name)
=======
            _, parties = db.execute_query("SELECT id, name FROM parties WHERE is_active=TRUE ORDER BY name", fetch=True)
            party_options = {p[1]: p[0] for p in parties} if parties else {}
            party_name = st.selectbox("الجهة *", list(party_options.keys()) if party_options else ["لا يوجد"])
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
            
            amount = st.number_input("المبلغ *", 0.01, 999999.0, 0.01)
        
        with col2:
            pdate = st.date_input("التاريخ", datetime.now())
            method = st.selectbox("طريقة الدفع", ["نقدي", "بطاقة", "تحويل"])
            reference = st.text_input("المرجع")
        
        notes = st.text_area("ملاحظات")
        
        submitted = st.form_submit_button("💾 حفظ")
        
        if submitted:
<<<<<<< HEAD
            if target_type == "عميل/مورد" and not party_options:
                st.error("❌ لا يوجد عملاء")
            elif target_type == "حساب (مصاريف بيت/إلخ)" and not account_options:
                st.error("❌ لا يوجد حسابات")
=======
            if not party_options:
                st.error("❌ لا يوجد عملاء")
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
            elif amount <= 0:
                st.error("❌ المبلغ غير صحيح")
            else:
                try:
<<<<<<< HEAD
                    party_id = party_options.get(target_name) if target_type == "عميل/مورد" else None
                    account_id = account_id if target_type == "حساب (مصاريف بيت/إلخ)" else None
                    
=======
                    party_id = party_options.get(party_name)
                    
                    # Get cash box
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
                    _, cb = db.execute_query("SELECT id FROM cash_boxes WHERE is_active=TRUE LIMIT 1", fetch=True)
                    cash_box_id = cb[0][0] if cb else 1
                    
                    db.execute_query(
<<<<<<< HEAD
                        "INSERT INTO payments (date, party_id, account_id, amount, payment_type, payment_method, reference_number, notes, currency_id, cash_box_id) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s)",
                        (pdate, party_id, account_id, amount, ptype, method, reference or None, notes or None, cash_box_id)
=======
                        "INSERT INTO payments (date, party_id, amount, payment_type, payment_method, reference_number, notes, currency_id, cash_box_id) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s)",
                        (pdate, party_id, amount, ptype, method, reference or None, notes or None, cash_box_id)
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
                    )
                    st.success("✅ تم حفظ السند")
                    st.session_state.show_new_payment = False
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: {e}")

def delete_payment(payment_id):
    st.warning(f"⚠️ سيتم حذف السند #{payment_id}!")
    if st.button("تأكيد الحذف", type="primary"):
        try:
            db.execute_query("DELETE FROM payments WHERE id=%s", (payment_id,))
            st.success("✅ تم الحذف")
            st.rerun()
        except Exception as e:
<<<<<<< HEAD
            st.error(f"خطأ: {e}")
=======
            st.error(f"خطأ: {e}")

>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
