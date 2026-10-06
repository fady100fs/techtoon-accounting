# pages/20_🗂️_التصنيفات.py
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
from models import Category
from auth_required import require_login, get_current_user_id, get_current_user_name

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="التصنيفات", page_icon="🗂️", layout="wide")
st.title("🗂️ إدارة تصنيفات الأصناف")
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()


def _delete_category(cat_id):
    """يحذف تصنيف + كل تصنيفاته الفرعية + يفك ارتباط الأصناف."""
    db_local = SessionLocal()
    try:
        cat = db_local.query(Category).filter(Category.id == cat_id).first()
        if not cat:
            raise ValueError("التصنيف غير موجود")

        # فك ارتباط الأصناف بالتصنيف وكل تصنيفاته الفرعية
        sub_ids = [c.id for c in db_local.query(Category).filter(
            Category.parent_id == cat_id
        ).all()]
        all_ids = [cat_id] + sub_ids

        for iid in all_ids:
            db_local.query(models.Item).filter(
                models.Item.category_id == iid
            ).update({"category_id": None}, synchronize_session=False)

        # حذف التصنيفات الفرعية
        db_local.query(Category).filter(Category.parent_id == cat_id).delete(
            synchronize_session=False
        )

        # حذف التصنيف الرئيسي
        db_local.delete(cat)
        db_local.commit()
    except Exception:
        db_local.rollback()
        raise
    finally:
        db_local.close()


tab1, tab2 = st.tabs(["➕ إضافة/تعديل تصنيف", "📋 قائمة التصنيفات"])


# ==========================================
# التبويب 1: إضافة/تعديل
# ==========================================
with tab1:
    st.subheader("➕ إضافة تصنيف جديد")
    st.caption("💡 بعد الحفظ، الحقول هتتفرّغ تلقائيًا.")

    category_name = st.text_input(
        "اسم التصنيف:",
        placeholder="مثال: أدوات مكتبية، مواد غذائية...",
        key="new_cat_name",
    )
    category_description = st.text_area(
        "الوصف (اختياري):",
        placeholder="وصف مختصر...",
        key="new_cat_desc",
        height=60,
    )

    all_categories = db.query(Category).filter(
        Category.is_active == True
    ).order_by(Category.name).all()

    category_options = {"بدون (تصنيف رئيسي)": None}
    for cat in all_categories:
        category_options[f"{cat.name}"] = cat.id

    parent_category = st.selectbox(
        "التصنيف الأب (اختياري):",
        options=list(category_options.values()),
        format_func=lambda x: next(
            (k for k, v in category_options.items() if v == x),
            "بدون",
        ),
        key="new_cat_parent",
    )

    if st.button("💾 إضافة التصنيف", type="primary", use_container_width=True):
        if not category_name.strip():
            st.error("❌ يرجى إدخال اسم التصنيف.")
        else:
            try:
                existing = db.query(Category).filter(
                    Category.name == category_name.strip()
                ).first()
                if existing:
                    st.error(f"❌ التصنيف '{category_name}' موجود مسبقًا.")
                else:
                    new_cat = Category(
                        name=category_name.strip(),
                        description=category_description.strip() or None,
                        parent_id=parent_category,
                        is_active=True,
                        created_at=datetime.now(),
                    )
                    db.add(new_cat)
                    db.commit()
                    st.success(f"✅ تم إضافة '{category_name}'!")
                    st.balloons()

                    queue_state_updates(
                        delete_keys=(
                            "new_cat_name", "new_cat_desc", "new_cat_parent",
                        ),
                        set_values={
                            "new_cat_name": "",
                            "new_cat_desc": "",
                            "new_cat_parent": None,
                        },
                    )
                    st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"❌ خطأ: {e}")

    st.markdown("---")
    st.subheader("✏️ تعديل تصنيف موجود")

    if all_categories:
        sel_id = st.selectbox(
            "اختر تصنيفاً:",
            options=[c.id for c in all_categories],
            format_func=lambda x: next(
                (c.name for c in all_categories if c.id == x), str(x)
            ),
            key="sel_cat_edit",
        )

        if sel_id:
            sel_cat = next((c for c in all_categories if c.id == sel_id), None)

            with st.form(f"edit_cat_form_{sel_id}"):
                edit_name = st.text_input("الاسم:", value=sel_cat.name)
                edit_desc = st.text_area(
                    "الوصف:",
                    value=sel_cat.description or "",
                    height=80,
                )
                edit_active = st.checkbox("نشط", value=bool(sel_cat.is_active))
                submitted = st.form_submit_button(
                    "💾 حفظ التعديلات", type="primary",
                )

            if submitted:
                try:
                    if not edit_name.strip():
                        st.error("❌ الاسم مطلوب.")
                    else:
                        dup = db.query(Category).filter(
                            Category.name == edit_name.strip(),
                            Category.id != sel_id,
                        ).first()
                        if dup:
                            st.error(f"❌ الاسم '{edit_name}' مستخدم لتصنيف آخر.")
                        else:
                            sel_cat.name = edit_name.strip()
                            sel_cat.description = edit_desc.strip() or None
                            sel_cat.is_active = edit_active
                            db.commit()
                            st.success("✅ تم التعديل.")
                            queue_state_updates(delete_keys=("sel_cat_edit",))
                            st.rerun()
                except Exception as e:
                    db.rollback()
                    st.error(f"❌ خطأ: {e}")
    else:
        st.info("لا توجد تصنيفات للتعديل.")


# ==========================================
# التبويب 2: قائمة التصنيفات
# ==========================================
with tab2:
    st.subheader("📋 قائمة التصنيفات")

    all_categories = db.query(Category).order_by(Category.name).all()

    if all_categories:
        # جدول تفصيلي
        rows = []
        for idx, cat in enumerate(all_categories, start=1):
            parent = next(
                (c.name for c in all_categories if c.id == cat.parent_id),
                "—",
            )
            items_count = db.query(models.Item).filter(
                models.Item.category_id == cat.id
            ).count()
            rows.append({
                "مسلسل": idx,
                "ID": cat.id,
                "الاسم": cat.name,
                "الأب": parent,
                "الوصف": cat.description or "—",
                "عدد الأصناف": items_count,
                "الحالة": "✅ نشط" if cat.is_active else "⛔ معطل",
            })
        df = pd.DataFrame(rows)
        st.dataframe(
            df.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")
        st.subheader("⚙️ حذف تصنيف")

        if not can_modify():
            st.info("⛔ الحذف للمدير فقط.")
        else:
            del_id = st.selectbox(
                "اختر تصنيفاً للحذف:",
                options=[c.id for c in all_categories],
                format_func=lambda x: next(
                    (f"{c.name}" for c in all_categories if c.id == x),
                    str(x),
                ),
                key="del_cat_select",
            )

            if del_id:
                del_cat = next((c for c in all_categories if c.id == del_id), None)
                items_count = db.query(models.Item).filter(
                    models.Item.category_id == del_id
                ).count()
                sub_count = db.query(Category).filter(
                    Category.parent_id == del_id
                ).count()

                st.warning(
                    f"⚠️ سيتم حذف **{del_cat.name}** "
                    f"({sub_count} تصنيف فرعي، {items_count} صنف مرتبط)."
                )
                st.info("💡 الأصناف لن تُحذف — بس هيتشال منها التصنيف.")

                confirm = st.checkbox(
                    "✅ أؤكد الحذف",
                    key=f"confirm_del_cat_{del_id}",
                )
                if st.button(
                    "🗑 حذف التصنيف",
                    type="secondary",
                    disabled=not confirm,
                    use_container_width=True,
                    key=f"del_cat_btn_{del_id}",
                ):
                    try:
                        _delete_category(del_id)
                        st.success(f"✅ تم حذف '{del_cat.name}'.")
                        queue_state_updates(
                            delete_keys=("del_cat_select",)
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")
    else:
        st.info("لا توجد تصنيفات مسجلة.")

db.close()