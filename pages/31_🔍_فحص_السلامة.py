# pages/31_🔍_فحص_السلامة.py
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
from services import check_accounting_integrity, validate_all_journal_entries
from auth_required import require_login, get_current_user_name
from form_manager import clear_form, show_clear_hint

# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لكل مفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "integrity_"


current_user = require_login()
current_user_name = get_current_user_name()

st.set_page_config(page_title="فحص السلامة", page_icon="🔍", layout="wide")
st.title("🔍 فحص سلامة النظام المحاسبي")

show_clear_hint()  # 💡 الحقول ستُفرَّغ تلقائياً بعد كل عملية
st.info(f"👤 المستخدم: **{current_user_name}**")

st.markdown("""
هذه الصفحة تفحص سلامة البيانات المحاسبية:
- القيود غير المتوازنة
- الأسطر اليتيمة
- أرقام الفواتير المكررة
- الأصناف تحت الحد الأدنى
""")

if st.button("🔍 بدء الفحص الشامل", type="primary", use_container_width=True):
    with st.spinner("جاري فحص النظام..."):
        report = check_accounting_integrity()

    st.markdown("---")
    st.subheader("📊 نتيجة الفحص")

    # 1) القيود غير المتوازنة
    if report["unbalanced_entries"]:
        st.error(f"⛔ يوجد **{len(report['unbalanced_entries'])}** قيد غير متوازن!")
        df = pd.DataFrame(report["unbalanced_entries"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.success("✅ جميع القيود متوازنة.")

    # 2) الأسطر اليتيمة
    if report["orphan_journal_lines"] > 0:
        st.warning(f"⚠️ يوجد **{report['orphan_journal_lines']}** سطر بدون قيد أب.")
    else:
        st.success("✅ لا يوجد أسطر يتيمة.")

    # 3) أرقام فواتير مكررة
    if report["duplicate_invoice_numbers"]:
        st.error(f"⛔ يوجد **{len(report['duplicate_invoice_numbers'])}** رقم فاتورة مكرر!")
        df = pd.DataFrame(report["duplicate_invoice_numbers"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.success("✅ جميع أرقام الفواتير فريدة.")

    # 4) أصناف تحت الحد
    if report["low_stock_count"] > 0:
        st.info(f"📦 يوجد **{report['low_stock_count']}** صنف تحت الحد الأدنى للمخزون.")
    else:
        st.success("✅ جميع الأصناف فوق الحد الأدنى.")

    st.markdown("---")
    st.caption(f"🕐 آخر فحص: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# === قسم إحصاءات الفترات ===
st.markdown("---")
st.subheader("📅 حالة الفترات المحاسبية")

db = SessionLocal()
try:
    periods = db.query(models.AccountingPeriod).order_by(
        models.AccountingPeriod.start_date.desc()
    ).all()

    if periods:
        rows = []
        for p in periods:
            rows.append({
                "الفترة": p.period_name,
                "من": p.start_date.strftime("%Y-%m-%d") if p.start_date else "-",
                "إلى": p.end_date.strftime("%Y-%m-%d") if p.end_date else "-",
                "الحالة": p.status.value,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد فترات محاسبية.")
finally:
    db.close()