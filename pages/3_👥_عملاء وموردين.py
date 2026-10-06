# pages/3_👥_عملاء وموردين.py
import sys
import os
import tempfile
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify
render_sidebar()

import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from services import (
    create_party_with_opening_balance,
    import_parties_from_file,
    export_import_template,
    export_parties_to_excel,
)
from auth_required import require_login, get_current_user_id, get_current_user_name
from form_manager import clear_form, show_clear_hint

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

try:
    from keyboard_nav import enable_enter_navigation, add_enter_hint
    enable_enter_navigation()
    add_enter_hint()
except Exception:
    pass

st.set_page_config(page_title="العملاء والموردين", page_icon="👥", layout="wide")
st.title("👥 إدارة العملاء والموردين")
show_clear_hint()   # ✅ تلميح
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")


# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لمفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "pty_"


db = SessionLocal()


def _delete_party(party_id):
    """يحذف عميل/مورد + حسابه. يرفض لو له فواتير أو مدفوعات."""
    db_local = SessionLocal()
    try:
        p = db_local.query(models.Party).filter(models.Party.id == party_id).first()
        if not p:
            raise ValueError("العميل/المورد غير موجود")

        inv_count = db_local.query(models.Invoice).filter(
            models.Invoice.party_id == party_id
        ).count()
        pay_count = db_local.query(models.Payment).filter(
            models.Payment.party_id == party_id
        ).count()

        if inv_count > 0 or pay_count > 0:
            raise ValueError(
                f"لا يمكن الحذف: له {inv_count} فاتورة و {pay_count} دفعة. "
                "الحل: اتركه بدون حذف."
            )

        if p.account_id:
            db_local.query(models.JournalLine).filter(
                models.JournalLine.account_id == p.account_id
            ).delete(synchronize_session=False)

        if p.account_id:
            acc = db_local.query(models.Account).filter(
                models.Account.id == p.account_id
            ).first()
            if acc:
                db_local.delete(acc)

        db_local.delete(p)
        db_local.commit()
    except Exception:
        db_local.rollback()
        raise
    finally:
        db_local.close()


tab1, tab2, tab3 = st.tabs([
    "➕ إضافة جديد",
    "📋 القائمة",
    "📥 استيراد وتصدير",
])


# ==========================================
# التبويب 1: إضافة جديد
# ==========================================
with tab1:
    st.subheader("➕ إضافة عميل أو مورد")

    party_type = st.radio(
        "النوع:",
        ["customer (عميل)", "supplier (مورد)"],
        horizontal=True,
        key=f"{PFX}type",
    )
    actual_type = "customer" if "customer" in party_type else "supplier"
    type_ar = "عميل" if actual_type == "customer" else "مورد"

    name = st.text_input("الاسم", key=f"{PFX}name")
    phone = st.text_input("الهاتف", key=f"{PFX}phone")
    address = st.text_area("العنوان", key=f"{PFX}address")
    opening_balance = st.number_input(
        "الرصيد الافتتاحي", min_value=0.0, step=100.0,
        format="%.2f", key=f"{PFX}balance",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 حفظ", type="primary", use_container_width=True,
                     key=f"{PFX}save"):
            if not name.strip():
                st.error("❌ يرجى إدخال الاسم.")
            else:
                try:
                    create_party_with_opening_balance(
                        name.strip(), actual_type, opening_balance,
                        phone.strip() or None, address.strip() or None,
                        created_by=current_user_id,
                    )
                    st.success(f"✅ تم إضافة {type_ar} '{name}'!")
                    st.balloons()

                    # ✅ تفريغ كل الحقول
                    clear_form(PFX)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

    with col2:
        if st.button("🧹 مسح", use_container_width=True, key=f"{PFX}clear_btn"):
            clear_form(PFX)
            st.rerun()

    with col3:
        if st.button("❌ إلغاء", use_container_width=True, key=f"{PFX}cancel_btn"):
            clear_form(PFX)
            st.rerun()


# ==========================================
# التبويب 2: القائمة
# ==========================================
with tab2:
    st.subheader("📋 قائمة العملاء والموردين")

    parties = db.query(models.Party).order_by(models.Party.name).all()

    if parties:
        data = []
        for idx, p in enumerate(parties, start=1):
            data.append({
                "مسلسل": idx,
                "ID": p.id,
                "الاسم": p.name,
                "النوع": "عميل" if p.type == "customer" else "مورد",
                "الهاتف": p.phone or "-",
                "العنوان": p.address or "-",
            })
        df = pd.DataFrame(data)
        st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("⚙️ تعديل / حذف")

        party_ids = [p.id for p in parties]
        selected_party_id = st.selectbox(
            "اختر عميل/مورد:",
            options=party_ids,
            format_func=lambda x: next(
                (f"{p.name} — ({'عميل' if p.type == 'customer' else 'مورد'})"
                 for p in parties if p.id == x),
                str(x)),
            key=f"{PFX}edit_select",   # ✅
        )

        if selected_party_id:
            sel_party = next((p for p in parties if p.id == selected_party_id), None)

            inv_count = db.query(models.Invoice).filter(
                models.Invoice.party_id == selected_party_id
            ).count()
            pay_count = db.query(models.Payment).filter(
                models.Payment.party_id == selected_party_id
            ).count()
            is_used = inv_count > 0 or pay_count > 0

            st.markdown(f"### 📄 تفاصيل: **{sel_party.name}**")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("النوع", "عميل" if sel_party.type == "customer" else "مورد")
            with c2:
                st.metric("الفواتير", inv_count)
            with c3:
                st.metric("المدفوعات", pay_count)

            col_edit, col_del = st.columns(2)

            # ===== التعديل =====
            with col_edit:
                st.markdown("#### ✏️ تعديل البيانات")
                with st.form(f"{PFX}edit_form_{selected_party_id}"):
                    new_name = st.text_input("الاسم:", value=sel_party.name,
                                             key=f"{PFX}edit_name_{selected_party_id}")
                    new_phone = st.text_input("الهاتف:", value=sel_party.phone or "",
                                              key=f"{PFX}edit_phone_{selected_party_id}")
                    new_address = st.text_area("العنوان:",
                                                value=sel_party.address or "",
                                                height=80,
                                                key=f"{PFX}edit_address_{selected_party_id}")
                    submitted = st.form_submit_button("💾 حفظ التعديلات",
                                                       type="primary")

                if submitted:
                    try:
                        if not new_name.strip():
                            st.error("❌ الاسم مطلوب.")
                        else:
                            sel_party.name = new_name.strip()
                            sel_party.phone = new_phone.strip() or None
                            sel_party.address = new_address.strip() or None

                            if sel_party.account_id:
                                acc = db.query(models.Account).filter(
                                    models.Account.id == sel_party.account_id
                                ).first()
                                if acc:
                                    acc.name = new_name.strip()
                            db.commit()
                            st.success("✅ تم التعديل!")

                            # ✅ تفريغ كل مفاتيح التعديل
                            clear_form(PFX)
                            st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ خطأ: {e}")

            # ===== الحذف =====
            with col_del:
                st.markdown("#### 🗑 حذف")
                if is_used:
                    st.error(
                        f"⛔ لا يمكن الحذف: له **{inv_count}** فاتورة "
                        f"و **{pay_count}** دفعة."
                    )
                    st.info("💡 الحل: احتفظ به بدون حذف.")
                else:
                    st.warning(f"⚠️ سيتم حذف **{sel_party.name}** نهائيًا.")
                    confirm = st.checkbox(
                        "✅ أؤكد الحذف النهائي",
                        key=f"{PFX}confirm_del_{selected_party_id}",
                    )
                    if st.button(
                        "🗑 حذف",
                        type="secondary",
                        disabled=not confirm,
                        use_container_width=True,
                        key=f"{PFX}del_btn_{selected_party_id}",
                    ):
                        try:
                            _delete_party(selected_party_id)
                            st.success("✅ تم الحذف.")

                            # ✅ تفريغ كل مفاتيح الصفحة
                            clear_form(PFX)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ خطأ: {e}")
    else:
        st.info("لا يوجد عملاء أو موردين.")


# ==========================================
# التبويب 3: استيراد وتصدير
# ==========================================
with tab3:
    st.subheader("📤 تصدير")
    export_type = st.radio(
        "نوع التصدير:",
        ["customer (عملاء)", "supplier (موردين)"],
        horizontal=True,
        key=f"{PFX}export_type",
    )
    actual_export_type = "customer" if "customer" in export_type else "supplier"

    if st.button("📤 تصدير إلى Excel", type="primary",
                 key=f"{PFX}export_btn"):
        try:
            output_path, count = export_parties_to_excel(actual_export_type)
            st.success(f"✅ تم تصدير {count} سجل!")
            with open(output_path, "rb") as file:
                st.download_button(label="⬇️ تحميل", data=file,
                                   file_name=output_path)
        except Exception as e:
            st.error(f"❌ خطأ: {e}")

    st.markdown("---")
    st.subheader("📥 استيراد")

    import_type = st.radio(
        "نوع الاستيراد:",
        ["customer (عملاء)", "supplier (موردين)"],
        key=f"{PFX}import_type",
    )
    actual_import_type = "customer" if "customer" in import_type else "supplier"

    uploaded_file = st.file_uploader(
        "اختر ملف:", type=["xlsx", "csv"],
        key=f"{PFX}upload_file",
    )

    if uploaded_file:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=os.path.splitext(uploaded_file.name)[1],
        ) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        if st.button("📥 استيراد", type="primary", key=f"{PFX}import_btn"):
            try:
                count, errors = import_parties_from_file(
                    tmp_path, actual_import_type, created_by=current_user_id
                )
                st.success(f"✅ تم استيراد {count}!")
                if errors:
                    for err in errors[:5]:
                        st.write(f"- {err}")

                # ✅ تفريغ حقل الرفع
                clear_form(PFX)
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
            finally:
                os.unlink(tmp_path)

db.close()