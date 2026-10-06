
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/7_💱_العملات.py
import streamlit as st
import pandas as pd
from database import SessionLocal
import models
from auth_required import require_login
from form_manager import clear_form, show_clear_hint
current_user = require_login()
st.set_page_config(page_title="إدارة العملات", page_icon="💱", layout="wide")
st.title("💱 إدارة العملات")

show_clear_hint()  # 💡 الحقول ستُفرَّغ تلقائياً بعد كل عملية
from keyboard_nav import enable_enter_navigation, add_enter_hint

# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لكل مفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "cur_"


# تفعيل التنقل بـ Enter
enable_enter_navigation()
add_enter_hint()
db = SessionLocal()

tab1, tab2 = st.tabs(["➕ إضافة عملة جديدة", " قائمة العملات"])

with tab1:
    st.subheader("إضافة عملة جديدة")
    
    code = st.text_input("كود العملة (مثال: USD, EUR, SAR)", placeholder="USD")
    name = st.text_input("اسم العملة (مثال: دولار أمريكي)", placeholder="دولار أمريكي")
    symbol = st.text_input("رمز العملة (مثال: $, €, ر.س)", placeholder="$")
    exchange_rate = st.number_input("سعر الصرف بالنسبة للجنيه المصري", min_value=0.01, step=0.1, value=1.0)
    is_default = st.checkbox("اجعلها العملة الافتراضية")
    
    if st.button("حفظ العملة", type="primary"):
        if not code or not name or not symbol:
            st.error("يرجى ملء جميع الحقول")
        else:
            try:
                existing = db.query(models.Currency).filter(models.Currency.code == code.upper()).first()
                if existing:
                    st.error("هذه العملة موجودة مسبقاً!")
                else:
                    if is_default:
                        db.query(models.Currency).update({models.Currency.is_default: False})
                    
                    new_currency = models.Currency(
                        code=code.upper(),
                        name=name,
                        symbol=symbol,
                        exchange_rate=exchange_rate,
                        is_default=is_default
                    )
                    db.add(new_currency)
                    db.commit()
                    st.success(f"تم إضافة العملة '{name}' بنجاح!")
                    clear_form(PFX)  # ✅ تفريغ الحقول
                    st.rerun()
            except Exception as e:
                st.error(f"خطأ: {e}")

with tab2:
    st.subheader("قائمة العملات")
    currencies = db.query(models.Currency).all()
    
    if currencies:
        data = []
        for curr in currencies:
            data.append({
                "الكود": curr.code,
                "الاسم": curr.name,
                "الرمز": curr.symbol,
                "سعر الصرف": curr.exchange_rate,
                "افتراضية": "نعم" if curr.is_default else "لا"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("⚙️ تعديل/حذف عملة")
        
        currency_ids = [curr.id for curr in currencies]
        currency_codes = [curr.code for curr in currencies]
        
        selected_currency_id = st.selectbox(
            "اختر عملة:",
            options=currency_ids,
            format_func=lambda x: next((curr.code for curr in currencies if curr.id == x), x)
        )
        
        if selected_currency_id:
            selected_currency = db.query(models.Currency).filter(models.Currency.id == selected_currency_id).first()
            
            col1, col2 = st.columns(2)
            
            with col1:
                new_exchange_rate = st.number_input("سعر الصرف الجديد:", value=selected_currency.exchange_rate, step=0.1)
                new_is_default = st.checkbox("اجعلها افتراضية", value=selected_currency.is_default)
                
                if st.button("حفظ التعديلات", type="primary"):
                    if new_is_default:
                        db.query(models.Currency).update({models.Currency.is_default: False})
                    
                    selected_currency.exchange_rate = new_exchange_rate
                    selected_currency.is_default = new_is_default
                    db.commit()
                    st.success("تم تحديث العملة بنجاح!")
                    clear_form(PFX)  # ✅ تفريغ الحقول
                    st.rerun()
            
            with col2:
                if st.button("🗑️ حذف العملة", type="secondary"):
                    if st.checkbox("تأكيد الحذف؟"):
                        db.delete(selected_currency)
                        db.commit()
                        st.success("تم حذف العملة بنجاح!")
                        clear_form(PFX)  # ✅ تفريغ الحقول
                        st.rerun()
    else:
        st.info("لا توجد عملات.")

db.close()