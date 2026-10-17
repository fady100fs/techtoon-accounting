# pages/42_📤_سند_صرف.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, can_modify, require_modify
render_sidebar()

import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from models import Account, AccountType, CashBox
from services import movement_serial
from auth_required import require_login, get_current_user_id, get_current_user_name
from period_guard import check_period_open

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()
st.set_page_config(page_title="سند صرف", page_icon="📤", layout="wide")
st.title("📤 سندات الصرف (المدفوع)")
st.info(f"👤 المستخدم: **{current_user_name}**")

PFX = "pay_"
db = SessionLocal()

# ==========================================
# تبويب 1: تسجيل سند صرف جديد
# ==========================================
tab1, tab2 = st.tabs(["➕ تسجيل سند صرف", "📋 السجل والتعديل"])

with tab1:
    cash_boxes = db.query(CashBox).filter(CashBox.is_active == True).all()
    if not cash_boxes:
        st.error("⚠️ لا توجد خزائن مفعّلة!")
        st.stop()
    box_opt = {b.id: f"{b.name} ({b.code})" for b in cash_boxes}
    selected_box_id = st.selectbox("1️⃣ الخزينة:", options=list(box_opt.keys()), format_func=lambda x: box_opt[x], key=f"{PFX}box")

    st.markdown("### 2️⃣ الحساب المقابل (جهة الصرف)")
    accs = db.query(Account).filter(Account.type.in_([AccountType.EXPENSE, AccountType.LIABILITY, AccountType.EQUITY, AccountType.ASSET])).order_by(Account.code).all()
    acc_opts = {a.id: f"{a.code} - {a.name}" for a in accs}
    selected_acc_id = st.selectbox("اختر الحساب:", options=list(acc_opts.keys()), format_func=lambda x: acc_opts.get(x, ""), key=f"{PFX}acc")

    st.markdown("### 3️⃣ تفاصيل الصرف")
    col_d, col_t = st.columns(2)
    with col_d:
        pay_date = st.date_input("التاريخ:", value=datetime.now().date(), key=f"{PFX}date")
    with col_t:
        pay_time = st.time_input("الوقت:", value=datetime.now().time(), key=f"{PFX}time")
    amount = st.number_input("المبلغ (ج.م):", min_value=0.01, step=100.0, value=100.0, format="%.2f", key=f"{PFX}amt")
    desc = st.text_area("الوصف:", key=f"{PFX}desc")
    ref = st.text_input("رقم المرجع (اختياري):", key=f"{PFX}ref")

    if st.button("💾 حفظ سند الصرف", type="primary", use_container_width=True, key=f"{PFX}save"):
        if not selected_acc_id:
            st.error("❌ اختر الحساب المقابل أولاً.")
        elif amount <= 0:
            st.error("❌ المبلغ يجب أن يكون أكبر من صفر.")
        else:
            try:
                dt = datetime.combine(pay_date, pay_time)
                from services import _after_write
                check_period_open(dt, entity="تسجيل سند صرف")
                cash_box = db.query(CashBox).filter(CashBox.id == selected_box_id).first()
                counter_acc = db.query(Account).filter(Account.id == selected_acc_id).first()
                entry = models.JournalEntry(date=dt, description=f"صادر: {desc} — {counter_acc.code} {counter_acc.name}", reference_type="cash_movement", created_by=current_user_id)
                db.add(entry)
                db.flush()
                db.add(models.JournalLine(entry_id=entry.id, account_id=selected_acc_id, debit=float(amount), credit=0.0))
                db.add(models.JournalLine(entry_id=entry.id, account_id=cash_box.account_id, debit=0.0, credit=float(amount)))
                db.commit()
                _after_write()
                st.success(f"✅ تم تسجيل سند الصرف بمبلغ {amount:,.2f} ج.م")
                st.balloons()
                st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"❌ خطأ: {e}")

# ==========================================
# تبويب 2: السجل والتعديل والحذف
# ==========================================
with tab2:
    st.subheader("📋 سجل سندات الصرف (المدفوع)")
    
    entries = db.query(models.JournalEntry).filter(
        models.JournalEntry.reference_type.in_(["cash_movement", "revenue", "expense"])
    ).order_by(models.JournalEntry.date.desc()).limit(200).all()
    
    payment_entries = []
    for e in entries:
        lines = db.query(models.JournalLine).filter(models.JournalLine.entry_id == e.id).all()
        for ln in lines:
            acc = db.query(Account).filter(Account.id == ln.account_id).first()
            if not acc: continue
            is_cb = db.query(CashBox).filter(CashBox.account_id == acc.id).first()
            # الصادر = الخزينة دائن (credit > 0)
            if is_cb and float(ln.credit or 0) > 0:
                payment_entries.append(e)
                break
    
    if not payment_entries:
        st.info("لا توجد سندات صرف مسجلة.")
    else:
        rows = []
        for e in payment_entries:
            lines = db.query(models.JournalLine).filter(models.JournalLine.entry_id == e.id).all()
            amt = 0.0
            counter_name = ""
            cash_name = ""
            for ln in lines:
                acc = db.query(Account).filter(Account.id == ln.account_id).first()
                is_cb = db.query(CashBox).filter(CashBox.account_id == acc.id).first() if acc else None
                if is_cb and ln.credit > 0:
                    amt = float(ln.credit)
                    cash_name = is_cb.name
                elif not is_cb:
                    counter_name = f"{acc.code} - {acc.name}" if acc else ""
            rows.append({
                "ID": e.id,
                "المسلسل": movement_serial("CM", e.id),
                "التاريخ": e.date.strftime("%Y-%m-%d %H:%M") if e.date else "—",
                "الخزينة": cash_name,
                "الطرف المقابل": counter_name,
                "المبلغ": amt,
                "الوصف": e.description or "—",
            })
        
        df = pd.DataFrame(rows)
        st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True, column_config={"المبلغ": st.column_config.NumberColumn("المبلغ", format="%.2f")})
        
        st.markdown("---")
        st.subheader("✏️ تعديل / حذف سند")
        
        opts = {r["ID"]: f'{r["المسلسل"]} — {r["المبلغ"]:,.2f} ج.م — {r["التاريخ"]}' for r in rows}
        sel_id = st.selectbox("اختر السند:", options=list(opts.keys()), format_func=lambda x: opts.get(x, ""), key=f"{PFX}edit_sel")
        
        if sel_id:
            entry = db.query(models.JournalEntry).filter(models.JournalEntry.id == sel_id).first()
            if entry:
                lines = db.query(models.JournalLine).filter(models.JournalLine.entry_id == entry.id).all()
                cash_line = counter_line = None
                for ln in lines:
                    acc = db.query(Account).filter(Account.id == ln.account_id).first()
                    is_cb = db.query(CashBox).filter(CashBox.account_id == acc.id).first() if acc else None
                    if is_cb:
                        cash_line = ln
                    else:
                        counter_line = ln
                
                col1, col2 = st.columns(2)
                with col1:
                    new_amount = st.number_input("المبلغ:", min_value=0.01, value=float(counter_line.debit or 0), step=100.0, format="%.2f", key=f"{PFX}edit_amt")
                    new_date = st.date_input("التاريخ:", value=entry.date.date() if entry.date else datetime.now().date(), key=f"{PFX}edit_d")
                with col2:
                    new_acc = st.selectbox("الحساب المقابل:", options=list(acc_opts.keys()),
                                           index=list(acc_opts.keys()).index(counter_line.account_id) if counter_line else 0,
                                           format_func=lambda x: acc_opts.get(x, ""), key=f"{PFX}edit_acc")
                    new_desc = st.text_input("الوصف:", value=entry.description or "", key=f"{PFX}edit_desc")
                
                if can_modify():
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("💾 حفظ التعديل", type="primary", use_container_width=True, key=f"{PFX}save_edit"):
                            try:
                                new_dt = datetime.combine(new_date, entry.date.time() if entry.date else datetime.now().time())
                                check_period_open(new_dt, entity="تعديل سند صرف")
                                counter_line.debit = float(new_amount)
                                counter_line.credit = 0.0
                                counter_line.account_id = new_acc
                                cash_line.debit = 0.0
                                cash_line.credit = float(new_amount)
                                entry.date = new_dt
                                entry.description = new_desc
                                db.commit()
                                from services import _after_write
                                _after_write()
                                st.success("✅ تم التعديل بنجاح!")
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"❌ {e}")
                    with c2:
                        if st.button("🗑 حذف السند", type="secondary", use_container_width=True, key=f"{PFX}del"):
                            try:
                                check_period_open(entry.date, entity="حذف سند صرف")
                                db.query(models.JournalLine).filter(models.JournalLine.entry_id == entry.id).delete()
                                db.delete(entry)
                                db.commit()
                                from services import _after_write
                                _after_write()
                                st.success("✅ تم الحذف بنجاح!")
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"❌ {e}")
                else:
                    st.info("⛔ التعديل والحذف للمدير فقط.")

db.close()
