import streamlit as st
import database as db
import pandas as pd

def show():
    st.title("👥 العملاء والموردين")
    
    search = st.text_input("🔍 بحث", placeholder="الاسم")
    
    query = "SELECT id, name, type, phone, credit_limit, opening_balance, is_active FROM parties WHERE is_active=TRUE"
    params = []
    if search:
        query += " AND name ILIKE %s"
        params.append(f"%{search}%")
    query += " ORDER BY name LIMIT 200"
    
    try:
        cols, rows = db.execute_query(query, tuple(params), fetch=True)
        if rows:
            df = pd.DataFrame(rows, columns=cols)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.markdown("### إجراءات")
            selected_id = st.selectbox("اختر", [r[0] for r in rows],
                                       format_func=lambda x: f"#{x} - {[r[1] for r in rows if r[0]==x][0]}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✏️ تعديل"):
                    st.session_state.edit_party = selected_id
                    st.rerun()
            with col2:
                if st.button("🗑️ حذف"):
                    delete_party(selected_id)
            with col3:
                if st.button("📋 كشف حساب"):
                    show_statement(selected_id)
    except Exception as e:
        st.error(f"خطأ: {e}")
    
    st.markdown("---")
    if st.button("➕ عميل/مورد جديد"):
        st.session_state.show_new_party = True
    
    if st.session_state.get("show_new_party"):
        party_form()
    if st.session_state.get("edit_party"):
        party_form(st.session_state.edit_party)

def party_form(edit_id=None):
    title = "✏️ تعديل" if edit_id else "➕ جديد"
    st.markdown(f"### {title}")
    
    existing = {}
    if edit_id:
        try:
            cols, rows = db.execute_query(
                "SELECT name, type, phone, credit_limit, opening_balance FROM parties WHERE id=%s",
                (edit_id,), fetch=True
            )
            if rows:
                existing = dict(zip(cols, rows[0]))
        except:
            pass
    
    with st.form("party_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("الاسم *", value=existing.get("name", ""))
            ptype = st.selectbox("النوع", ["customer", "supplier", "both"],
                                 index=["customer","supplier","both"].index(existing.get("type","customer")) if existing.get("type") in ["customer","supplier","both"] else 0)
        
        with col2:
            phone = st.text_input("الهاتف", value="")
            credit_limit = st.number_input("حد الائتمان", 0.0, 999999.0, float(existing.get("credit_limit") or 0))
            opening_balance = st.number_input("الرصيد الافتتاحي", -999999.0, 999999.0, float(existing.get("opening_balance") or 0))
        
        submitted = st.form_submit_button("💾 حفظ")
        
        if submitted:
            if not name:
                st.error("❌ الاسم مطلوب")
            else:
                try:
                    if edit_id:
                        db.execute_query(
                            "UPDATE parties SET name=%s, type=%s, credit_limit=%s, opening_balance=%s WHERE id=%s",
                            (name, ptype, credit_limit, opening_balance, edit_id)
                        )
                        st.success("✅ تم التحديث")
                    else:
                        db.execute_query(
                            "INSERT INTO parties (name, type, phone, credit_limit, opening_balance, is_active) "
                            "VALUES (%s, %s, %s, %s, %s, TRUE)",
                            (name, ptype, phone, credit_limit, opening_balance)
                        )
                        st.success("✅ تم الإضافة")
                    
                    st.session_state.show_new_party = False
                    st.session_state.edit_party = None
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: {e}")

def delete_party(party_id):
    st.warning(f"⚠️ سيتم تعطيل العميل #{party_id}!")
    if st.button("تأكيد", type="primary"):
        try:
            db.execute_query("UPDATE parties SET is_active=FALSE WHERE id=%s", (party_id,))
            st.success("✅ تم التعطيل")
            st.rerun()
        except Exception as e:
            st.error(f"خطأ: {e}")

def show_statement(party_id):
    st.markdown("### 📋 كشف الحساب")
    try:
        _, party = db.execute_query("SELECT name FROM parties WHERE id=%s", (party_id,), fetch=True)
        st.markdown(f"**العميل:** {party[0][0] if party else ''}")
        
        # الفواتير
        _, inv_rows = db.execute_query(
            "SELECT date, invoice_number, total, paid_amount FROM invoices WHERE party_id=%s ORDER BY date DESC LIMIT 50",
            (party_id,), fetch=True
        )
        
        # المدفوعات
        _, pay_rows = db.execute_query(
            "SELECT date, reference_number, amount FROM payments WHERE party_id=%s ORDER BY date DESC LIMIT 50",
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
