# pages/2_📦_الأصناف.py
import os
import sys
import tempfile
import traceback
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

st.set_page_config(page_title="الأصناف", page_icon="📦", layout="wide")

from sidebar import render_sidebar, can_modify, require_modify, queue_state_updates
render_sidebar()

from database import SessionLocal
import models
from models import Category
from services import (
    create_item, create_kit_item, import_items_from_file,
    export_import_template, export_items_to_excel, export_categories_to_excel,
    import_categories_from_file
)
from auth_required import require_login, get_current_user_id, get_current_user_name
from code_search import CodeSearch, FormState
from form_manager import clear_form, show_clear_hint

# ✅ Cache Layer
from cache_helpers import (
    get_items_with_stock,
    get_stock_map,
    invalidate_all,
)

current_user = require_login()

# ⭐ استقبال التنقل من شجرة الحسابات
from navigation_helper import consume_navigation_flags, show_navigation_banner
_nav = consume_navigation_flags()
show_navigation_banner(_nav, page_name="الأصناف")
_open_item_id = _nav.get("_open_items_id")
if _open_item_id:
    st.session_state["_highlight_item_id"] = _open_item_id
    st.info(f"🎯 تم استدعاؤك لعرض الصنف رقم `{_open_item_id}`")

current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

try:
    from keyboard_nav import enable_enter_navigation, add_enter_hint
    enable_enter_navigation()
    add_enter_hint()
except Exception:
    pass


# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لمفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "itm_"


# ==========================================
# أدوات مساعدة
# ==========================================
CODE_FIELDS = [f for f in ("code", "item_code", "barcode", "sku") if hasattr(models.Item, f)]

KC_QTY_FIELD = next(
    (f for f in ("quantity", "qty", "component_quantity") if hasattr(models.KitComponent, f)),
    None,
)

KIT_LABEL = "صنف مدمج (Kit)"
NORMAL_LABEL = "صنف عادي"

QTY_MIN = 0.0
QTY_STEP = 0.25
QTY_DEFAULT = 1.0
QTY_FORMAT = "%.2f"


def flash(msg):
    st.session_state["_items_flash"] = msg


def parse_components(edited_df, by_label):
    result = {}
    for _, row in edited_df.iterrows():
        lbl = row.get("المكوّن")
        if lbl is None or pd.isna(lbl) or not str(lbl).strip():
            continue
        comp = by_label(lbl)
        if comp is None:
            continue
        qty = row.get("الكمية")
        if qty is None or pd.isna(qty) or float(qty) <= 0:
            qty = QTY_DEFAULT
        else:
            qty = float(qty)
        result[comp.id] = result.get(comp.id, 0.0) + qty
    return result


def next_selection(cs, current_label, saved_item=None, deleting=False):
    labels = cs.labels
    pos = labels.index(current_label) if current_label in labels else -1
    if 0 <= pos < len(labels) - 1:
        return labels[pos + 1]
    if deleting:
        return labels[pos - 1] if pos > 0 else None
    return cs.label(saved_item) if saved_item is not None else current_label


def queue_after_item_change(cs, next_label):
    values = {cs.code_key: ""}
    if next_label:
        values[cs.item_key] = next_label
    queue_state_updates(
        delete_prefixes=("edit_", "kit_editor_", "confirm_del_"),
        delete_keys=(cs.query_key, cs.pick_key),
        set_values=values,
    )


def add_kit_components(db, kit_id, components):
    for comp_id, qty in components.items():
        kwargs = {"kit_item_id": kit_id, "component_item_id": comp_id}
        if KC_QTY_FIELD:
            kwargs[KC_QTY_FIELD] = qty
        db.add(models.KitComponent(**kwargs))


# ==========================================
# الصفحة
# ==========================================
st.title("📦 إدارة الأصناف")
show_clear_hint()   # ✅ تلميح
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

msg = st.session_state.pop("_items_flash", None)
if msg:
    st.success(msg)

db = SessionLocal()
fs = FormState("itemadd")

SECTIONS = [
    "➕ إضافة صنف",
    "📋 قائمة الأصناف / تعديل",
    "📥 استيراد وتصدير الأصناف",
    "🗂️ استيراد وتصدير التصنيفات",
]
section = st.radio("القسم", SECTIONS, horizontal=True, key="items_section",
                   label_visibility="collapsed")
st.markdown("---")


# ==========================================
# التبويب 1: إضافة صنف
# ==========================================
if section == SECTIONS[0]:
    st.subheader("➕ إضافة صنف جديد")

    item_type = st.radio("نوع الصنف:", [NORMAL_LABEL, KIT_LABEL], key=fs.key("type"))

    name = st.text_input("اسم الصنف", key=fs.key("name"))

    from cache_helpers import get_active_categories
    all_categories_data = get_active_categories()
    category_options = {"بدون تصنيف": None}
    for cat_id, cat_name in all_categories_data:
        category_options[cat_name] = cat_id

    selected_category_id = st.selectbox(
        "التصنيف:",
        options=list(category_options.values()),
        format_func=lambda x: next((k for k, v in category_options.items() if v == x), "بدون تصنيف"),
        key=fs.key("category")
    )

    cost_price = st.number_input("سعر التكلفة", min_value=0.0, step=0.1, key=fs.key("cost"))
    sell_price = st.number_input("سعر البيع", min_value=0.0, step=0.1, key=fs.key("sell"))
    barcode = st.text_input("الباركود (اختياري)", key=fs.key("barcode"))

    components_data = []
    if item_type == KIT_LABEL:
        st.info("⚠️ الصنف المدمج يتكون من أصناف أخرى")
        non_kit_items = [it for it in db.query(models.Item).all() if not it.is_kit]
        comp_cs = CodeSearch(non_kit_items, prefix="addcomp", code_field=CODE_FIELDS, name_field="name")
        selected_labels = st.multiselect("اختر المكونات:",
                                         comp_cs.labels, key=fs.key("components"))
        for lbl in selected_labels:
            comp_item = comp_cs.by_label(lbl)
            if comp_item is None:
                continue
            qty = st.number_input(
                f"كمية {lbl}",
                min_value=QTY_MIN, step=QTY_STEP, value=QTY_DEFAULT,
                format=QTY_FORMAT,
                key=fs.key(f"qty_{comp_item.id}"),
            )
            components_data.append({'item_name': comp_item.name, 'quantity': qty})

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💾 حفظ الصنف", type="primary"):
            if not name:
                st.error("يرجى إدخال اسم الصنف")
            else:
                saved = False
                try:
                    if item_type == NORMAL_LABEL:
                        item = create_item(name, cost_price, sell_price,
                                           barcode if barcode else None,
                                           created_by=current_user_id)
                        if selected_category_id:
                            item.category_id = selected_category_id
                            db.commit()
                        saved = True
                    elif not components_data:
                        st.error("يرجى اختيار مكون واحد على الأقل")
                    else:
                        item = create_kit_item(name, components_data, sell_price,
                                                created_by=current_user_id)
                        if selected_category_id:
                            item.category_id = selected_category_id
                            db.commit()
                        saved = True
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

                if saved:
                    flash("✅ تم الحفظ بنجاح!")
                    invalidate_all()
                    queue_state_updates(
                        delete_prefixes=("itemadd_", "qty_"),
                    )
                    try:
                        fs.reset()
                    except Exception:
                        pass
                    st.rerun()

    with col2:
        if st.button("🧹 مسح الحقول"):
            queue_state_updates(delete_prefixes=("itemadd_", "qty_"))
            try:
                fs.reset()
            except Exception:
                pass
            st.rerun()

    with col3:
        if st.button("❌ إلغاء"):
            queue_state_updates(delete_prefixes=("itemadd_", "qty_"))
            try:
                fs.reset()
            except Exception:
                pass
            st.rerun()


# ==========================================
# التبويب 2: قائمة الأصناف + التعديل
# ==========================================
if section == SECTIONS[1]:
    st.subheader("📋 قائمة الأصناف")

    from cache_helpers import get_active_categories
    all_categories_data = get_active_categories()
    category_filter_options = ["الكل"] + [name for _, name in all_categories_data]
    filter_category = st.selectbox("تصفية حسب التصنيف:", options=category_filter_options)

    all_items_cached = get_items_with_stock()

    if filter_category == "الكل":
        filtered_items = all_items_cached
    else:
        filtered_items = [
            it for it in all_items_cached
            if it["category_name"] == filter_category
        ]

    if filtered_items:
        # ✅ Pagination
        PAGE_SIZE = 50
        total_count = len(filtered_items)
        total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)

        col_p1, col_p2 = st.columns([3, 1])
        with col_p1:
            st.caption(f"📊 إجمالي: **{total_count}** صنف | صفحة **{total_pages}**")
        with col_p2:
            page_num = st.number_input(
                "صفحة:", min_value=1, max_value=total_pages,
                value=1, step=1, key=f"{PFX}page_num"
            )

        start = (page_num - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items_data = filtered_items[start:end]

        data = []
        for it in page_items_data:
            data.append({
                "ID": it["id"],
                "الاسم": it["name"],
                "التصنيف": it["category_name"] or "بدون",
                "النوع": "مدمج" if it["is_kit"] else "عادي",
                "سعر التكلفة": it["cost_price"],
                "سعر البيع": it["sell_price"],
                "الرصيد الحالي": it["current_stock"],
                "الباركود": it["barcode"] or "-"
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"عرض {start + 1} - {min(end, total_count)} من {total_count}")

        if total_pages > 1:
            col_prev, col_next = st.columns(2)
            with col_prev:
                if st.button("⬅️ السابق", disabled=(page_num <= 1), key=f"{PFX}items_prev"):
                    st.session_state[f"{PFX}page_num"] = page_num - 1
                    st.rerun()
            with col_next:
                if st.button("التالي ➡️", disabled=(page_num >= total_pages), key=f"{PFX}items_next"):
                    st.session_state[f"{PFX}page_num"] = page_num + 1
                    st.rerun()

        st.markdown("---")
        st.subheader("🔎 اختيار صنف للتعديل أو الحذف")

        item_ids_page = [it["id"] for it in filtered_items]
        items_objects = db.query(models.Item).filter(
            models.Item.id.in_(item_ids_page)
        ).order_by(models.Item.name).all()

        cat_index = category_filter_options.index(filter_category)
        cs = CodeSearch(items_objects, prefix=f"itmsel{cat_index}",
                        code_field=CODE_FIELDS, name_field="name")
        cs.render_input()
        sel_label = st.selectbox("اختر صنف:", cs.labels, key=cs.item_key)
        selected_item = cs.by_label(sel_label)

        if selected_item is not None and not can_modify():
            st.info("✏️ التعديل والحذف للمدير فقط.")

        if selected_item is not None and can_modify():
            sid = selected_item.id
            invoice_lines = db.query(models.InvoiceLine).filter(
                models.InvoiceLine.item_id == sid
            ).all()
            is_used_in_invoices = len(invoice_lines) > 0

            st.markdown("---")
            st.subheader("✏️ تعديل الصنف")

            new_name = st.text_input("الاسم الجديد:", value=selected_item.name,
                                     key=f"edit_name_{sid}")

            c_cost, c_sell = st.columns(2)
            with c_cost:
                new_cost = st.number_input("سعر التكلفة الجديد:",
                                           min_value=0.0, step=0.1,
                                           value=float(selected_item.cost_price or 0),
                                           key=f"edit_cost_{sid}")
            with c_sell:
                new_sell = st.number_input("سعر البيع الجديد:",
                                           min_value=0.0, step=0.1,
                                           value=float(selected_item.sell_price or 0),
                                           key=f"edit_sell_{sid}")

            new_barcode = st.text_input("الباركود الجديد:",
                                        value=selected_item.barcode or "",
                                        key=f"edit_barcode_{sid}")

            cat_names = ["بدون تصنيف"] + [name for _, name in all_categories_data]
            current_cat_name = next(
                (name for cid, name in all_categories_data if cid == selected_item.category_id),
                "بدون تصنيف"
            )
            new_category = st.selectbox("التصنيف الجديد:", options=cat_names,
                                        index=cat_names.index(current_cat_name),
                                        key=f"edit_category_{sid}")

            new_type = st.radio("نوع الصنف:", [NORMAL_LABEL, KIT_LABEL],
                                index=1 if selected_item.is_kit else 0,
                                horizontal=True, key=f"edit_type_{sid}")
            want_kit = new_type == KIT_LABEL

            new_components = {}
            used_as_component = 0
            if want_kit:
                st.markdown("**📦 محتوى الصنف المدمج (المكونات):**")
                st.caption("أضف صفاً جديداً، واختر المكوّن، وحدّد الكمية (0.25 / 0.5).")

                non_kit_items = [it for it in db.query(models.Item).all()
                                 if not it.is_kit and it.id != sid]
                comp_cs = CodeSearch(non_kit_items, prefix=f"kitcomp{sid}",
                                     code_field=CODE_FIELDS, name_field="name")
                id_to_label = {it.id: comp_cs.label(it) for it in non_kit_items}

                existing = db.query(models.KitComponent).filter(
                    models.KitComponent.kit_item_id == sid
                ).all()
                rows = [(id_to_label[c.component_item_id],
                         float((getattr(c, KC_QTY_FIELD) if KC_QTY_FIELD else 1) or 1))
                        for c in existing if c.component_item_id in id_to_label]
                base_df = pd.DataFrame({
                    "المكوّن": pd.Series([r[0] for r in rows], dtype="object"),
                    "الكمية": pd.Series([r[1] for r in rows], dtype="float64"),
                })

                kver = st.session_state.get(f"kitver_{sid}", 0)
                edited_df = st.data_editor(
                    base_df,
                    num_rows="dynamic",
                    use_container_width=True,
                    key=f"kit_editor_{sid}_{kver}",
                    column_config={
                        "المكوّن": st.column_config.SelectboxColumn("المكوّن",
                                                                    options=comp_cs.labels,
                                                                    required=True),
                        "الكمية": st.column_config.NumberColumn(
                            "الكمية", min_value=QTY_MIN, step=QTY_STEP,
                            default=QTY_DEFAULT, format=QTY_FORMAT,
                        ),
                    },
                )
                new_components = parse_components(edited_df, comp_cs.by_label)

                if new_components:
                    by_id = {it.id: it for it in non_kit_items}
                    comps_cost = sum(float(by_id[i].cost_price or 0) * q
                                     for i, q in new_components.items())
                    st.caption(f"💡 مجموع تكلفة المكونات: {comps_cost:,.2f}")

                if not selected_item.is_kit:
                    used_as_component = db.query(models.KitComponent).filter(
                        models.KitComponent.component_item_id == sid
                    ).count()
                    movements_count = db.query(models.InventoryMovement).filter(
                        models.InventoryMovement.item_id == sid
                    ).count()
                    if movements_count:
                        st.warning(f"⚠️ لهذا الصنف {movements_count} حركة مخزون مسجلة.")

            if st.button("💾 حفظ التعديلات", type="primary", key=f"save_edit_{sid}"):
                if require_modify("تعديل الصنف"):
                    errors = []
                    clean_name = (new_name or "").strip()
                    if not clean_name:
                        errors.append("اسم الصنف مطلوب")
                    elif db.query(models.Item).filter(
                        models.Item.name == clean_name, models.Item.id != sid
                    ).first():
                        errors.append("يوجد صنف آخر بنفس الاسم")
                    if want_kit and not new_components:
                        errors.append("الصنف المدمج يحتاج مكوناً واحداً على الأقل")
                    if want_kit and not selected_item.is_kit and used_as_component:
                        errors.append(f"هذا الصنف مكوّن داخل {used_as_component} صنف مدمج.")

                    if errors:
                        for e in errors:
                            st.error(f"❌ {e}")
                    else:
                        try:
                            selected_item.name = clean_name
                            selected_item.cost_price = new_cost
                            selected_item.sell_price = new_sell
                            selected_item.barcode = new_barcode.strip() if new_barcode.strip() else None

                            if new_category == "بدون تصنيف":
                                selected_item.category_id = None
                            else:
                                category = db.query(Category).filter(
                                    Category.name == new_category
                                ).first()
                                if category:
                                    selected_item.category_id = category.id

                            selected_item.is_kit = want_kit
                            db.query(models.KitComponent).filter(
                                models.KitComponent.kit_item_id == sid
                            ).delete()
                            if want_kit:
                                add_kit_components(db, sid, new_components)

                            db.commit()
                            invalidate_all()
                            st.session_state[f"kitver_{sid}"] = st.session_state.get(f"kitver_{sid}", 0) + 1
                            nxt = next_selection(cs, sel_label, saved_item=selected_item)
                            queue_after_item_change(cs, nxt)
                            flash(f"✅ تم تحديث «{clean_name}» — انتقلت للصنف التالي.")
                            st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"❌ خطأ: {e}")
                            st.code(traceback.format_exc())

            st.markdown("---")
            st.subheader("🗑️ حذف الصنف")

            if is_used_in_invoices:
                st.error(f"🚫 لا يمكن حذف هذا الصنف! مستخدم في {len(invoice_lines)} فاتورة.")
            else:
                confirm_delete = st.checkbox(
                    "تأكيد الحذف",
                    key=f"confirm_del_{sid}",
                )
                if st.button("🗑️ حذف الصنف", type="secondary",
                             disabled=not confirm_delete, key=f"del_item_{sid}"):
                    if require_modify("حذف الصنف"):
                        try:
                            db.query(models.KitComponent).filter(
                                models.KitComponent.kit_item_id == sid
                            ).delete()
                            db.query(models.KitComponent).filter(
                                models.KitComponent.component_item_id == sid
                            ).delete()
                            db.query(models.InventoryMovement).filter(
                                models.InventoryMovement.item_id == sid
                            ).delete()

                            deleted_name = selected_item.name
                            db.delete(selected_item)
                            db.commit()
                            invalidate_all()

                            queue_state_updates(
                                delete_prefixes=("edit_", "kit_editor_", "confirm_del_"),
                                delete_keys=(cs.query_key, cs.pick_key),
                            )
                            flash(f"✅ تم حذف «{deleted_name}» بنجاح!")
                            st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"❌ خطأ في الحذف: {e}")
    else:
        st.info("لا توجد أصناف.")


# ==========================================
# التبويب 3: استيراد وتصدير الأصناف
# ==========================================
if section == SECTIONS[2]:
    st.subheader("📤 تصدير الأصناف")
    st.info("💡 يتم تصدير: الكود، الاسم، الأسعار، التصنيف، الرصيد الافتتاحي، الحد الأدنى.")

    if st.button("📤 تصدير جميع الأصناف إلى Excel", type="primary"):
        try:
            output_path, count = export_items_to_excel()
            st.success(f"✅ تم تصدير {count} صنف بنجاح!")
            with open(output_path, "rb") as file:
                st.download_button(
                    label="⬇️ تحميل ملف الأصناف",
                    data=file,
                    file_name=output_path,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.error(f"❌ خطأ في التصدير: {e}")

    st.markdown("---")
    st.subheader("📥 استيراد الأصناف من ملف")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬇️ تحميل قالب الأصناف"):
            try:
                template_path = export_import_template('items', 'template_items.xlsx')
                with open(template_path, "rb") as file:
                    st.download_button(
                        label="⬇️ تحميل القالب",
                        data=file,
                        file_name="template_items.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"خطأ: {e}")

    with col2:
        uploaded_file = st.file_uploader(
            "اختر ملف:",
            type=['xlsx', 'csv'],
            key=f"{PFX}upload_items",
        )

        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            if st.button("📥 استيراد", type="primary"):
                try:
                    count, errors = import_items_from_file(tmp_path, created_by=current_user_id)
                    st.success(f"✅ تم استيراد {count} صنف!")
                    if errors:
                        for error in errors[:5]:
                            st.write(f"- {error}")
                    invalidate_all()

                    # ✅ تفريغ حقل الرفع
                    clear_form(PFX)
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: {e}")
                finally:
                    os.unlink(tmp_path)


# ==========================================
# التبويب 4: استيراد وتصدير التصنيفات
# ==========================================
if section == SECTIONS[3]:
    st.subheader("📤 تصدير التصنيفات")

    if st.button("📤 تصدير التصنيفات إلى Excel", type="primary"):
        try:
            output_path, count = export_categories_to_excel()
            st.success(f"✅ تم تصدير {count} تصنيف!")
            with open(output_path, "rb") as file:
                st.download_button(
                    label="⬇️ تحميل",
                    data=file,
                    file_name=output_path
                )
        except Exception as e:
            st.error(f"❌ خطأ: {e}")

    st.markdown("---")
    st.subheader("📥 استيراد التصنيفات")

    uploaded_file = st.file_uploader(
        "اختر ملف التصنيفات:",
        type=['xlsx', 'csv'],
        key=f"{PFX}upload_categories",
    )

    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        if st.button("📥 استيراد التصنيفات", type="primary"):
            try:
                count, errors = import_categories_from_file(tmp_path, created_by=current_user_id)
                st.success(f"✅ تم استيراد {count} تصنيف!")
                invalidate_all()

                # ✅ تفريغ حقل الرفع
                clear_form(PFX)
                st.rerun()
            except Exception as e:
                st.error(f"خطأ: {e}")
            finally:
                os.unlink(tmp_path)

db.close()