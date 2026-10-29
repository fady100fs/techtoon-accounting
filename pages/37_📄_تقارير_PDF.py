"""
تقارير PDF — Lazy imports لتسريع البدء.
"""

import streamlit as st
from datetime import datetime
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar
render_sidebar()
st.set_page_config(page_title="تقارير PDF", page_icon="📄", layout="wide")

from feature_flags import pdf_reports_enabled
if not pdf_reports_enabled():
    st.warning("⚠️ ميزة تقارير PDF غير مفعّلة في هذه النسخة.")
    st.stop()


# ============ دوال الاستيراد المتأخر ============
def _load_reportlab():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    return A4, canvas, mm, pdfmetrics, TTFont


def _load_arabic():
    import arabic_reshaper
    from bidi.algorithm import get_display
    return arabic_reshaper, get_display


def _register_arabic_font():
    """تسجيل خط عربي في reportlab."""
    _, _, _, pdfmetrics, TTFont = _load_reportlab()
    font_path = "fonts/Amiri-Regular.ttf"
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont("Amiri", font_path))
            return "Amiri"
        except Exception:
            pass
    return "Helvetica"


def ar(text: str) -> str:
    """تحويل نص عربي لعرضه في PDF."""
    try:
        arabic_reshaper, get_display = _load_arabic()
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)


# ============ إنشاء PDF ============
def generate_simple_pdf(title: str, rows: list, filename: str):
    """توليد PDF بسيط مع عنوان وجدول بيانات."""
    A4, canvas, mm, _, _ = _load_reportlab()
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as cv

    font = _register_arabic_font()
    c = cv.Canvas(filename, pagesize=A4)
    width, height = A4

    # العنوان
    c.setFont(font, 18)
    c.drawCentredString(width / 2, height - 30 * mm, ar(title))

    # التاريخ
    c.setFont(font, 10)
    c.drawCentredString(width / 2, height - 38 * mm, ar(datetime.now().strftime("%Y-%m-%d %H:%M")))

    # البيانات
    c.setFont(font, 11)
    y = height - 50 * mm
    for row in rows:
        if y < 20 * mm:
            c.showPage()
            c.setFont(font, 11)
            y = height - 20 * mm
        text = " | ".join(str(v) for v in row.values()) if isinstance(row, dict) else str(row)
        c.drawRightString(width - 15 * mm, y, ar(text))
        y -= 7 * mm

    c.save()
    return filename


# ============ الواجهة ============
st.title("📄 تقارير PDF")
st.caption("أنشئ تقارير احترافية بالعربية جاهزة للطباعة.")

report_type = st.selectbox(
    "نوع التقرير",
    ["فاتورة", "كشف حساب", "ميزانية عمومية", "تقرير أرباح"],
)

st.divider()

if st.button("📥 إنشاء PDF", type="primary"):
    with st.spinner("جارٍ إنشاء التقرير..."):
        try:
            rows = [{"البيان": "عينة", "القيمة": "0.00"}]
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            generate_simple_pdf(report_type, rows, filename)

            with open(filename, "rb") as f:
                st.download_button(
                    "⬇️ تنزيل التقرير",
                    f.read(),
                    file_name=filename,
                    mime="application/pdf",
                )
            st.success("✅ تم إنشاء التقرير بنجاح.")
        except Exception as e:
            st.error(f"⚠️ خطأ: {e}")
            st.caption("تأكد من وجود خط عربي في مجلد fonts/")