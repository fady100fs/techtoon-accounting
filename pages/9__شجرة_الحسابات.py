
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/9_📚_شجرة_الحسابات.py
import streamlit as st
import pandas as pd
from sqlalchemy import func
from database import SessionLocal
import models
from models import AccountType
from auth_required import require_login
current_user = require_login()
st.set_page_config(page_title="شجرة الحسابات", page_icon="📚", layout="wide")
st.title("📚 إدارة شجرة الحسابات")
from keyboard_nav import enable_enter_navigation, add_enter_hint

# تفعيل التنقل بـ Enter
enable_enter_navigation()
add_enter_hint()
db = SessionLocal()

tab1, tab2 = st.tabs(["➕ إضافة حساب جديد", " عرض شجرة الحسابات"])

with tab1:
    st.subheader("إضافة حساب جديد")
    
    account_type = st.selectbox(
        "نوع الحساب:",
        options=[acc_type.value for acc_type in AccountType],
        format_func=lambda x: x
    )
    
    parent_accounts = db.query(models.Account).filter(
        models.Account.type == AccountType(account_type),
        models.Account.parent_id.isnot(None)
    ).all()
    
    parent_options = {"بدون (حساب رئيسي)": None}
    for acc in parent_accounts:
        parent_options[f"{acc.code} - {acc.name}"] = acc.id
    
    selected_parent = st.selectbox(
        "الحساب الأب:",
        options=list(parent_options.values()),
        format_func=lambda x: next((k for k, v in parent_options.items() if v == x), "بدون")
    )
    
    code = st.text_input("كود الحساب:", placeholder="مثال: 1103")
    name = st.text_input("اسم الحساب:", placeholder="مثال: صندوق فرعي")
    
    if st.button("حفظ الحساب", type="primary"):
        if not code or not name:
            st.error("يرجى ملء كود واسم الحساب")
        else:
            try:
                existing = db.query(models.Account).filter(models.Account.code == code).first()
                if existing:
                    st.error("هذا الكود موجود مسبقاً!")
                else:
                    new_account = models.Account(
                        code=code,
                        name=name,
                        type=AccountType(account_type),
                        parent_id=selected_parent
                    )
                    db.add(new_account)
                    db.commit()
                    st.success(f"تم إضافة الحساب '{name}' بنجاح!")
                    st.rerun()
            except Exception as e:
                st.error(f"خطأ: {e}")

with tab2:
    st.subheader("شجرة الحسابات")
    
    all_accounts = db.query(models.Account).order_by(models.Account.code).all()
    
    if all_accounts:
        main_accounts = [acc for acc in all_accounts if acc.parent_id is None]
        
        for main_acc in main_accounts:
            with st.expander(f"{main_acc.code} - {main_acc.name} ({main_acc.type.value})", expanded=False):
                sub_accounts = [acc for acc in all_accounts if acc.parent_id == main_acc.id]
                
                if sub_accounts:
                    data = []
                    for sub_acc in sub_accounts:
                        debit_total = db.query(models.JournalLine).filter(
                            models.JournalLine.account_id == sub_acc.id
                        ).with_entities(func.sum(models.JournalLine.debit)).scalar() or 0
                        
                        credit_total = db.query(models.JournalLine).filter(
                            models.JournalLine.account_id == sub_acc.id
                        ).with_entities(func.sum(models.JournalLine.credit)).scalar() or 0
                        
                        balance = debit_total - credit_total
                        
                        data.append({
                            "الكود": sub_acc.code,
                            "الاسم": sub_acc.name,
                            "مدين": f"{debit_total:,.2f}",
                            "دائن": f"{credit_total:,.2f}",
                            "الرصيد": f"{balance:,.2f}"
                        })
                    
                    if data:
                        df = pd.DataFrame(data)
                        st.dataframe(df, use_container_width=True)
                else:
                    st.info("لا توجد حسابات فرعية")
        
        st.markdown("---")
        st.subheader("️ تعديل/حذف حساب")
        
        account_ids = [acc.id for acc in all_accounts]
        
        selected_account_id = st.selectbox(
            "اختر حساباً:",
            options=account_ids,
            format_func=lambda x: next((f"{acc.code} - {acc.name}" for acc in all_accounts if acc.id == x), x)
        )
        
        if selected_account_id:
            selected_account = db.query(models.Account).filter(models.Account.id == selected_account_id).first()
            
            # التحقق من وجود الحساب في قيود يومية
            journal_lines = db.query(models.JournalLine).filter(models.JournalLine.account_id == selected_account_id).all()
            # التحقق من وجود الحساب كحساب مرتبط بعميل/مورد
            linked_parties = db.query(models.Party).filter(models.Party.account_id == selected_account_id).all()
            
            is_used = len(journal_lines) > 0 or len(linked_parties) > 0
            
            if is_used:
                st.warning(f"⚠️ هذا الحساب مستخدم في {len(journal_lines)} قيد يومية و {len(linked_parties)} عميل/مورد. لا يمكن حذفه أو تعديله.")
                st.info("يمكنك فقط عرض تفاصيله:")
                st.write(f"**الكود:** {selected_account.code}")
                st.write(f"**الاسم:** {selected_account.name}")
                st.write(f"**النوع:** {selected_account.type.value}")
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**التعديل:**")
                    new_name = st.text_input("الاسم الجديد:", value=selected_account.name, key=f"edit_acc_name_{selected_account_id}")
                    new_code = st.text_input("الكود الجديد:", value=selected_account.code, key=f"edit_acc_code_{selected_account_id}")
                    
                    if st.button("حفظ التعديلات", type="primary"):
                        selected_account.name = new_name
                        selected_account.code = new_code
                        db.commit()
                        st.success("تم تحديث الحساب بنجاح!")
                        st.rerun()
                
                with col2:
                    st.markdown("**الحذف:**")
                    st.warning("⚠️ سيتم حذف الحساب نهائياً!")
                    if st.button("🗑️ حذف الحساب", type="secondary"):
                        if st.checkbox("تأكيد الحذف؟"):
                            # حذف الحسابات الفرعية
                            db.query(models.Account).filter(
                                models.Account.parent_id == selected_account_id
                            ).delete()
                            
                            # حذف الحساب
                            db.delete(selected_account)
                            db.commit()
                            st.success("تم حذف الحساب بنجاح!")
                            st.rerun()
    else:
        st.info("لا توجد حسابات.")

db.close()