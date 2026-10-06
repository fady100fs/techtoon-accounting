# pages/6_📋_فهرس_الفواتير.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()

import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from models import CashBox
from services import create_payment, movement_serial
from auth_required import require_login, get_current_user_id, get_current_user_name
from cache_helpers import get_invoices_index, invalidate_all

current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="فهرس الفواتير", page_icon="📋", layout="wide")
st.title("📋 فهرس الفواتير")

db = SessionLocal()

try:
    search_query = st.text_input(
        "🔍 البحث برقم الفاتورة:",
        placeholder="أدخل رقم الفاتورة للبحث..."
    )

    filter_type = st.radio(
        "تصفية حسب النوع:",
        ["الكل", "بيع", "شراء"],
        horizontal=True
    )

    # ✅ استعلام واحد مخزّن بدل N+1
    all_invoices = get_invoices_index(limit=1000)

    # تصفية في الذاكرة (سريعة جداً)
    invoices_data = all_invoices
    if search_query:
        invoices_data = [
            i for i in invoices_data
            if search_query in i["invoice_number"]
        ]
    if filter_type != "الكل":
        actual_type = 'sale' if filter_type == 'بيع' else 'purchase'
        invoices_data = [i for i in invoices_data if i["type"] == actual_type]

    if invoices_data:
        # ==========================================
        # جدول الفواتير + Pagination
        # ==========================================
        PAGE_SIZE = 30
        total_count = len(invoices_data)
        total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)

        col_p1, col_p2, col_p3 = st.columns([2, 2, 1])
        with col_p1:
            st.caption(f"📊 إجمالي: **{total_count}** فاتورة")
        with col_p2:
            st.caption(f"📄 صفحة **{total_pages}**")
        with col_p3:
            page_num = st.number_input(
                "صفحة:",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1,
                key="inv_page_num"
            )

        start = (page_num - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        page_invoices = invoices_data[start:end]

        data = []
        for inv in page_invoices:
            data.append({
                "المسلسل": inv["invoice_number"],
                "ID": inv["id"],
                "التاريخ": inv["date"].strftime("%Y-%m-%d %H:%M") if inv["date"] else "-",
                "النوع": "بيع" if inv["type"] == 'sale' else "شراء",
                "العميل/المورد": inv["party_name"],
                "المبلغ": f"{inv['net_amount']:,.2f} ج.م",
                "المدفوع": f"{inv['paid_amount']:,.2f} ج.م",
                "المتبقي": f"{inv['remaining']:,.2f} ج.م",
                "الحالة": inv["status"],
                "أنشأها": inv["created_by_name"],
            })

        df = pd.DataFrame(data)
        st.dataframe(
            df.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            f"عرض {start + 1} - {min(end, total_count)} من {total_count}"
        )

        st.markdown("---")
        st.subheader("⚙️ إدارة الفواتير")

        # قائمة الاختيار
        invoice_ids = [inv["id"] for inv in invoices_data]
        invoice_nums = {inv["id"]: inv["invoice_number"] for inv in invoices_data}

        selected_invoice_id = st.selectbox(
            "اختر فاتورة:",
            options=invoice_ids,
            format_func=lambda x: invoice_nums.get(x, str(x)),
            key="idx_selected_invoice"
        )

        if selected_invoice_id:
            selected_invoice = db.query(models.Invoice).filter(
                models.Invoice.id == selected_invoice_id
            ).first()

            tab1, tab2, tab3 = st.tabs(
                ["📄 عرض التفاصيل", "✏️ تعديل/حذف", "💰 تسجيل دفعة"]
            )

            # ==========================================
            # تبويب 1: التفاصيل
            # ==========================================
            with tab1:
                st.markdown("**تفاصيل الفاتورة:**")
                party = db.query(models.Party).filter(
                    models.Party.id == selected_invoice.party_id
                ).first()
                currency = db.query(models.Currency).filter(
                    models.Currency.id == selected_invoice.currency_id
                ).first()
                currency_symbol = currency.symbol if currency else "ج.م"

                creator = db.query(models.User).filter(
                    models.User.id == selected_invoice.created_by
                ).first() if selected_invoice.created_by else None
                creator_name = creator.full_name if creator else "النظام"

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.write(f"**رقم الفاتورة:** {selected_invoice.invoice_number}")
                    st.write(f"**التاريخ:** {selected_invoice.date.strftime('%Y-%m-%d %H:%M') if selected_invoice.date else '-'}")
                    st.write(f"**النوع:** {'بيع' if selected_invoice.type == 'sale' else 'شراء'}")
                with col_b:
                    st.write(f"**العميل/المورد:** {party.name if party else 'غير محدد'}")
                    st.write(f"**الإجمالي:** {selected_invoice.net_amount:,.2f} {currency_symbol}")
                    st.write(f"**الحالة:** {selected_invoice.status}")
                with col_c:
                    st.write(f"**أنشأها:** {creator_name}")

                st.markdown("---")
                st.markdown("**أصناف الفاتورة:**")

                invoice_lines = db.query(models.InvoiceLine).filter(
                    models.InvoiceLine.invoice_id == selected_invoice.id
                ).all()

                if invoice_lines:
                    item_ids = [line.item_id for line in invoice_lines]
                    items_map = {it.id: it.name for it in db.query(models.Item).filter(
                        models.Item.id.in_(item_ids)
                    ).all()}

                    lines_data = []
                    for line in invoice_lines:
                        lines_data.append({
                            "الصنف": items_map.get(line.item_id, "غير محدد"),
                            "الكمية": line.quantity,
                            "سعر الوحدة": f"{line.price:,.2f} {currency_symbol}",
                            "الإجمالي": f"{line.total:,.2f} {currency_symbol}"
                        })
                    st.dataframe(
                        pd.DataFrame(lines_data),
                        use_container_width=True,
                        hide_index=True
                    )

            # ==========================================
            # تبويب 2: التعديل/الحذف
            # ==========================================
            with tab2:
                st.subheader("⚙️ قواعد التعديل والحذف")

                payments = db.query(models.Payment).filter(
                    models.Payment.reference_number == selected_invoice.invoice_number
                ).all()
                has_payments = len(payments) > 0

                if has_payments:
                    st.error(f"⛔ هذه الفاتورة مرتبطة بـ {len(payments)} سند دفع/قبض")
                    st.info("للتعديل: ألغِ السندات أولاً، أو غيّر حالة الفاتورة فقط.")
                else:
                    st.warning("هذه الفاتورة غير مرتبطة بأي سندات.")

                st.markdown("---")
                st.subheader("✏️ تعديل حالة الفاتورة")

                new_status = st.selectbox(
                    "الحالة الجديدة:",
                    ["pending", "paid", "cancelled"],
                    format_func=lambda x: {
                        "pending": "معلقة",
                        "paid": "مدفوعة",
                        "cancelled": "ملغاة"
                    }.get(x, x),
                    index=["pending", "paid", "cancelled"].index(
                        selected_invoice.status
                    ) if selected_invoice.status in ["pending", "paid", "cancelled"] else 0,
                    key=f"idx_status_{selected_invoice.id}"
                )

                if st.button(
                    "💾 حفظ تغييرات الحالة",
                    type="primary",
                    key=f"idx_save_status_{selected_invoice.id}"
                ):
                    selected_invoice.status = new_status
                    db.commit()
                    invalidate_all()
                    st.success(f"✅ تم تحديث الحالة! (بواسطة: {current_user_name})")
                    st.rerun()

                st.markdown("---")
                st.info(
                    "💡 **لا يمكن حذف الفواتير** — وثائق محاسبية رسمية. "
                    "استخدم 'ملغاة' بدلاً من الحذف."
                )

            # ==========================================
            # تبويب 3: تسجيل دفعة
            # ==========================================
            with tab3:
                st.markdown("**تسجيل دفعة جديدة:**")

                existing_payments = db.query(models.Payment).filter(
                    models.Payment.reference_number == selected_invoice.invoice_number
                ).all()
                paid_amount = sum(p.amount or 0 for p in existing_payments)
                remaining = (selected_invoice.net_amount or 0) - paid_amount

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("الإجمالي", f"{selected_invoice.net_amount:,.2f} ج.م")
                with col_b:
                    st.metric("المدفوع", f"{paid_amount:,.2f} ج.م")
                with col_c:
                    st.metric("المتبقي", f"{remaining:,.2f} ج.م")

                if remaining <= 0.01:
                    st.success("✅ تم سداد هذه الفاتورة بالكامل!")
                else:
                    st.markdown("---")

                    payment_date = st.date_input(
                        "تاريخ الدفعة:",
                        value=datetime.now().date(),
                        key=f"idx_pay_date_{selected_invoice.id}"
                    )
                    payment_time = st.time_input(
                        "وقت الدفعة:",
                        value=datetime.now().time(),
                        key=f"idx_pay_time_{selected_invoice.id}"
                    )

                    payment_amount = st.number_input(
                        "مبلغ الدفعة:",
                        min_value=0.01,
                        max_value=float(remaining),
                        value=float(remaining),
                        step=100.0,
                        key=f"idx_pay_amount_{selected_invoice.id}"
                    )

                    payment_method = st.selectbox(
                        "طريقة الدفع:",
                        ["cash (نقدي)", "bank_transfer (تحويل بنكي)", "check (شيك)"],
                        key=f"idx_pay_method_{selected_invoice.id}"
                    )
                    actual_method = payment_method.split(" ")[0]

                    cash_boxes = db.query(CashBox).filter(
                        CashBox.is_active == True
                    ).all()
                    cash_box_dict = {
                        box.id: f"{box.name} ({box.code})" for box in cash_boxes
                    }

                    if cash_boxes:
                        selected_cash_box_id = st.selectbox(
                            "الخزينة:",
                            options=list(cash_box_dict.keys()),
                            format_func=lambda x: cash_box_dict[x],
                            key=f"idx_pay_box_{selected_invoice.id}"
                        )

                        from services import get_cash_box_balance
                        current_balance = get_cash_box_balance(selected_cash_box_id)
                        st.info(f"💰 الرصيد الحالي: **{current_balance:,.2f} ج.م**")
                    else:
                        st.warning("⚠️ لا توجد خزائن!")
                        selected_cash_box_id = None

                    reference_number = st.text_input(
                        "رقم المرجع:",
                        value=f"دفعة فاتورة {selected_invoice.invoice_number}",
                        key=f"idx_pay_ref_{selected_invoice.id}"
                    )
                    notes = st.text_area(
                        "ملاحظات:",
                        key=f"idx_pay_notes_{selected_invoice.id}"
                    )

                    if st.button(
                        "💰 تسجيل الدفعة",
                        type="primary",
                        key=f"idx_save_payment_{selected_invoice.id}"
                    ):
                        if not selected_cash_box_id:
                            st.error("يرجى اختيار الخزينة")
                        else:
                            try:
                                payment_datetime = datetime.combine(
                                    payment_date, payment_time
                                )
                                create_payment(
                                    party_id=selected_invoice.party_id,
                                    amount=payment_amount,
                                    payment_type="receipt" if selected_invoice.type == 'sale' else "payment",
                                    payment_method=actual_method,
                                    reference_number=reference_number,
                                    notes=notes,
                                    currency_id=selected_invoice.currency_id,
                                    payment_date=payment_datetime,
                                    created_by=current_user_id,
                                    cash_box_id=selected_cash_box_id
                                )

                                if payment_amount >= remaining - 0.01:
                                    selected_invoice.status = 'paid'
                                    db.commit()

                                invalidate_all()
                                st.success(
                                    f"✅ تم تسجيل دفعة {payment_amount:,.2f} ج.م!"
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ خطأ: {e}")
    else:
        st.info("لا توجد فواتير مطابقة.")

finally:
    db.close()