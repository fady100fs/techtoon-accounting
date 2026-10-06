# pages/37_📄_تقارير_PDF.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

from database import SessionLocal
import models
from pdf_reports import (
    build_invoice_pdf,
    build_statement_pdf,
    build_balance_sheet_pdf,
    build_profit_loss_pdf,
    test_pdf_generation,
)
from services import (
    get_balance_sheet,
    get_income_statement,
    get_user_name_by_id,
)
from auth_required import require_login, get_current_user_name

current_user = require_login()
current_user_name = get_current_user_name()

st.set_page_config(page_title="تقارير PDF", page_icon="📄", layout="wide")
st.title("📄 تقارير PDF الاحترافية")
st.info(f"👤 المستخدم: **{current_user_name}**")


# ==========================================
# فحص الإعداد
# ==========================================
with st.expander("⚙️ حالة النظام", expanded=False):
    info = test_pdf_generation()

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if info["font_found"]:
            st.success(f"✅ خط عربي: موجود")
        else:
            st.error("❌ خط عربي غير موجود!")
        st.caption(f"المسار: `{info['font_path'] or 'غير موجود'}`")

    with col_b:
        if info["arabic_support"]:
            st.success("✅ دعم العربية: مفعّل")
        else:
            st.warning("⚠️ دعم العربية: غير مفعّل")

    with col_c:
        st.info(f"الخط المسجّل: `{info['registered_font']}`")

    if not info["font_found"]:
        st.warning("""
        ⚠️ **لم يُعثر على خط عربي!**

        **الحل:**
        1. حمّل خط من:
           - https://github.com/aliftype/amiri/releases
           - https://fonts.google.com/specimen/Cairo
        2. ضعه في مجلد `fonts/` بجذر المشروع
        3. أعد التشغيل
        """)


# ==========================================
# التبويبات
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🧾 فاتورة",
    "📋 كشف حساب",
    "⚖️ ميزانية عمومية",
    "💰 أرباح وخسائر",
])

db = SessionLocal()


# ==========================================
# التبويب 1: فاتورة
# ==========================================
with tab1:
    st.subheader("🧾 تصدير فاتورة PDF")

    # فلاتر
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        inv_type_filter = st.radio(
            "نوع الفاتورة:",
            ["الكل", "بيع", "شراء"],
            horizontal=True,
            key="pdf_inv_type",
        )
    with col_f2:
        days = st.number_input(
            "آخر كم يوم:",
            min_value=1, max_value=365,
            value=90, step=30,
            key="pdf_inv_days",
        )

    # جلب الفواتير
    cutoff = datetime.now() - timedelta(days=days)
    q = db.query(models.Invoice).filter(models.Invoice.date >= cutoff)
    if inv_type_filter == "بيع":
        q = q.filter(models.Invoice.type == 'sale')
    elif inv_type_filter == "شراء":
        q = q.filter(models.Invoice.type == 'purchase')

    invoices = q.order_by(models.Invoice.date.desc()).limit(200).all()

    if not invoices:
        st.info("لا توجد فواتير في الفترة المحددة.")
    else:
        inv_opts = {}
        for inv in invoices:
            type_ar = "بيع" if inv.type == "sale" else "شراء"
            date_s = inv.date.strftime("%Y-%m-%d") if inv.date else "—"
            inv_opts[inv.id] = f"{inv.invoice_number} — {type_ar} — {date_s} — {inv.net_amount:,.2f} ج.م"

        selected_inv_id = st.selectbox(
            "اختر فاتورة:",
            options=list(inv_opts.keys()),
            format_func=lambda x: inv_opts[x],
            key="pdf_inv_sel",
        )

        if selected_inv_id:
            inv = next((i for i in invoices if i.id == selected_inv_id), None)
            if inv:
                # معاينة
                party = db.query(models.Party).filter(models.Party.id == inv.party_id).first()

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("رقم الفاتورة", inv.invoice_number)
                with col_b:
                    st.metric("الطرف", party.name if party else "—")
                with col_c:
                    st.metric("الصافي", f"{inv.net_amount:,.2f} ج.م")

                if st.button("📄 توليد PDF", type="primary", use_container_width=True, key="gen_inv_pdf"):
                    try:
                        from export_pdf import export_invoice_to_pdf

                        output_path = export_invoice_to_pdf(inv.id)

                        with open(output_path, "rb") as f:
                            pdf_bytes = f.read()

                        st.success(f"✅ تم التوليد: {output_path}")
                        st.download_button(
                            label="⬇️ تحميل PDF",
                            data=pdf_bytes,
                            file_name=output_path,
                            mime="application/pdf",
                            key="dl_inv_pdf",
                        )
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")
                        import traceback
                        st.code(traceback.format_exc())


# ==========================================
# التبويب 2: كشف حساب
# ==========================================
with tab2:
    st.subheader("📋 تصدير كشف حساب PDF")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        party_type = st.radio(
            "نوع الطرف:",
            ["customer", "supplier"],
            format_func=lambda x: "عميل" if x == "customer" else "مورد",
            horizontal=True,
            key="pdf_stmt_type",
        )
    with col_f2:
        st.write("")

    parties = db.query(models.Party).filter(
        models.Party.type == party_type
    ).order_by(models.Party.name).all()

    if not parties:
        st.info("لا يوجد عملاء/موردين.")
    else:
        party_opts = {p.id: p.name for p in parties}
        selected_party_id = st.selectbox(
            "اختر الطرف:",
            options=list(party_opts.keys()),
            format_func=lambda x: party_opts[x],
            key="pdf_stmt_party",
        )

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            from_date = st.date_input(
                "من تاريخ:",
                value=datetime.now().replace(day=1).date(),
                key="pdf_stmt_from",
            )
        with col_d2:
            to_date = st.date_input(
                "إلى تاريخ:",
                value=date.today(),
                key="pdf_stmt_to",
            )

        if st.button("📄 توليد كشف حساب", type="primary", use_container_width=True, key="gen_stmt_pdf"):
            try:
                from services import _build_statement_data  # سأضيفها لاحقاً
            except ImportError:
                # نبني الكشف محلياً
                party = db.query(models.Party).filter(models.Party.id == selected_party_id).first()

                start_dt = datetime.combine(from_date, datetime.min.time())
                end_dt = datetime.combine(to_date, datetime.max.time())

                # الفواتير
                invoices = db.query(models.Invoice).filter(
                    models.Invoice.party_id == selected_party_id,
                    models.Invoice.date >= start_dt,
                    models.Invoice.date <= end_dt,
                ).order_by(models.Invoice.date).all()

                # المدفوعات
                payments = db.query(models.Payment).filter(
                    models.Payment.party_id == selected_party_id,
                    models.Payment.date >= start_dt,
                    models.Payment.date <= end_dt,
                ).order_by(models.Payment.date).all()

                # بناء الصفوف
                rows = []
                running = 0.0
                total_debit = 0.0
                total_credit = 0.0

                all_events = []
                for inv in invoices:
                    if inv.type == 'sale':
                        all_events.append({
                            "date": inv.date,
                            "desc": f"فاتورة بيع {inv.invoice_number}",
                            "debit": float(inv.net_amount or 0),
                            "credit": 0.0,
                        })
                    else:
                        all_events.append({
                            "date": inv.date,
                            "desc": f"فاتورة شراء {inv.invoice_number}",
                            "debit": 0.0,
                            "credit": float(inv.net_amount or 0),
                        })

                for pay in payments:
                    if pay.payment_type == 'receipt':
                        all_events.append({
                            "date": pay.date,
                            "desc": f"دفعة قبض {pay.reference_number or ''}",
                            "debit": 0.0,
                            "credit": float(pay.amount or 0),
                        })
                    else:
                        all_events.append({
                            "date": pay.date,
                            "desc": f"دفعة صرف {pay.reference_number or ''}",
                            "debit": float(pay.amount or 0),
                            "credit": 0.0,
                        })

                all_events.sort(key=lambda x: x["date"] or datetime.min)

                for ev in all_events:
                    running += ev["debit"] - ev["credit"]
                    total_debit += ev["debit"]
                    total_credit += ev["credit"]
                    rows.append({
                        "date": ev["date"].strftime("%Y-%m-%d") if ev["date"] else "—",
                        "description": ev["desc"],
                        "debit": ev["debit"],
                        "credit": ev["credit"],
                        "balance": running,
                    })

                # توليد PDF
                output_path = f"Statement_{party.name[:30]}_{to_date}.pdf"
                statement_data = {
                    "party_name": party.name,
                    "party_type": party_type,
                    "party_phone": party.phone or "",
                    "party_address": party.address or "",
                    "from_date": from_date.strftime("%Y-%m-%d"),
                    "to_date": to_date.strftime("%Y-%m-%d"),
                    "rows": rows,
                    "total_debit": total_debit,
                    "total_credit": total_credit,
                    "running_balance": running,
                }

                build_statement_pdf(statement_data, output_path)

                with open(output_path, "rb") as f:
                    pdf_bytes = f.read()

                st.success(f"✅ تم التوليد: {output_path}")
                st.download_button(
                    label="⬇️ تحميل PDF",
                    data=pdf_bytes,
                    file_name=output_path,
                    mime="application/pdf",
                    key="dl_stmt_pdf",
                )
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
                import traceback
                st.code(traceback.format_exc())


# ==========================================
# التبويب 3: ميزانية عمومية
# ==========================================
with tab3:
    st.subheader("⚖️ تصدير ميزانية عمومية PDF")

    as_of = st.date_input(
        "بتاريخ:",
        value=date.today(),
        key="pdf_bs_date",
    )

    if st.button("📄 توليد الميزانية", type="primary", use_container_width=True, key="gen_bs_pdf"):
        try:
            balance_data = get_balance_sheet(datetime.combine(as_of, datetime.max.time()))

            output_path = f"BalanceSheet_{as_of}.pdf"
            build_balance_sheet_pdf(balance_data, output_path)

            with open(output_path, "rb") as f:
                pdf_bytes = f.read()

            st.success(f"✅ تم التوليد: {output_path}")
            st.download_button(
                label="⬇️ تحميل PDF",
                data=pdf_bytes,
                file_name=output_path,
                mime="application/pdf",
                key="dl_bs_pdf",
            )

            # معاينة
            st.markdown("---")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("إجمالي الأصول", f"{balance_data['total_assets']:,.2f} ج.م")
            with col_b:
                st.metric("إجمالي الخصوم", f"{balance_data['total_liabilities']:,.2f} ج.م")
            with col_c:
                st.metric("حقوق الملكية", f"{balance_data['total_equity']:,.2f} ج.م")
        except Exception as e:
            st.error(f"❌ خطأ: {e}")
            import traceback
            st.code(traceback.format_exc())


# ==========================================
# التبويب 4: أرباح وخسائر
# ==========================================
with tab4:
    st.subheader("💰 تصدير تقرير الأرباح والخسائر PDF")

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        pl_from = st.date_input(
            "من تاريخ:",
            value=datetime.now().replace(month=1, day=1).date(),
            key="pdf_pl_from",
        )
    with col_d2:
        pl_to = st.date_input(
            "إلى تاريخ:",
            value=date.today(),
            key="pdf_pl_to",
        )

    if st.button("📄 توليد التقرير", type="primary", use_container_width=True, key="gen_pl_pdf"):
        try:
            pl_data = get_income_statement(
                datetime.combine(pl_from, datetime.min.time()),
                datetime.combine(pl_to, datetime.max.time()),
            )

            output_path = f"ProfitLoss_{pl_from}_{pl_to}.pdf"
            build_profit_loss_pdf(pl_data, output_path)

            with open(output_path, "rb") as f:
                pdf_bytes = f.read()

            st.success(f"✅ تم التوليد: {output_path}")
            st.download_button(
                label="⬇️ تحميل PDF",
                data=pdf_bytes,
                file_name=output_path,
                mime="application/pdf",
                key="dl_pl_pdf",
            )

            # معاينة
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("الإيرادات", f"{pl_data['revenue']:,.2f} ج.م")
            with c2:
                st.metric("إجمالي المصروفات", f"{pl_data['total_expenses']:,.2f} ج.م")
            with c3:
                st.metric("صافي الربح/الخسارة", f"{pl_data['net_profit']:,.2f} ج.م")
            with c4:
                st.metric("هامش الربح", f"{pl_data['net_margin']:.1f}%")
        except Exception as e:
            st.error(f"❌ خطأ: {e}")
            import traceback
            st.code(traceback.format_exc())

db.close()