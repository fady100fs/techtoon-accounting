# pages/32_📝_قيود_اليومية.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify
render_sidebar()

import streamlit as st
import pandas as pd
import traceback
from datetime import datetime, date

from database import SessionLocal
import models
from models import Account, AccountType
from services import movement_serial, validate_journal_entry
from period_guard import check_period_open
from auth_required import require_login, get_current_user_id, get_current_user_name
from form_manager import clear_form, show_clear_hint

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="قيود اليومية", page_icon="📝", layout="wide")
st.title("📝 قيود اليومية اليدوية")
show_clear_hint()   # ✅ تلميح
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")


# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لمفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "je_"


db = SessionLocal()


# ==========================================
# أدوات مساعدة
# ==========================================
def _serial(entry_id):
    return movement_serial("JE", entry_id)


def _entry_lines(db, entry_id):
    """يرجع أسطر قيد معينة مع بيانات الحسابات."""
    lines = db.query(models.JournalLine).filter(
        models.JournalLine.entry_id == entry_id
    ).all()

    if not lines:
        return []

    acc_ids = list({l.account_id for l in lines if l.account_id})
    acc_map = {}
    if acc_ids:
        acc_map = {
            a.id: a for a in db.query(Account).filter(
                Account.id.in_(acc_ids)
            ).all()
        }

    rows = []
    for l in lines:
        acc = acc_map.get(l.account_id)
        rows.append({
            "account_id": l.account_id,
            "account_code": acc.code if acc else "—",
            "account_name": acc.name if acc else "—",
            "debit": float(l.debit or 0),
            "credit": float(l.credit or 0),
        })
    return rows


REF_TYPE_LABEL = {
    "manual": "📝 يدوي",
    "manual_reversal": "🔄 عكس يدوي",
    "invoice": "🧾 فاتورة",
    "cogs": "📦 تكلفة مبيعات",
    "payment": "💰 دفعة",
    "expense": "💸 مصروف",
    "revenue": "💵 إيراد",
    "cash_movement": "🏦 حركة خزينة",
    "cash_transfer": "🔀 تحويل خزائن",
    "opening_balance": "🚀 رصيد افتتاحي",
    "depreciation": "📉 إهلاك",
    "loan": "🏦 قرض",
    "loan_payment": "💳 سداد قرض",
    "salary": "👔 راتب",
    "cost_allocation": "🏢 تخصيص تكلفة",
    "period_closing": "📅 إقفال فترة",
    "asset_disposal": "🏭 التخلص من أصل",
}


def _ref_label(ref_type):
    return REF_TYPE_LABEL.get(ref_type or "", ref_type or "—")


# ==========================================
# التبويبات
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "➕ إنشاء قيد جديد",
    "📋 سجل القيود",
    "⚙️ إدارة القيود اليدوية",
])


# ==========================================
# التبويب 1: إنشاء قيد جديد
# ==========================================
with tab1:
    st.subheader("➕ إنشاء قيد يومية يدوي")
    st.caption(
        "💡 القيد اليدوي يُستخدم للقيود التي لا تُنشأ تلقائياً: "
        "قيد افتتاحي، تسويات، إقفال حسابات، تصحيحات..."
    )

    col_d, col_t = st.columns(2)
    with col_d:
        je_date = st.date_input(
            "التاريخ:",
            value=date.today(),
            key=f"{PFX}date",   # ✅
        )
    with col_t:
        je_time = st.time_input(
            "الوقت:",
            value=datetime.now().time(),
            key=f"{PFX}time",   # ✅
        )

    je_desc = st.text_area(
        "البيان (وصف القيد):",
        placeholder="مثال: قيد افتتاحي — إثبات رأس المال الافتتاحي",
        key=f"{PFX}desc",   # ✅
        height=68,
    )

    st.markdown("---")
    st.markdown("### 📋 أسطر القيد")
    st.caption(
        "💡 أضف سطرين على الأقل. كل سطر: الحساب + مدين أو دائن (وليس الاثنان)."
    )

    # جلب الحسابات مرة واحدة
    accounts = db.query(Account).order_by(Account.code).all()
    account_labels = [f"{a.code} — {a.name}" for a in accounts]
    account_map = {f"{a.code} — {a.name}": a.id for a in accounts}

    if not account_labels:
        st.error("⚠️ لا توجد حسابات! راجع شجرة الحسابات أولاً.")
        st.stop()

    # نموذج أسطر فارغ
    default_df = pd.DataFrame({
        "الحساب": pd.Series([None, None], dtype="object"),
        "البيان": pd.Series(["", ""], dtype="object"),
        "مدين": pd.Series([0.0, 0.0], dtype="float64"),
        "دائن": pd.Series([0.0, 0.0], dtype="float64"),
    })

    edited_df = st.data_editor(
        default_df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"{PFX}editor",   # ✅
        column_config={
            "الحساب": st.column_config.SelectboxColumn(
                "الحساب",
                options=account_labels,
                required=False,
                width="large",
            ),
            "البيان": st.column_config.TextColumn("البيان", width="medium"),
            "مدين": st.column_config.NumberColumn(
                "مدين", min_value=0.0, step=100.0, format="%.2f"
            ),
            "دائن": st.column_config.NumberColumn(
                "دائن", min_value=0.0, step=100.0, format="%.2f"
            ),
        },
    )

    # حساب الإجماليات
    if not edited_df.empty:
        total_debit = float(edited_df["مدين"].fillna(0).astype(float).sum())
        total_credit = float(edited_df["دائن"].fillna(0).astype(float).sum())
    else:
        total_debit = 0.0
        total_credit = 0.0

    diff = total_debit - total_credit

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("إجمالي المدين", f"{total_debit:,.2f} ج.م")
    with c2:
        st.metric("إجمالي الدائن", f"{total_credit:,.2f} ج.م")
    with c3:
        st.metric("الفرق", f"{diff:,.2f} ج.م")

    # حالة التوازن
    is_balanced = abs(diff) < 0.01 and total_debit > 0

    if total_debit == 0 and total_credit == 0:
        st.info("ℹ️ أدخل أسطر القيد في الجدول أعلاه.")
    elif abs(diff) > 0.01:
        st.error(f"❌ القيد غير متوازن — الفرق: **{diff:,.2f} ج.م**")
    else:
        st.success("✅ القيد متوازن وجاهز للحفظ.")

    st.markdown("---")

    col_save, col_clear = st.columns([2, 1])
    with col_save:
        save_btn = st.button(
            "💾 حفظ القيد",
            type="primary",
            use_container_width=True,
            disabled=not is_balanced,
            key=f"{PFX}save",
        )
    with col_clear:
        if st.button("🗑 تفريغ الأسطر", use_container_width=True,
                     key=f"{PFX}clear_btn"):
            clear_form(PFX)
            st.rerun()

    if save_btn:
        if not je_desc.strip():
            st.error("❌ البيان مطلوب.")
        else:
            try:
                je_dt = datetime.combine(je_date, je_time)

                # ✅ فحص الفترة
                check_period_open(je_dt, entity="قيد يدوي")

                # تجميع الأسطر الصالحة
                valid_lines = []
                for idx, row in edited_df.iterrows():
                    acc_label = row.get("الحساب")
                    if acc_label is None or pd.isna(acc_label):
                        continue
                    acc_id = account_map.get(acc_label)
                    if not acc_id:
                        continue

                    debit = float(row.get("مدين", 0) or 0)
                    credit = float(row.get("دائن", 0) or 0)

                    if debit == 0 and credit == 0:
                        continue

                    if debit > 0 and credit > 0:
                        raise ValueError(
                            f"السطر {idx + 1}: لا يمكن إدخال مدين ودائن معاً في نفس السطر."
                        )

                    valid_lines.append({
                        "account_id": acc_id,
                        "description": str(row.get("البيان", "") or "").strip(),
                        "debit": debit,
                        "credit": credit,
                    })

                if len(valid_lines) < 2:
                    raise ValueError("القيد اليدوي يحتاج سطرين على الأقل.")

                # إنشاء القيد
                entry = models.JournalEntry(
                    date=je_dt,
                    description=je_desc.strip()[:250],
                    reference_type="manual",
                    reference_id=None,
                    created_by=current_user_id,
                )
                db.add(entry)
                db.flush()

                for ln in valid_lines:
                    db.add(models.JournalLine(
                        entry_id=entry.id,
                        account_id=ln["account_id"],
                        debit=ln["debit"],
                        credit=ln["credit"],
                    ))

                # ✅ فحص التوازن
                db.flush()
                validate_journal_entry(db, entry.id)

                db.commit()

                st.success(f"✅ تم حفظ القيد `{_serial(entry.id)}` بنجاح!")
                st.balloons()

                # ✅ تفريغ كل حقول النموذج
                clear_form(PFX)
                st.rerun()

            except Exception as e:
                db.rollback()
                st.error(f"❌ خطأ: {e}")
                st.code(traceback.format_exc())


# ==========================================
# التبويب 2: سجل القيود
# ==========================================
with tab2:
    st.subheader("📋 سجل قيود اليومية")

    # فلاتر
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        f_start = st.date_input(
            "من:",
            value=datetime.now().replace(day=1).date(),
            key=f"{PFX}filter_start",
        )
    with col_d2:
        f_end = st.date_input(
            "إلى:",
            value=datetime.now().date(),
            key=f"{PFX}filter_end",
        )
    with col_d3:
        f_type = st.selectbox(
            "النوع:",
            ["الكل", "📝 يدوي فقط", "معاكس يدوي", "تلقائي فقط"],
            key=f"{PFX}filter_type",
        )

    start_dt = datetime.combine(f_start, datetime.min.time())
    end_dt = datetime.combine(f_end, datetime.max.time())

    q = db.query(models.JournalEntry).filter(
        models.JournalEntry.date >= start_dt,
        models.JournalEntry.date <= end_dt,
    )

    if f_type == "📝 يدوي فقط":
        q = q.filter(models.JournalEntry.reference_type == "manual")
    elif f_type == "معاكس يدوي":
        q = q.filter(models.JournalEntry.reference_type == "manual_reversal")
    elif f_type == "تلقائي فقط":
        q = q.filter(~models.JournalEntry.reference_type.in_(["manual", "manual_reversal"]))

    # Pagination
    PAGE_SIZE = 50
    total_count = q.count()
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)

    col_p1, col_p2 = st.columns([3, 1])
    with col_p1:
        st.caption(f"📊 إجمالي: **{total_count}** قيد | صفحة **{total_pages}**")
    with col_p2:
        if total_pages > 1:
            page_num = st.number_input(
                "صفحة:", min_value=1, max_value=total_pages,
                value=1, step=1, key=f"{PFX}page_num"
            )
        else:
            page_num = 1

    start = (page_num - 1) * PAGE_SIZE
    entries = q.order_by(models.JournalEntry.date.desc()).offset(start).limit(PAGE_SIZE).all()

    if not entries:
        st.info("لا توجد قيود في هذه الفترة.")
    else:
        # ✅ استعلام واحد لجلب كل الأسطر
        entry_ids = [e.id for e in entries]
        all_lines = db.query(models.JournalLine).filter(
            models.JournalLine.entry_id.in_(entry_ids)
        ).all()

        totals = {}
        for l in all_lines:
            if l.entry_id not in totals:
                totals[l.entry_id] = {"debit": 0.0, "credit": 0.0}
            totals[l.entry_id]["debit"] += float(l.debit or 0)
            totals[l.entry_id]["credit"] += float(l.credit or 0)

        data = []
        for e in entries:
            t = totals.get(e.id, {"debit": 0.0, "credit": 0.0})
            balanced = abs(t["debit"] - t["credit"]) < 0.01
            data.append({
                "المسلسل": _serial(e.id),
                "ID": e.id,
                "التاريخ": e.date.strftime("%Y-%m-%d %H:%M") if e.date else "—",
                "البيان": (e.description or "")[:80],
                "النوع": _ref_label(e.reference_type),
                "مدين": t["debit"],
                "دائن": t["credit"],
                "الحالة": "✅" if balanced else "⚠️ غير متوازن",
            })

        df = pd.DataFrame(data)
        st.dataframe(
            df.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "المسلسل": st.column_config.TextColumn("المسلسل", width="small"),
                "مدين": st.column_config.NumberColumn("مدين", format="%.2f"),
                "دائن": st.column_config.NumberColumn("دائن", format="%.2f"),
            },
        )
        st.caption(f"عرض {start + 1} - {min(start + PAGE_SIZE, total_count)} من {total_count}")

        # أزرار التنقل
        if total_pages > 1:
            col_prev, col_next = st.columns(2)
            with col_prev:
                if st.button("⬅️ السابق", disabled=(page_num <= 1),
                             key=f"{PFX}prev"):
                    st.session_state[f"{PFX}page_num"] = page_num - 1
                    st.rerun()
            with col_next:
                if st.button("التالي ➡️", disabled=(page_num >= total_pages),
                             key=f"{PFX}next"):
                    st.session_state[f"{PFX}page_num"] = page_num + 1
                    st.rerun()

        # تفاصيل قيد محدد
        st.markdown("---")
        st.markdown("### 📄 عرض تفاصيل قيد")
        je_opts = {e.id: f"{_serial(e.id)} — {(e.description or '')[:60]}" for e in entries}
        selected_view_id = st.selectbox(
            "اختر قيداً للعرض:",
            options=list(je_opts.keys()),
            format_func=lambda x: je_opts[x],
            key=f"{PFX}view_sel",
        )

        if selected_view_id:
            entry = next((e for e in entries if e.id == selected_view_id), None)
            if entry:
                lines = _entry_lines(db, entry.id)
                st.markdown(f"**القيد:** `{_serial(entry.id)}` — {entry.description}")
                st.caption(f"التاريخ: {entry.date.strftime('%Y-%m-%d %H:%M') if entry.date else '—'} | النوع: {_ref_label(entry.reference_type)}")

                if lines:
                    rows = []
                    for l in lines:
                        rows.append({
                            "الحساب": f"{l['account_code']} — {l['account_name']}",
                            "مدين": l["debit"],
                            "دائن": l["credit"],
                        })
                    df_lines = pd.DataFrame(rows)
                    st.dataframe(
                        df_lines, use_container_width=True, hide_index=True,
                        column_config={
                            "مدين": st.column_config.NumberColumn("مدين", format="%.2f"),
                            "دائن": st.column_config.NumberColumn("دائن", format="%.2f"),
                        },
                    )
                    st.caption(
                        f"الإجمالي: مدين {df_lines['مدين'].sum():,.2f} | "
                        f"دائن {df_lines['دائن'].sum():,.2f}"
                    )


# ==========================================
# التبويب 3: إدارة القيود اليدوية
# ==========================================
with tab3:
    st.subheader("⚙️ إدارة القيود اليدوية")
    st.caption(
        "💡 يمكن حذف أو عكس القيود اليدوية فقط (reference_type='manual'). "
        "القيود التلقائية (فواتير، دفعات...) تُدار من صفحاتها."
    )

    manual_entries = db.query(models.JournalEntry).filter(
        models.JournalEntry.reference_type == "manual"
    ).order_by(models.JournalEntry.date.desc()).limit(200).all()

    if not manual_entries:
        st.info("لا توجد قيود يدوية.")
    else:
        je_opts = {}
        for e in manual_entries:
            date_s = e.date.strftime("%Y-%m-%d") if e.date else "—"
            desc_s = (e.description or "")[:60]
            je_opts[e.id] = f"{_serial(e.id)} — {date_s} — {desc_s}"

        selected_id = st.selectbox(
            "اختر قيداً:",
            options=list(je_opts.keys()),
            format_func=lambda x: je_opts[x],
            key=f"{PFX}manage_sel",
        )

        if selected_id:
            entry = db.query(models.JournalEntry).filter(
                models.JournalEntry.id == selected_id
            ).first()

            if entry:
                st.markdown(f"### 📄 تفاصيل القيد `{_serial(entry.id)}`")
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**التاريخ:** {entry.date.strftime('%Y-%m-%d %H:%M') if entry.date else '—'}")
                with c2:
                    st.write(f"**النوع:** {_ref_label(entry.reference_type)}")
                st.write(f"**البيان:** {entry.description or '—'}")

                # أسطر القيد
                lines = _entry_lines(db, entry.id)
                if lines:
                    rows = [{
                        "الحساب": f"{l['account_code']} — {l['account_name']}",
                        "مدين": l["debit"],
                        "دائن": l["credit"],
                    } for l in lines]
                    df_lines = pd.DataFrame(rows)
                    st.dataframe(
                        df_lines, use_container_width=True, hide_index=True,
                        column_config={
                            "مدين": st.column_config.NumberColumn("مدين", format="%.2f"),
                            "دائن": st.column_config.NumberColumn("دائن", format="%.2f"),
                        },
                    )
                    st.caption(
                        f"الإجمالي: مدين {df_lines['مدين'].sum():,.2f} | "
                        f"دائن {df_lines['دائن'].sum():,.2f}"
                    )

                st.markdown("---")

                if not can_modify():
                    st.info("⛔ التعديل والحذف للمدير فقط.")
                else:
                    col_rev, col_del = st.columns(2)

                    # ===== الترحيل العكسي =====
                    with col_rev:
                        st.markdown("#### 🔄 الترحيل العكسي")
                        st.caption(
                            "إنشاء قيد جديد يعكس هذا القيد. يُستخدم بدل الحذف "
                            "للحفاظ على الأثر التدقيقي."
                        )
                        if st.button(
                            "🔄 إنشاء قيد عكسي",
                            type="primary",
                            use_container_width=True,
                            key=f"{PFX}reverse_{entry.id}",
                        ):
                            try:
                                check_period_open(datetime.now(), entity="ترحيل عكسي")

                                rev_entry = models.JournalEntry(
                                    date=datetime.now(),
                                    description=f"عكس القيد {_serial(entry.id)}: {(entry.description or '')[:180]}",
                                    reference_type="manual_reversal",
                                    reference_id=entry.id,
                                    created_by=current_user_id,
                                )
                                db.add(rev_entry)
                                db.flush()

                                for l in lines:
                                    db.add(models.JournalLine(
                                        entry_id=rev_entry.id,
                                        account_id=l["account_id"],
                                        debit=l["credit"],
                                        credit=l["debit"],
                                    ))

                                db.flush()
                                validate_journal_entry(db, rev_entry.id)
                                db.commit()

                                st.success(f"✅ تم إنشاء القيد العكسي `{_serial(rev_entry.id)}`")

                                # ✅ تفريغ كل مفاتيح الصفحة
                                clear_form(PFX)
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"❌ خطأ: {e}")
                                st.code(traceback.format_exc())

                    # ===== الحذف =====
                    with col_del:
                        st.markdown("#### 🗑 حذف القيد")
                        st.warning("⚠️ الحذف يمحو القيد نهائياً — يُفضَّل استخدام الترحيل العكسي.")

                        confirm = st.checkbox(
                            "أؤكد الحذف النهائي",
                            key=f"{PFX}confirm_del_{entry.id}",
                        )
                        if st.button(
                            "🗑 حذف القيد",
                            type="secondary",
                            disabled=not confirm,
                            use_container_width=True,
                            key=f"{PFX}del_btn_{entry.id}",
                        ):
                            try:
                                if entry.date:
                                    check_period_open(entry.date, entity="حذف قيد يدوي")

                                db.query(models.JournalLine).filter(
                                    models.JournalLine.entry_id == entry.id
                                ).delete(synchronize_session=False)
                                db.delete(entry)
                                db.commit()

                                st.success(f"✅ تم حذف القيد `{_serial(entry.id)}`.")

                                # ✅ تفريغ كل مفاتيح الصفحة
                                clear_form(PFX)
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"❌ خطأ: {e}")

db.close()