# pages/8_💰_المدفوعات.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify
render_sidebar()

import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from services import create_payment, movement_serial
from auth_required import require_login, get_current_user_id, get_current_user_name

# ✅ Cache Layer
from cache_helpers import (
    get_payments_index,
    get_parties,
    invalidate_all,
)

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="المدفوعات", page_icon="💰", layout="wide")
st.title("💰 المدفوعات والسداد")
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

try:
    from keyboard_nav import enable_enter_navigation, add_enter_hint
    enable_enter_navigation()
    add_enter_hint()
except Exception:
    pass

db = SessionLocal()


def _delete_payment_full(payment_id):
    """يحذف دفعة + القيد المحاسبي المرتبط بها."""
    db_local = SessionLocal()
    try:
        pay = db_local.query(models.Payment).filter(
            models.Payment.id == payment_id
        ).first()
        if not pay:
            raise ValueError("الدفعة غير موجودة")

        ref_marker = pay.reference_number or str(pay.id)
        je = db_local.query(models.JournalEntry).filter(
            models.JournalEntry.reference_type == "payment",
            models.JournalEntry.description.contains(ref_marker),
        ).first()
        if je:
            db_local.query(models.JournalLine).filter(
                models.JournalLine.entry_id == je.id
            ).delete(synchronize_session=False)
            db_local.delete(je)

        db_local.delete(pay)
        db_local.commit()
    except Exception:
        db_local.rollback()
        raise
    finally:
        db_local.close()


tab1, tab2, tab3 = st.tabs([
    "➕ تسجيل دفعة جديدة",
    "📋 سجل المدفوعات",
    "⚙️ تعديل/حذف دفعة",
])


# ==========================================
# التبويب 1: تسجيل دفعة جديدة
# ==========================================
with tab1:
    st.subheader("➕ تسجيل دفعة جديدة")
    st.caption("💡 بعد الحفظ، الحقول هتتفرّغ تلقائيًا.")

    col_date, col_time = st.columns(2)
    with col_date:
        payment_date = st.date_input("التاريخ:",
                                      value=datetime.now().date(),
                                      key="new_pay_date")
    with col_time:
        payment_time = st.time_input("الوقت:",
                                      value=datetime.now().time(),
                                      key="new_pay_time")

    payment_type = st.radio(
        "نوع الدفعة:",
        ["receipt (قبض من عميل)", "payment (صرف لمورد)"],
        horizontal=True,
        key="new_pay_type",
    )
    actual_type = "receipt" if "receipt" in payment_type else "payment"
    type_ar = "قبض" if actual_type == "receipt" else "صرف"

    if actual_type == "receipt":
        parties = db.query(models.Party).filter(
            models.Party.type == "customer"
        ).all()
    else:
        parties = db.query(models.Party).filter(
            models.Party.type == "supplier"
        ).all()

    if not parties:
        st.warning(f"⚠️ لا يوجد {'عملاء' if actual_type == 'receipt' else 'موردين'}!")
        st.stop()

    party_dict = {p.id: p.name for p in parties}
    selected_party_id = st.selectbox(
        f"اختر {'العميل' if actual_type == 'receipt' else 'المورد'}:",
        options=list(party_dict.keys()),
        format_func=lambda x: party_dict[x],
        key="new_pay_party",
    )

    amount = st.number_input("مبلغ الدفعة:", min_value=0.01, step=100.0,
                              format="%.2f", key="new_pay_amount")

    payment_method = st.selectbox(
        "طريقة الدفع:",
        ["cash (نقدي)", "bank_transfer (تحويل بنكي)", "check (شيك)"],
        key="new_pay_method",
    )
    actual_method = payment_method.split(" ")[0]

    reference_number = st.text_input(
        "رقم المرجع (رقم الشيك/التحويل) - اختياري",
        key="new_pay_ref",
    )
    notes = st.text_area("ملاحظات - اختياري", key="new_pay_notes")

    currencies = db.query(models.Currency).all()
    currency_options = {c.id: f"{c.name} ({c.symbol})" for c in currencies}
    selected_currency_id = st.selectbox(
        "العملة:",
        options=list(currency_options.keys()),
        format_func=lambda x: currency_options[x],
        key="new_pay_currency",
    )

    if st.button("💾 حفظ الدفعة", type="primary", use_container_width=True):
        if not selected_party_id or amount <= 0:
            st.error("❌ يرجى اختيار العميل/المورد وإدخال مبلغ صحيح.")
        else:
            try:
                payment_datetime = datetime.combine(payment_date, payment_time)
                create_payment(
                    party_id=selected_party_id,
                    amount=amount,
                    payment_type=actual_type,
                    payment_method=actual_method,
                    reference_number=reference_number or None,
                    notes=notes or None,
                    currency_id=selected_currency_id,
                    payment_date=payment_datetime,
                )
                invalidate_all()   # ✅
                st.success(f"✅ تم تسجيل دفعة {type_ar} بمبلغ {amount:,.2f}!")
                st.balloons()

                queue_state_updates(
                    delete_keys=(
                        "new_pay_date", "new_pay_time", "new_pay_party",
                        "new_pay_amount", "new_pay_method", "new_pay_ref",
                        "new_pay_notes", "new_pay_currency",
                    ),
                    set_values={
                        "new_pay_amount": 0.01,
                        "new_pay_ref": "",
                        "new_pay_notes": "",
                    },
                )
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 2: سجل المدفوعات (مع cache)
# ==========================================
with tab2:
    st.subheader("📋 سجل المدفوعات")

    # ✅ استدعاء واحد مخزّن بدل N+1
    payments_data = get_payments_index(limit=1000)

    if payments_data:
        data = []
        for idx, pay in enumerate(payments_data, start=1):
            data.append({
                "المسلسل": movement_serial("PAY", pay["id"]),
                "ID": pay["id"],
                "التاريخ": pay["date"].strftime("%Y-%m-%d %H:%M") if pay["date"] else "-",
                "النوع": "قبض" if pay["payment_type"] == "receipt" else "صرف",
                "العميل/المورد": pay["party_name"],
                "المبلغ": pay["amount"],
                "العملة": pay["currency_symbol"],
                "الطريقة": pay["payment_method"] or "-",
                "المرجع": pay["reference_number"] or "-",
                "الخزينة": pay["cash_box_name"],
            })

        df = pd.DataFrame(data)
        st.dataframe(
            df.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "المسلسل": st.column_config.TextColumn("المسلسل", width="small"),
                "المبلغ": st.column_config.NumberColumn("المبلغ", format="%.2f"),
            },
        )

        total_receipts = sum(
            p["amount"] for p in payments_data
            if p["payment_type"] == "receipt"
        )
        total_payments = sum(
            p["amount"] for p in payments_data
            if p["payment_type"] == "payment"
        )
        net_cash = total_receipts - total_payments

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("إجمالي المقبوضات", f"{total_receipts:,.2f} ج.م")
        with col2:
            st.metric("إجمالي المدفوعات", f"{total_payments:,.2f} ج.م")
        with col3:
            st.metric("صافي التدفق النقدي", f"{net_cash:,.2f} ج.م",
                      delta="زيادة" if net_cash >= 0 else "نقص",
                      delta_color="normal" if net_cash >= 0 else "inverse")
    else:
        st.info("لا توجد مدفوعات مسجلة.")


# ==========================================
# التبويب 3: تعديل/حذف دفعة
# ==========================================
with tab3:
    st.subheader("⚙️ تعديل / حذف دفعة")

    # ✅ استخدام cache للقوائم
    payments_data = get_payments_index(limit=1000)

    if not payments_data:
        st.info("لا توجد مدفوعات للتعديل.")
    else:
        payment_ids = [p["id"] for p in payments_data]
        payment_lookup = {p["id"]: p for p in payments_data}

        selected_payment_id = st.selectbox(
            "اختر دفعة (بالمسلسل):",
            options=payment_ids,
            format_func=lambda x: (
                f"{movement_serial('PAY', x)} — "
                f"{payment_lookup[x]['date'].strftime('%Y-%m-%d') if payment_lookup[x]['date'] else '?'} — "
                f"{payment_lookup[x]['amount']:,.2f} — "
                f"{payment_lookup[x]['party_name']}"
            ),
            key="sel_payment_edit",
        )

        if selected_payment_id:
            # جلب الكائن الفعلي من db (ليس من cache — لأننا سنعدّل)
            sel_pay = db.query(models.Payment).filter(
                models.Payment.id == selected_payment_id
            ).first()
            sel_party = db.query(models.Party).filter(
                models.Party.id == sel_pay.party_id
            ).first()
            sel_curr = db.query(models.Currency).filter(
                models.Currency.id == sel_pay.currency_id
            ).first()
            sym = sel_curr.symbol if sel_curr else "ج.م"

            st.markdown("### 📄 تفاصيل الدفعة المحددة")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("المبلغ", f"{sel_pay.amount:,.2f} {sym}")
            with col2:
                st.metric("النوع",
                          "قبض" if sel_pay.payment_type == "receipt" else "صرف")
            with col3:
                st.metric("التاريخ",
                          sel_pay.date.strftime("%Y-%m-%d") if sel_pay.date else "-")

            st.write(f"**العميل/المورد:** {sel_party.name if sel_party else 'غير محدد'}")
            st.write(f"**طريقة الدفع:** {sel_pay.payment_method}")
            st.write(f"**المرجع:** {sel_pay.reference_number or '-'}")
            st.write(f"**ملاحظات:** {sel_pay.notes or '-'}")

            st.markdown("---")
            col_edit, col_del = st.columns(2)

            # ===== التعديل =====
            with col_edit:
                st.markdown("#### ✏️ تعديل الدفعة")
                with st.form(f"edit_pay_form_{selected_payment_id}"):
                    new_amount = st.number_input(
                        "المبلغ الجديد:",
                        min_value=0.01,
                        value=float(sel_pay.amount or 0.01),
                        step=100.0, format="%.2f",
                    )
                    methods_list = ["cash", "bank_transfer", "check"]
                    current_idx = (methods_list.index(sel_pay.payment_method)
                                   if sel_pay.payment_method in methods_list else 0)
                    new_method = st.selectbox(
                        "طريقة الدفع:",
                        methods_list,
                        index=current_idx,
                    )
                    new_ref = st.text_input(
                        "رقم المرجع:",
                        value=sel_pay.reference_number or "",
                    )
                    new_notes = st.text_area(
                        "ملاحظات:",
                        value=sel_pay.notes or "",
                        height=80,
                    )
                    submitted = st.form_submit_button(
                        "💾 حفظ التعديلات", type="primary",
                    )

                if submitted:
                    try:
                        ref_marker = sel_pay.reference_number or str(sel_pay.id)
                        old_je = db.query(models.JournalEntry).filter(
                            models.JournalEntry.reference_type == "payment",
                            models.JournalEntry.description.contains(ref_marker),
                        ).first()
                        if old_je:
                            db.query(models.JournalLine).filter(
                                models.JournalLine.entry_id == old_je.id
                            ).delete(synchronize_session=False)
                            db.delete(old_je)

                        sel_pay.amount = new_amount
                        sel_pay.payment_method = new_method
                        sel_pay.reference_number = new_ref.strip() or None
                        sel_pay.notes = new_notes.strip() or None

                        cash_acc = db.query(models.Account).filter(
                            models.Account.code == "1101"
                        ).first()
                        if not cash_acc:
                            raise ValueError("حساب النقدية (1101) غير موجود")

                        je = models.JournalEntry(
                            date=sel_pay.date,
                            description=(f"دفعة {sel_pay.payment_type} لـ "
                                         f"{sel_party.name} - {new_ref or ''}"),
                            reference_type="payment",
                        )
                        db.add(je)
                        db.flush()

                        if sel_pay.payment_type == "receipt":
                            db.add(models.JournalLine(
                                entry_id=je.id, account_id=cash_acc.id,
                                debit=new_amount, credit=0.0,
                            ))
                            db.add(models.JournalLine(
                                entry_id=je.id, account_id=sel_party.account_id,
                                debit=0.0, credit=new_amount,
                            ))
                        else:
                            db.add(models.JournalLine(
                                entry_id=je.id, account_id=sel_party.account_id,
                                debit=new_amount, credit=0.0,
                            ))
                            db.add(models.JournalLine(
                                entry_id=je.id, account_id=cash_acc.id,
                                debit=0.0, credit=new_amount,
                            ))

                        db.commit()
                        invalidate_all()   # ✅
                        st.success("✅ تم التعديل بنجاح!")
                        queue_state_updates(delete_keys=("sel_payment_edit",))
                        st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ خطأ: {e}")

            # ===== الحذف =====
            with col_del:
                st.markdown("#### 🗑 حذف الدفعة")
                st.warning("⚠️ سيتم حذف الدفعة + القيد المحاسبي المرتبط.")
                confirm = st.checkbox(
                    "✅ أؤكد الحذف النهائي",
                    key=f"confirm_del_pay_{selected_payment_id}",
                )
                if st.button(
                    "🗑 حذف الدفعة",
                    type="secondary",
                    disabled=not confirm,
                    use_container_width=True,
                    key=f"del_pay_btn_{selected_payment_id}",
                ):
                    try:
                        _delete_payment_full(selected_payment_id)
                        invalidate_all()   # ✅
                        st.success("✅ تم الحذف.")
                        queue_state_updates(delete_keys=("sel_payment_edit",))
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")

db.close()