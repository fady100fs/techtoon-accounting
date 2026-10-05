# pages/4_🧾_الفواتير.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from services import create_invoice, create_payment
from auth_required import require_login, get_current_user_id, get_current_user_name

# ✅ 1. إعدادات الصفحة أولاً
st.set_page_config(page_title="الفواتير", page_icon="🧾", layout="wide")

# ✅ 2. التحقق من الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

# ✅ 3. التنقل بـ Enter
from keyboard_nav import enable_enter_navigation, add_enter_hint
enable_enter_navigation()
add_enter_hint()

st.title("🧾 إنشاء الفواتير")
st.info(f"👤 المستخدم: **{current_user_name}**")

db = SessionLocal()

# ==========================================
# التحقق من وجود بيانات أساسية
# ==========================================
parties = db.query(models.Party).all()
items = db.query(models.Item).all()

if not parties:
    st.error("⚠️ لا يوجد عملاء أو موردين! يرجى إضافتهم أولاً من صفحة 'العملاء والموردين'")
    st.stop()

if not items:
    st.error("⚠️ لا توجد أصناف! يرجى إضافتها أولاً من صفحة 'الأصناف'")
    st.stop()

# ==========================================
# نوع الفاتورة
# ==========================================
invoice_type = st.radio("نوع الفاتورة:", ["sale (بيع)", "purchase (شراء)"])
actual_type = "sale" if "sale" in invoice_type else "purchase"
type_ar = "بيع" if actual_type == "sale" else "شراء"

# ==========================================
# اختيار العميل/المورد
# ==========================================
if actual_type == "sale":
    customers = db.query(models.Party).filter(models.Party.type == 'customer').all()
    if not customers:
        st.warning("⚠️ لا يوجد عملاء! يرجى إضافة عملاء أولاً")
        st.stop()
    party_dict = {p.id: p.name for p in customers}
    label = "اختر العميل:"
else:
    suppliers = db.query(models.Party).filter(models.Party.type == 'supplier').all()
    if not suppliers:
        st.warning("⚠️ لا يوجد موردين! يرجى إضافة موردين أولاً")
        st.stop()
    party_dict = {p.id: p.name for p in suppliers}
    label = "اختر المورد:"

selected_party_id = st.selectbox(
    label, 
    options=list(party_dict.keys()),
    format_func=lambda x: party_dict[x]
)

# ==========================================
# الأصناف
# ==========================================
item_dict = {item.id: item for item in items}
item_names = [item.name for item in items]

if 'invoice_items' not in st.session_state:
    st.session_state.invoice_items = []

st.markdown("---")
st.subheader("أصناف الفاتورة")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    sel_item_name = st.selectbox("الصنف:", item_names, key="sel_item")

with col2:
    qty = st.number_input("الكمية:", min_value=1, step=1, key="qty")

with col3:
    # ✅ البحث عن الصنف المحدد
    current_item = next((item for item in items if item.name == sel_item_name), None)
    
    # ✅ التحقق من وجود الصنف قبل الوصول إلى خصائصه
    if current_item:
        if actual_type == "sale":
            default_price = current_item.sell_price if current_item.sell_price else 0.0
        else:
            default_price = current_item.cost_price if current_item.cost_price else 0.0
    else:
        default_price = 0.0
    
    price = st.number_input("السعر:", value=default_price, step=0.1, key="price")

if st.button("➕ إضافة للفاتورة"):
    if sel_item_name and qty > 0 and price > 0:
        st.session_state.invoice_items.append({
            'item_name': sel_item_name,
            'quantity': qty,
            'price': price
        })
        st.success(f"✅ تمت إضافة {sel_item_name}")
        st.rerun()
    else:
        st.error("يرجى اختيار صنف وإدخال كمية وسعر صحيحين")

# ==========================================
# عرض الفاتورة
# ==========================================
if st.session_state.invoice_items:
    st.markdown("---")
    st.subheader("تفاصيل الفاتورة")
    
    subtotal = sum(item['quantity'] * item['price'] for item in st.session_state.invoice_items)
    
    df = pd.DataFrame(st.session_state.invoice_items)
    df['الإجمالي'] = df['quantity'] * df['price']
    st.dataframe(df, use_container_width=True)
    
    st.metric("الإجمالي", f"{subtotal:,.2f} ج.م")
    
    # الخصم والضريبة
    col_disc, col_tax = st.columns(2)
    with col_disc:
        discount_pct = st.number_input("خصم %:", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    with col_tax:
        tax_pct = st.number_input("ضريبة %:", min_value=0.0, max_value=100.0, value=14.0, step=1.0)
    
    discount_amount = subtotal * (discount_pct / 100)
    amount_after_discount = subtotal - discount_amount
    tax_amount = amount_after_discount * (tax_pct / 100)
    net_amount = amount_after_discount + tax_amount
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("المجموع", f"{subtotal:,.2f}")
    with col2:
        st.metric("الخصم", f"{discount_amount:,.2f}")
    with col3:
        st.metric("الضريبة", f"{tax_amount:,.2f}")
    with col4:
        st.metric("الصافي", f"{net_amount:,.2f}")
    
    st.markdown("---")
    
    if st.button(" حفظ الفاتورة", type="primary"):
        if not selected_party_id:
            st.error("يرجى اختيار عميل/مورد")
        elif not st.session_state.invoice_items:
            st.error("يرجى إضافة أصناف للفاتورة")
        else:
            try:
                inv_num = f"INV-{db.query(models.Invoice).count() + 1:06d}"
                
                invoice = create_invoice(
                    party_id=selected_party_id,
                    invoice_type=actual_type,
                    items=st.session_state.invoice_items,
                    invoice_number=inv_num,
                    discount_percentage=discount_pct,
                    tax_rate=tax_pct,
                    created_by=current_user_id
                )
                
                invoice.status = 'paid'
                db.commit()
                
                st.success(f"✅ تم حفظ فاتورة {type_ar} رقم {inv_num} بنجاح!")
                st.balloons()
                
                st.session_state.invoice_items = []
                st.rerun()
            except Exception as e:
                st.error(f" خطأ: {e}")
else:
    st.info("🛒 السلة فارغة. أضف أصنافاً لبدء الفاتورة.")

db.close()