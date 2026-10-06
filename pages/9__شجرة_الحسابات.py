# pages/9_📚_شجرة_الحسابات.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify
render_sidebar()

import streamlit as st
import pandas as pd
from sqlalchemy import func
from database import SessionLocal
import models
from models import AccountType, Account, Party, CashBox, ExpenseCategory
from auth_required import require_login

current_user = require_login()

st.set_page_config(page_title="شجرة الحسابات", page_icon="📚", layout="wide")
st.title("📚 إدارة شجرة الحسابات")

try:
    from keyboard_nav import enable_enter_navigation, add_enter_hint
    enable_enter_navigation()
    add_enter_hint()
except Exception:
    pass

db = SessionLocal()


# ==========================================
# دوال مساعدة
# ==========================================
def _account_usage(account_id):
    """يرجع dict بكل استخدامات الحساب."""
    sub_count = db.query(Account).filter(Account.parent_id == account_id).count()
    jl_count = db.query(models.JournalLine).filter(
        models.JournalLine.account_id == account_id
    ).count()
    party_count = db.query(Party).filter(Party.account_id == account_id).count()
    cashbox_count = db.query(CashBox).filter(CashBox.account_id == account_id).count()
    expcat_count = db.query(ExpenseCategory).filter(
        ExpenseCategory.account_id == account_id
    ).count()
    item_inv = db.query(models.Item).filter(
        models.Item.inventory_account_id == account_id
    ).count()
    item_cogs = db.query(models.Item).filter(
        models.Item.cogs_account_id == account_id
    ).count()
    item_rev = db.query(models.Item).filter(
        models.Item.revenue_account_id == account_id
    ).count()

    return {
        "sub_accounts": sub_count,
        "journal_lines": jl_count,
        "parties": party_count,
        "cash_boxes": cashbox_count,
        "expense_categories": expcat_count,
        "items": item_inv + item_cogs + item_rev,
    }


def _is_used(usage):
    return any(v > 0 for v in usage.values())


def _balance_for(account_id):
    debit_total = float(db.query(func.sum(models.JournalLine.debit)).filter(
        models.JournalLine.account_id == account_id
    ).scalar() or 0)
    credit_total = float(db.query(func.sum(models.JournalLine.credit)).filter(
        models.JournalLine.account_id == account_id
    ).scalar() or 0)
    return debit_total, credit_total, debit_total - credit_total


def _flatten_tree(all_accounts, parent_id=None, depth=0):
    """يرجع list من الأبناء (recursive) مع معلومات العمق."""
    children = sorted(
        [a for a in all_accounts if a.parent_id == parent_id],
        key=lambda x: x.code,
    )
    rows = []
    for child in children:
        rows.append((child, depth))
        rows.extend(_flatten_tree(all_accounts, child.id, depth + 1))
    return rows


# ==========================================
# التبويبات
# ==========================================
tab1, tab2 = st.tabs(["➕ إضافة حساب جديد", "🌳 عرض شجرة الحسابات"])


# ==========================================
# تبويب 1: إضافة حساب جديد
# ==========================================
with tab1:
    st.subheader("➕ إضافة حساب جديد")
    st.caption("💡 بعد الحفظ، الحقول هتتفرّغ تلقائيًا عشان تقدر تدخل حساب تاني فورًا.")

    account_type = st.selectbox(
        "نوع الحساب:",
        options=[acc_type.value for acc_type in AccountType],
        key="new_acc_type",
    )

    parent_accounts = db.query(Account).filter(
        Account.type == AccountType(account_type)
    ).order_by(Account.code).all()

    parent_options = {"بدون (حساب رئيسي)": None}
    for acc in parent_accounts:
        parent_options[f"{acc.code} - {acc.name}"] = acc.id

    selected_parent = st.selectbox(
        "الحساب الأب:",
        options=list(parent_options.values()),
        format_func=lambda x: next(
            (k for k, v in parent_options.items() if v == x), "بدون"
        ),
        key="new_acc_parent",
    )

    code = st.text_input("كود الحساب:", placeholder="مثال: 1103", key="new_acc_code")
    name = st.text_input("اسم الحساب:", placeholder="مثال: صندوق فرعي", key="new_acc_name")

    if st.button("💾 حفظ الحساب", type="primary", use_container_width=True):
        if not code or not name:
            st.error("❌ يرجى ملء كود واسم الحساب.")
        else:
            try:
                existing = db.query(Account).filter(Account.code == code.strip()).first()
                if existing:
                    st.error(f"❌ الكود {code} مستخدم بالفعل في الحساب '{existing.name}'.")
                else:
                    new_account = Account(
                        code=code.strip(),
                        name=name.strip(),
                        type=AccountType(account_type),
                        parent_id=selected_parent,
                    )
                    db.add(new_account)
                    db.commit()

                    st.success(f"✅ تم إضافة الحساب '{name}' بنجاح!")
                    st.balloons()

                    # ✅ تفريغ الحقول تلقائيًا (يُطبَّق في الـ run القادم)
                    queue_state_updates(
                        delete_keys=("new_acc_code", "new_acc_name", "new_acc_parent"),
                        set_values={
                            "new_acc_type": AccountType.ASSET.value,
                            "new_acc_parent": None,
                        },
                    )
                    st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"❌ خطأ: {e}")


# ==========================================
# تبويب 2: عرض شجرة الحسابات + تعديل/حذف
# ==========================================
with tab2:
    st.subheader("🌳 شجرة الحسابات")

    all_accounts = db.query(Account).order_by(Account.code).all()

    if not all_accounts:
        st.info("لا توجد حسابات بعد.")
    else:
        # ---------- عرض الشجرة ----------
        main_accounts = [a for a in all_accounts if a.parent_id is None]

        for main_acc in main_accounts:
            _, _, main_bal = _balance_for(main_acc.id)
            with st.expander(
                f"📁 {main_acc.code} - {main_acc.name} ({main_acc.type.value})  —  رصيد: {main_bal:,.2f}",
                expanded=False,
            ):
                descendants = _flatten_tree(all_accounts, parent_id=main_acc.id, depth=1)
                if not descendants:
                    st.info("لا توجد حسابات فرعية.")
                else:
                    rows = []
                    for acc, depth in descendants:
                        indent = ("    " * (depth - 1)) + "└ " if depth > 1 else ""
                        d_, c_, b_ = _balance_for(acc.id)
                        rows.append({
                            "الكود": acc.code,
                            "الاسم": f"{indent}{acc.name}",
                            "مدين": d_,
                            "دائن": c_,
                            "الرصيد": b_,
                        })
                    df = pd.DataFrame(rows)
                    st.dataframe(
                        df, use_container_width=True, hide_index=True,
                        column_config={
                            "مدين": st.column_config.NumberColumn("مدين", format="%.2f"),
                            "دائن": st.column_config.NumberColumn("دائن", format="%.2f"),
                            "الرصيد": st.column_config.NumberColumn("الرصيد", format="%.2f"),
                        },
                    )

        st.markdown("---")

        # ---------- قسم التعديل والحذف ----------
        st.subheader("⚙️ تعديل / حذف حساب")

        account_ids = [a.id for a in all_accounts]
        selected_account_id = st.selectbox(
            "اختر حساباً:",
            options=account_ids,
            format_func=lambda x: next(
                (f"{a.code} - {a.name}" for a in all_accounts if a.id == x),
                str(x),
            ),
            key="sel_account_for_edit",
        )

        if selected_account_id:
            selected = next(
                (a for a in all_accounts if a.id == selected_account_id), None
            )
            usage = _account_usage(selected_account_id)
            used = _is_used(usage)

            # عرض معلومات الاستخدام
            st.markdown("#### 📊 معلومات الاستخدام")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("حسابات فرعية", usage["sub_accounts"])
                st.metric("قيود يومية", usage["journal_lines"])
            with c2:
                st.metric("عملاء/موردين", usage["parties"])
                st.metric("خزائن", usage["cash_boxes"])
            with c3:
                st.metric("تصنيفات مصروفات", usage["expense_categories"])
                st.metric("أصناف", usage["items"])

            st.markdown("---")

            # =========== التعديل ===========
            st.markdown("#### ✏️ تعديل الحساب")

            if usage["journal_lines"] > 0:
                st.warning("⚠️ لا يمكن التعديل — الحساب مستخدم في قيود يومية.")
            else:
                with st.form(f"edit_form_{selected_account_id}"):
                    new_code = st.text_input("الكود الجديد:", value=selected.code)
                    new_name = st.text_input("الاسم الجديد:", value=selected.name)
                    submitted = st.form_submit_button(
                        "💾 حفظ التعديلات", type="primary"
                    )

                if submitted:
                    try:
                        if not new_code.strip() or not new_name.strip():
                            st.error("❌ الكود والاسم مطلوبان.")
                        else:
                            dup = db.query(Account).filter(
                                Account.code == new_code.strip(),
                                Account.id != selected_account_id,
                            ).first()
                            if dup:
                                st.error(f"❌ الكود '{new_code}' مستخدم بالفعل في حساب آخر.")
                            else:
                                selected.code = new_code.strip()
                                selected.name = new_name.strip()
                                db.commit()
                                st.success("✅ تم تحديث الحساب بنجاح!")
                                st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ خطأ: {e}")

            st.markdown("---")

            # =========== الحذف ===========
            st.markdown("#### 🗑️ حذف الحساب")

            if used:
                st.error("⛔ **لا يمكن حذف هذا الحساب** للأسباب التالية:")
                if usage["sub_accounts"] > 0:
                    st.write(f"• 🔸 يحتوي على **{usage['sub_accounts']}** حساب فرعي")
                if usage["journal_lines"] > 0:
                    st.write(f"• 🔸 مستخدم في **{usage['journal_lines']}** قيد يومية")
                if usage["parties"] > 0:
                    st.write(f"• 🔸 مرتبط بـ **{usage['parties']}** عميل/مورد")
                if usage["cash_boxes"] > 0:
                    st.write(f"• 🔸 مرتبط بـ **{usage['cash_boxes']}** خزينة")
                if usage["expense_categories"] > 0:
                    st.write(f"• 🔸 مرتبط بـ **{usage['expense_categories']}** تصنيف مصروفات")
                if usage["items"] > 0:
                    st.write(f"• 🔸 مرتبط بـ **{usage['items']}** صنف")

                st.info("💡 **الحل:** احذف الارتباطات أولاً، أو استخدم حساب آخر.")
            else:
                st.warning(
                    f"⚠️ سيتم حذف الحساب **{selected.code} - {selected.name}** نهائيًا."
                )
                confirm = st.checkbox(
                    "✅ أؤكد الحذف النهائي",
                    key=f"confirm_del_{selected_account_id}",
                )

                if st.button(
                    "🗑️ حذف الحساب نهائيًا",
                    type="secondary",
                    disabled=not confirm,
                    use_container_width=True,
                    key=f"del_btn_{selected_account_id}",
                ):
                    try:
                        deleted_name = selected.name
                        db.delete(selected)
                        db.commit()

                        st.success(f"✅ تم حذف الحساب '{deleted_name}' نهائيًا!")

                        # ✅ تفريغ الاختيار تلقائيًا
                        queue_state_updates(
                            delete_keys=(
                                "sel_account_for_edit",
                                f"confirm_del_{selected_account_id}",
                            ),
                        )
                        st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ خطأ: {e}")

db.close()