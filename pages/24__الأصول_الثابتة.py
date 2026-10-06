# pages/24_🏭_الأصول_الثابتة.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify
render_sidebar()

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from database import SessionLocal
import models
from models import FixedAsset, DepreciationRecord, DepreciationMethod
from services import (
    create_fixed_asset, calculate_annual_depreciation,
    run_annual_depreciation, get_asset_depreciation_schedule,
    dispose_asset,
)
from auth_required import require_login, get_current_user_id, get_current_user_name

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="الأصول الثابتة", page_icon="🏭", layout="wide")
st.title("🏭 إدارة الأصول الثابتة")
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()


def _delete_asset(asset_id):
    """يحذف أصل ثابت + سجلات الإهلاك + القيود المحاسبية."""
    db_local = SessionLocal()
    try:
        asset = db_local.query(FixedAsset).filter(
            FixedAsset.id == asset_id
        ).first()
        if not asset:
            raise ValueError("الأصل غير موجود")

        # التحقق من سجلات الإهلاك
        dep_count = db_local.query(DepreciationRecord).filter(
            DepreciationRecord.asset_id == asset_id
        ).count()
        if dep_count > 0:
            raise ValueError(
                f"لا يمكن الحذف: للأصل {dep_count} سجل إهلاك. "
                "استخدم 'التخلص من الأصل' بدلاً من الحذف."
            )

        # حذف القيود المحاسبية المرتبطة (لو موجودة)
        je_ids = [r[0] for r in db_local.query(models.JournalEntry.id).filter(
            models.JournalEntry.reference_id == asset_id,
            models.JournalEntry.reference_type.in_(["depreciation",
                                                     "asset_disposal"]),
        ).all()]
        if je_ids:
            db_local.query(models.JournalLine).filter(
                models.JournalLine.entry_id.in_(je_ids)
            ).delete(synchronize_session=False)
            db_local.query(models.JournalEntry).filter(
                models.JournalEntry.id.in_(je_ids)
            ).delete(synchronize_session=False)

        db_local.delete(asset)
        db_local.commit()
    except Exception:
        db_local.rollback()
        raise
    finally:
        db_local.close()


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "➕ إضافة أصل ثابت",
    "📋 قائمة الأصول",
    "📉 حساب الإهلاك",
    "📊 جدول الإهلاك",
    "🗑️ التخلص من أصل",
])


# ==========================================
# التبويب 1: إضافة أصل ثابت
# ==========================================
with tab1:
    st.subheader("➕ إضافة أصل ثابت جديد")
    st.caption("💡 بعد الحفظ، الحقول هتتفرّغ تلقائيًا.")

    col1, col2 = st.columns(2)
    with col1:
        asset_name = st.text_input("اسم الأصل:",
                                    placeholder="مثال: سيارة نقل...",
                                    key="new_asset_name")
        asset_code = st.text_input("كود الأصل:",
                                    placeholder="مثال: FA001...",
                                    key="new_asset_code")
        asset_category = st.selectbox(
            "التصنيف:",
            ["مباني", "سيارات", "أجهزة ومعدات", "أثاث", "أراضي", "أخرى"],
            key="new_asset_category",
        )
        purchase_date = st.date_input("تاريخ الشراء:",
                                       value=datetime.now().date(),
                                       key="new_asset_purchase_date")
    with col2:
        purchase_cost = st.number_input(
            "تكلفة الشراء:", min_value=0.01, step=1000.0,
            format="%.2f", key="new_asset_cost",
        )
        salvage_value = st.number_input(
            "قيمة الخردة:", min_value=0.0, step=100.0,
            format="%.2f", key="new_asset_salvage",
        )
        useful_life = st.number_input(
            "العمر الإنتاجي (سنوات):", min_value=1, max_value=50,
            value=10, step=1, key="new_asset_life",
        )
        depreciation_method = st.selectbox(
            "طريقة الإهلاك:",
            options=[m.value for m in DepreciationMethod],
            key="new_asset_dep_method",
        )

    location = st.text_input("الموقع (اختياري):", key="new_asset_location")
    responsible_person = st.text_input("المسؤول (اختياري):",
                                        key="new_asset_responsible")
    notes = st.text_area("ملاحظات (اختياري):", key="new_asset_notes")

    if st.button("💾 إضافة الأصل", type="primary", use_container_width=True):
        if not asset_name.strip() or not asset_code.strip():
            st.error("❌ يرجى إدخال اسم وكود الأصل.")
        elif purchase_cost <= 0:
            st.error("❌ تكلفة الشراء يجب أن تكون أكبر من صفر.")
        elif useful_life <= 0:
            st.error("❌ العمر الإنتاجي غير صحيح.")
        else:
            try:
                purchase_dt = datetime.combine(purchase_date, datetime.min.time())
                actual_method = next(
                    m for m in DepreciationMethod if m.value == depreciation_method
                )
                create_fixed_asset(
                    name=asset_name.strip(),
                    code=asset_code.strip(),
                    category=asset_category,
                    purchase_date=purchase_dt,
                    purchase_cost=purchase_cost,
                    salvage_value=salvage_value,
                    useful_life_years=useful_life,
                    depreciation_method=actual_method,
                    location=location.strip() or None,
                    responsible_person=responsible_person.strip() or None,
                    notes=notes.strip() or None,
                    created_by=current_user_id,
                )
                st.success(f"✅ تم إضافة الأصل '{asset_name}'!")
                st.balloons()

                queue_state_updates(
                    delete_keys=(
                        "new_asset_name", "new_asset_code", "new_asset_category",
                        "new_asset_purchase_date", "new_asset_cost",
                        "new_asset_salvage", "new_asset_life",
                        "new_asset_dep_method", "new_asset_location",
                        "new_asset_responsible", "new_asset_notes",
                    ),
                    set_values={
                        "new_asset_name": "", "new_asset_code": "",
                        "new_asset_cost": 0.01, "new_asset_salvage": 0.0,
                        "new_asset_life": 10, "new_asset_location": "",
                        "new_asset_responsible": "", "new_asset_notes": "",
                    },
                )
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 2: قائمة الأصول
# ==========================================
with tab2:
    st.subheader("📋 قائمة الأصول الثابتة")

    sub_t1, sub_t2 = st.tabs(["عرض", "تعديل/حذف"])

    with sub_t1:
        assets = db.query(FixedAsset).order_by(FixedAsset.code).all()

        if assets:
            rows = []
            for idx, a in enumerate(assets, start=1):
                rows.append({
                    "مسلسل": idx,
                    "الكود": a.code,
                    "الاسم": a.name,
                    "التصنيف": a.category,
                    "تاريخ الشراء": a.purchase_date.strftime("%Y-%m-%d")
                        if a.purchase_date else "—",
                    "التكلفة": float(a.purchase_cost or 0),
                    "مجمع الإهلاك": float(a.accumulated_depreciation or 0),
                    "صافي القيمة": float(a.net_book_value or 0),
                    "الحالة": "✅ نشط" if a.status == "active" else "⚠️ متوقف",
                })
            df = pd.DataFrame(rows)
            st.dataframe(
                df, use_container_width=True, hide_index=True,
                column_config={
                    "التكلفة": st.column_config.NumberColumn("التكلفة",
                                                              format="%.2f"),
                    "مجمع الإهلاك": st.column_config.NumberColumn("مجمع الإهلاك",
                                                                    format="%.2f"),
                    "صافي القيمة": st.column_config.NumberColumn("صافي القيمة",
                                                                   format="%.2f"),
                },
            )

            # إحصائيات
            total_cost = sum(a.purchase_cost for a in assets)
            total_dep = sum(a.accumulated_depreciation for a in assets)
            total_net = sum(a.net_book_value for a in assets)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("إجمالي التكلفة", f"{total_cost:,.2f} ج.م")
            with c2:
                st.metric("إجمالي مجمع الإهلاك", f"{total_dep:,.2f} ج.م")
            with c3:
                st.metric("إجمالي صافي القيمة", f"{total_net:,.2f} ج.م")
        else:
            st.info("لا توجد أصول ثابتة.")

    with sub_t2:
        assets = db.query(FixedAsset).all()

        if not assets:
            st.info("لا توجد أصول.")
        else:
            sel_id = st.selectbox(
                "اختر أصلاً:",
                options=[a.id for a in assets],
                format_func=lambda x: next(
                    (f"{a.code} — {a.name}" for a in assets if a.id == x),
                    str(x)),
                key="sel_asset_edit",
            )

            if sel_id:
                sel_asset = next((a for a in assets if a.id == sel_id), None)
                dep_count = db.query(DepreciationRecord).filter(
                    DepreciationRecord.asset_id == sel_id
                ).count()

                st.markdown(f"### 📄 تفاصيل: **{sel_asset.name}**")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("التكلفة", f"{sel_asset.purchase_cost:,.2f}")
                with c2:
                    st.metric("مجمع الإهلاك",
                              f"{sel_asset.accumulated_depreciation:,.2f}")
                with c3:
                    st.metric("صافي القيمة", f"{sel_asset.net_book_value:,.2f}")
                with c4:
                    st.metric("سجلات إهلاك", dep_count)

                col_edit, col_del = st.columns(2)

                # ----- تعديل -----
                with col_edit:
                    st.markdown("#### ✏️ تعديل البيانات")
                    with st.form(f"edit_asset_form_{sel_id}"):
                        e_name = st.text_input("الاسم:",
                                                value=sel_asset.name)
                        e_cat = st.selectbox(
                            "التصنيف:",
                            ["مباني", "سيارات", "أجهزة ومعدات", "أثاث",
                             "أراضي", "أخرى"],
                            index=(["مباني", "سيارات", "أجهزة ومعدات", "أثاث",
                                    "أراضي", "أخرى"].index(sel_asset.category)
                                   if sel_asset.category in
                                   ["مباني", "سيارات", "أجهزة ومعدات", "أثاث",
                                    "أراضي", "أخرى"] else 0),
                        )
                        e_loc = st.text_input("الموقع:",
                                               value=sel_asset.location or "")
                        e_resp = st.text_input(
                            "المسؤول:",
                            value=sel_asset.responsible_person or "")
                        e_notes = st.text_area("ملاحظات:",
                                                value=sel_asset.notes or "",
                                                height=80)
                        e_status = st.selectbox(
                            "الحالة:",
                            ["active", "inactive", "sold", "scrapped"],
                            index=(['active', 'inactive', 'sold', 'scrapped']
                                   .index(sel_asset.status)
                                   if sel_asset.status in
                                   ['active', 'inactive', 'sold', 'scrapped']
                                   else 0),
                        )
                        submitted = st.form_submit_button(
                            "💾 حفظ التعديلات", type="primary",
                        )

                    if submitted:
                        try:
                            if not e_name.strip():
                                st.error("❌ الاسم مطلوب.")
                            else:
                                sel_asset.name = e_name.strip()
                                sel_asset.category = e_cat
                                sel_asset.location = e_loc.strip() or None
                                sel_asset.responsible_person = e_resp.strip() or None
                                sel_asset.notes = e_notes.strip() or None
                                sel_asset.status = e_status
                                db.commit()
                                st.success("✅ تم التعديل.")
                                queue_state_updates(delete_keys=("sel_asset_edit",))
                                st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"❌ {e}")

                # ----- حذف -----
                with col_del:
                    st.markdown("#### 🗑 حذف الأصل")

                    if dep_count > 0:
                        st.error(f"⛔ لا يمكن الحذف: للأصل **{dep_count}** سجل إهلاك.")
                        st.info("💡 الحل: استخدم **التخلص من الأصل** (تبويب 5).")
                    else:
                        st.warning("⚠️ الحذف نهائي.")
                        confirm = st.checkbox(
                            "✅ أؤكد الحذف",
                            key=f"confirm_del_asset_{sel_id}",
                        )
                        if st.button(
                            "🗑 حذف الأصل",
                            type="secondary",
                            disabled=not confirm,
                            use_container_width=True,
                            key=f"del_asset_btn_{sel_id}",
                        ):
                            try:
                                _delete_asset(sel_id)
                                st.success("✅ تم الحذف.")
                                queue_state_updates(delete_keys=("sel_asset_edit",))
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ {e}")


# ==========================================
# التبويب 3: حساب الإهلاك
# ==========================================
with tab3:
    st.subheader("📉 حساب الإهلاك السنوي")

    active_assets = db.query(FixedAsset).filter(
        FixedAsset.status == "active"
    ).all()

    if not active_assets:
        st.info("لا توجد أصول نشطة.")
    else:
        year = st.number_input(
            "السنة المالية:", min_value=2020, max_value=2100,
            value=datetime.now().year, step=1, key="dep_year",
        )

        if st.button("🧮 حساب الإهلاك المتوقع", type="primary"):
            results = []
            for a in active_assets:
                annual = calculate_annual_depreciation(a)
                results.append({
                    "الكود": a.code,
                    "الاسم": a.name,
                    "طريقة الإهلاك": a.depreciation_method.value,
                    "الإهلاك السنوي": float(annual),
                    "صافي القيمة الحالي": float(a.net_book_value or 0),
                })
            st.dataframe(pd.DataFrame(results), use_container_width=True,
                         hide_index=True)

        st.markdown("---")
        st.markdown("### ✅ تسجيل الإهلاك الفعلي")
        st.warning("⚠️ سيتم إنشاء قيد محاسبي وتحديث قيم الأصل.")

        sel_asset_id = st.selectbox(
            "اختر أصلاً:",
            options=[a.id for a in active_assets],
            format_func=lambda x: next(
                (f"{a.code} - {a.name}" for a in active_assets if a.id == x),
                str(x)),
            key="dep_asset_sel",
        )

        if sel_asset_id and st.button("💾 تسجيل الإهلاك",
                                       type="secondary",
                                       use_container_width=True):
            try:
                rec = run_annual_depreciation(
                    asset_id=sel_asset_id,
                    year=year,
                    created_by=current_user_id,
                )
                st.success(f"✅ تم تسجيل إهلاك {year}.")
                st.info(f"مبلغ الإهلاك: {rec.depreciation_amount:,.2f} ج.م")
                queue_state_updates(delete_keys=("dep_asset_sel",))
                st.rerun()
            except Exception as e:
                st.error(f"❌ {e}")


# ==========================================
# التبويب 4: جدول الإهلاك
# ==========================================
with tab4:
    st.subheader("📊 جدول الإهلاك الكامل")

    all_assets = db.query(FixedAsset).all()

    if not all_assets:
        st.info("لا توجد أصول.")
    else:
        sel_id = st.selectbox(
            "اختر أصلاً:",
            options=[a.id for a in all_assets],
            format_func=lambda x: next(
                (f"{a.code} - {a.name}" for a in all_assets if a.id == x),
                str(x)),
            key="schedule_asset_sel",
        )

        if sel_id:
            schedule_data = get_asset_depreciation_schedule(sel_id)
            if schedule_data:
                asset = schedule_data["asset"]
                schedule = schedule_data["schedule"]

                st.markdown(f"### 📄 {asset.name} ({asset.code})")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("التكلفة", f"{asset.purchase_cost:,.2f}")
                with c2:
                    st.metric("قيمة الخردة", f"{asset.salvage_value:,.2f}")
                with c3:
                    st.metric("العمر", f"{asset.useful_life_years} سنة")
                with c4:
                    st.metric("طريقة", asset.depreciation_method.value)

                if schedule:
                    df = pd.DataFrame(schedule)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    fig = px.line(df, x="السنة", y="صافي القيمة الدفترية",
                                  title="تطور صافي القيمة الدفترية",
                                  markers=True)
                    st.plotly_chart(fig, use_container_width=True)


# ==========================================
# التبويب 5: التخلص من أصل
# ==========================================
with tab5:
    st.subheader("🗑️ التخلص من أصل ثابت")

    st.warning("""⚠️ التخلص = بيع/إعدام الأصل. سيتم إنشاء قيد محاسبي.""")

    active_assets = db.query(FixedAsset).filter(
        FixedAsset.status == "active"
    ).all()

    if not active_assets:
        st.info("لا توجد أصول نشطة.")
    else:
        sel_id = st.selectbox(
            "اختر أصلاً:",
            options=[a.id for a in active_assets],
            format_func=lambda x: next(
                (f"{a.code} - {a.name} (صافي: {a.net_book_value:,.2f})"
                 for a in active_assets if a.id == x),
                str(x)),
            key="dispose_asset_sel",
        )

        if sel_id:
            sel_asset = next((a for a in active_assets if a.id == sel_id), None)

            st.markdown(f"### 📄 {sel_asset.name}")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("التكلفة", f"{sel_asset.purchase_cost:,.2f}")
            with c2:
                st.metric("مجمع الإهلاك",
                          f"{sel_asset.accumulated_depreciation:,.2f}")
            with c3:
                st.metric("صافي القيمة",
                          f"{sel_asset.net_book_value:,.2f}")

            disposal_date = st.date_input("تاريخ التخلص:",
                                           value=datetime.now().date(),
                                           key="dispose_date")
            disposal_value = st.number_input(
                "قيمة البيع:", min_value=0.0, step=100.0,
                format="%.2f", key="dispose_value",
            )
            disposal_notes = st.text_area("ملاحظات:", key="dispose_notes")

            if disposal_value > 0:
                gl = disposal_value - sel_asset.net_book_value
                if gl > 0:
                    st.success(f"💰 ربح: {gl:,.2f} ج.م")
                elif gl < 0:
                    st.error(f"📉 خسارة: {gl:,.2f} ج.م")

            if st.button("🗑 التخلص من الأصل",
                         type="secondary",
                         use_container_width=True):
                confirm = st.checkbox(
                    "✅ أؤكد التخلص النهائي",
                    key="confirm_dispose",
                )
                if confirm:
                    try:
                        result = dispose_asset(
                            asset_id=sel_id,
                            disposal_date=datetime.combine(
                                disposal_date, datetime.min.time()),
                            disposal_value=disposal_value,
                            notes=disposal_notes.strip() or None,
                            created_by=current_user_id,
                        )
                        st.success(f"✅ تم التخلص من '{sel_asset.name}'.")
                        queue_state_updates(
                            delete_keys=("dispose_asset_sel", "dispose_date",
                                         "dispose_value", "dispose_notes",
                                         "confirm_dispose"),
                            set_values={"dispose_value": 0.0,
                                        "dispose_notes": ""},
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")

db.close()