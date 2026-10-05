
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/8_💰_المدفوعات.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from services import create_payment
from auth_required import require_login
current_user = require_login()
st.set_page_config(page_title="المدفوعات", page_icon="💰", layout="wide")
st.title("💰 المدفوعات والسداد")
from keyboard_nav import enable_enter_navigation, add_enter_hint

# تفعيل التنقل بـ Enter
enable_enter_navigation()
add_enter_hint()
db = SessionLocal()

tab1, tab2, tab3 = st.tabs(["➕ تسجيل دفعة جديدة", "📋 سجل المدفوعات", "⚙️ تعديل/حذف دفعة"])

with tab1:
    st.subheader("تسجيل دفعة جديدة")
    
    # التاريخ والوقت
    st.markdown("### 📅 تاريخ ووقت الدفعة")
    col_date, col_time = st.columns(2)
    with col_date:
        payment_date = st.date_input("التاريخ:", value=datetime.now().date(), key="payment_date")
    with col_time:
        payment_time = st.time_input("الوقت:", value=datetime.now().time(), key="payment_time")
    
    payment_type = st.radio("نوع الدفعة:", ["receipt (قبض من عميل)", "payment (صرف لمورد)"], horizontal=True)
    actual_type = "receipt" if "receipt" in payment_type else "payment"
    type_ar = "قبض" if actual_type == "receipt" else "صرف"
    
    if actual_type == "receipt":
        parties = db.query(models.Party).filter(models.Party.type == 'customer').all()
    else:
        parties = db.query(models.Party).filter(models.Party.type == 'supplier').all()
    
    party_dict = {p.id: p.name for p in parties}
    selected_party_id = st.selectbox(
        f"اختر {'العميل' if actual_type == 'receipt' else 'المورد'}:", 
        options=list(party_dict.keys()),
        format_func=lambda x: party_dict[x]
    )
    
    amount = st.number_input("مبلغ الدفعة:", min_value=0.01, step=100.0)
    
    payment_method = st.selectbox("طريقة الدفع:", ["cash (نقدي)", "bank_transfer (تحويل بنكي)", "check (شيك)"])
    actual_method = payment_method.split(" ")[0]
    
    reference_number = st.text_input("رقم المرجع (رقم الشيك/التحويل) - اختياري")
    notes = st.text_area("ملاحظات - اختياري")
    
    currencies = db.query(models.Currency).all()
    currency_options = {curr.id: f"{curr.name} ({curr.symbol})" for curr in currencies}
    selected_currency_id = st.selectbox("العملة:", options=list(currency_options.keys()), format_func=lambda x: currency_options[x])
    
    if st.button("💾 حفظ الدفعة", type="primary"):
        if not selected_party_id or amount <= 0:
            st.error("يرجى اختيار العميل/المورد وإدخال مبلغ صحيح")
        else:
            try:
                # دمج التاريخ والوقت
                payment_datetime = datetime.combine(payment_date, payment_time)
                
                create_payment(
                    party_id=selected_party_id,
                    amount=amount,
                    payment_type=actual_type,
                    payment_method=actual_method,
                    reference_number=reference_number,
                    notes=notes,
                    currency_id=selected_currency_id,
                    payment_date=payment_datetime
                )
                st.success(f"تم تسجيل دفعة {type_ar} بمبلغ {amount:,.2f} بنجاح!")
                st.rerun()
            except Exception as e:
                st.error(f"خطأ: {e}")

with tab2:
    st.subheader("سجل المدفوعات")
    payments = db.query(models.Payment).order_by(models.Payment.date.desc()).all()
    
    if payments:
        data = []
        for pay in payments:
            party = db.query(models.Party).filter(models.Party.id == pay.party_id).first()
            currency = db.query(models.Currency).filter(models.Currency.id == pay.currency_id).first()
            currency_symbol = currency.symbol if currency else "ج.م"
            
            data.append({
                "ID": pay.id,
                "التاريخ": pay.date.strftime("%Y-%m-%d %H:%M") if pay.date else "-",
                "النوع": "قبض" if pay.payment_type == 'receipt' else "صرف",
                "العميل/المورد": party.name if party else "غير محدد",
                "المبلغ": f"{pay.amount:,.2f} {currency_symbol}",
                "الطريقة": pay.payment_method,
                "رقم المرجع": pay.reference_number or "-",
                "ملاحظات": pay.notes or "-"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        
        total_receipts = sum(p.amount for p in payments if p.payment_type == 'receipt')
        total_payments = sum(p.amount for p in payments if p.payment_type == 'payment')
        net_cash = total_receipts - total_payments
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("إجمالي المقبوضات", f"{total_receipts:,.2f} ج.م")
        with col2:
            st.metric("إجمالي المدفوعات", f"{total_payments:,.2f} ج.م")
        with col3:
            st.metric("صافي التدفق النقدي", f"{net_cash:,.2f} ج.م", delta=f"{net_cash:,.2f}")
    else:
        st.info("لا توجد مدفوعات مسجلة.")

with tab3:
    st.subheader("️ تعديل/حذف دفعة")
    
    payments = db.query(models.Payment).order_by(models.Payment.date.desc()).all()
    
    if payments:
        payment_ids = [p.id for p in payments]
        
        selected_payment_id = st.selectbox(
            "اختر دفعة:",
            options=payment_ids,
            format_func=lambda x: next((
                f"{p.date.strftime('%Y-%m-%d')} - {p.amount:,.2f} ج.م - {p.reference_number or 'بدون مرجع'}" 
                for p in payments if p.id == x
            ), x)
        )
        
        if selected_payment_id:
            selected_payment = db.query(models.Payment).filter(
                models.Payment.id == selected_payment_id
            ).first()
            
            party = db.query(models.Party).filter(
                models.Party.id == selected_payment.party_id
            ).first()
            
            currency = db.query(models.Currency).filter(
                models.Currency.id == selected_payment.currency_id
            ).first()
            currency_symbol = currency.symbol if currency else "ج.م"
            
            # عرض تفاصيل الدفعة
            st.markdown("### 📄 تفاصيل الدفعة المحددة")
            st.write(f"**التاريخ:** {selected_payment.date.strftime('%Y-%m-%d %H:%M') if selected_payment.date else '-'}")
            st.write(f"**النوع:** {'قبض' if selected_payment.payment_type == 'receipt' else 'صرف'}")
            st.write(f"**العميل/المورد:** {party.name if party else 'غير محدد'}")
            st.write(f"**المبلغ:** {selected_payment.amount:,.2f} {currency_symbol}")
            st.write(f"**طريقة الدفع:** {selected_payment.payment_method}")
            st.write(f"**رقم المرجع:** {selected_payment.reference_number or '-'}")
            st.write(f"**ملاحظات:** {selected_payment.notes or '-'}")
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### ✏️ تعديل الدفعة")
                st.warning("️ سيتم حذف القيود المحاسبية القديمة وإنشاء قيود جديدة بالمبالغ المعدلة.")
                
                new_amount = st.number_input(
                    "المبلغ الجديد:", 
                    min_value=0.01, 
                    value=selected_payment.amount, 
                    step=100.0,
                    key=f"edit_amount_{selected_payment_id}"
                )
                
                new_payment_method = st.selectbox(
                    "طريقة الدفع الجديدة:", 
                    ["cash (نقدي)", "bank_transfer (تحويل بنكي)", "check (شيك)"],
                    index=["cash", "bank_transfer", "check"].index(selected_payment.payment_method) 
                    if selected_payment.payment_method in ["cash", "bank_transfer", "check"] else 0,
                    key=f"edit_method_{selected_payment_id}"
                )
                new_method = new_payment_method.split(" ")[0]
                
                new_reference = st.text_input(
                    "رقم المرجع الجديد:", 
                    value=selected_payment.reference_number or "",
                    key=f"edit_ref_{selected_payment_id}"
                )
                
                new_notes = st.text_area(
                    "ملاحظات جديدة:", 
                    value=selected_payment.notes or "",
                    key=f"edit_notes_{selected_payment_id}"
                )
                
                if st.button("💾 حفظ التعديلات", type="primary"):
                    try:
                        # حذف القيود المحاسبية القديمة
                        old_journal_entry = db.query(models.JournalEntry).filter(
                            models.JournalEntry.reference_type == "payment",
                            models.JournalEntry.description.contains(selected_payment.reference_number or str(selected_payment.id))
                        ).first()
                        
                        if old_journal_entry:
                            db.query(models.JournalLine).filter(
                                models.JournalLine.entry_id == old_journal_entry.id
                            ).delete()
                            db.delete(old_journal_entry)
                        
                        # تحديث الدفعة
                        selected_payment.amount = new_amount
                        selected_payment.payment_method = new_method
                        selected_payment.reference_number = new_reference if new_reference else None
                        selected_payment.notes = new_notes if new_notes else None
                        
                        # إنشاء قيد محاسبي جديد
                        journal_entry = models.JournalEntry(
                            date=selected_payment.date,
                            description=f"دفعة {selected_payment.payment_type} لـ {party.name} - {new_reference or ''}",
                            reference_type="payment",
                            reference_id=None
                        )
                        db.add(journal_entry)
                        db.flush()
                        
                        cash_account = db.query(models.Account).filter(
                            models.Account.code == "1101"
                        ).first()
                        
                        if not cash_account:
                            raise ValueError("حساب النقدية غير موجود!")
                        
                        if selected_payment.payment_type == 'receipt':
                            db.add(models.JournalLine(
                                entry_id=journal_entry.id,
                                account_id=cash_account.id,
                                debit=new_amount,
                                credit=0.0
                            ))
                            db.add(models.JournalLine(
                                entry_id=journal_entry.id,
                                account_id=party.account_id,
                                debit=0.0,
                                credit=new_amount
                            ))
                        else:
                            db.add(models.JournalLine(
                                entry_id=journal_entry.id,
                                account_id=party.account_id,
                                debit=new_amount,
                                credit=0.0
                            ))
                            db.add(models.JournalLine(
                                entry_id=journal_entry.id,
                                account_id=cash_account.id,
                                debit=0.0,
                                credit=new_amount
                            ))
                        
                        db.commit()
                        st.success("✅ تم تحديث الدفعة والقيود المحاسبية بنجاح!")
                        st.rerun()
                    except Exception as e:
                        st.error(f" خطأ في التعديل: {e}")
            
            with col2:
                st.markdown("### 🗑️ حذف الدفعة")
                st.warning("⚠️ سيتم حذف الدفعة والقيود المحاسبية المرتبطة بها نهائياً!")
                st.error("⚠️ هذا الإجراء لا يمكن التراجع عنه!")
                
                if st.button("🗑️ حذف الدفعة", type="secondary"):
                    if st.checkbox("✅ أؤكد أنني أفهم أن هذه العملية لا يمكن التراجع عنها"):
                        try:
                            # حذف القيود المحاسبية المرتبطة
                            old_journal_entry = db.query(models.JournalEntry).filter(
                                models.JournalEntry.reference_type == "payment",
                                models.JournalEntry.description.contains(selected_payment.reference_number or str(selected_payment.id))
                            ).first()
                            
                            if old_journal_entry:
                                db.query(models.JournalLine).filter(
                                    models.JournalLine.entry_id == old_journal_entry.id
                                ).delete()
                                db.delete(old_journal_entry)
                            
                            # حذف الدفعة
                            db.delete(selected_payment)
                            db.commit()
                            
                            st.success("✅ تم حذف الدفعة والقيود المحاسبية المرتبطة بنجاح!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ خطأ في الحذف: {e}")
    else:
        st.info("لا توجد مدفوعات للتعديل أو الحذف.")

db.close()