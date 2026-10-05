# pages/4_🧾_الفواتير.py
import re
import sys
import traceback
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

# ✅ 1. إعدادات الصفحة أولاً
st.set_page_config(page_title="الفواتير", page_icon="🧾", layout="wide")

# القائمة الجانبية + الصلاحيات + queue_state_updates
from sidebar import render_sidebar, queue_state_updates
render_sidebar()

# ✅ الاختصارات
from shortcuts import install_shortcuts, show_shortcuts_guide

from sqlalchemy import Float, Integer, Numeric
from database import SessionLocal
import models
from services import create_invoice, create_payment
from auth_required import require_login, get_current_user_id, get_current_user_name
from code_search import CodeSearch, FormState

# ✅ 2. التحقق من الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

# ✅ 3. التنقل بـ Enter
from keyboard_nav import enable_enter_navigation, add_enter_hint
enable_enter_navigation()
add_enter_hint()

# ✅ 4. الاختصارات — في بداية الصفحة قبل أي widget آخر
show_shortcuts_guide()
kb = install_shortcuts()


# ==========================================
# أدوات مساعدة
# ==========================================
CODE_FIELDS = [f for f in ("code", "item_code", "barcode", "sku") if hasattr(models.Item, f)]


def zero_null_numbers(obj):
    changed = False
    for col in obj.__table__.columns:
        if col.primary_key or col.foreign_keys:
            continue
        if isinstance(col.type, (Integer, Float, Numeric)) and getattr(obj, col.key, 0) is None:
            setattr(obj, col.key, 0)
            changed = True
    return changed


def used_invoice_numbers(db):
    used = {}
    if hasattr(models.Invoice, "invoice_number"):
        for (num,) in db.query(models.Invoice.invoice_number).all():
            m = re.search(r"(\d+)$", str(num or ""))
            if m:
                used.setdefault(int(m.group(1)), str(num))
    return used


def format_invoice_number(n):
    return f"INV-{int(n):06d}"


def _line_info(db, ln):
    name = None
    item_obj = getattr(ln, "item", None)
    if item_obj is not None:
        name = getattr(item_obj, "name", None)
    if name is None and getattr(ln, "item_id", None) is not None:
        it = db.query(models.Item).filter(models.Item.id == ln.item_id).first()
        name = it.name if it else None
    if name is None:
        name = getattr(ln, "item_name", None) or getattr(ln, "description", None) or "—"

    qty = getattr(ln, "quantity", None)
    price = next(
        (getattr(ln, a) for a in ("unit_price", "price", "sell_price", "cost_price")
         if getattr(ln, a, None) is not None),
        None,
    )
    total = next(
        (getattr(ln, a) for a in ("total", "total_price", "line_total")
         if getattr(ln, a, None) is not None),
        None,
    )
    if total is None and qty is not None and price is not None:
        total = qty * price
    return {"الصنف": name, "الكمية": qty, "السعر": price, "الإجمالي": total}


def invoice_lines(db, invoice):
    for rel in models.Invoice.__mapper__.relationships:
        if rel.uselist and hasattr(rel.mapper.class_, "quantity"):
            return [_line_info(db, ln) for ln in getattr(invoice, rel.key)]
    return None


def _go_new(key, value):
    st.session_state[key] = value


def _clear_edit_state():
    for k in ("_editing_invoice_id", "_editing_invoice_no", "_editing_invoice_type"):
        st.session_state.pop(k, None)


def _delete_invoice_fully(db, invoice):
    inv_id = invoice.id

    db.query(models.InvoiceLine).filter(
        models.InvoiceLine.invoice_id == inv_id
    ).delete(synchronize_session=False)

    db.query(models.InventoryMovement).filter(
        models.InventoryMovement.reference_id == inv_id
    ).delete(synchronize_session=False)

    db.query(models.CostHistory).filter(
        models.CostHistory.invoice_id == inv_id
    ).delete(synchronize_session=False)

    je_ids = [row[0] for row in db.query(models.JournalEntry.id).filter(
        models.JournalEntry.reference_id == inv_id,
        models.JournalEntry.reference_type.in_(["invoice", "cogs"]),
    ).all()]
    if je_ids:
        db.query(models.JournalLine).filter(
            models.JournalLine.entry_id.in_(je_ids)
        ).delete(synchronize_session=False)
        db.query(models.JournalEntry).filter(
            models.JournalEntry.id.in_(je_ids)
        ).delete(synchronize_session=False)

    db.delete(invoice)
    db.commit()


def _load_invoice_data(db, invoice):
    inv_id = invoice.id
    inv_no_str = invoice.invoice_number
    inv_type = invoice.type or "sale"
    party_id = invoice.party_id
    discount = float(invoice.discount_percentage or 0.0)
    tax = float(invoice.tax_rate or 0.0)

    lines = db.query(models.InvoiceLine).filter(
        models.InvoiceLine.invoice_id == inv_id
    ).all()
    new_items = []
    for ln in lines:
        item = db.query(models.Item).filter(models.Item.id == ln.item_id).first()
        if item:
            new_items.append({
                'item_name': item.name,
                'quantity': float(ln.quantity or 0),
                'price': float(ln.price or 0),
            })

    return {
        "id": inv_id,
        "no_str": inv_no_str,
        "type": inv_type,
        "party_id": party_id,
        "discount": discount,
        "tax": tax,
        "items": new_items,
    }


def _prepare_invoice_for_edit(data, fs, no_key):
    st.session_state["_editing_invoice_id"] = data["id"]
    st.session_state["_editing_invoice_no"] = data["no_str"]
    st.session_state["_editing_invoice_type"] = data["type"]

    m = re.search(r"(\d+)$", str(data["no_str"] or ""))
    inv_num = int(m.group(1)) if m else 1

    queue_state_updates(
        delete_keys=("inv_items_editor",),
        set_values={
            no_key: inv_num,
            fs.key("type"): "sale (بيع)" if data["type"] == "sale" else "purchase (شراء)",
            fs.key(f"party_{data['type']}"): data["party_id"],
            fs.key("discount"): data["discount"],
            fs.key("tax"): data["tax"],
            "invoice_items": data["items"],
        },
    )


def show_saved_invoice(db, inv_no, inv_text, next_no, no_key, fs, kb=None):
    """عرض فاتورة محفوظة (للقراءة) + أزرار التعديل والحذف. تدعم Alt+4 للحذف و Alt+0 للتعديل."""
    invoice = None
    try:
        invoice = (db.query(models.Invoice)
                   .filter(models.Invoice.invoice_number == inv_text).first())
        if invoice is None:
            st.warning("تعذّر العثور على الفاتورة.")
            return

        st.subheader(f"📄 فاتورة رقم {inv_no}  ({inv_text})")

        facts = {}
        for attr, title in (("invoice_type", "النوع"), ("status", "الحالة"),
                            ("invoice_date", "التاريخ"), ("created_at", "تاريخ الإنشاء")):
            v = getattr(invoice, attr, None)
            if v is not None:
                facts[title] = str(getattr(v, "value", v))[:19]
        pid = getattr(invoice, "party_id", None)
        if pid is not None:
            p = db.query(models.Party).filter(models.Party.id == pid).first()
            if p:
                facts["العميل/المورد"] = p.name
        for attr, title in (("total_amount", "الإجمالي"), ("discount_amount", "الخصم"),
                            ("tax_amount", "الضريبة"), ("net_amount", "الصافي")):
            v = getattr(invoice, attr, None)
            if v is not None:
                facts[title] = f"{float(v):,.2f}"

        if facts:
            cols = st.columns(min(len(facts), 4))
            for i, (k, v) in enumerate(facts.items()):
                cols[i % len(cols)].metric(k, v)

        lines = invoice_lines(db, invoice)
        if lines is None:
            st.warning("تعذّر التعرف على أصناف هذه الفاتورة في قاعدة البيانات.")
        elif not lines:
            st.info("لا توجد أصناف في هذه الفاتورة.")
        else:
            st.markdown("**أصناف الفاتورة:**")
            st.dataframe(pd.DataFrame(lines), use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"❌ تعذّر عرض الفاتورة: {e}")
        st.code(traceback.format_exc())

    st.markdown("---")
    st.markdown("### ⚙️ إدارة الفاتورة")
    col_edit, col_del = st.columns(2)

    # ✅ Alt+0 = تحميل للتعديل على الفاتورة المعروضة
    load_for_edit = False
    if invoice is not None:
        # زر التعديل
        with col_edit:
            if st.button("✏️ تحميل للتعديل", type="primary", use_container_width=True,
                         key=f"edit_inv_{invoice.id}"):
                load_for_edit = True

        # ✅ Alt+0 (حفظ) في وضع "الفاتورة المعروضة" = نعتبره تحميل للتعديل
        if kb and kb.get('save'):
            load_for_edit = True

        if load_for_edit:
            try:
                data = _load_invoice_data(db, invoice)
                _prepare_invoice_for_edit(data, fs, no_key)
                st.session_state["_inv_edit_flash"] = (
                    f"✏️ وضع التعديل: فاتورة {invoice.invoice_number}. "
                    f"عدّل الأصناف/البيانات ثم اضغط **Alt+0** أو زر حفظ التعديلات."
                )
                st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"❌ تعذّر تحميل الفاتورة للتعديل: {e}")
                st.code(traceback.format_exc())

        # الحذف
        with col_del:
            confirm_key = f"confirm_del_inv_{invoice.id}"
            confirm = st.checkbox("تأكيد الحذف", key=confirm_key)

            delete_now = False
            if st.button("🗑 حذف الفاتورة بالكامل", type="secondary",
                         use_container_width=True, disabled=not confirm,
                         key=f"del_inv_{invoice.id}"):
                delete_now = True

            # ✅ Alt+4 = حذف الفاتورة المعروضة (يشترط تأكيد الحذف)
            if kb and kb.get('delete') and confirm:
                delete_now = True

            if delete_now:
                try:
                    deleted_no = invoice.invoice_number
                    _delete_invoice_fully(db, invoice)
                    st.session_state["_inv_flash"] = (
                        f"✅ تم حذف الفاتورة {deleted_no} بالكامل."
                    )
                    queue_state_updates(
                        delete_keys=("inv_items_editor",),
                        set_values={
                            no_key: next_no,
                            "invoice_items": [],
                        },
                    )
                    st.rerun()
                except Exception as e:
                    db.rollback()
                    st.error(f"❌ تعذّر حذف الفاتورة: {e}")
                    st.code(traceback.format_exc())

    st.markdown("---")
    st.button("➕ فاتورة جديدة", on_click=_go_new, args=(no_key, next_no))


# ==========================================
# الصفحة
# ==========================================
fs = FormState("inv", cart_keys=("invoice_items",))

st.title("🧾 إنشاء الفواتير")
st.info(f"👤 المستخدم: **{current_user_name}**")

flash = st.session_state.pop("_inv_flash", None)
if flash:
    st.success(flash)
    st.balloons()

db = SessionLocal()

# ==========================================
# التحقق من بيانات أساسية
# ==========================================
parties = db.query(models.Party).all()
items = db.query(models.Item).all()

if not parties:
    st.error("⚠️ لا يوجد عملاء أو موردين! يرجى إضافتهم أولاً من صفحة 'العملاء والموردين'")
    st.stop()

if not items:
    st.error("⚠️ لا توجد أصناف! يرجى إضافتها أولاً من صفحة 'الأصناف'")
    st.stop()

# ==========================================
# 🔢 رقم الفاتورة
# ==========================================
used_numbers = used_invoice_numbers(db)
next_no = (max(used_numbers) + 1) if used_numbers else 1
no_key = fs.key("inv_no")

editing_id = st.session_state.get("_editing_invoice_id")
is_editing = editing_id is not None

edit_flash = st.session_state.pop("_inv_edit_flash", None)
if edit_flash:
    st.warning(edit_flash)

if is_editing:
    editing_no = st.session_state.get("_editing_invoice_no", "?")
    col_banner, col_cancel = st.columns([4, 1])
    with col_banner:
        st.info(
            f"🔴 **وضع التعديل** — أنت تعدّل الفاتورة **{editing_no}**. "
            f"اضغط **Alt+0** (أو زر حفظ التعديلات) للتأكيد، "
            f"أو **Alt+1** (جديد) للخروج بدون حفظ."
        )
    with col_cancel:
        if st.button("❌ إلغاء التعديل", use_container_width=True, key="cancel_edit_btn"):
            _clear_edit_state()
            queue_state_updates(
                delete_keys=("inv_items_editor",),
                set_values={
                    no_key: next_no,
                    "invoice_items": [],
                },
            )
            st.rerun()

# ✅ Alt+1 (جديد) — يُنفّذ فورًا قبل أي widget
if kb['new']:
    _clear_edit_state()
    queue_state_updates(
        delete_keys=("inv_items_editor",),
        set_values={
            no_key: next_no,
            "invoice_items": [],
        },
    )
    st.rerun()

# ✅ Alt+2 (تفريغ) — يفرّغ السلة فقط
if kb['clear']:
    queue_state_updates(
        delete_keys=("inv_items_editor",),
        set_values={"invoice_items": []},
    )
    st.rerun()

col_no, col_state = st.columns([1, 3])
with col_no:
    inv_no = int(st.number_input("🔢 رقم الفاتورة:", min_value=1, step=1, value=next_no, key=no_key))
is_existing = inv_no in used_numbers
with col_state:
    st.write("")
    if is_existing and not is_editing:
        st.info(f"📂 الفاتورة رقم {inv_no} محفوظة سابقاً، وبياناتها معروضة أدناه.")
    elif is_editing:
        st.caption(f"✏️ في وضع التعديل — يمكنك تغيير الرقم، لكن لن يُسمح بتكراره.")
    else:
        st.caption(f"✅ الرقم {inv_no} متاح. (الرقم التالي المقترح: {next_no})")

# ✅ رقم موجود + مش في وضع تعديل → نعرض الفاتورة المحفوظة (تمرير kb لتفعيل Alt+0 / Alt+4)
if is_existing and not is_editing:
    show_saved_invoice(db, inv_no, used_numbers[inv_no], next_no, no_key, fs, kb=kb)
    db.close()
    st.stop()

# ==========================================
# نوع الفاتورة
# ==========================================
invoice_type = st.radio("نوع الفاتورة:", ["sale (بيع)", "purchase (شراء)"], key=fs.key("type"))
actual_type = "sale" if "sale" in invoice_type else "purchase"
type_ar = "بيع" if actual_type == "sale" else "شراء"

# ==========================================
# اختيار العميل/المورد
# ==========================================
if actual_type == "sale":
    customers = db.query(models.Party).filter(models.Party.type == 'customer').all()
    if not customers:
        st.warning("⚠️ لا يوجد عملاء! يرجى إضافة عملاء أولاً")
        st.stop()
    party_dict = {p.id: p.name for p in customers}
    label = "اختر العميل:"
else:
    suppliers = db.query(models.Party).filter(models.Party.type == 'supplier').all()
    if not suppliers:
        st.warning("⚠️ لا يوجد موردين! يرجى إضافة موردين أولاً")
        st.stop()
    party_dict = {p.id: p.name for p in suppliers}
    label = "اختر المورد:"

selected_party_id = st.selectbox(
    label,
    options=list(party_dict.keys()),
    format_func=lambda x: party_dict[x],
    key=fs.key(f"party_{actual_type}"),
)

# ==========================================
# الأصناف
# ==========================================
if 'invoice_items' not in st.session_state:
    st.session_state.invoice_items = []

st.markdown("---")
st.subheader("أصناف الفاتورة")

if not CODE_FIELDS:
    st.caption("ℹ️ لا يوجد حقل كود في جدول الأصناف، لذلك يعمل البحث بالاسم فقط.")

cs = CodeSearch(
    items,
    prefix=fs.prefix(),
    code_field=CODE_FIELDS,
    name_field="name",
    price_field=(lambda it: it.sell_price or 0.0) if actual_type == "sale"
                else (lambda it: it.cost_price or 0.0),
    qty_key=fs.key("qty"),
)

cs.render_input()

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    sel_label = st.selectbox("الصنف:", cs.labels, key=cs.item_key)

cs.sync_price(sel_label, actual_type)
current_item = cs.by_label(sel_label)

with col2:
    qty = st.number_input("الكمية:", min_value=1, step=1, key=fs.key("qty"))

with col3:
    price = st.number_input("السعر:", min_value=0.0, step=0.1, key=cs.price_key)

if st.button("➕ إضافة للفاتورة"):
    if current_item is not None and qty > 0 and price > 0:
        st.session_state.invoice_items.append({
            'item_name': current_item.name,
            'quantity': qty,
            'price': price
        })
        st.toast(f"✅ تمت إضافة {current_item.name}")
        st.rerun()
    else:
        st.error("يرجى اختيار صنف وإدخال كمية وسعر صحيحين")

# ==========================================
# جدول تفاصيل الفاتورة
# ==========================================
save_clicked = False  # هنحدده لاحقًا من الاختصار أو الزر

if st.session_state.invoice_items:
    st.markdown("---")
    st.subheader("تفاصيل الفاتورة")
    st.caption("💡 عدّل الكمية/السعر مباشرة (اضغط Enter للتأكيد). 🗑 احذف صف بالماوس. "
               "➕ أضف صف بالزر أسفل الجدول.")

    df_edit = pd.DataFrame([
        {
            'الصنف': it['item_name'],
            'الكمية': float(it['quantity']),
            'السعر': float(it['price']),
            'الإجمالي': float(it['quantity']) * float(it['price']),
        }
        for it in st.session_state.invoice_items
    ])

    edited_df = st.data_editor(
        df_edit,
        num_rows="dynamic",
        use_container_width=True,
        key="inv_items_editor",
        column_config={
            "الصنف": st.column_config.TextColumn("الصنف", required=True, width="large"),
            "الكمية": st.column_config.NumberColumn("الكمية", min_value=0.0, step=1.0, format="%.2f"),
            "السعر": st.column_config.NumberColumn("السعر", min_value=0.0, step=0.1, format="%.2f"),
            "الإجمالي": st.column_config.NumberColumn("الإجمالي", disabled=True, format="%.2f"),
        },
    )

    new_items = []
    for _, row in edited_df.iterrows():
        name = str(row['الصنف']).strip() if pd.notna(row['الصنف']) else ""
        q = float(row['الكمية']) if pd.notna(row['الكمية']) else 0.0
        p = float(row['السعر']) if pd.notna(row['السعر']) else 0.0
        if name and q > 0:
            new_items.append({'item_name': name, 'quantity': q, 'price': p})

    st.session_state.invoice_items = new_items

    if not edited_df.empty:
        _q = edited_df['الكمية'].fillna(0).astype(float)
        _p = edited_df['السعر'].fillna(0).astype(float)
        subtotal = float((_q * _p).sum())
    else:
        subtotal = 0.0

    st.metric("الإجمالي", f"{subtotal:,.2f} ج.م")

    col_disc, col_tax = st.columns(2)
    with col_disc:
        discount_pct = st.number_input("خصم %:", min_value=0.0, max_value=100.0, value=0.0,
                                       step=1.0, key=fs.key("discount"))
    with col_tax:
        tax_pct = st.number_input("ضريبة %:", min_value=0.0, max_value=100.0, value=0.0,
                                  step=1.0, key=fs.key("tax"))

    discount_amount = subtotal * (discount_pct / 100)
    amount_after_discount = subtotal - discount_amount
    tax_amount = amount_after_discount * (tax_pct / 100)
    net_amount = amount_after_discount + tax_amount

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("المجموع", f"{subtotal:,.2f}")
    with col2:
        st.metric("الخصم", f"{discount_amount:,.2f}")
    with col3:
        st.metric("الضريبة", f"{tax_amount:,.2f}")
    with col4:
        st.metric("الصافي", f"{net_amount:,.2f}")

    st.markdown("---")

    col_save, col_clear = st.columns([2, 1])
    with col_save:
        save_label = "💾 حفظ التعديلات (Alt+0)" if is_editing else "💾 حفظ الفاتورة (Alt+0)"
        if st.button(save_label, type="primary", use_container_width=True):
            save_clicked = True
    with col_clear:
        if st.button("🗑 تفريغ السلة (Alt+2)", use_container_width=True):
            queue_state_updates(
                delete_keys=("inv_items_editor",),
                set_values={"invoice_items": []},
            )
            st.rerun()

    # ✅ Alt+0 = حفظ
    if kb['save']:
        save_clicked = True

    if save_clicked:
        can_save = True
        current_num_str = format_invoice_number(inv_no)

        if is_editing:
            existing = db.query(models.Invoice).filter(
                models.Invoice.invoice_number == current_num_str
            ).first()
            if existing is not None and existing.id != editing_id:
                st.error(f"❌ الرقم {inv_no} مستخدم في فاتورة أخرى. غيّر الرقم.")
                can_save = False
        else:
            if inv_no in used_invoice_numbers(db):
                st.error(f"❌ الرقم {inv_no} مستخدم بالفعل. غيّر الرقم.")
                can_save = False

        if not selected_party_id:
            st.error("يرجى اختيار عميل/مورد")
            can_save = False
        elif not st.session_state.invoice_items:
            st.error("يرجى إضافة أصناف للفاتورة")
            can_save = False

        if can_save:
            saved_msg = None
            try:
                names = {ln['item_name'] for ln in st.session_state.invoice_items}
                changed = False
                for it in db.query(models.Item).filter(models.Item.name.in_(names)).all():
                    changed = zero_null_numbers(it) or changed
                party_obj = db.query(models.Party).filter(models.Party.id == selected_party_id).first()
                if party_obj is not None:
                    changed = zero_null_numbers(party_obj) or changed
                if changed:
                    db.commit()

                if is_editing:
                    old = db.query(models.Invoice).filter(models.Invoice.id == editing_id).first()
                    if old is not None:
                        _delete_invoice_fully(db, old)

                invoice = create_invoice(
                    party_id=selected_party_id,
                    invoice_type=actual_type,
                    items=st.session_state.invoice_items,
                    invoice_number=current_num_str,
                    discount_percentage=discount_pct,
                    tax_rate=tax_pct,
                    created_by=current_user_id
                )

                invoice.status = 'paid'
                db.commit()

                action_word = "تعديل" if is_editing else "حفظ"
                saved_msg = f"✅ تم {action_word} فاتورة {type_ar} رقم {current_num_str} بنجاح!"

                _clear_edit_state()
            except Exception as e:
                db.rollback()
                st.error(f"❌ خطأ: {e}")
                st.code(traceback.format_exc())

            if saved_msg:
                st.session_state["_inv_flash"] = saved_msg
                queue_state_updates(
                    delete_keys=("inv_items_editor",),
                    set_values={"invoice_items": []},
                )
                db.close()
                fs.reset()
else:
    st.info("🛒 السلة فارغة. أضف أصنافاً لبدء الفاتورة.")

db.close()