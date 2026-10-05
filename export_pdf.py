# export_pdf.py
"""
تصدير الفواتير إلى PDF
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from database import SessionLocal
import models
from datetime import datetime

try:
    pdfmetrics.registerFont(TTFont('Arabic', 'arial.ttf'))
    ARABIC_FONT = 'Arabic'
except:
    ARABIC_FONT = 'Helvetica'

def export_invoice_to_pdf(invoice_id: int, output_path: str = None):
    """
    تصدير فاتورة إلى PDF
    """
    db = SessionLocal()
    
    try:
        invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("الفاتورة غير موجودة!")
        
        party = db.query(models.Party).filter(models.Party.id == invoice.party_id).first()
        currency = db.query(models.Currency).filter(models.Currency.id == invoice.currency_id).first()
        currency_symbol = currency.symbol if currency else "ج.م"
        
        if not output_path:
            output_path = f"Invoice_{invoice.invoice_number}.pdf"
        
        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
        
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        elements.append(Paragraph("Techtoon Accounting", title_style))
        elements.append(Paragraph("فاتورة مبيعات" if invoice.type == 'sale' else "فاتورة مشتريات", title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        info_data = [
            ['رقم الفاتورة:', invoice.invoice_number],
            ['التاريخ:', invoice.date.strftime("%Y-%m-%d") if invoice.date else "-"],
            ['العميل/المورد:', party.name if party else "غير محدد"],
            ['الهاتف:', party.phone if party else "-"],
            ['العنوان:', party.address if party else "-"]
        ]
        
        info_table = Table(info_data, colWidths=[3*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        items_data = [['الصنف', 'الكمية', 'سعر الوحدة', 'الإجمالي']]
        
        invoice_lines = db.query(models.InvoiceLine).filter(models.InvoiceLine.invoice_id == invoice.id).all()
        for line in invoice_lines:
            item = db.query(models.Item).filter(models.Item.id == line.item_id).first()
            items_data.append([
                item.name if item else "غير محدد",
                str(line.quantity),
                f"{line.price:,.2f} {currency_symbol}",
                f"{line.total:,.2f} {currency_symbol}"
            ])
        
        items_data.append(['', '', 'الإجمالي الكلي:', f"{invoice.total_amount:,.2f} {currency_symbol}"])
        
        items_table = Table(items_data, colWidths=[3*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        items_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), ARABIC_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
            ('FONTNAME', (0, -1), (-1, -1), ARABIC_FONT),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('FONTWEIGHT', (0, -1), (-1, -1), 'bold'),
        ]))
        
        elements.append(items_table)
        elements.append(Spacer(1, 0.5*inch))
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        
        elements.append(Paragraph("شكراً لتعاملكم معنا", footer_style))
        elements.append(Paragraph("Techtoon Accounting System", footer_style))
        
        doc.build(elements)
        print(f"✅ تم تصدير الفاتورة إلى: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        raise
    finally:
        db.close()