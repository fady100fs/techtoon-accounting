# pages/23_📦_إدارة_المخزون.py
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
from models import Warehouse, StockLevel, WarehouseTransfer, StockCount
from services import (
    create_warehouse, get_stock_level, update_stock_level,
    transfer_between_warehouses, create_stock_count,
    get_warehouse_stock_report,
)
from auth_required import require_login, get_current_user_id, get_current_user_name

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="إدارة المخزون", page_icon="📦", layout="wide")
st.title("📦 إدارة المخزون المتقدمة")
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()


def _warehouse_usage(wh_id):
    """يرجع عدد الأصناف + التحويلات + الجرد للمخزن."""
    stock_count = db.query(StockLevel).filter(
        StockLevel.warehouse_id == wh_id,
        StockLevel.quantity > 0,
    ).count()
    transfers_count = db.query(WarehouseTransfer).filter(
        (WarehouseTransfer.from_warehouse_id == wh_id) |
        (WarehouseTransfer.to_warehouse_id == wh_id)
    ).count()
    counts_count = db.query(StockCount).filter(
        StockCount.warehouse_id == wh_id
    ).count()
    return {
        "stock": stock_count,
        "transfers": transfers_count,
        "counts": counts_count,
    }


def _delete_warehouse(wh_id):
    """يحذف مخزن + كل حركاته + أرصدته + جرده."""
    db_local = SessionLocal()
    try:
        wh = db_local.query(Warehouse).filter(Warehouse.id == wh_id).first()
        if not wh:
            raise ValueError("المخزن غير موجود")

        db_local.query(StockLevel).filter(
            StockLevel.warehouse_id == wh_id
        ).delete(synchronize_session=False)
        db_local.query(WarehouseTransfer).filter(
            (WarehouseTransfer.from_warehouse_id == wh_id) |
            (WarehouseTransfer.to_warehouse_id == wh_id)
        ).delete(synchronize_session=False)
        db_local.query(StockCount).filter(
            StockCount.warehouse_id == wh_id
        ).delete(synchronize_session=False)

        db_local.delete(wh)
        db_local.commit()
    except Exception:
        db_local.rollback()
        raise
    finally:
        db_local.close()


def _delete_transfer(transfer_id):
    """يحذف حركة تحويل + يعكس تأثيرها على الأرصدة."""
    db_local = SessionLocal()
    try:
        t = db_local.query(WarehouseTransfer).filter(
            WarehouseTransfer.id == transfer_id
        ).first()
        if not t:
            raise ValueError("الحركة غير موجودة")

        # إرجاع الكمية من المخزن الهدف للمصدر
        to_stock = db_local.query(StockLevel).filter(
            StockLevel.warehouse_id == t.to_warehouse_id,
            StockLevel.item_id == t.item_id,
        ).first()
        if to_stock:
            to_stock.quantity = max(0.0, float(to_stock.quantity or 0) - float(t.quantity or 0))
            to_stock.last_updated = datetime.now()

        from_stock = db_local.query(StockLevel).filter(
            StockLevel.warehouse_id == t.from_warehouse_id,
            StockLevel.item_id == t.item_id,
        ).first()
        if from_stock:
            from_stock.quantity = float(from_stock.quantity or 0) + float(t.quantity or 0)
            from_stock.last_updated = datetime.now()
        else:
            db_local.add(StockLevel(
                warehouse_id=t.from_warehouse_id,
                item_id=t.item_id,
                quantity=float(t.quantity or 0),
            ))

        db_local.delete(t)
        db_local.commit()
    except Exception:
        db_local.rollback()
        raise
    finally:
        db_local.close()


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏭 إدارة المخازن",
    "📊 مستويات المخزون",
    "🔄 تحويل بين المخازن",
    "📋 الجرد الدوري",
    "📈 تقارير المخزون",
])


# ==========================================
# التبويب 1: إدارة المخازن
# ==========================================
with tab1:
    st.subheader("🏭 إدارة المخازن")

    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "➕ إضافة مخزن", "📋 القائمة", "⚙️ تعديل/حذف",
    ])

    # ============= إضافة =============
    with sub_tab1:
        st.markdown("### ➕ إضافة مخزن جديد")
        st.caption("💡 بعد الحفظ، الحقول هتتفرّغ تلقائيًا.")

        wh_name = st.text_input("اسم المخزن:",
                                 placeholder="مثال: المخزن الرئيسي...",
                                 key="new_wh_name")
        wh_code = st.text_input("كود المخزن:",
                                 placeholder="مثال: WH001...",
                                 key="new_wh_code")
        wh_location = st.text_input("الموقع (اختياري):",
                                     key="new_wh_location")
        wh_responsible = st.text_input("المسؤول (اختياري):",
                                        key="new_wh_responsible")
        wh_notes = st.text_area("ملاحظات (اختياري):", key="new_wh_notes")

        if st.button("💾 إنشاء المخزن", type="primary", use_container_width=True):
            if not wh_name.strip() or not wh_code.strip():
                st.error("❌ يرجى إدخال اسم وكود المخزن.")
            else:
                try:
                    create_warehouse(
                        name=wh_name.strip(),
                        code=wh_code.strip(),
                        location=wh_location.strip() or None,
                        responsible_person=wh_responsible.strip() or None,
                        notes=wh_notes.strip() or None,
                    )
                    st.success(f"✅ تم إنشاء المخزن '{wh_name}'!")
                    st.balloons()

                    queue_state_updates(
                        delete_keys=(
                            "new_wh_name", "new_wh_code", "new_wh_location",
                            "new_wh_responsible", "new_wh_notes",
                        ),
                        set_values={
                            "new_wh_name": "", "new_wh_code": "",
                            "new_wh_location": "", "new_wh_responsible": "",
                            "new_wh_notes": "",
                        },
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

    # ============= القائمة =============
    with sub_tab2:
        st.markdown("### 📋 قائمة المخازن")

        warehouses = db.query(Warehouse).order_by(Warehouse.code).all()

        if warehouses:
            rows = []
            for idx, wh in enumerate(warehouses, start=1):
                usage = _warehouse_usage(wh.id)
                rows.append({
                    "مسلسل": idx,
                    "الكود": wh.code,
                    "الاسم": wh.name,
                    "الموقع": wh.location or "—",
                    "المسؤول": wh.responsible_person or "—",
                    "أصناف": usage["stock"],
                    "تحويلات": usage["transfers"],
                    "الحالة": "✅ نشط" if wh.is_active else "⛔ معطل",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True,
                         hide_index=True)
        else:
            st.info("لا توجد مخازن.")

    # ============= تعديل/حذف =============
    with sub_tab3:
        st.markdown("### ⚙️ تعديل / حذف مخزن")

        warehouses = db.query(Warehouse).all()

        if not warehouses:
            st.info("لا توجد مخازن.")
        else:
            sel_wh_id = st.selectbox(
                "اختر مخزن:",
                options=[w.id for w in warehouses],
                format_func=lambda x: next(
                    (f"{w.code} — {w.name}" for w in warehouses if w.id == x),
                    str(x)),
                key="sel_wh_edit",
            )

            if sel_wh_id:
                sel_wh = next((w for w in warehouses if w.id == sel_wh_id), None)
                usage = _warehouse_usage(sel_wh_id)

                st.markdown(f"### 📄 تفاصيل: **{sel_wh.name}**")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("أصناف", usage["stock"])
                with c2:
                    st.metric("تحويلات", usage["transfers"])
                with c3:
                    st.metric("عمليات جرد", usage["counts"])
                with c4:
                    st.metric("الحالة",
                              "✅ نشط" if sel_wh.is_active else "⛔ معطل")

                col_edit, col_del = st.columns(2)

                # ----- تعديل -----
                with col_edit:
                    st.markdown("#### ✏️ تعديل البيانات")
                    with st.form(f"edit_wh_form_{sel_wh_id}"):
                        e_name = st.text_input("الاسم:", value=sel_wh.name)
                        e_loc = st.text_input("الموقع:",
                                               value=sel_wh.location or "")
                        e_resp = st.text_input("المسؤول:",
                                                value=sel_wh.responsible_person or "")
                        e_notes = st.text_area("ملاحظات:",
                                                value=sel_wh.notes or "",
                                                height=80)
                        e_active = st.checkbox("نشط",
                                                value=bool(sel_wh.is_active))
                        submitted = st.form_submit_button(
                            "💾 حفظ التعديلات", type="primary",
                        )

                    if submitted:
                        try:
                            if not e_name.strip():
                                st.error("❌ الاسم مطلوب.")
                            else:
                                sel_wh.name = e_name.strip()
                                sel_wh.location = e_loc.strip() or None
                                sel_wh.responsible_person = e_resp.strip() or None
                                sel_wh.notes = e_notes.strip() or None
                                sel_wh.is_active = e_active
                                db.commit()
                                st.success("✅ تم التعديل.")
                                queue_state_updates(delete_keys=("sel_wh_edit",))
                                st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"❌ خطأ: {e}")

                # ----- حذف / تعطيل -----
                with col_del:
                    st.markdown("#### 🗑 حذف / تعطيل")

                    if sel_wh.is_active:
                        if st.button("⛔ تعطيل المخزن",
                                     use_container_width=True,
                                     key=f"disable_wh_{sel_wh_id}"):
                            try:
                                sel_wh.is_active = False
                                db.commit()
                                st.success("✅ تم التعطيل.")
                                queue_state_updates(delete_keys=("sel_wh_edit",))
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"❌ {e}")
                    else:
                        if st.button("✅ تفعيل المخزن",
                                     use_container_width=True,
                                     key=f"enable_wh_{sel_wh_id}"):
                            try:
                                sel_wh.is_active = True
                                db.commit()
                                st.success("✅ تم التفعيل.")
                                queue_state_updates(delete_keys=("sel_wh_edit",))
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"❌ {e}")

                    st.markdown("---")

                    if usage["stock"] > 0 or usage["transfers"] > 0:
                        st.error("⛔ لا يمكن الحذف:")
                        if usage["stock"] > 0:
                            st.write(f"- به {usage['stock']} صنف برصيد")
                        if usage["transfers"] > 0:
                            st.write(f"- به {usage['transfers']} تحويل")
                        st.info("💡 الحل: عطّل المخزن.")
                    else:
                        st.warning("⚠️ الحذف نهائي!")
                        confirm = st.checkbox(
                            "✅ أؤكد الحذف",
                            key=f"confirm_del_wh_{sel_wh_id}",
                        )
                        if st.button(
                            "🗑 حذف المخزن",
                            type="secondary",
                            disabled=not confirm,
                            use_container_width=True,
                            key=f"del_wh_btn_{sel_wh_id}",
                        ):
                            try:
                                _delete_warehouse(sel_wh_id)
                                st.success("✅ تم الحذف.")
                                queue_state_updates(delete_keys=("sel_wh_edit",))
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ {e}")


# ==========================================
# التبويب 2: مستويات المخزون
# ==========================================
with tab2:
    st.subheader("📊 مستويات المخزون")

    warehouses = db.query(Warehouse).filter(
        Warehouse.is_active == True
    ).all()

    if not warehouses:
        st.warning("⚠️ لا توجد مخازن نشطة.")
    else:
        sel_wh_id = st.selectbox(
            "اختر المخزن:",
            options=[w.id for w in warehouses],
            format_func=lambda x: next(
                (w.name for w in warehouses if w.id == x), str(x)),
            key="stock_wh_sel",
        )

        if sel_wh_id:
            report = get_warehouse_stock_report(sel_wh_id)

            if report:
                # إضافة مسلسل
                for i, r in enumerate(report, start=1):
                    r["مسلسل"] = i

                df = pd.DataFrame(report)
                # نرتب الأعمدة
                cols_order = ["مسلسل", "item_name", "barcode", "quantity",
                              "min_stock", "status"]
                cols_present = [c for c in cols_order if c in df.columns]
                df = df[cols_present]

                st.dataframe(df, use_container_width=True, hide_index=True)

                low = len([r for r in report if r["status"] == "منخفض"])
                good = len([r for r in report if r["status"] == "جيد"])
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("مخزون جيد", good)
                with c2:
                    st.metric("مخزون منخفض", low)
            else:
                st.info("لا توجد أصناف في هذا المخزن.")


# ==========================================
# التبويب 3: تحويل بين المخازن
# ==========================================
with tab3:
    st.subheader("🔄 تحويل صنف بين مخزنين")

    sub_t1, sub_t2 = st.tabs(["➕ تحويل جديد", "📋 سجل التحويلات"])

    # ============ تحويل جديد ============
    with sub_t1:
        st.caption("💡 بعد التحويل، الحقول هتتفرّغ تلقائيًا.")

        warehouses = db.query(Warehouse).filter(
            Warehouse.is_active == True
        ).all()

        if len(warehouses) < 2:
            st.warning("⚠️ يجب وجود مخزنين نشطين على الأقل.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                from_wh_id = st.selectbox(
                    "من مخزن:",
                    options=[w.id for w in warehouses],
                    format_func=lambda x: next(
                        (w.name for w in warehouses if w.id == x), str(x)),
                    key="tr_from",
                )
            with col2:
                to_wh_id = st.selectbox(
                    "إلى مخزن:",
                    options=[w.id for w in warehouses],
                    format_func=lambda x: next(
                        (w.name for w in warehouses if w.id == x), str(x)),
                    key="tr_to",
                )

            items = db.query(models.Item).filter(
                models.Item.is_kit == False
            ).all()
            item_dict = {it.id: it.name for it in items}

            if not items:
                st.warning("لا توجد أصناف.")
            else:
                sel_item_id = st.selectbox(
                    "اختر الصنف:",
                    options=list(item_dict.keys()),
                    format_func=lambda x: item_dict[x],
                    key="tr_item",
                )

                if sel_item_id and from_wh_id:
                    current_stock = get_stock_level(from_wh_id, sel_item_id)
                    st.info(f"💰 الرصيد في المخزن المصدر: **{current_stock}**")

                quantity = st.number_input(
                    "الكمية:", min_value=1, step=1, key="tr_qty",
                )
                tr_notes = st.text_area("ملاحظات (اختياري):", key="tr_notes")

                if st.button("🔄 تنفيذ التحويل", type="primary",
                             use_container_width=True):
                    if from_wh_id == to_wh_id:
                        st.error("❌ لا يمكن التحويل بين نفس المخزن.")
                    elif not sel_item_id:
                        st.error("❌ يرجى اختيار صنف.")
                    elif quantity <= 0:
                        st.error("❌ كمية غير صحيحة.")
                    else:
                        try:
                            transfer_between_warehouses(
                                from_warehouse_id=from_wh_id,
                                to_warehouse_id=to_wh_id,
                                item_id=sel_item_id,
                                quantity=quantity,
                                notes=tr_notes or None,
                                created_by=current_user_id,
                            )
                            st.success("✅ تم التحويل!")
                            st.balloons()

                            queue_state_updates(
                                delete_keys=("tr_item", "tr_qty", "tr_notes"),
                                set_values={"tr_qty": 1, "tr_notes": ""},
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ خطأ: {e}")

    # ============ سجل التحويلات ============
    with sub_t2:
        st.markdown("### 📋 سجل التحويلات")

        transfers = db.query(WarehouseTransfer).order_by(
            WarehouseTransfer.date.desc()
        ).limit(50).all()

        if not transfers:
            st.info("لا توجد تحويلات.")
        else:
            wh_map = {w.id: w.name for w in db.query(Warehouse).all()}
            item_map = {it.id: it.name for it in db.query(models.Item).all()}

            rows = []
            for idx, t in enumerate(transfers, start=1):
                rows.append({
                    "مسلسل": idx,
                    "ID": t.id,
                    "التاريخ": t.date.strftime("%Y-%m-%d %H:%M") if t.date else "—",
                    "من": wh_map.get(t.from_warehouse_id, "—"),
                    "إلى": wh_map.get(t.to_warehouse_id, "—"),
                    "الصنف": item_map.get(t.item_id, "—"),
                    "الكمية": float(t.quantity or 0),
                    "ملاحظات": t.notes or "—",
                })
            df = pd.DataFrame(rows)
            st.dataframe(df.drop(columns=["ID"]), use_container_width=True,
                         hide_index=True)

            # حذف تحويل
            if can_modify():
                st.markdown("---")
                st.markdown("#### 🗑 حذف تحويل")
                st.caption("⚠️ حذف التحويل سيعكس الكميات على المخزنين.")

                del_id = st.selectbox(
                    "اختر تحويل:",
                    options=[t.id for t in transfers],
                    format_func=lambda x: next(
                        (f"#{t.id} — {wh_map.get(t.from_warehouse_id, '?')} → "
                         f"{wh_map.get(t.to_warehouse_id, '?')} — "
                         f"{t.quantity} {item_map.get(t.item_id, '?')}"
                         for t in transfers if t.id == x),
                        str(x)),
                    key="del_tr_sel",
                )

                confirm = st.checkbox("✅ أؤكد الحذف", key="confirm_del_tr")
                if st.button(
                    "🗑 حذف التحويل",
                    type="secondary",
                    disabled=not confirm,
                    use_container_width=True,
                    key="del_tr_btn",
                ):
                    try:
                        _delete_transfer(del_id)
                        st.success("✅ تم الحذف وعكس الأرصدة.")
                        queue_state_updates(delete_keys=("del_tr_sel",
                                                          "confirm_del_tr"))
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 4: الجرد الدوري
# ==========================================
with tab4:
    st.subheader("📋 الجرد الدوري")
    st.caption("💡 بعد كل صنف، الحقول هتتفرّغ تلقائيًا.")

    warehouses = db.query(Warehouse).filter(
        Warehouse.is_active == True
    ).all()

    if not warehouses:
        st.warning("⚠️ لا توجد مخازن نشطة.")
    else:
        sel_wh_id = st.selectbox(
            "اختر المخزن للجرد:",
            options=[w.id for w in warehouses],
            format_func=lambda x: next(
                (w.name for w in warehouses if w.id == x), str(x)),
            key="inv_wh_sel",
        )

        if sel_wh_id:
            stocks = db.query(StockLevel).filter(
                StockLevel.warehouse_id == sel_wh_id,
                StockLevel.quantity > 0,
            ).all()

            if stocks:
                st.markdown("### 📝 أدخل الكميات الفعلية")

                for idx, stock in enumerate(stocks, start=1):
                    item = db.query(models.Item).filter(
                        models.Item.id == stock.item_id
                    ).first()
                    if not item:
                        continue

                    st.markdown(f"**{idx}. {item.name}** "
                                f"({item.barcode or 'بدون باركود'})")
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1:
                        st.caption(f"رصيد النظام: {stock.quantity}")
                    with c2:
                        counted = st.number_input(
                            "الفعلي:", min_value=0,
                            value=int(stock.quantity),
                            step=1,
                            key=f"count_{stock.id}",
                        )
                    with c3:
                        if st.button("💾 حفظ", key=f"save_{stock.id}"):
                            try:
                                create_stock_count(
                                    warehouse_id=sel_wh_id,
                                    item_id=stock.item_id,
                                    counted_quantity=counted,
                                    counted_by=current_user_id,
                                )
                                st.success(f"✅ تم تحديث '{item.name}'.")
                                queue_state_updates(
                                    delete_keys=(f"count_{stock.id}",)
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ {e}")

                    st.markdown("---")
            else:
                st.info("لا توجد أصناف في هذا المخزن.")


# ==========================================
# التبويب 5: تقارير المخزون
# ==========================================
with tab5:
    st.subheader("📈 تقارير المخزون")

    rt1, rt2 = st.tabs(["📊 تقرير شامل", "📋 سجل الجرد"])

    with rt1:
        warehouses = db.query(Warehouse).filter(
            Warehouse.is_active == True
        ).all()

        if warehouses:
            all_stocks = []
            for wh in warehouses:
                stocks = db.query(StockLevel).filter(
                    StockLevel.warehouse_id == wh.id,
                    StockLevel.quantity > 0,
                ).all()
                for stock in stocks:
                    item = db.query(models.Item).filter(
                        models.Item.id == stock.item_id
                    ).first()
                    if item:
                        all_stocks.append({
                            "المخزن": wh.name,
                            "الصنف": item.name,
                            "الباركود": item.barcode or "—",
                            "الكمية": float(stock.quantity or 0),
                            "الحد الأدنى": float(item.min_stock or 0),
                            "الحالة": ("⚠️ منخفض"
                                       if (stock.quantity or 0) <= (item.min_stock or 0)
                                       else "✅ جيد"),
                        })

            if all_stocks:
                df = pd.DataFrame(all_stocks)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد بيانات.")
        else:
            st.info("لا توجد مخازن نشطة.")

    with rt2:
        counts = db.query(StockCount).order_by(
            StockCount.date.desc()
        ).limit(50).all()

        if counts:
            wh_map = {w.id: w.name for w in db.query(Warehouse).all()}
            item_map = {it.id: it.name for it in db.query(models.Item).all()}

            rows = []
            for idx, c in enumerate(counts, start=1):
                rows.append({
                    "مسلسل": idx,
                    "التاريخ": c.date.strftime("%Y-%m-%d %H:%M") if c.date else "—",
                    "المخزن": wh_map.get(c.warehouse_id, "—"),
                    "الصنف": item_map.get(c.item_id, "—"),
                    "رصيد النظام": float(c.system_quantity or 0),
                    "الفعلي": float(c.counted_quantity or 0),
                    "الفرق": float(c.difference or 0),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True,
                         hide_index=True)
        else:
            st.info("لا توجد عمليات جرد.")

db.close()