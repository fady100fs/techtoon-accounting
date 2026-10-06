# pdf_reports.py
"""
مولّد تقارير PDF احترافي بالعربية
- يستخدم إعدادات الشركة من settings_manager
- يدعم RTL + تشكيل عربي
- قوالب: فاتورة، كشف حساب، ميزانية، أرباح
"""

import base64
import io
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
    PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# معالجة العربية
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    ARABIC_SUPPORT = False

from settings_manager import get_company_info, get_financial_defaults


# ==========================================================
# إدارة الخطوط
# ==========================================================
_FONTS_DIR = Path(__file__).parent / "fonts"
_REGISTERED_FONT = None
_FONT_NAME = "ArabicFont"


def _find_font_file():
    """يبحث عن ملف خط عربي في أماكن متعددة."""
    # 1) مجلد fonts المحلي
    candidates = [
        _FONTS_DIR / "Amiri-Regular.ttf",
        _FONTS_DIR / "Cairo-Regular.ttf",
        _FONTS_DIR / "NotoSansArabic-Regular.ttf",
        _FONTS_DIR / "arial.ttf",
        _FONTS_DIR / "tahoma.ttf",
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    # 2) خطوط النظام
    system = platform.system()
    if system == "Windows":
        win_fonts = [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\tahoma.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
        ]
        for f in win_fonts:
            if os.path.exists(f):
                return f
    elif system == "Linux":
        linux_fonts = [
            "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
        for f in linux_fonts:
            if os.path.exists(f):
                return f

    return None


def _register_font():
    """يسجّل الخط العربي عند أول استخدام."""
    global _REGISTERED_FONT
    if _REGISTERED_FONT is not None:
        return _REGISTERED_FONT

    font_path = _find_font_file()
    if not font_path:
        _REGISTERED_FONT = "Helvetica"
        return _REGISTERED_FONT

    try:
        pdfmetrics.registerFont(TTFont(_FONT_NAME, font_path))
        _REGISTERED_FONT = _FONT_NAME
    except Exception:
        _REGISTERED_FONT = "Helvetica"

    return _REGISTERED_FONT


def ar(text):
    """يعالج النص العربي للعرض في PDF (تشكيل + RTL)."""
    if text is None:
        return ""
    text = str(text)
    if not text.strip():
        return ""

    if not ARABIC_SUPPORT:
        return text

    try:
        reshaped = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped)
        return bidi_text
    except Exception:
        return text


# ==========================================================
# الأنماط
# ==========================================================
def _get_styles():
    font = _register_font()
    company = get_company_info()
    primary = colors.HexColor(company.get("primary_color", "#2563eb"))

    styles = getSampleStyleSheet()

    # عنوان رئيسي
    title = ParagraphStyle(
        "ArabicTitle",
        parent=styles["Heading1"],
        fontName=font,
        fontSize=22,
        textColor=primary,
        alignment=TA_CENTER,
        spaceAfter=8,
        leading=28,
    )

    # عنوان فرعي
    subtitle = ParagraphStyle(
        "ArabicSubtitle",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=14,
        textColor=colors.HexColor("#444444"),
        alignment=TA_CENTER,
        spaceAfter=6,
    )

    # عنوان قسم
    section = ParagraphStyle(
        "ArabicSection",
        parent=styles["Heading3"],
        fontName=font,
        fontSize=13,
        textColor=primary,
        alignment=TA_RIGHT,
        spaceBefore=12,
        spaceAfter=8,
        borderPadding=4,
    )

    # نص عادي RTL
    body_rtl = ParagraphStyle(
        "ArabicBody",
        parent=styles["Normal"],
        fontName=font,
        fontSize=10,
        alignment=TA_RIGHT,
        leading=15,
        spaceAfter=4,
    )

    # نص عادي LTR
    body_ltr = ParagraphStyle(
        "ArabicBodyLTR",
        parent=styles["Normal"],
        fontName=font,
        fontSize=10,
        alignment=TA_LEFT,
        leading=15,
    )

    # سطر صغير
    small = ParagraphStyle(
        "ArabicSmall",
        parent=styles["Normal"],
        fontName=font,
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )

    return {
        "title": title,
        "subtitle": subtitle,
        "section": section,
        "body": body_rtl,
        "body_ltr": body_ltr,
        "small": small,
        "font": font,
        "primary": primary,
    }


# ==========================================================
# Header مشترك لكل الصفحات
# ==========================================================
def _build_header(styles, document_title: str, extra_info: dict = None):
    """يبني ترويسة موحّدة للتقارير."""
    company = get_company_info()
    font = styles["font"]
    primary = styles["primary"]

    elements = []

    # الشعار + اسم الشركة
    logo_data = company.get("logo_base64", "")
    logo_image = None

    if logo_data:
        try:
            logo_bytes = base64.b64decode(logo_data)
            logo_image = Image(io.BytesIO(logo_bytes), width=3*cm, height=3*cm)
        except Exception:
            logo_image = None

    # معلومات الشركة
    company_info_lines = [
        Paragraph(ar(company["name"]), ParagraphStyle(
            "CompanyName", fontName=font, fontSize=16,
            textColor=primary, alignment=TA_RIGHT, leading=20,
        )),
        Paragraph(ar(company.get("tagline", "")), styles["small"]) if company.get("tagline") else Spacer(1, 1),
    ]

    contact_parts = []
    if company.get("phone"):
        contact_parts.append(f"📞 {company['phone']}")
    if company.get("email"):
        contact_parts.append(f"📧 {company['email']}")
    if company.get("tax_id"):
        contact_parts.append(f"🧾 {company['tax_id']}")

    if contact_parts:
        company_info_lines.append(
            Paragraph(ar(" | ".join(contact_parts)), styles["small"])
        )

    if company.get("address"):
        company_info_lines.append(
            Paragraph(ar(f"📍 {company['address']}"), styles["small"])
        )

    # جدول الترويسة
    if logo_image:
        header_data = [[logo_image, company_info_lines]]
        col_widths = [3.5*cm, 13.5*cm]
    else:
        header_data = [[company_info_lines]]
        col_widths = [17*cm]

    header_table = Table(header_data, colWidths=col_widths)
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)

    # فاصل ملون
    separator = Table([[""]], colWidths=[17*cm], rowHeights=[3])
    separator.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), primary),
    ]))
    elements.append(Spacer(1, 4))
    elements.append(separator)
    elements.append(Spacer(1, 12))

    # عنوان التقرير
    elements.append(Paragraph(ar(document_title), styles["title"]))
    elements.append(Spacer(1, 6))

    # معلومات إضافية
    if extra_info:
        info_parts = []
        for k, v in extra_info.items():
            if v:
                info_parts.append(f"<b>{ar(k)}:</b> {ar(v)}")
        if info_parts:
            info_para = Paragraph(
                " &nbsp;•&nbsp; ".join(info_parts),
                styles["body"]
            )
            elements.append(info_para)

    elements.append(Spacer(1, 14))
    return elements


def _build_footer(styles):
    """يبني تذييل موحّد."""
    company = get_company_info()
    elements = []
    elements.append(Spacer(1, 20))

    footer_text = (
        f"{company['name']} — تم إنشاء التقرير في "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    elements.append(Paragraph(ar(footer_text), styles["small"]))
    return elements


# ==========================================================
# قوالب التقارير
# ==========================================================
def build_invoice_pdf(invoice_data: dict, output_path: str) -> str:
    """يبني PDF لفاتورة.

    Args:
        invoice_data: dict مع:
            - invoice_number: str
            - invoice_date: str/datetime
            - invoice_type: 'sale' | 'purchase'
            - party_name: str
            - party_phone, party_address: str (اختياري)
            - lines: list of {item_name, quantity, price, total}
            - subtotal, discount, tax, net_amount: float
            - notes: str (اختياري)
            - status: str
        output_path: مسار الملف الناتج

    Returns:
        مسار الملف
    """
    styles = _get_styles()
    font = styles["font"]
    primary = styles["primary"]
    company = get_company_info()

    # نوع الفاتورة
    inv_type_label = "فاتورة مبيعات" if invoice_data.get("invoice_type") == "sale" else "فاتورة مشتريات"

    extra_info = {
        "رقم الفاتورة": invoice_data.get("invoice_number", "—"),
        "التاريخ": str(invoice_data.get("invoice_date", "—"))[:10],
        "الحالة": invoice_data.get("status", "—"),
    }

    elements = _build_header(styles, inv_type_label, extra_info)

    # بيانات الطرف
    party_label = "العميل" if invoice_data.get("invoice_type") == "sale" else "المورد"
    party_info = f"""
    <b>{ar(party_label)}:</b> {ar(invoice_data.get('party_name', '—'))}<br/>
    """
    if invoice_data.get("party_phone"):
        party_info += f"<b>{ar('الهاتف')}:</b> {ar(invoice_data['party_phone'])}<br/>"
    if invoice_data.get("party_address"):
        party_info += f"<b>{ar('العنوان')}:</b> {ar(invoice_data['party_address'])}"

    elements.append(Paragraph(party_info, styles["body"]))
    elements.append(Spacer(1, 14))

    # جدول الأسطر
    lines = invoice_data.get("lines", [])
    if lines:
        headers = ["#", "الصنف", "الكمية", "السعر", "الإجمالي"]
        table_data = [[Paragraph(ar(h), styles["body_ltr"]) for h in headers]]

        for idx, line in enumerate(lines, start=1):
            table_data.append([
                Paragraph(str(idx), styles["body_ltr"]),
                Paragraph(ar(line.get("item_name", "—")), styles["body"]),
                Paragraph(f"{float(line.get('quantity', 0)):,.2f}", styles["body_ltr"]),
                Paragraph(f"{float(line.get('price', 0)):,.2f}", styles["body_ltr"]),
                Paragraph(f"{float(line.get('total', 0)):,.2f}", styles["body_ltr"]),
            ])

        col_widths = [1*cm, 7*cm, 2.5*cm, 3*cm, 3.5*cm]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            # رأس الجدول
            ("BACKGROUND", (0, 0), (-1, 0), primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), font),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),

            # الصفوف
            ("FONTNAME", (0, 1), (-1, -1), font),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (0, 1), (0, -1), "CENTER"),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("ALIGN", (2, 1), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("TOPPADDING", (0, 1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ]))
        elements.append(table)

    elements.append(Spacer(1, 14))

    # ملخص المبالغ
    financial_data = [
        [Paragraph(ar("المجموع الفرعي"), styles["body"]),
         Paragraph(f"{float(invoice_data.get('subtotal', 0)):,.2f}", styles["body_ltr"])],
    ]
    if invoice_data.get("discount", 0) > 0:
        financial_data.append([
            Paragraph(ar("الخصم"), styles["body"]),
            Paragraph(f"- {float(invoice_data['discount']):,.2f}", styles["body_ltr"]),
        ])
    if invoice_data.get("tax", 0) > 0:
        financial_data.append([
            Paragraph(ar("الضريبة"), styles["body"]),
            Paragraph(f"+ {float(invoice_data['tax']):,.2f}", styles["body_ltr"]),
        ])
    financial_data.append([
        Paragraph(f"<b>{ar('الصافي')}</b>", styles["body"]),
        Paragraph(f"<b>{float(invoice_data.get('net_amount', 0)):,.2f}</b>", styles["body_ltr"]),
    ])

    summary_table = Table(financial_data, colWidths=[13*cm, 4*cm])
    summary_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -2), 10),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("TEXTCOLOR", (0, -1), (-1, -1), primary),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, primary),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(summary_table)

    # الشروط + التذييل
    footer_text = company.get("tagline", "")
    terms = ""
    try:
        from settings_manager import get_setting
        footer_text = get_setting("invoice_footer_text", "")
        terms = get_setting("invoice_terms", "")
    except Exception:
        pass

    if terms:
        elements.append(Spacer(1, 18))
        elements.append(Paragraph(ar("الشروط والأحكام:"), styles["section"]))
        elements.append(Paragraph(ar(terms), styles["body"]))

    if footer_text:
        elements.append(Spacer(1, 18))
        elements.append(Paragraph(ar(footer_text), styles["small"]))

    elements.extend(_build_footer(styles))

    # بناء الملف
    _build_pdf(output_path, elements)
    return output_path


def build_statement_pdf(statement_data: dict, output_path: str) -> str:
    """يبني PDF لكشف حساب.

    Args:
        statement_data: dict مع:
            - party_name: str
            - party_type: 'customer' | 'supplier'
            - party_phone, party_address: str
            - rows: list of {date, description, debit, credit, balance}
            - total_debit, total_credit, running_balance: float
            - from_date, to_date: str
    """
    styles = _get_styles()
    font = styles["font"]
    primary = styles["primary"]

    party_type_label = "كشف حساب عميل" if statement_data.get("party_type") == "customer" else "كشف حساب مورد"

    extra_info = {
        "من": str(statement_data.get("from_date", "—"))[:10],
        "إلى": str(statement_data.get("to_date", "—"))[:10],
    }

    elements = _build_header(styles, party_type_label, extra_info)

    # بيانات الطرف
    party_info = f"<b>{ar('الاسم')}:</b> {ar(statement_data.get('party_name', '—'))}<br/>"
    if statement_data.get("party_phone"):
        party_info += f"<b>{ar('الهاتف')}:</b> {ar(statement_data['party_phone'])}<br/>"
    if statement_data.get("party_address"):
        party_info += f"<b>{ar('العنوان')}:</b> {ar(statement_data['party_address'])}"

    elements.append(Paragraph(party_info, styles["body"]))
    elements.append(Spacer(1, 14))

    # الجدول
    rows = statement_data.get("rows", [])
    if rows:
        headers = ["التاريخ", "البيان", "مدين", "دائن", "الرصيد"]
        table_data = [[Paragraph(ar(h), styles["body_ltr"]) for h in headers]]

        for r in rows:
            table_data.append([
                Paragraph(str(r.get("date", "—"))[:10], styles["body_ltr"]),
                Paragraph(ar(r.get("description", "—")), styles["body"]),
                Paragraph(f"{float(r.get('debit', 0)):,.2f}" if r.get("debit") else "—", styles["body_ltr"]),
                Paragraph(f"{float(r.get('credit', 0)):,.2f}" if r.get("credit") else "—", styles["body_ltr"]),
                Paragraph(f"{float(r.get('balance', 0)):,.2f}", styles["body_ltr"]),
            ])

        # صف الإجماليات
        table_data.append([
            Paragraph(f"<b>{ar('الإجمالي')}</b>", styles["body"]),
            Paragraph("", styles["body"]),
            Paragraph(f"<b>{float(statement_data.get('total_debit', 0)):,.2f}</b>", styles["body_ltr"]),
            Paragraph(f"<b>{float(statement_data.get('total_credit', 0)):,.2f}</b>", styles["body_ltr"]),
            Paragraph(f"<b>{float(statement_data.get('running_balance', 0)):,.2f}</b>", styles["body_ltr"]),
        ])

        col_widths = [2.5*cm, 6*cm, 2.8*cm, 2.8*cm, 2.9*cm]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), font),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8f9fa")]),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f4f8")),
            ("TEXTCOLOR", (0, -1), (-1, -1), primary),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph(ar("لا توجد حركات"), styles["body"]))

    # ملخص
    elements.append(Spacer(1, 14))
    balance = float(statement_data.get("running_balance", 0))
    balance_label = "له" if balance > 0 else "عليه"
    summary = f"""
    <b>{ar('الرصيد النهائي')}:</b>
    {abs(balance):,.2f} ج.م ({ar(balance_label)})
    """
    elements.append(Paragraph(summary, styles["body"]))

    elements.extend(_build_footer(styles))
    _build_pdf(output_path, elements)
    return output_path


def build_balance_sheet_pdf(balance_data: dict, output_path: str) -> str:
    """يبني PDF للميزانية العمومية.

    Args:
        balance_data: dict من get_balance_sheet
    """
    styles = _get_styles()
    font = styles["font"]
    primary = styles["primary"]

    extra_info = {"التاريخ": datetime.now().strftime("%Y-%m-%d")}
    elements = _build_header(styles, "الميزانية العمومية", extra_info)

    def _account_table(accounts_dict, title, total, color):
        """يبني جدول حسابات."""
        header = Paragraph(ar(title), ParagraphStyle(
            "SectionTitle", fontName=font, fontSize=12,
            textColor=color, alignment=TA_RIGHT, spaceAfter=6,
        ))
        rows = [[header, ""]]
        for acc_name, amount in accounts_dict.items():
            rows.append([
                Paragraph(ar(acc_name), styles["body"]),
                Paragraph(f"{float(amount):,.2f}", styles["body_ltr"]),
            ])
        rows.append([
            Paragraph(f"<b>{ar('الإجمالي')}</b>", styles["body"]),
            Paragraph(f"<b>{float(total):,.2f}</b>", styles["body_ltr"]),
        ])

        table = Table(rows, colWidths=[12*cm, 5*cm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("SPAN", (0, 0), (1, 0)),
            ("BACKGROUND", (0, 0), (-1, 0), color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f0f0f0")),
            ("LINEABOVE", (0, -1), (-1, -1), 1, color),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return table

    # الأصول
    elements.append(_account_table(
        balance_data.get("assets", {}), "الأصول",
        balance_data.get("total_assets", 0),
        colors.HexColor("#10b981"),
    ))
    elements.append(Spacer(1, 14))

    # الخصوم
    elements.append(_account_table(
        balance_data.get("liabilities", {}), "الخصوم",
        balance_data.get("total_liabilities", 0),
        colors.HexColor("#ef4444"),
    ))
    elements.append(Spacer(1, 14))

    # حقوق الملكية
    elements.append(_account_table(
        balance_data.get("equity", {}), "حقوق الملكية",
        balance_data.get("total_equity", 0),
        colors.HexColor("#3b82f6"),
    ))

    # فحص التوازن
    elements.append(Spacer(1, 18))
    assets = float(balance_data.get("total_assets", 0))
    liab_eq = float(balance_data.get("total_liabilities", 0)) + float(balance_data.get("total_equity", 0))
    diff = assets - liab_eq

    if abs(diff) < 0.01:
        msg = f"✅ {ar('الميزانية متوازنة')}"
        color = colors.HexColor("#10b981")
    else:
        msg = f"⚠️ {ar('الميزانية غير متوازنة')} — {ar('الفرق')}: {diff:,.2f}"
        color = colors.HexColor("#ef4444")

    balance_msg = Paragraph(msg, ParagraphStyle(
        "BalanceMsg", fontName=font, fontSize=11,
        textColor=color, alignment=TA_CENTER,
    ))
    elements.append(balance_msg)

    elements.extend(_build_footer(styles))
    _build_pdf(output_path, elements)
    return output_path


def build_profit_loss_pdf(pl_data: dict, output_path: str) -> str:
    """يبني PDF لتقرير أرباح وخسائر.

    Args:
        pl_data: dict مع revenue, cogs, gross_profit, expenses, net_profit...
    """
    styles = _get_styles()
    font = styles["font"]
    primary = styles["primary"]

    extra_info = {
        "التاريخ": datetime.now().strftime("%Y-%m-%d"),
    }
    elements = _build_header(styles, "تقرير الأرباح والخسائر", extra_info)

    def _row(label, value, bold=False, color=None, is_total=False):
        label_text = f"<b>{ar(label)}</b>" if bold else ar(label)
        value_text = f"<b>{float(value):,.2f}</b>" if bold else f"{float(value):,.2f}"
        if is_total:
            label_text = f"<b>{ar(label)}</b>"
            value_text = f"<b>{float(value):,.2f}</b>"
        return [
            Paragraph(label_text, styles["body"]),
            Paragraph(value_text, styles["body_ltr"]),
        ]

    rows = []
    rows.append(_row("الإيرادات", pl_data.get("revenue", 0), bold=True))
    rows.append(_row("تكلفة البضاعة المباعة", pl_data.get("cogs", 0)))
    rows.append(_row("الربح الإجمالي", pl_data.get("gross_profit", 0), bold=True, is_total=True))
    rows.append(_row("المصروفات التشغيلية", pl_data.get("operating_expenses", 0)))
    rows.append(_row("مصروفات الرواتب", pl_data.get("salary_expenses", 0)))
    rows.append(_row("مصروفات الإهلاك", pl_data.get("depreciation_expenses", 0)))
    rows.append(_row("إجمالي المصروفات", pl_data.get("total_expenses", 0), bold=True))
    rows.append(_row("صافي الربح/الخسارة", pl_data.get("net_profit", 0), bold=True, is_total=True))

    table = Table(rows, colWidths=[12*cm, 5*cm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#e0e0e0")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f0f9ff")),
        ("BACKGROUND", (0, 6), (-1, 6), colors.HexColor("#fef2f2")),
        ("BACKGROUND", (0, 7), (-1, 7),
         colors.HexColor("#d1fae5") if pl_data.get("net_profit", 0) > 0 else colors.HexColor("#fee2e2")),
        ("TEXTCOLOR", (0, 7), (-1, 7),
         colors.HexColor("#065f46") if pl_data.get("net_profit", 0) > 0 else colors.HexColor("#991b1b")),
    ]))
    elements.append(table)

    # هوامش
    elements.append(Spacer(1, 18))
    margin_text = f"""
    <b>{ar('هامش الربح الإجمالي')}:</b> {pl_data.get('gross_margin', 0):.1f}% &nbsp;&nbsp;
    <b>{ar('هامش الربح الصافي')}:</b> {pl_data.get('net_margin', 0):.1f}%
    """
    elements.append(Paragraph(margin_text, styles["body"]))

    elements.extend(_build_footer(styles))
    _build_pdf(output_path, elements)
    return output_path


# ==========================================================
# البناء الفعلي
# ==========================================================
def _build_pdf(output_path: str, elements: list):
    """يبني PDF من قائمة عناصر مع ترويسة/تذييل الصفحة."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    doc.build(elements)


# ==========================================================
# اختبار سريع
# ==========================================================
def test_pdf_generation() -> dict:
    """يولّد PDF تجريبي للتحقق من الإعداد."""
    result = {
        "font_found": _find_font_file() is not None,
        "font_path": _find_font_file(),
        "arabic_support": ARABIC_SUPPORT,
        "registered_font": _register_font(),
    }
    return result