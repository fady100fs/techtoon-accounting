# pages/30_🏢_مراكز_التكلفة.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify
render_sidebar()

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import SessionLocal
import models
from models import CostCenter, CostAllocation, CostCenterTransaction, Account
from services import (
    create_cost_center, get_cost_centers_tree, allocate_cost_to_center,
    get_cost_center_report, get_all_cost_centers_summary,
    transfer_between_cost_centers,
)
from auth_required import require_login, get_current_user_id, get_current_user_name
from form_manager import clear_form, show_clear_hint

current_user = require_login()

# ⭐ استقبال التنقل من شجرة الحسابات
from navigation_helper import consume_navigation_flags, show_navigation_banner
_nav = consume_navigation_flags()
show_navigation_banner(_nav, page_name="مراكز التكلفة")
_filter_account_id = _nav.get("filter_account_id")
if _filter_account_id:
    st.session_state["cc_filter_account_id"] = _filter_account_id
    _acc = db.query(models.Account).filter(models.Account.id == _filter_account_id).first()
    if _acc:
        st.info(f"🎯 مفلتر على الحساب: **{_acc.code} — {_acc.name}**")

current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="مراكز التكلفة", page_icon="🏢", layout="wide")
st.title("🏢 إدارة مراكز التكلفة")
show_clear_hint()   # ✅ تلميح
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")


# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لمفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "cc_"


db = SessionLocal()


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "➕ إضافة مركز تكلفة",
    "📋 قائمة مراكز التكلفة",
    "💰 تخصيص تكلفة",
    "📊 تقارير مراكز التكلفة",
    "🔄 التحويلات بين المراكز",
])


# ==========================================
# التبويب 1: إضافة مركز تكلفة
# ==========================================
with tab1:
    st.subheader("➕ إضافة مركز تكلفة جديد")

    st.info("""
    💡 **مراكز التكلفة:**
    - وحدات داخل المنظمة تُخصص لها التكاليف
    - تساعد في تتبع المصروفات حسب الأقسام
    - أمثلة: قسم المبيعات، قسم الإنتاج، قسم التسويق
    """)

    col1, col2 = st.columns(2)

    with col1:
        center_code = st.text_input(
            "كود المركز:",
            placeholder="مثال: CC001, SALES, PROD...",
            key=f"{PFX}new_code",   # ✅
        )
        center_name = st.text_input(
            "اسم المركز:",
            placeholder="مثال: قسم المبيعات، قسم الإنتاج...",
            key=f"{PFX}new_name",   # ✅
        )
        manager_name = st.text_input(
            "اسم المسؤول:",
            placeholder="اسم مدير المركز",
            key=f"{PFX}new_manager",   # ✅
        )
        description = st.text_area("الوصف:", key=f"{PFX}new_desc")   # ✅

    with col2:
        all_centers = db.query(CostCenter).filter(CostCenter.is_active == True).all()
        parent_options = {"بدون (مركز رئيسي)": None}
        for c in all_centers:
            parent_options[c.name] = c.id

        selected_parent = st.selectbox(
            "المركز الأب (اختياري):",
            options=list(parent_options.values()),
            format_func=lambda x: next(
                (k for k, v in parent_options.items() if v == x),
                "بدون"
            ),
            key=f"{PFX}new_parent",   # ✅
        )

        budget_limit = st.number_input(
            "حد الميزانية (اختياري):",
            min_value=0.0, step=10000.0,
            format="%.2f", key=f"{PFX}new_budget",   # ✅
        )
        notes = st.text_area("ملاحظات:", key=f"{PFX}new_notes")   # ✅

    if st.button("💾 إنشاء مركز التكلفة", type="primary",
                 use_container_width=True, key=f"{PFX}new_save"):
        if not center_code or not center_name:
            st.error("❌ يرجى إدخال الكود والاسم")
        else:
            try:
                create_cost_center(
                    code=center_code,
                    name=center_name,
                    description=description if description else None,
                    manager_name=manager_name if manager_name else None,
                    parent_id=selected_parent,
                    budget_limit=budget_limit if budget_limit > 0 else None,
                    notes=notes if notes else None,
                    created_by=current_user_id,
                )

                st.success(f"✅ تم إنشاء مركز التكلفة '{center_name}' بنجاح!")
                st.balloons()

                # ✅ تفريغ كل حقول النموذج
                clear_form(PFX)
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 2: قائمة مراكز التكلفة
# ==========================================
with tab2:
    st.subheader("📋 قائمة مراكز التكلفة")

    centers = db.query(CostCenter).all()

    if centers:
        # عرض الشجرة
        tree = get_cost_centers_tree()

        st.markdown("### 🌳 شجرة مراكز التكلفة")

        for node in tree:
            with st.expander(f"📁 {node['code']} - {node['name']}", expanded=False):
                st.write(f"**المسؤول:** {node['manager'] or '-'}")
                st.write(f"**الميزانية:** {node['budget_limit']:,.2f} ج.م"
                         if node['budget_limit'] else "**الميزانية:** غير محددة")

                if node['children']:
                    st.markdown("**المراكز الفرعية:**")
                    for child in node['children']:
                        st.write(f"  - 📄 {child['code']} - {child['name']}")

        st.markdown("---")

        # جدول شامل
        st.markdown("### 📊 جدول مراكز التكلفة")

        # خريطة الأب
        center_map = {c.id: c for c in centers}

        # عدّ المعاملات — استعلام واحد
        trans_counts = db.query(
            models.CostCenterTransaction.cost_center_id,
            models.func.count(models.CostCenterTransaction.id),
        ).group_by(models.CostCenterTransaction.cost_center_id).all()
        trans_map = {cid: cnt for cid, cnt in trans_counts}

        data = []
        for center in centers:
            parent = center_map.get(center.parent_id)
            data.append({
                "الكود": center.code,
                "الاسم": center.name,
                "المركز الأب": parent.name if parent else "-",
                "المسؤول": center.manager_name or "-",
                "الميزانية": f"{center.budget_limit:,.2f}" if center.budget_limit else "-",
                "عدد المعاملات": trans_map.get(center.id, 0),
                "الحالة": "✅ نشط" if center.is_active else "⛔ معطل",
            })

        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ===== تعديل / حذف =====
        st.markdown("---")
        st.markdown("### ⚙️ تعديل / حذف مركز")

        if not can_modify():
            st.info("⛔ التعديل والحذف للمدير فقط.")
        else:
            sel_id = st.selectbox(
                "اختر مركزاً:",
                options=[c.id for c in centers],
                format_func=lambda x: next(
                    (f"{c.code} — {c.name}" for c in centers if c.id == x),
                    str(x)),
                key=f"{PFX}edit_select",   # ✅
            )

            if sel_id:
                sel = next((c for c in centers if c.id == sel_id), None)

                col_edit, col_del = st.columns(2)

                # تعديل
                with col_edit:
                    st.markdown("#### ✏️ تعديل البيانات")
                    with st.form(f"{PFX}edit_form_{sel_id}"):
                        e_name = st.text_input(
                            "الاسم:",
                            value=sel.name,
                            key=f"{PFX}edit_name_{sel_id}",   # ✅
                        )
                        e_manager = st.text_input(
                            "المسؤول:",
                            value=sel.manager_name or "",
                            key=f"{PFX}edit_manager_{sel_id}",   # ✅
                        )
                        e_budget = st.number_input(
                            "الميزانية:",
                            min_value=0.0,
                            value=float(sel.budget_limit or 0),
                            step=1000.0,
                            key=f"{PFX}edit_budget_{sel_id}",   # ✅
                        )
                        e_notes = st.text_area(
                            "ملاحظات:",
                            value=sel.notes or "",
                            height=80,
                            key=f"{PFX}edit_notes_{sel_id}",   # ✅
                        )
                        e_active = st.checkbox(
                            "نشط",
                            value=bool(sel.is_active),
                            key=f"{PFX}edit_active_{sel_id}",   # ✅
                        )
                        submitted = st.form_submit_button(
                            "💾 حفظ التعديلات", type="primary",
                        )

                    if submitted:
                        try:
                            if not e_name.strip():
                                st.error("❌ الاسم مطلوب.")
                            else:
                                sel.name = e_name.strip()
                                sel.manager_name = e_manager.strip() or None
                                sel.budget_limit = e_budget if e_budget > 0 else None
                                sel.notes = e_notes.strip() or None
                                sel.is_active = e_active
                                db.commit()
                                st.success("✅ تم التعديل.")

                                # ✅ تفريغ كل مفاتيح التعديل
                                clear_form(PFX)
                                st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"❌ خطأ: {e}")

                # حذف
                with col_del:
                    st.markdown("#### 🗑 حذف المركز")
                    children_count = db.query(CostCenter).filter(
                        CostCenter.parent_id == sel_id
                    ).count()
                    tx_count = db.query(CostCenterTransaction).filter(
                        CostCenterTransaction.cost_center_id == sel_id
                    ).count()

                    if children_count > 0 or tx_count > 0:
                        st.error(f"⛔ لا يمكن الحذف:")
                        if children_count > 0:
                            st.write(f"- به {children_count} مركز فرعي")
                        if tx_count > 0:
                            st.write(f"- به {tx_count} معاملة")
                        st.info("💡 الحل: عطّل المركز بدل الحذف.")
                    else:
                        st.warning("⚠️ الحذف نهائي.")
                        confirm = st.checkbox(
                            "✅ أؤكد الحذف",
                            key=f"{PFX}confirm_del_{sel_id}",   # ✅
                        )
                        if st.button(
                            "🗑 حذف المركز",
                            type="secondary",
                            disabled=not confirm,
                            use_container_width=True,
                            key=f"{PFX}del_btn_{sel_id}",   # ✅
                        ):
                            try:
                                db.delete(sel)
                                db.commit()
                                st.success("✅ تم الحذف.")

                                # ✅ تفريغ كل مفاتيح الصفحة
                                clear_form(PFX)
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"❌ {e}")
    else:
        st.info("لا توجد مراكز تكلفة مسجلة.")


# ==========================================
# التبويب 3: تخصيص تكلفة
# ==========================================
with tab3:
    st.subheader("💰 تخصيص تكلفة لمركز تكلفة")

    active_centers = db.query(CostCenter).filter(CostCenter.is_active == True).all()

    if not active_centers:
        st.warning("⚠️ لا توجد مراكز تكلفة نشطة!")
    else:
        col1, col2 = st.columns(2)

        with col1:
            selected_center_id = st.selectbox(
                "اختر مركز التكلفة:",
                options=[c.id for c in active_centers],
                format_func=lambda x: next(
                    (f"{c.code} - {c.name}" for c in active_centers if c.id == x),
                    str(x)),
                key=f"{PFX}alloc_center",   # ✅
            )

            expense_accounts = db.query(Account).filter(
                Account.type == models.AccountType.EXPENSE
            ).all()
            account_dict = {acc.id: f"{acc.code} - {acc.name}"
                            for acc in expense_accounts}

            selected_account_id = st.selectbox(
                "اختر حساب المصروف:",
                options=list(account_dict.keys()),
                format_func=lambda x: account_dict[x],
                key=f"{PFX}alloc_account",   # ✅
            )

        with col2:
            allocation_date = st.date_input(
                "التاريخ:",
                value=datetime.now().date(),
                key=f"{PFX}alloc_date",   # ✅
            )
            amount = st.number_input(
                "المبلغ:",
                min_value=0.01, step=100.0,
                format="%.2f", key=f"{PFX}alloc_amount",   # ✅
            )
            description = st.text_area(
                "الوصف:",
                placeholder="وصف التكلفة...",
                key=f"{PFX}alloc_desc",   # ✅
            )

        if st.button("💾 تخصيص التكلفة", type="primary",
                     use_container_width=True, key=f"{PFX}alloc_save"):
            if not description:
                st.error("❌ يرجى إدخال وصف التكلفة")
            elif amount <= 0:
                st.error("❌ يرجى إدخال مبلغ صحيح")
            else:
                try:
                    allocation_datetime = datetime.combine(
                        allocation_date, datetime.min.time()
                    )

                    allocate_cost_to_center(
                        cost_center_id=selected_center_id,
                        account_id=selected_account_id,
                        amount=amount,
                        description=description,
                        allocation_date=allocation_datetime,
                        created_by=current_user_id,
                    )

                    st.success("✅ تم تخصيص التكلفة بنجاح!")
                    st.balloons()

                    # ✅ تفريغ كل حقول النموذج
                    clear_form(PFX)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 4: تقارير مراكز التكلفة
# ==========================================
with tab4:
    st.subheader("📊 تقارير مراكز التكلفة")

    report_type = st.radio(
        "نوع التقرير:",
        ["تقرير مركز واحد", "ملخص جميع المراكز"],
        horizontal=True,
        key=f"{PFX}report_type",   # ✅
    )

    if report_type == "تقرير مركز واحد":
        all_centers = db.query(CostCenter).all()

        if not all_centers:
            st.info("لا توجد مراكز تكلفة.")
        else:
            selected_center_id = st.selectbox(
                "اختر مركز التكلفة:",
                options=[c.id for c in all_centers],
                format_func=lambda x: next(
                    (f"{c.code} - {c.name}" for c in all_centers if c.id == x),
                    str(x)),
                key=f"{PFX}report_center",   # ✅
            )

            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "من تاريخ:",
                    value=datetime.now().replace(day=1).date(),
                    key=f"{PFX}report_start",   # ✅
                )
            with col2:
                end_date = st.date_input(
                    "إلى تاريخ:",
                    value=datetime.now().date(),
                    key=f"{PFX}report_end",   # ✅
                )

            if st.button("📊 عرض التقرير", type="primary",
                         key=f"{PFX}report_show"):
                start_dt = datetime.combine(start_date, datetime.min.time())
                end_dt = datetime.combine(end_date, datetime.max.time())

                report = get_cost_center_report(selected_center_id, start_dt, end_dt)

                if report:
                    center = report['cost_center']

                    st.markdown(f"### 📄 تقرير: {center.name} ({center.code})")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("إجمالي المصروفات",
                                  f"{report['total_expenses']:,.2f} ج.م")
                    with col2:
                        st.metric("إجمالي الإيرادات",
                                  f"{report['total_revenues']:,.2f} ج.م")
                    with col3:
                        st.metric("صافي المبلغ",
                                  f"{report['net_amount']:,.2f} ج.م")

                    if center.budget_limit:
                        usage_pct = (report['total_expenses'] / center.budget_limit * 100)
                        st.progress(min(usage_pct / 100, 1.0))
                        st.write(f"**نسبة الاستخدام:** {usage_pct:.1f}% من الميزانية")

                    st.markdown("---")
                    st.markdown("### 📝 المعاملات")

                    if report['transactions']:
                        data = []
                        for t in report['transactions']:
                            data.append({
                                "التاريخ": t.date.strftime("%Y-%m-%d"),
                                "الوصف": t.description,
                                "النوع": t.transaction_type,
                                "المبلغ": f"{t.amount:,.2f} ج.م",
                            })

                        df = pd.DataFrame(data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("لا توجد معاملات في هذه الفترة.")

                    if report['children']:
                        fig = px.pie(
                            pd.DataFrame(report['children']),
                            values='total',
                            names='name',
                            title='توزيع التكاليف على المراكز الفرعية'
                        )
                        st.plotly_chart(fig, use_container_width=True)

    else:
        # ملخص جميع المراكز
        col1, col2 = st.columns(2)
        with col1:
            summary_start = st.date_input(
                "من تاريخ:",
                value=datetime.now().replace(day=1).date(),
                key=f"{PFX}summary_start",   # ✅
            )
        with col2:
            summary_end = st.date_input(
                "إلى تاريخ:",
                value=datetime.now().date(),
                key=f"{PFX}summary_end",   # ✅
            )

        if st.button("📊 عرض الملخص", type="primary",
                     key=f"{PFX}summary_show"):
            summary_start_dt = datetime.combine(summary_start, datetime.min.time())
            summary_end_dt = datetime.combine(summary_end, datetime.max.time())

            summary = get_all_cost_centers_summary(summary_start_dt, summary_end_dt)

            if summary:
                df = pd.DataFrame(summary)
                st.dataframe(df, use_container_width=True, hide_index=True)

                fig = px.bar(
                    df,
                    x='name',
                    y='total_spent',
                    color='usage_percentage',
                    title='إجمالي المصروفات حسب مركز التكلفة',
                    color_continuous_scale='RdYlGn_r'
                )
                st.plotly_chart(fig, use_container_width=True)

                total_spent = sum(s['total_spent'] for s in summary)
                st.metric("إجمالي مصروفات جميع المراكز",
                          f"{total_spent:,.2f} ج.م")


# ==========================================
# التبويب 5: التحويلات بين المراكز
# ==========================================
with tab5:
    st.subheader("🔄 التحويلات بين مراكز التكلفة")

    active_centers = db.query(CostCenter).filter(CostCenter.is_active == True).all()

    if len(active_centers) < 2:
        st.warning("⚠️ يجب وجود مركزين نشطين على الأقل!")
    else:
        col1, col2 = st.columns(2)

        with col1:
            from_center_id = st.selectbox(
                "من مركز:",
                options=[c.id for c in active_centers],
                format_func=lambda x: next(
                    (f"{c.code} - {c.name}" for c in active_centers if c.id == x),
                    str(x)),
                key=f"{PFX}tr_from",   # ✅
            )

        with col2:
            to_center_id = st.selectbox(
                "إلى مركز:",
                options=[c.id for c in active_centers],
                format_func=lambda x: next(
                    (f"{c.code} - {c.name}" for c in active_centers if c.id == x),
                    str(x)),
                key=f"{PFX}tr_to",   # ✅
            )

        transfer_date = st.date_input(
            "تاريخ التحويل:",
            value=datetime.now().date(),
            key=f"{PFX}tr_date",   # ✅
        )
        transfer_amount = st.number_input(
            "مبلغ التحويل:",
            min_value=0.01, step=100.0,
            format="%.2f", key=f"{PFX}tr_amount",   # ✅
        )
        transfer_description = st.text_area(
            "وصف التحويل:",
            key=f"{PFX}tr_desc",   # ✅
        )

        if st.button("🔄 تنفيذ التحويل", type="primary",
                     use_container_width=True, key=f"{PFX}tr_save"):
            if from_center_id == to_center_id:
                st.error("❌ لا يمكن التحويل بين نفس المركز!")
            elif transfer_amount <= 0:
                st.error("❌ يرجى إدخال مبلغ صحيح!")
            elif not transfer_description:
                st.error("❌ يرجى إدخال وصف التحويل!")
            else:
                try:
                    transfer_datetime = datetime.combine(
                        transfer_date, datetime.min.time()
                    )

                    result = transfer_between_cost_centers(
                        from_center_id=from_center_id,
                        to_center_id=to_center_id,
                        amount=transfer_amount,
                        description=transfer_description,
                        transfer_date=transfer_datetime,
                        created_by=current_user_id,
                    )

                    st.success(
                        f"✅ تم التحويل بنجاح: {transfer_amount:,.2f} ج.م من "
                        f"{result['from']} إلى {result['to']}"
                    )

                    # ✅ تفريغ كل حقول النموذج
                    clear_form(PFX)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

        st.markdown("---")
        st.markdown("### 📋 سجل التحويلات")

        transfers = db.query(CostCenterTransaction).filter(
            CostCenterTransaction.transaction_type.in_(['transfer_in', 'transfer_out'])
        ).order_by(CostCenterTransaction.date.desc()).limit(20).all()

        if transfers:
            center_map = {c.id: c for c in db.query(CostCenter).all()}

            data = []
            for t in transfers:
                center = center_map.get(t.cost_center_id)
                data.append({
                    "التاريخ": t.date.strftime("%Y-%m-%d"),
                    "المركز": center.name if center else "-",
                    "النوع": "وارد" if t.transaction_type == 'transfer_in' else "صادر",
                    "المبلغ": f"{t.amount:,.2f} ج.م",
                    "الوصف": t.description,
                })

            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("لا توجد تحويلات مسجلة.")

db.close()