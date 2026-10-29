import streamlit as st
import database as db
import pandas as pd

def show():
    st.title("📦 الأصناف")
    
    # Search
    search = st.text_input("🔍 بحث", placeholder="اسم الصنف أو الباركود")
    
    query = "SELECT id, name, barcode, cost_price, sell_price, opening_quantity, is_active FROM items WHERE is_active=TRUE"
    params = []
    if search:
        query += " AND (name ILIKE %s OR barcode ILIKE %s)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY name LIMIT 200"
    
    try:
        cols, rows = db.execute_query(query, tuple(params), fetch=True)
        if rows:
            df = pd.DataFrame(rows, columns=cols)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Edit/Delete
            st.markdown("### إجراءات")
            selected_id = st.selectbox("اختر صنف", [r[0] for r in rows],
                                       format_func=lambda x: f"#{x} - {[r[1] for r in rows if r[0]==x][0]}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✏️ تعديل"):
                    st.session_state.edit_item = selected_id
                    st.rerun()
            with col2:
                if st.button("🗑️ حذف"):
                    delete_item(selected_id)
    except Exception as e:
        st.error(f"خطأ: {e}")
    
    # New item
    st.markdown("---")
    if st.button("➕ صنف جديد"):
        st.session_state.show_new_item = True
    
    if st.session_state.get("show_new_item"):
        item_form()
    
    if st.session_state.get("edit_item"):
        item_form(st.session_state.edit_item)

def item_form(edit_id=None):
    title = "✏️ تعديل صنف" if edit_id else "➕ صنف جديد"
    st.markdown(f"### {title}")
    
    # Load existing data
    existing = {}
    if edit_id:
        try:
            cols, rows = db.execute_query(
                "SELECT name, barcode, cost_price, sell_price, opening_quantity FROM items WHERE id=%s",
                (edit_id,), fetch=True
            )
            if rows:
                existing = dict(zip(cols, rows[0]))
        except:
            pass
    
    with st.form("item_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("اسم الصنف *", value=existing.get("name", ""))
            barcode = st.text_input("الباركود", value=existing.get("barcode", ""))
            cost_price = st.number_input("سعر التكلفة", 0.0, 999999.0, float(existing.get("cost_price") or 0.0))
        
        with col2:
            sell_price = st.number_input("سعر البيع", 0.0, 999999.0, float(existing.get("sell_price") or 0.0))
            opening_qty = st.number_input("الكمية الافتتاحية", 0.0, 999999.0, float(existing.get("opening_quantity") or 0.0))
        
        submitted = st.form_submit_button("💾 حفظ")
        
        if submitted:
            if not name:
                st.error("❌ اسم الصنف مطلوب")
            else:
                try:
                    if edit_id:
                        db.execute_query(
                            "UPDATE items SET name=%s, barcode=%s, cost_price=%s, sell_price=%s, opening_quantity=%s WHERE id=%s",
                            (name, barcode or None, cost_price, sell_price, opening_qty, edit_id)
                        )
                        st.success("✅ تم التحديث")
                    else:
                        db.execute_query(
                            "INSERT INTO items (name, barcode, cost_price, sell_price, opening_quantity, is_active, is_kit) "
                            "VALUES (%s, %s, %s, %s, %s, TRUE, FALSE)",
                            (name, barcode or None, cost_price, sell_price, opening_qty)
                        )
                        st.success("✅ تم إضافة الصنف")
                    
                    st.session_state.show_new_item = False
                    st.session_state.edit_item = None
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: {e}")

def delete_item(item_id):
    st.warning(f"⚠️ سيتم حذف الصنف #{item_id}!")
    if st.button("تأكيد الحذف", type="primary"):
        try:
            db.execute_query("UPDATE items SET is_active=FALSE WHERE id=%s", (item_id,))
            st.success("✅ تم تعطيل الصنف (لمسحه بالكامل يجب عدم وجود فواتير مرتبطة)")
            st.rerun()
        except Exception as e:
<<<<<<< HEAD
            st.error(f"خطأ: {e}")

=======
            st.error(f"خطأ: {e}")

>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
