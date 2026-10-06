# pages/7_💱_العملات.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify
render_sidebar()

import streamlit as st
import pandas as pd
from database import SessionLocal
import models
from auth_required import require_login, get_current_user_id, get_current_user_name
from form_manager import clear_form, show_clear_hint

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="إدارة العملات", page_icon="💱", layout="wide")
st.title("💱 إدارة العملات")
show_clear_hint()   # ✅ تلميح
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")


# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لمفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "cur_"


try:
    from keyboard_nav import enable_enter_navigation, add_enter_hint
    enable_enter_navigation()
    add_enter_hint()
except Exception:
    pass


db = SessionLocal()


tab1, tab2 = st.tabs(["➕ إضافة عملة جديدة", "📋 قائمة العملات"])


# ==========================================
# التبويب 1: إضافة عملة جديدة
# ==========================================
with tab1:
    st.subheader("إضافة عملة جديدة")

    code = st.text_input(
        "كود العملة (مثال: USD, EUR, SAR)",
        placeholder="USD",
        key=f"{PFX}new_code",   # ✅
    )
    name = st.text_input(
        "اسم العملة (مثال: دولار أمريكي)",
        placeholder="دولار أمريكي",
        key=f"{PFX}new_name",   # ✅
    )
    symbol = st.text_input(
        "رمز العملة (مثال: $, €, ر.س)",
        placeholder="$",
        key=f"{PFX}new_symbol",   # ✅
    )
    exchange_rate = st.number_input(
        "سعر الصرف بالنسبة للجنيه المصري",
        min_value=0.01, step=0.1, value=1.0,
        key=f"{PFX}new_rate",   # ✅
    )
    is_default = st.checkbox(
        "اجعلها العملة الافتراضية",
        key=f"{PFX}new_default",   # ✅
    )

    if st.button("💾 حفظ العملة", type="primary", key=f"{PFX}new_save"):
        if not code or not name or not symbol:
            st.error("❌ يرجى ملء جميع الحقول")
        else:
            try:
                existing = db.query(models.Currency).filter(
                    models.Currency.code == code.upper()
                ).first()
                if existing:
                    st.error("❌ هذه العملة موجودة مسبقاً!")
                else:
                    if is_default:
                        db.query(models.Currency).update({
                            models.Currency.is_default: False
                        })

                    new_currency = models.Currency(
                        code=code.upper(),
                        name=name.strip(),
                        symbol=symbol.strip(),
                        exchange_rate=exchange_rate,
                        is_default=is_default,
                    )
                    db.add(new_currency)
                    db.commit()
                    st.success(f"✅ تم إضافة العملة '{name}' بنجاح!")

                    # ✅ تفريغ كل حقول النموذج
                    clear_form(PFX)
                    st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 2: قائمة العملات
# ==========================================
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
                "افتراضية": "نعم" if curr.is_default else "لا",
            })

        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("⚙️ تعديل/حذف عملة")

        currency_ids = [curr.id for curr in currencies]

        selected_currency_id = st.selectbox(
            "اختر عملة:",
            options=currency_ids,
            format_func=lambda x: next(
                (curr.code for curr in currencies if curr.id == x), str(x)
            ),
            key=f"{PFX}edit_select",   # ✅
        )

        if selected_currency_id:
            selected_currency = db.query(models.Currency).filter(
                models.Currency.id == selected_currency_id
            ).first()

            col1, col2 = st.columns(2)

            with col1:
                new_exchange_rate = st.number_input(
                    "سعر الصرف الجديد:",
                    value=float(selected_currency.exchange_rate or 1.0),
                    step=0.1,
                    key=f"{PFX}edit_rate_{selected_currency_id}",   # ✅
                )
                new_is_default = st.checkbox(
                    "اجعلها افتراضية",
                    value=bool(selected_currency.is_default),
                    key=f"{PFX}edit_default_{selected_currency_id}",   # ✅
                )

                if st.button(
                    "💾 حفظ التعديلات",
                    type="primary",
                    key=f"{PFX}edit_save_{selected_currency_id}",
                ):
                    try:
                        if new_is_default:
                            db.query(models.Currency).update({
                                models.Currency.is_default: False
                            })

                        selected_currency.exchange_rate = new_exchange_rate
                        selected_currency.is_default = new_is_default
                        db.commit()
                        st.success("✅ تم تحديث العملة بنجاح!")

                        # ✅ تفريغ كل مفاتيح التعديل
                        clear_form(PFX)
                        st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ خطأ: {e}")

            with col2:
                st.markdown("**🗑 حذف العملة**")
                if not can_modify():
                    st.info("⛔ الحذف للمدير فقط.")
                else:
                    confirm_del = st.checkbox(
                        "تأكيد الحذف؟",
                        key=f"{PFX}confirm_del_{selected_currency_id}",   # ✅
                    )
                    if st.button(
                        "🗑️ حذف العملة",
                        type="secondary",
                        disabled=not confirm_del,
                        key=f"{PFX}del_btn_{selected_currency_id}",   # ✅
                    ):
                        try:
                            # منع حذف العملة الافتراضية
                            if selected_currency.is_default:
                                st.error("❌ لا يمكن حذف العملة الافتراضية!")
                            else:
                                db.delete(selected_currency)
                                db.commit()
                                st.success("✅ تم حذف العملة بنجاح!")

                                # ✅ تفريغ كل مفاتيح الصفحة
                                clear_form(PFX)
                                st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"❌ خطأ: {e}")
    else:
        st.info("لا توجد عملات.")

db.close()