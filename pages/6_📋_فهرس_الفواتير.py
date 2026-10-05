
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/6__فهرس_الفواتير.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from models import CashBox
from services import create_payment, get_user_name_by_id
from auth_required import require_login, get_current_user_id, get_current_user_name

# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="فهرس الفواتير", page_icon="📋", layout="wide")
st.title("📋 فهرس الفواتير")

db = SessionLocal()

try:
    search_query = st.text_input("🔍 البحث برقم الفاتورة:", placeholder="أدخل رقم الفاتورة للبحث...")
    
    filter_type = st.radio("تصفية حسب النوع:", ["الكل", "بيع", "شراء"], horizontal=True)
    
    query = db.query(models.Invoice)
    
    if search_query:
        query = query.filter(models.Invoice.invoice_number.contains(search_query))
    
    if filter_type != "الكل":
        actual_type = 'sale' if filter_type == 'بيع' else 'purchase'
        query = query.filter(models.Invoice.type == actual_type)
    
    invoices = query.order_by(models.Invoice.date.desc()).all()
    
    if invoices:
        data = []
        for inv in invoices:
            party = db.query(models.Party).filter(models.Party.id == inv.party_id).first()
            currency = db.query(models.Currency).filter(models.Currency.id == inv.currency_id).first()
            currency_symbol = currency.symbol if currency else "ج.م"
            
            payments = db.query(models.Payment).filter(
                models.Payment.reference_number.contains(inv.invoice_number)
            ).all()
            paid_amount = sum(p.amount for p in payments)
            remaining = inv.net_amount - paid_amount
            
            creator_name = get_user_name_by_id(inv.created_by)
            
            data.append({
                "ID": inv.id,
                "رقم الفاتورة": inv.invoice_number,
                "التاريخ": inv.date.strftime("%Y-%m-%d %H:%M") if inv.date else "-",
                "النوع": "بيع" if inv.type == 'sale' else "شراء",
                "العميل/المورد": party.name if party else "غير محدد",
                "المبلغ": f"{inv.net_amount:,.2f} {currency_symbol}",
                "المدفوع": f"{paid_amount:,.2f} {currency_symbol}",
                "المتبقي": f"{remaining:,.2f} {currency_symbol}",
                "الحالة": inv.status,
                "أنشأها": creator_name
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("⚙️ إدارة الفواتير")
        
        invoice_ids = [inv.id for inv in invoices]
        
        selected_invoice_id = st.selectbox(
            "اختر فاتورة:",
            options=invoice_ids,
            format_func=lambda x: next((inv.invoice_number for inv in invoices if inv.id == x), x)
        )
        
        if selected_invoice_id:
            selected_invoice = db.query(models.Invoice).filter(models.Invoice.id == selected_invoice_id).first()
            
            tab1, tab2, tab3 = st.tabs(["📄 عرض التفاصيل", "✏️ تعديل/حذف", "💰 تسجيل دفعة"])
            
            with tab1:
                st.markdown("**تفاصيل الفاتورة:**")
                party = db.query(models.Party).filter(models.Party.id == selected_invoice.party_id).first()
                currency = db.query(models.Currency).filter(models.Currency.id == selected_invoice.currency_id).first()
                currency_symbol = currency.symbol if currency else "ج.م"
                
                creator_name = get_user_name_by_id(selected_invoice.created_by)
                
                st.write(f"**رقم الفاتورة:** {selected_invoice.invoice_number}")
                st.write(f"**التاريخ:** {selected_invoice.date.strftime('%Y-%m-%d %H:%M') if selected_invoice.date else '-'}")
                st.write(f"**النوع:** {'بيع' if selected_invoice.type == 'sale' else 'شراء'}")
                st.write(f"**العميل/المورد:** {party.name if party else 'غير محدد'}")
                st.write(f"**المبلغ الإجمالي:** {selected_invoice.net_amount:,.2f} {currency_symbol}")
                st.write(f"**الحالة:** {selected_invoice.status}")
                st.write(f"**أنشأها:** {creator_name}")
                
                st.markdown("---")
                st.markdown("**أصناف الفاتورة:**")
                
                invoice_lines = db.query(models.InvoiceLine).filter(
                    models.InvoiceLine.invoice_id == selected_invoice.id
                ).all()
                
                if invoice_lines:
                    lines_data = []
                    for line in invoice_lines:
                        item = db.query(models.Item).filter(models.Item.id == line.item_id).first()
                        lines_data.append({
                            "الصنف": item.name if item else "غير محدد",
                            "الكمية": line.quantity,
                            "سعر الوحدة": f"{line.price:,.2f} {currency_symbol}",
                            "الإجمالي": f"{line.total:,.2f} {currency_symbol}"
                        })
                    lines_df = pd.DataFrame(lines_data)
                    st.dataframe(lines_df, use_container_width=True)
            
            with tab2:
                st.subheader("️ قواعد التعديل والحذف")
                
                # التحقق من وجود مدفوعات مرتبطة
                payments = db.query(models.Payment).filter(
                    models.Payment.reference_number.contains(selected_invoice.invoice_number)
                ).all()
                
                has_payments = len(payments) > 0
                
                # عرض حالة الفاتورة
                if has_payments:
                    st.error(f"""
                    ⛔ **هذه الفاتورة مرتبطة بـ {len(payments)} سند دفع/قبض**
                    
                    **القواعد المحاسبية:**
                    - ❌ لا يمكن تعديل هذه الفاتورة (لأن السندات مرتبطة بمبلغها)
                    - ❌ لا يمكن حذف هذه الفاتورة (وثيقة محاسبية رسمية)
                    
                    **الحل البديل:**
                    إذا كان هناك خطأ في الفاتورة، يجب:
                    1. إلغاء السندات المرتبطة أولاً
                    2. ثم تعديل الفاتورة
                    """)
                else:
                    st.warning(f"""
                    ️ **هذه الفاتورة غير مرتبطة بأي سندات دفع/قبض**
                    
                    **القواعد المحاسبية:**
                    - ✅ يمكن تعديل هذه الفاتورة (تغيير الحالة فقط)
                    - ❌ لا يمكن حذف هذه الفاتورة (وثيقة محاسبية رسمية)
                    
                    **ملاحظة:**
                    الفواتير وثائق محاسبية رسمية لا تُحذف أبداً للحفاظ على سلامة السجلات المالية.
                    """)
                
                st.markdown("---")
                
                # قسم التعديل
                st.subheader("️ تعديل الفاتورة")
                
                if has_payments:
                    st.info("🔒 لا يمكن تعديل هذه الفاتورة لأنها مرتبطة بسندات دفع/قبض")
                else:
                    st.markdown("**تعديل حالة الفاتورة:**")
                    
                    new_status = st.selectbox(
                        "الحالة الجديدة:",
                        ["pending", "paid", "cancelled"],
                        format_func=lambda x: {"pending": "معلقة", "paid": "مدفوعة", "cancelled": "ملغاة"}.get(x, x),
                        index=["pending", "paid", "cancelled"].index(selected_invoice.status) if selected_invoice.status in ["pending", "paid", "cancelled"] else 0
                    )
                    
                    if st.button("💾 حفظ تغييرات الحالة", type="primary"):
                        selected_invoice.status = new_status
                        db.commit()
                        st.success(f"✅ تم تحديث حالة الفاتورة بنجاح! (بواسطة: {current_user_name})")
                        st.rerun()
                
                st.markdown("---")
                
                # قسم الحذف
                st.subheader("️ حذف الفاتورة")
                
                st.error("""
                ⛔ **لا يمكن حذف الفواتير**
                
                الفواتير وثائق محاسبية رسمية لا يمكن حذفها أبداً للحفاظ على:
                - سلامة السجلات المالية
                - دقة التقارير المحاسبية
                - التوافق مع المعايير المحاسبية
                
                **الحلول البديلة:**
                1. تغيير حالة الفاتورة إلى "ملغاة" إذا كانت خاطئة
                2. إنشاء فاتورة جديدة صحيحة
                3. إضافة ملاحظة توضيحية في الفاتورة
                """)
            
            with tab3:
                st.markdown("**تسجيل دفعة جديدة لهذه الفاتورة:**")
                
                existing_payments = db.query(models.Payment).filter(
                    models.Payment.reference_number.contains(selected_invoice.invoice_number)
                ).all()
                paid_amount = sum(p.amount for p in existing_payments)
                remaining = selected_invoice.net_amount - paid_amount
                
                st.info(f"المبلغ الإجمالي: {selected_invoice.net_amount:,.2f} ج.م")
                st.info(f"المبلغ المدفوع: {paid_amount:,.2f} ج.م")
                st.info(f"المبلغ المتبقي: {remaining:,.2f} ج.م")
                
                if remaining <= 0:
                    st.success("✅ تم سداد هذه الفاتورة بالكامل!")
                else:
                    st.markdown("---")
                    st.subheader("تفاصيل الدفعة")
                    
                    payment_date = st.date_input("تاريخ الدفعة:", value=datetime.now().date())
                    payment_time = st.time_input("وقت الدفعة:", value=datetime.now().time())
                    
                    payment_amount = st.number_input(
                        "مبلغ الدفعة:", 
                        min_value=0.01, 
                        max_value=remaining, 
                        value=remaining, 
                        step=100.0
                    )
                    
                    payment_method = st.selectbox("طريقة الدفع:", ["cash (نقدي)", "bank_transfer (تحويل بنكي)", "check (شيك)"])
                    actual_method = payment_method.split(" ")[0]
                    
                    # اختيار الخزينة
                    cash_boxes = db.query(CashBox).filter(CashBox.is_active == True).all()
                    cash_box_dict = {box.id: f"{box.name} ({box.code})" for box in cash_boxes}
                    
                    if cash_boxes:
                        selected_cash_box_id = st.selectbox(
                            "الخزينة/الحساب:",
                            options=list(cash_box_dict.keys()),
                            format_func=lambda x: cash_box_dict[x]
                        )
                        
                        from services import get_cash_box_balance
                        current_balance = get_cash_box_balance(selected_cash_box_id)
                        st.info(f"💰 الرصيد الحالي للخزينة: **{current_balance:,.2f} ج.م**")
                    else:
                        st.warning("⚠️ لا توجد خزائن مسجلة!")
                        selected_cash_box_id = None
                    
                    reference_number = st.text_input("رقم المرجع (اختياري):", value=f"دفعة فاتورة {selected_invoice.invoice_number}")
                    notes = st.text_area("ملاحظات (اختياري):")
                    
                    if st.button("💰 تسجيل الدفعة", type="primary"):
                        if not selected_cash_box_id:
                            st.error("يرجى اختيار الخزينة")
                        else:
                            try:
                                payment_datetime = datetime.combine(payment_date, payment_time)
                                
                                create_payment(
                                    party_id=selected_invoice.party_id,
                                    amount=payment_amount,
                                    payment_type="receipt" if selected_invoice.type == 'sale' else "payment",
                                    payment_method=actual_method,
                                    reference_number=reference_number,
                                    notes=notes,
                                    currency_id=selected_invoice.currency_id,
                                    payment_date=payment_datetime,
                                    created_by=current_user_id,
                                    cash_box_id=selected_cash_box_id
                                )
                                
                                if payment_amount >= remaining:
                                    selected_invoice.status = 'paid'
                                    db.commit()
                                
                                st.success(f"✅ تم تسجيل دفعة بمبلغ {payment_amount:,.2f} ج.م بنجاح! (بواسطة: {current_user_name})")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ خطأ: {e}")
    else:
        st.info("لا توجد فواتير.")

finally:
    db.close()