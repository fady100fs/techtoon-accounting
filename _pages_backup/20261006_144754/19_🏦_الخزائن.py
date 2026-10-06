# pages/19_🏦_الخزائن.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify
render_sidebar()

import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import func
from database import SessionLocal
import models
from models import CashBox, CashBoxType, CashTransfer
from services import create_cash_box, get_cash_box_balance, transfer_between_cash_boxes
from auth_required import require_login, get_current_user_id, get_current_user_name

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="الخزائن", page_icon="🏦", layout="wide")
st.title("🏦 إدارة الخزائن والحسابات البنكية")
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💰 أرصدة الخزائن",
    "➕ إضافة خزينة جديدة",
    "🔄 تحويل بين الخزائن",
    "⚙️ تعديل/حذف الخزائن",
    "📋 سجل التحويلات",
])


# ==========================================
# التبويب 1: أرصدة الخزائن
# ==========================================
with tab1:
    st.subheader("📊 أرصدة الخزائن الحالية")

    cash_boxes = db.query(CashBox).all()

    if cash_boxes:
        cols = st.columns(min(len(cash_boxes), 4))
        total_balance = 0.0

        for idx, box in enumerate(cash_boxes):
            if not box.is_active:
                continue
            balance = get_cash_box_balance(box.id)
            total_balance += balance
            col_idx = idx % 4
            with cols[col_idx]:
                type_icon = {"نقدية": "💵", "بنك": "🏦",
                             "محفظة إلكترونية": "📱", "أخرى": "💼"}.get(
                    box.type.value, "💰")
                st.metric(f"{type_icon} {box.name}", f"{balance:,.2f} ج.م")

        st.markdown("---")
        st.metric("إجمالي جميع الخزائن", f"{total_balance:,.2f} ج.م")

        st.markdown("---")
        st.subheader("📋 تفاصيل الخزائن")

        data = []
        for idx, box in enumerate(cash_boxes, start=1):
            balance = get_cash_box_balance(box.id)
            account = db.query(models.Account).filter(
                models.Account.id == box.account_id
            ).first()
            data.append({
                "مسلسل": idx,
                "الكود": box.code,
                "الاسم": box.name,
                "النوع": box.type.value,
                "الحساب": account.name if account else "-",
                "المسؤول": box.responsible_person or "-",
                "الرصيد": float(balance),
                "الحالة": "✅ نشط" if box.is_active else "⛔ معطل",
            })
        st.dataframe(
            pd.DataFrame(data), use_container_width=True, hide_index=True,
            column_config={
                "الرصيد": st.column_config.NumberColumn("الرصيد", format="%.2f"),
            },
        )
    else:
        st.warning("⚠️ لا توجد خزائن. أضف خزينة من التبويب التالي.")


# ==========================================
# التبويب 2: إضافة خزينة جديدة
# ==========================================
with tab2:
    st.subheader("➕ إضافة خزينة جديدة")
    st.caption("💡 بعد الحفظ، الحقول هتتفرّغ تلقائيًا.")

    box_name = st.text_input(
        "اسم الخزينة:",
        placeholder="مثال: الخزينة الرئيسية، بنك الأهلي...",
        key="new_box_name",
    )
    box_code = st.text_input(
        "كود الخزينة:",
        placeholder="مثال: CB001, BANK01...",
        key="new_box_code",
    )

    box_type = st.selectbox(
        "نوع الخزينة:",
        options=[t.value for t in CashBoxType],
        key="new_box_type",
    )

    responsible_person = st.text_input(
        "الشخص المسؤول (اختياري):",
        placeholder="اسم أمين الصندوق...",
        key="new_box_responsible",
    )
    max_limit = st.number_input(
        "الحد الأقصى للرصيد (اختياري):",
        min_value=0.0, step=1000.0, key="new_box_max",
    )
    notes = st.text_area("ملاحظات (اختياري):", key="new_box_notes")

    if st.button("💾 إنشاء الخزينة", type="primary", use_container_width=True):
        if not box_name.strip() or not box_code.strip():
            st.error("❌ يرجى إدخال اسم وكود الخزينة.")
        else:
            try:
                current_assets = db.query(models.Account).filter(
                    models.Account.code == "1100"
                ).first()

                if not current_assets:
                    assets_parent = db.query(models.Account).filter(
                        models.Account.code == "1000"
                    ).first()
                    if assets_parent:
                        current_assets = models.Account(
                            code="1100", name="الأصول المتداولة",
                            type=models.AccountType.ASSET,
                            parent_id=assets_parent.id,
                        )
                        db.add(current_assets)
                        db.commit()

                account_code = f"11{box_code.zfill(4)}"
                cash_account = models.Account(
                    code=account_code, name=box_name,
                    type=models.AccountType.ASSET,
                    parent_id=current_assets.id if current_assets else None,
                )
                db.add(cash_account)
                db.commit()

                actual_type = next(t for t in CashBoxType if t.value == box_type)

                create_cash_box(
                    name=box_name, code=box_code, box_type=actual_type,
                    account_id=cash_account.id,
                    responsible_person=responsible_person or None,
                    max_limit=max_limit if max_limit > 0 else None,
                    notes=notes or None,
                    created_by=current_user_id,
                )

                st.success(f"✅ تم إنشاء الخزينة '{box_name}'!")
                st.balloons()

                queue_state_updates(
                    delete_keys=(
                        "new_box_name", "new_box_code", "new_box_responsible",
                        "new_box_max", "new_box_notes",
                    ),
                    set_values={
                        "new_box_name": "",
                        "new_box_code": "",
                        "new_box_responsible": "",
                        "new_box_max": 0.0,
                        "new_box_notes": "",
                    },
                )
                st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 3: تحويل بين الخزائن
# ==========================================
with tab3:
    st.subheader("🔄 تحويل مبلغ بين خزينتين")
    st.caption("💡 بعد التحويل، الحقول هتتفرّغ تلقائيًا.")

    cash_boxes = db.query(CashBox).filter(CashBox.is_active == True).all()

    if len(cash_boxes) < 2:
        st.warning("⚠️ يجب وجود خزينتين نشطتين على الأقل.")
    else:
        box_options = {b.id: f"{b.name} ({b.code})" for b in cash_boxes}

        col1, col2 = st.columns(2)
        with col1:
            from_box_id = st.selectbox(
                "من خزينة:",
                options=list(box_options.keys()),
                format_func=lambda x: box_options[x],
                key="from_box",
            )
            from_balance = get_cash_box_balance(from_box_id)
            st.info(f"💰 الرصيد: {from_balance:,.2f} ج.م")

        with col2:
            to_box_id = st.selectbox(
                "إلى خزينة:",
                options=list(box_options.keys()),
                format_func=lambda x: box_options[x],
                key="to_box",
            )
            to_balance = get_cash_box_balance(to_box_id)
            st.info(f"💰 الرصيد: {to_balance:,.2f} ج.م")

        transfer_amount = st.number_input(
            "مبلغ التحويل:", min_value=0.01, step=100.0,
            format="%.2f", key="transfer_amount",
        )
        transfer_notes = st.text_area("ملاحظات (اختياري):", key="transfer_notes")

        if st.button("🔄 تنفيذ التحويل", type="primary", use_container_width=True):
            if from_box_id == to_box_id:
                st.error("❌ لا يمكن التحويل بين نفس الخزينة.")
            elif transfer_amount <= 0:
                st.error("❌ مبلغ غير صحيح.")
            elif transfer_amount > from_balance:
                st.error(f"❌ الرصيد غير كافٍ! المتاح: {from_balance:,.2f}")
            else:
                try:
                    transfer_between_cash_boxes(
                        from_cash_box_id=from_box_id,
                        to_cash_box_id=to_box_id,
                        amount=transfer_amount,
                        notes=transfer_notes or None,
                        created_by=current_user_id,
                    )
                    st.success(f"✅ تم التحويل: {transfer_amount:,.2f} ج.م")
                    st.balloons()

                    queue_state_updates(
                        delete_keys=(
                            "from_box", "to_box", "transfer_amount",
                            "transfer_notes",
                        ),
                        set_values={
                            "transfer_amount": 0.01,
                            "transfer_notes": "",
                        },
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 4: تعديل/حذف الخزائن
# ==========================================
with tab4:
    st.subheader("⚙️ تعديل وحذف الخزائن")

    cash_boxes = db.query(CashBox).all()

    if not cash_boxes:
        st.info("لا توجد خزائن.")
    else:
        box_options = {b.id: f"{b.name} ({b.code}) - {b.type.value}"
                       for b in cash_boxes}

        selected_box_id = st.selectbox(
            "اختر خزينة:",
            options=list(box_options.keys()),
            format_func=lambda x: box_options[x],
            key="select_box_edit",
        )

        if selected_box_id:
            selected_box = db.query(CashBox).filter(
                CashBox.id == selected_box_id
            ).first()

            if selected_box:
                current_balance = get_cash_box_balance(selected_box.id)
                account = db.query(models.Account).filter(
                    models.Account.id == selected_box.account_id
                ).first()

                st.markdown("### 📄 معلومات الخزينة")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("الرصيد", f"{current_balance:,.2f} ج.م")
                with col2:
                    st.metric("النوع", selected_box.type.value)
                with col3:
                    st.metric("الحالة",
                              "نشط" if selected_box.is_active else "معطل")

                col_edit, col_del = st.columns(2)

                # ===== التعديل =====
                with col_edit:
                    st.markdown("#### ✏️ تعديل البيانات")
                    with st.form(f"edit_box_form_{selected_box_id}"):
                        new_name = st.text_input("الاسم:",
                                                  value=selected_box.name)
                        new_responsible = st.text_input(
                            "المسؤول:",
                            value=selected_box.responsible_person or "",
                        )
                        new_max_limit = st.number_input(
                            "الحد الأقصى:",
                            min_value=0.0,
                            value=float(selected_box.max_limit or 0),
                            step=1000.0,
                        )
                        new_notes = st.text_area(
                            "ملاحظات:",
                            value=selected_box.notes or "",
                            height=80,
                        )
                        new_is_active = st.checkbox(
                            "خزينة نشطة",
                            value=selected_box.is_active,
                        )
                        submitted = st.form_submit_button(
                            "💾 حفظ التعديلات", type="primary",
                        )

                    if submitted:
                        try:
                            if not new_name.strip():
                                st.error("❌ الاسم مطلوب.")
                            else:
                                selected_box.name = new_name.strip()
                                selected_box.responsible_person = (
                                    new_responsible.strip() or None
                                )
                                selected_box.max_limit = (
                                    new_max_limit if new_max_limit > 0 else None
                                )
                                selected_box.notes = new_notes.strip() or None
                                selected_box.is_active = new_is_active
                                if account:
                                    account.name = new_name.strip()
                                db.commit()
                                st.success("✅ تم التعديل.")
                                queue_state_updates(
                                    delete_keys=("select_box_edit",)
                                )
                                st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"❌ خطأ: {e}")

                # ===== الحذف =====
                with col_del:
                    st.markdown("#### 🗑 حذف / تعطيل")

                    transfers_count = db.query(CashTransfer).filter(
                        (CashTransfer.from_cash_box_id == selected_box_id) |
                        (CashTransfer.to_cash_box_id == selected_box_id)
                    ).count()

                    payments_count = db.query(models.Payment).filter(
                        models.Payment.cash_box_id == selected_box_id
                    ).count()

                    st.write(f"**التحويلات:** {transfers_count}")
                    st.write(f"**المدفوعات:** {payments_count}")

                    if selected_box.is_active:
                        if st.button("⛔ تعطيل الخزينة",
                                     use_container_width=True,
                                     key=f"disable_box_{selected_box_id}"):
                            try:
                                selected_box.is_active = False
                                db.commit()
                                st.success("✅ تم التعطيل.")
                                queue_state_updates(
                                    delete_keys=("select_box_edit",)
                                )
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"❌ {e}")
                    else:
                        if st.button("✅ تفعيل الخزينة",
                                     use_container_width=True,
                                     key=f"enable_box_{selected_box_id}"):
                            try:
                                selected_box.is_active = True
                                db.commit()
                                st.success("✅ تم التفعيل.")
                                queue_state_updates(
                                    delete_keys=("select_box_edit",)
                                )
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"❌ {e}")

                    st.markdown("---")

                    # التحقق قبل الحذف
                    can_delete = True
                    reasons = []
                    if abs(current_balance) > 0.01:
                        can_delete = False
                        reasons.append(f"رصيد: {current_balance:,.2f} ج.م")
                    if transfers_count > 0:
                        can_delete = False
                        reasons.append(f"{transfers_count} تحويل")
                    if payments_count > 0:
                        can_delete = False
                        reasons.append(f"{payments_count} دفعة")

                    if not can_delete:
                        st.error("⛔ لا يمكن الحذف:")
                        for r in reasons:
                            st.write(f"- {r}")
                        st.info("💡 الحل: عطّل الخزينة.")
                    else:
                        st.warning("⚠️ الحذف نهائي!")
                        confirm = st.checkbox(
                            "✅ أؤكد الحذف",
                            key=f"confirm_del_box_{selected_box_id}",
                        )
                        if st.button(
                            "🗑 حذف الخزينة",
                            type="secondary",
                            disabled=not confirm,
                            use_container_width=True,
                            key=f"del_box_btn_{selected_box_id}",
                        ):
                            try:
                                if account:
                                    db.delete(account)
                                db.delete(selected_box)
                                db.commit()
                                st.success("✅ تم الحذف.")
                                queue_state_updates(
                                    delete_keys=("select_box_edit",)
                                )
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"❌ {e}")


# ==========================================
# التبويب 5: سجل التحويلات
# ==========================================
with tab5:
    st.subheader("📋 سجل التحويلات بين الخزائن")

    transfers = db.query(CashTransfer).order_by(
        CashTransfer.date.desc()
    ).all()

    if transfers:
        box_map = {b.id: b.name for b in db.query(CashBox).all()}

        data = []
        for idx, t in enumerate(transfers, start=1):
            data.append({
                "مسلسل": idx,
                "التاريخ": t.date.strftime("%Y-%m-%d %H:%M") if t.date else "-",
                "من": box_map.get(t.from_cash_box_id, "-"),
                "إلى": box_map.get(t.to_cash_box_id, "-"),
                "المبلغ": float(t.amount or 0),
                "ملاحظات": t.notes or "-",
            })

        st.dataframe(
            pd.DataFrame(data), use_container_width=True, hide_index=True,
            column_config={
                "المبلغ": st.column_config.NumberColumn("المبلغ", format="%.2f"),
            },
        )
        total = sum(t.amount for t in transfers)
        st.metric("إجمالي التحويلات", f"{total:,.2f} ج.م")
    else:
        st.info("لا توجد تحويلات مسجلة.")

db.close()