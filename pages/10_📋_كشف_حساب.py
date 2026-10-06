
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

# pages/10_📋_كشف_حساب.py
import streamlit as st
import pandas as pd
from sqlalchemy import func
from database import SessionLocal
import models
from auth_required import require_login
current_user = require_login()
st.set_page_config(page_title="كشف حساب", page_icon="📋", layout="wide")
st.title("📋 كشف حساب عميل/مورد")
from keyboard_nav import enable_enter_navigation, add_enter_hint

# تفعيل التنقل بـ Enter
enable_enter_navigation()
add_enter_hint()
db = SessionLocal()

# اختيار العميل أو المورد
party_type = st.radio("نوع الحساب:", ["customer (عميل)", "supplier (مورد)"], horizontal=True)
actual_type = "customer" if "customer" in party_type else "supplier"
type_ar = "عميل" if actual_type == "customer" else "مورد"

parties = db.query(models.Party).filter(models.Party.type == actual_type).all()
party_names = [p.name for p in parties]

if party_names:
    selected_party_name = st.selectbox(f"اختر {type_ar}:", party_names)
    
    if selected_party_name:
        selected_party = db.query(models.Party).filter(
            models.Party.name == selected_party_name,
            models.Party.type == actual_type
        ).first()
        
        if selected_party:
            st.markdown("---")
            st.subheader(f"كشف حساب {type_ar}: {selected_party.name}")
            
            # جلب جميع الفواتير
            invoices = db.query(models.Invoice).filter(
                models.Invoice.party_id == selected_party.id
            ).order_by(models.Invoice.date).all()
            
            # جلب جميع المدفوعات
            payments = db.query(models.Payment).filter(
                models.Payment.party_id == selected_party.id
            ).order_by(models.Payment.date).all()
            
            # بناء جدول كشف الحساب
            statement_data = []
            total_debit = 0
            total_credit = 0
            running_balance = 0
            
            # إضافة الرصيد الافتتاحي من القيود
            opening_entry = db.query(models.JournalEntry).filter(
                models.JournalEntry.reference_type == "opening_balance",
                models.JournalEntry.description.contains(selected_party.name)
            ).first()
            
            if opening_entry:
                opening_line = db.query(models.JournalLine).filter(
                    models.JournalLine.entry_id == opening_entry.id,
                    models.JournalLine.account_id == selected_party.account_id
                ).first()
                
                if opening_line:
                    opening_balance = opening_line.debit - opening_line.credit
                    running_balance = opening_balance
                    statement_data.append({
                        "التاريخ": opening_entry.date.strftime("%Y-%m-%d") if opening_entry.date else "-",
                        "البيان": "رصيد افتتاحي",
                        "مدين": f"{opening_line.debit:,.2f}" if opening_line.debit > 0 else "-",
                        "دائن": f"{opening_line.credit:,.2f}" if opening_line.credit > 0 else "-",
                        "الرصيد": f"{running_balance:,.2f}"
                    })
            
            # إضافة الفواتير
            for inv in invoices:
                currency = db.query(models.Currency).filter(models.Currency.id == inv.currency_id).first()
                currency_symbol = currency.symbol if currency else "ج.م"
                
                if inv.type == 'sale':
                    # فاتورة بيع: مدين للعميل
                    running_balance += inv.total_amount
                    total_debit += inv.total_amount
                    statement_data.append({
                        "التاريخ": inv.date.strftime("%Y-%m-%d") if inv.date else "-",
                        "البيان": f"فاتورة بيع رقم {inv.invoice_number}",
                        "مدين": f"{inv.total_amount:,.2f} {currency_symbol}",
                        "دائن": "-",
                        "الرصيد": f"{running_balance:,.2f}"
                    })
                else:
                    # فاتورة شراء: دائن للمورد
                    running_balance -= inv.total_amount
                    total_credit += inv.total_amount
                    statement_data.append({
                        "التاريخ": inv.date.strftime("%Y-%m-%d") if inv.date else "-",
                        "البيان": f"فاتورة شراء رقم {inv.invoice_number}",
                        "مدين": "-",
                        "دائن": f"{inv.total_amount:,.2f} {currency_symbol}",
                        "الرصيد": f"{running_balance:,.2f}"
                    })
            
            # إضافة المدفوعات
            for pay in payments:
                currency = db.query(models.Currency).filter(models.Currency.id == pay.currency_id).first()
                currency_symbol = currency.symbol if currency else "ج.م"
                
                if pay.payment_type == 'receipt':
                    # قبض من عميل: دائن
                    running_balance -= pay.amount
                    total_credit += pay.amount
                    statement_data.append({
                        "التاريخ": pay.date.strftime("%Y-%m-%d") if pay.date else "-",
                        "البيان": f"دفعة قبض - {pay.payment_method}",
                        "مدين": "-",
                        "دائن": f"{pay.amount:,.2f} {currency_symbol}",
                        "الرصيد": f"{running_balance:,.2f}"
                    })
                else:
                    # صرف لمورد: مدين
                    running_balance += pay.amount
                    total_debit += pay.amount
                    statement_data.append({
                        "التاريخ": pay.date.strftime("%Y-%m-%d") if pay.date else "-",
                        "البيان": f"دفعة صرف - {pay.payment_method}",
                        "مدين": f"{pay.amount:,.2f} {currency_symbol}",
                        "دائن": "-",
                        "الرصيد": f"{running_balance:,.2f}"
                    })
            
            # عرض الجدول
            if statement_data:
                df = pd.DataFrame(statement_data)
                st.dataframe(df, use_container_width=True)
                
                st.markdown("---")
                
                # ملخص الحساب
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("إجمالي المدين", f"{total_debit:,.2f} ج.م")
                with col2:
                    st.metric("إجمالي الدائن", f"{total_credit:,.2f} ج.م")
                with col3:
                    balance_type = "له" if running_balance > 0 else "عليه"
                    st.metric(f"الرصيد الحالي ({balance_type})", f"{abs(running_balance):,.2f} ج.م")
                
                # زر تصدير Excel
                if st.button("📊 تصدير كشف الحساب إلى Excel", type="primary"):
                    try:
                        from export_excel import export_statement_to_excel
                        excel_path = export_statement_to_excel(
                            party_name=selected_party.name,
                            party_type=actual_type,
                            statement_data=statement_data,
                            total_debit=total_debit,
                            total_credit=total_credit,
                            running_balance=running_balance
                        )
                        st.success(f"تم التصدير: {excel_path}")
                        
                        with open(excel_path, "rb") as file:
                            st.download_button(
                                label="⬇️ تحميل Excel",
                                data=file,
                                file_name=excel_path,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    except Exception as e:
                        st.error(f"خطأ في التصدير: {e}")
            else:
                st.info("لا توجد حركات لهذا الحساب.")
else:
    st.info(f"لا يوجد {type_ar}s مسجلين.")

db.close()