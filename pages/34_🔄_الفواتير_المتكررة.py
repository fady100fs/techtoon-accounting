# pages/34_🔄_الفواتير_المتكررة.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify
render_sidebar()

import streamlit as st
import pandas as pd
import traceback
from datetime import datetime, date, timedelta

from database import SessionLocal
import models
from models import RecurrenceFrequency
from services import (
    create_recurring_template,
    get_recurring_templates,
    get_recurring_template,
    get_recurring_template_lines,
    update_recurring_template,
    delete_recurring_template,
    run_recurring_template,
    process_due_recurring_templates,
    get_due_recurring_templates,
)
from period_guard import check_period_open
from auth_required import require_login, get_current_user_id, get_current_user_name
from form_manager import clear_form, show_clear_hint

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="الفواتير المتكررة", page_icon="🔄", layout="wide")
st.title("🔄 الفواتير المتكررة")
show_clear_hint()   # ✅ تلميح
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")


# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لمفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "rec_"


db = SessionLocal()


# ==========================================
# التبويبات
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "➕ قالب جديد",
    "📋 القوالب",
    "⏰ المستحقة التنفيذ",
    "⚙️ تعديل / حذف",
])


# ==========================================
# التبويب 1: إنشاء قالب جديد
# ==========================================
with tab1:
    st.subheader("➕ إنشاء قالب فاتورة متكررة")
    st.caption(
        "💡 الفواتير المتكررة تُستخدم للإيجار الشهري، الصيانة الدورية، "
        "الاشتراكات، الرواتب الثابتة..."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        t_name = st.text_input(
            "اسم القالب:",
            placeholder="مثال: إيجار شهري، صيانة دورية...",
            key=f"{PFX}new_name",   # ✅
        )
        t_type = st.radio(
            "نوع الفاتورة:",
            ["sale (بيع)", "purchase (شراء)"],
            horizontal=True,
            key=f"{PFX}new_type",   # ✅
        )
        actual_type = "sale" if "sale" in t_type else "purchase"
    with col_b:
        freq_labels = [f.value for f in RecurrenceFrequency]
        freq_default = RecurrenceFrequency.MONTHLY.value
        t_freq = st.selectbox(
            "التكرار:",
            options=freq_labels,
            index=freq_labels.index(freq_default),
            key=f"{PFX}new_freq",   # ✅
        )
        t_auto_post = st.checkbox(
            "تنفيذ تلقائي عند الاستحقاق",
            value=False,
            key=f"{PFX}new_auto",   # ✅
            help="لو غير محدد، سيظهر القالب كمستحق فقط وسيتم التنفيذ يدوياً.",
        )

    col_c, col_d = st.columns(2)
    with col_c:
        t_start = st.date_input(
            "تاريخ البداية:",
            value=date.today(),
            key=f"{PFX}new_start",   # ✅
        )
    with col_d:
        has_end = st.checkbox(
            "تاريخ نهاية",
            key=f"{PFX}new_has_end",   # ✅
        )
        if has_end:
            t_end = st.date_input(
                "تاريخ النهاية:",
                value=date.today() + timedelta(days=365),
                key=f"{PFX}new_end",   # ✅
            )
        else:
            t_end = None

    # اختيار الطرف
    if actual_type == "sale":
        parties = db.query(models.Party).filter(models.Party.type == "customer").all()
        party_label = "العميل:"
    else:
        parties = db.query(models.Party).filter(models.Party.type == "supplier").all()
        party_label = "المورد:"

    if not parties:
        st.error(f"⚠️ لا يوجد {'عملاء' if actual_type == 'sale' else 'موردين'}!")
        st.stop()

    party_dict = {p.id: p.name for p in parties}
    selected_party_id = st.selectbox(
        party_label,
        options=list(party_dict.keys()),
        format_func=lambda x: party_dict[x],
        key=f"{PFX}new_party",   # ✅
    )

    st.markdown("---")
    st.markdown("### 📋 أصناف القالب")

    items = db.query(models.Item).order_by(models.Item.name).all()
    item_labels = [it.name for it in items]
    item_map = {it.name: it for it in items}

    if not items:
        st.error("⚠️ لا توجد أصناف! أضف أصنافاً أولاً.")
        st.stop()

    default_df = pd.DataFrame({
        "الصنف": pd.Series([None, None], dtype="object"),
        "الكمية": pd.Series([1.0, 1.0], dtype="float64"),
        "السعر": pd.Series([0.0, 0.0], dtype="float64"),
    })

    edited_df = st.data_editor(
        default_df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"{PFX}new_lines_editor",   # ✅
        column_config={
            "الصنف": st.column_config.SelectboxColumn(
                "الصنف", options=item_labels, required=False, width="large"
            ),
            "الكمية": st.column_config.NumberColumn(
                "الكمية", min_value=0.0, step=1.0, format="%.2f"
            ),
            "السعر": st.column_config.NumberColumn(
                "السعر", min_value=0.0, step=0.1, format="%.2f"
            ),
        },
    )

    # تحويل السطور
    lines = []
    total = 0.0
    for _, row in edited_df.iterrows():
        name = row.get("الصنف")
        if name is None or pd.isna(name) or not str(name).strip():
            continue
        q = float(row.get("الكمية", 0) or 0)
        p = float(row.get("السعر", 0) or 0)
        if q <= 0:
            continue
        lines.append({"item_name": str(name), "quantity": q, "price": p})
        total += q * p

    if lines:
        st.success(f"✅ **{len(lines)}** سطر — المجموع التقديري: **{total:,.2f} ج.م**")
    else:
        st.info("ℹ️ أضف سطراً واحداً على الأقل.")

    st.markdown("---")

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        t_discount = st.number_input(
            "خصم %:", min_value=0.0, max_value=100.0,
            value=0.0, step=1.0, key=f"{PFX}new_discount",   # ✅
        )
    with col_d2:
        t_tax = st.number_input(
            "ضريبة %:", min_value=0.0, max_value=100.0,
            value=14.0, step=1.0, key=f"{PFX}new_tax",   # ✅
        )

    t_notes = st.text_area("ملاحظات:", key=f"{PFX}new_notes", height=68)   # ✅

    st.markdown("---")
    if st.button("💾 حفظ القالب", type="primary", use_container_width=True,
                 key=f"{PFX}new_save"):
        if not t_name.strip():
            st.error("❌ اسم القالب مطلوب.")
        elif not lines:
            st.error("❌ أضف سطراً واحداً على الأقل.")
        elif t_end and t_end < t_start:
            st.error("❌ تاريخ النهاية قبل البداية.")
        else:
            try:
                start_dt = datetime.combine(t_start, datetime.min.time())
                end_dt = datetime.combine(t_end, datetime.min.time()) if t_end else None
                freq_enum = next(f for f in RecurrenceFrequency if f.value == t_freq)

                create_recurring_template(
                    name=t_name.strip(),
                    party_id=selected_party_id,
                    invoice_type=actual_type,
                    frequency=freq_enum,
                    start_date=start_dt,
                    lines=lines,
                    end_date=end_dt,
                    discount_percentage=t_discount,
                    tax_rate=t_tax,
                    notes=t_notes.strip() or None,
                    auto_post=t_auto_post,
                    created_by=current_user_id,
                )

                st.success(f"✅ تم إنشاء القالب '{t_name}' بنجاح!")
                st.balloons()

                # ✅ تفريغ كل حقول النموذج
                clear_form(PFX)
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
                st.code(traceback.format_exc())


# ==========================================
# التبويب 2: القائمة
# ==========================================
with tab2:
    st.subheader("📋 قوالب الفواتير المتكررة")

    templates = get_recurring_templates()
    if not templates:
        st.info("لا توجد قوالب بعد.")
    else:
        party_ids = list({t.party_id for t in templates if t.party_id})
        party_map = {}
        if party_ids:
            party_map = {
                p.id: p.name for p in db.query(models.Party).filter(
                    models.Party.id.in_(party_ids)
                ).all()
            }

        data = []
        for t in templates:
            data.append({
                "ID": t.id,
                "الاسم": t.name,
                "النوع": "بيع" if t.invoice_type == "sale" else "شراء",
                "الطرف": party_map.get(t.party_id, "—"),
                "التكرار": t.frequency.value if t.frequency else "—",
                "التنفيذ التالي": t.next_run_date.strftime("%Y-%m-%d") if t.next_run_date else "—",
                "آخر تنفيذ": t.last_run_date.strftime("%Y-%m-%d") if t.last_run_date else "لم يُنفّذ",
                "عدد المرات": t.runs_count or 0,
                "الحالة": "✅ نشط" if t.is_active else "⛔ معطل",
                "تلقائي": "✅" if t.auto_post else "❌",
            })
        df = pd.DataFrame(data)
        st.dataframe(
            df.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "عدد المرات": st.column_config.NumberColumn("عدد المرات", format="%d"),
            },
        )

        st.caption(f"📊 إجمالي: **{len(templates)}** قالب")


# ==========================================
# التبويب 3: المستحقة التنفيذ
# ==========================================
with tab3:
    st.subheader("⏰ القوالب المستحقة التنفيذ")

    due = get_due_recurring_templates()

    if not due:
        st.success("✅ لا توجد قوالب مستحقة حالياً.")
    else:
        st.warning(f"⚠️ يوجد **{len(due)}** قالب مستحق التنفيذ.")

        party_ids = list({t.party_id for t in due if t.party_id})
        party_map = {}
        if party_ids:
            party_map = {
                p.id: p.name for p in db.query(models.Party).filter(
                    models.Party.id.in_(party_ids)
                ).all()
            }

        rows = []
        for t in due:
            rows.append({
                "ID": t.id,
                "الاسم": t.name,
                "الطرف": party_map.get(t.party_id, "—"),
                "النوع": "بيع" if t.invoice_type == "sale" else "شراء",
                "التكرار": t.frequency.value if t.frequency else "—",
                "الاستحقاق": t.next_run_date.strftime("%Y-%m-%d") if t.next_run_date else "—",
                "تلقائي": "✅" if t.auto_post else "❌",
            })
        df = pd.DataFrame(rows)
        st.dataframe(
            df.drop(columns=["ID"]), use_container_width=True, hide_index=True
        )

        st.markdown("---")
        col_a, col_b = st.columns(2)

        with col_a:
            if st.button(
                "▶️ تنفيذ الكل الآن",
                type="primary",
                use_container_width=True,
                key=f"{PFX}process_all",
            ):
                try:
                    result = process_due_recurring_templates(
                        auto_run=True, created_by=current_user_id
                    )
                    st.success(
                        f"✅ تم تنفيذ {result['processed']} قالب، "
                        f"فشل {result['failed']}."
                    )
                    if result['results']:
                        for r in result['results']:
                            if r['status'] == 'success':
                                st.write(
                                    f"✅ {r['template'].name} → "
                                    f"فاتورة {r['invoice_number']}"
                                )
                            else:
                                st.write(
                                    f"❌ {r['template'].name}: {r.get('error', '')}"
                                )
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

        with col_b:
            st.caption(
                "💡 لتنفيذ قالب واحد فقط، اذهب إلى تبويب **⚙️ تعديل / حذف**."
            )


# ==========================================
# التبويب 4: تعديل / حذف
# ==========================================
with tab4:
    st.subheader("⚙️ تعديل / حذف / تنفيذ قالب")

    templates = get_recurring_templates()
    if not templates:
        st.info("لا توجد قوالب.")
    else:
        t_opts = {t.id: f"{t.name} — {t.frequency.value if t.frequency else ''}"
                  for t in templates}
        selected_id = st.selectbox(
            "اختر قالباً:",
            options=list(t_opts.keys()),
            format_func=lambda x: t_opts[x],
            key=f"{PFX}manage_sel",   # ✅
        )

        if selected_id:
            t = get_recurring_template(selected_id)
            if t:
                # تفاصيل
                st.markdown(f"### 📄 تفاصيل: **{t.name}**")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("التكرار", t.frequency.value if t.frequency else "—")
                with c2:
                    st.metric("عدد التنفيذات", t.runs_count or 0)
                with c3:
                    st.metric(
                        "التنفيذ التالي",
                        t.next_run_date.strftime("%Y-%m-%d") if t.next_run_date else "—",
                    )
                with c4:
                    st.metric("الحالة", "✅ نشط" if t.is_active else "⛔ معطل")

                # السطور
                lines = get_recurring_template_lines(t.id)
                if lines:
                    df = pd.DataFrame([{
                        "الصنف": l["item_name"],
                        "الكمية": l["quantity"],
                        "السعر": l["price"],
                        "الإجمالي": l["quantity"] * l["price"],
                    } for l in lines])
                    st.dataframe(
                        df, use_container_width=True, hide_index=True,
                        column_config={
                            "السعر": st.column_config.NumberColumn("السعر", format="%.2f"),
                            "الإجمالي": st.column_config.NumberColumn("الإجمالي", format="%.2f"),
                        },
                    )

                st.markdown("---")

                col_run, col_toggle = st.columns(2)

                # تنفيذ الآن (force)
                with col_run:
                    st.markdown("#### ▶️ تنفيذ القالب الآن")
                    st.caption("ينشئ فاتورة فعلية بالرغم من عدم الاستحقاق.")
                    if st.button(
                        "▶️ تنفيذ الآن",
                        type="primary",
                        use_container_width=True,
                        key=f"{PFX}run_now_{t.id}",   # ✅
                    ):
                        try:
                            r = run_recurring_template(
                                t.id, force=True, created_by=current_user_id
                            )
                            st.success(
                                f"✅ تم إنشاء فاتورة `{r['invoice_number']}`"
                            )
                            # ✅ تفريغ كل مفاتيح الصفحة
                            clear_form(PFX)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ خطأ: {e}")
                            st.code(traceback.format_exc())

                # تفعيل / تعطيل
                with col_toggle:
                    st.markdown("#### 🔘 تفعيل / تعطيل")
                    if t.is_active:
                        if st.button(
                            "⛔ تعطيل القالب",
                            use_container_width=True,
                            key=f"{PFX}toggle_{t.id}",   # ✅
                        ):
                            try:
                                update_recurring_template(t.id, is_active=False)
                                st.success("✅ تم التعطيل.")
                                clear_form(PFX)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ {e}")
                    else:
                        if st.button(
                            "✅ تفعيل القالب",
                            use_container_width=True,
                            key=f"{PFX}toggle_{t.id}",   # ✅
                        ):
                            try:
                                update_recurring_template(t.id, is_active=True)
                                st.success("✅ تم التفعيل.")
                                clear_form(PFX)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ {e}")

                # تعديل البيانات الأساسية
                st.markdown("---")
                st.markdown("#### ✏️ تعديل البيانات الأساسية")
                with st.form(f"{PFX}edit_form_{t.id}"):
                    e_name = st.text_input(
                        "الاسم:",
                        value=t.name,
                        key=f"{PFX}edit_name_{t.id}",   # ✅
                    )
                    e_freq_labels = [f.value for f in RecurrenceFrequency]
                    e_freq = st.selectbox(
                        "التكرار:",
                        options=e_freq_labels,
                        index=e_freq_labels.index(t.frequency.value) if t.frequency else 0,
                        key=f"{PFX}edit_freq_{t.id}",   # ✅
                    )
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        e_discount = st.number_input(
                            "خصم %:",
                            min_value=0.0,
                            max_value=100.0,
                            value=float(t.discount_percentage or 0),
                            step=1.0,
                            key=f"{PFX}edit_discount_{t.id}",   # ✅
                        )
                    with col_d2:
                        e_tax = st.number_input(
                            "ضريبة %:",
                            min_value=0.0,
                            max_value=100.0,
                            value=float(t.tax_rate or 0),
                            step=1.0,
                            key=f"{PFX}edit_tax_{t.id}",   # ✅
                        )
                    e_auto = st.checkbox(
                        "تنفيذ تلقائي",
                        value=bool(t.auto_post),
                        key=f"{PFX}edit_auto_{t.id}",   # ✅
                    )
                    e_notes = st.text_area(
                        "ملاحظات:",
                        value=t.notes or "",
                        height=68,
                        key=f"{PFX}edit_notes_{t.id}",   # ✅
                    )
                    e_submit = st.form_submit_button(
                        "💾 حفظ التعديلات", type="primary",
                    )

                if e_submit:
                    try:
                        freq_enum = next(f for f in RecurrenceFrequency if f.value == e_freq)
                        update_recurring_template(
                            t.id,
                            name=e_name,
                            frequency=freq_enum,
                            discount_percentage=e_discount,
                            tax_rate=e_tax,
                            notes=e_notes.strip() or None,
                            is_active=t.is_active,
                            auto_post=e_auto,
                        )
                        st.success("✅ تم التعديل.")

                        # ✅ تفريغ كل مفاتيح التعديل
                        clear_form(PFX)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")

                # حذف
                st.markdown("---")
                st.markdown("#### 🗑 حذف القالب")

                if not can_modify():
                    st.info("⛔ الحذف للمدير فقط.")
                else:
                    st.error(
                        f"⚠️ سيتم حذف قالب **{t.name}** نهائياً. "
                        f"لن تُحذف الفواتير المولَّدة مسبقاً."
                    )
                    confirm = st.checkbox(
                        "أؤكد الحذف",
                        key=f"{PFX}confirm_del_{t.id}",   # ✅
                    )
                    if st.button(
                        "🗑 حذف القالب",
                        type="secondary",
                        disabled=not confirm,
                        use_container_width=True,
                        key=f"{PFX}del_btn_{t.id}",   # ✅
                    ):
                        try:
                            delete_recurring_template(t.id)
                            st.success(f"✅ تم حذف '{t.name}'.")

                            # ✅ تفريغ كل مفاتيح الصفحة
                            clear_form(PFX)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {e}")

db.close()