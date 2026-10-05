
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/3_👥_العملاء_والموردين.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from services import create_party_with_opening_balance, import_parties_from_file, export_import_template, export_parties_to_excel
from auth_required import require_login, get_current_user_id, get_current_user_name
import tempfile
import os

# ✅ 1. إعدادات الصفحة أولاً
st.set_page_config(page_title="العملاء والموردين", page_icon="👥", layout="wide")

# ✅ 2. التحقق من الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

# ✅ 3. التنقل بـ Enter
from keyboard_nav import enable_enter_navigation, add_enter_hint
enable_enter_navigation()
add_enter_hint()

st.title("👥 إدارة العملاء والموردين")
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

if 'party_name' not in st.session_state:
    st.session_state.party_name = ""
if 'party_phone' not in st.session_state:
    st.session_state.party_phone = ""
if 'party_address' not in st.session_state:
    st.session_state.party_address = ""
if 'party_opening_balance' not in st.session_state:
    st.session_state.party_opening_balance = 0.0

tab1, tab2, tab3 = st.tabs(["➕ إضافة جديد", "📋 القائمة", "📥 استيراد وتصدير"])

with tab1:
    st.subheader("إضافة عميل أو مورد")
    
    party_type = st.radio("النوع:", ["customer (عميل)", "supplier (مورد)"])
    actual_type = "customer" if "customer" in party_type else "supplier"
    type_ar = "عميل" if actual_type == "customer" else "مورد"
    
    name = st.text_input("الاسم", value=st.session_state.party_name, key="input_party_name")
    phone = st.text_input("الهاتف", value=st.session_state.party_phone, key="input_party_phone")
    address = st.text_area("العنوان", value=st.session_state.party_address, key="input_party_address")
    opening_balance = st.number_input("الرصيد الافتتاحي", min_value=0.0, step=100.0, 
                                       value=st.session_state.party_opening_balance, 
                                       key="input_party_balance")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 حفظ", type="primary"):
            if not name:
                st.error("يرجى إدخال الاسم")
            else:
                try:
                    create_party_with_opening_balance(
                        name, actual_type, opening_balance, phone, address,
                        created_by=current_user_id
                    )
                    st.success(f"✅ تم إضافة {type_ar} '{name}' بنجاح!")
                    
                    st.session_state.party_name = ""
                    st.session_state.party_phone = ""
                    st.session_state.party_address = ""
                    st.session_state.party_opening_balance = 0.0
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: {e}")
    
    with col2:
        if st.button("🧹 مسح"):
            st.session_state.party_name = ""
            st.session_state.party_phone = ""
            st.session_state.party_address = ""
            st.session_state.party_opening_balance = 0.0
            st.rerun()
    
    with col3:
        if st.button("❌ إلغاء"):
            st.session_state.party_name = ""
            st.session_state.party_phone = ""
            st.session_state.party_address = ""
            st.session_state.party_opening_balance = 0.0
            st.rerun()

with tab2:
    st.subheader("قائمة العملاء والموردين")
    parties = db.query(models.Party).all()
    
    if parties:
        data = []
        for p in parties:
            data.append({
                "ID": p.id,
                "الاسم": p.name,
                "النوع": "عميل" if p.type == 'customer' else "مورد",
                "الهاتف": p.phone or "-",
                "العنوان": p.address or "-"
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("⚙️ تعديل/حذف")
        
        party_ids = [p.id for p in parties]
        
        selected_party_id = st.selectbox(
            "اختر عميل/مورد:",
            options=party_ids,
            format_func=lambda x: next((f"{p.name}" for p in parties if p.id == x), x)
        )
        
        if selected_party_id:
            selected_party = db.query(models.Party).filter(models.Party.id == selected_party_id).first()
            
            invoices = db.query(models.Invoice).filter(models.Invoice.party_id == selected_party_id).all()
            payments = db.query(models.Payment).filter(models.Payment.party_id == selected_party_id).all()
            is_used = len(invoices) > 0 or len(payments) > 0
            
            if is_used:
                st.warning(f"⚠️ مستخدم في فواتير. لا يمكن حذفه.")
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**التعديل:**")
                    new_name = st.text_input("الاسم الجديد:", value=selected_party.name, key=f"edit_name_{selected_party_id}")
                    
                    if st.button("حفظ التعديلات", type="primary"):
                        selected_party.name = new_name
                        account = db.query(models.Account).filter(models.Account.id == selected_party.account_id).first()
                        if account:
                            account.name = new_name
                        db.commit()
                        st.success("✅ تم التحديث!")
                        st.rerun()
                
                with col2:
                    st.markdown("**الحذف:**")
                    if st.button("🗑️ حذف", type="secondary"):
                        if st.checkbox("تأكيد؟"):
                            account = db.query(models.Account).filter(models.Account.id == selected_party.account_id).first()
                            if account: db.delete(account)
                            db.delete(selected_party)
                            db.commit()
                            st.success("✅ تم الحذف!")
                            st.rerun()
    else:
        st.info("لا يوجد عملاء أو موردين.")

with tab3:
    st.subheader("📤 تصدير العملاء/الموردين")
    
    export_type = st.radio("نوع التصدير:", ["customer (عملاء)", "supplier (موردين)"], horizontal=True)
    actual_export_type = "customer" if "customer" in export_type else "supplier"
    
    if st.button(f"📤 تصدير إلى Excel", type="primary"):
        try:
            output_path, count = export_parties_to_excel(actual_export_type)
            st.success(f"✅ تم التصدير!")
            with open(output_path, "rb") as file:
                st.download_button(label="️ تحميل", data=file, file_name=output_path)
        except Exception as e:
            st.error(f"خطأ: {e}")
    
    st.markdown("---")
    st.subheader("📥 استيراد")
    
    import_type = st.radio("نوع الاستيراد:", ["customer (عملاء)", "supplier (موردين)"], key="import_type_radio")
    actual_import_type = "customer" if "customer" in import_type else "supplier"
    
    uploaded_file = st.file_uploader("اختر ملف:", type=['xlsx', 'csv'], key=f"upload_{actual_import_type}")
    
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        if st.button(" استيراد", type="primary"):
            try:
                count, errors = import_parties_from_file(tmp_path, actual_import_type, created_by=current_user_id)
                st.success(f"✅ تم استيراد {count}!")
                st.rerun()
            except Exception as e:
                st.error(f"خطأ: {e}")
            finally:
                os.unlink(tmp_path)

db.close()