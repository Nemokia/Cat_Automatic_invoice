from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
from invoices.models import Invoice
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
import os
import glob
import io


def register_persian_font():
    """Register a Persian-capable font."""
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans*.ttf',
        '/usr/share/fonts/truetype/noto/NotoSans*.ttf',
        '/usr/share/fonts/truetype/liberation/Liberation*.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSans*.ttf',
    ]
    for pattern in font_paths:
        files = glob.glob(pattern)
        if files:
            try:
                pdfmetrics.registerFont(TTFont('PersianFont', files[0]))
                return 'PersianFont'
            except Exception:
                continue
    return 'Helvetica'


def generate_pdf_content(invoice):
    """Generate PDF bytes for an invoice in-memory (no request context needed).

    Returns raw PDF bytes that can be written to a file or ZIP.
    """
    buf = io.BytesIO()
    font_name = register_persian_font()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Colors
    primary = HexColor('#0B1849')
    accent = HexColor('#E4B028')
    green = HexColor('#347433')
    bg_light = HexColor('#EBEDE3')

    y = height - 30 * mm

    # Header background
    c.setFillColor(primary)
    c.rect(0, height - 35 * mm, width, 35 * mm, fill=1)

    # Title
    c.setFillColor(accent)
    c.setFont(font_name, 22)
    c.drawCentredString(width / 2, height - 20 * mm, 'INVOICE / فاکتور')

    # Invoice number
    c.setFillColor(HexColor('#FFFFFF'))
    c.setFont(font_name, 12)
    c.drawCentredString(width / 2, height - 30 * mm, invoice.invoice_number)

    y = height - 45 * mm

    # Info boxes
    c.setFillColor(bg_light)
    c.roundRect(15 * mm, y - 30 * mm, (width - 35 * mm) / 2, 28 * mm, 3, fill=1)
    c.roundRect(width / 2 + 5 * mm, y - 30 * mm, (width - 35 * mm) / 2, 28 * mm, 3, fill=1)

    c.setFillColor(primary)
    c.setFont(font_name, 10)
    # Seller info (right side for RTL)
    sx = width / 2 + 10 * mm
    c.drawString(sx, y - 8 * mm, f"Seller: {invoice.seller_business or invoice.seller_name or '-'}")
    c.drawString(sx, y - 15 * mm, f"Phone: {invoice.seller_phone or '-'}")
    c.drawString(sx, y - 22 * mm, f"Date: {invoice.invoice_date}  Time: {invoice.created_at.strftime('%H:%M')}")

    # Customer info (left side)
    cx = 20 * mm
    c.drawString(cx, y - 8 * mm, f"Customer: {invoice.customer_name or '-'}")
    c.drawString(cx, y - 15 * mm, f"Phone: {invoice.customer_phone or '-'}")
    if invoice.customer_address:
        c.drawString(cx, y - 22 * mm, f"Address: {invoice.customer_address}")

    y -= 40 * mm

    # Items table header
    c.setFillColor(green)
    c.roundRect(15 * mm, y - 10 * mm, width - 30 * mm, 10 * mm, 2, fill=1)
    c.setFillColor(HexColor('#FFFFFF'))
    c.setFont(font_name, 9)
    headers = ['#', 'Item', 'Qty', 'Price', 'Tax%', 'Total']
    x_positions = [20 * mm, 35 * mm, 85 * mm, 110 * mm, 145 * mm, 170 * mm]
    for i, h in enumerate(headers):
        c.drawString(x_positions[i], y - 8 * mm, h)

    y -= 12 * mm
    c.setFillColor(primary)
    c.setFont(font_name, 8)

    items = invoice.items.all()
    for idx, item in enumerate(items):
        if y < 60 * mm:
            c.showPage()
            y = height - 30 * mm

        c.drawString(x_positions[0], y, str(idx + 1))
        c.drawString(x_positions[1], y, item.product_name[:30])
        c.drawString(x_positions[2], y, str(item.quantity))
        c.drawString(x_positions[3], y, f"{item.unit_price:,.0f}")
        c.drawString(x_positions[4], y, f"{item.tax_rate}%" if item.tax_rate else "-")
        c.drawString(x_positions[5], y, f"{item.total_price:,.0f}")
        y -= 7 * mm

    y -= 5 * mm

    # Totals
    c.setStrokeColor(accent)
    c.setLineWidth(1)
    c.line(100 * mm, y, width - 15 * mm, y)
    y -= 8 * mm

    totals = [
        ('Subtotal:', f"{invoice.subtotal:,.0f}"),
        ('Item Taxes:', f"{invoice.item_taxes_total:,.0f}"),
    ]
    if invoice.invoice_tax_rate > 0:
        totals.append(('Invoice Tax:', f"{invoice.invoice_tax_amount:,.0f}"))
    if invoice.discount_amount > 0:
        discount_label = 'Discount:'
        if invoice.discount_type == 'percent':
            discount_label = f"Discount ({invoice.discount_value}%):"
        totals.append((discount_label, f"-{invoice.discount_amount:,.0f}"))

    for label, value in totals:
        c.drawString(120 * mm, y, label)
        c.drawString(width - 20 * mm, y, value)
        y -= 6 * mm

    # Final amount highlight
    y -= 3 * mm
    c.setFillColor(accent)
    c.roundRect(100 * mm, y - 8 * mm, width - 115 * mm, 12 * mm, 3, fill=1)
    c.setFillColor(primary)
    c.setFont(font_name, 12)
    c.drawString(105 * mm, y - 4 * mm, 'TOTAL:')
    c.drawString(width - 50 * mm, y - 4 * mm, f"{invoice.final_amount:,.0f}")

    y -= 25 * mm

    # Bank info
    if invoice.card_number or invoice.iban:
        c.setFillColor(bg_light)
        c.roundRect(15 * mm, y - 20 * mm, width - 30 * mm, 22 * mm, 3, fill=1)
        c.setFillColor(primary)
        c.setFont(font_name, 9)
        c.drawString(20 * mm, y - 8 * mm, f"Bank: {invoice.bank_name or '-'}")
        c.drawString(20 * mm, y - 15 * mm, f"Card: {invoice.card_number or '-'}")
        c.drawString(width / 2, y - 8 * mm, f"IBAN: {invoice.iban or '-'}")
        y -= 28 * mm

    # Notes
    if invoice.notes:
        c.setFillColor(primary)
        c.setFont(font_name, 8)
        c.drawString(20 * mm, y - 5 * mm, f"Notes: {invoice.notes[:100]}")
        y -= 12 * mm

    # Footer
    c.setFillColor(primary)
    c.setFont(font_name, 7)
    c.drawCentredString(width / 2, 15 * mm, 'Generated by Cat_Automatic_invoice')

    c.save()
    return buf.getvalue()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_pdf(request, invoice_id):
    """Generate PDF for an invoice."""
    try:
        invoice = Invoice.objects.get(id=invoice_id, user=request.user)
    except Invoice.DoesNotExist:
        return Response({'detail': 'فاکتور یافت نشد'}, status=404)

    pdf_bytes = generate_pdf_content(invoice)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_number}.pdf"'
    return response
