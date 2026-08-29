from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
from invoices.models import Invoice, InvoiceItem
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_excel(request):
    """Export invoices to Excel."""
    user = request.user
    report_type = request.query_params.get('type', 'invoices')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    customer_id = request.query_params.get('customer_id')

    invoices = Invoice.objects.filter(user=user)
    if date_from:
        invoices = invoices.filter(invoice_date__gte=date_from)
    if date_to:
        invoices = invoices.filter(invoice_date__lte=date_to)
    if customer_id:
        invoices = invoices.filter(customer_id=customer_id)

    wb = Workbook()

    # Styles
    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='0B1849', end_color='0B1849', fill_type='solid')
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin'),
    )

    if report_type == 'invoices':
        ws = wb.active
        ws.title = 'Invoices'
        headers = ['شماره فاکتور', 'مشتری', 'تلفن', 'تاریخ', 'جمع', 'مالیات', 'تخفیف', 'نهایی', 'وضعیت']
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border

        for row, inv in enumerate(invoices, 2):
            data = [
                inv.invoice_number, inv.customer_name, inv.customer_phone,
                str(inv.invoice_date), float(inv.subtotal), float(inv.item_taxes_total),
                float(inv.discount_amount), float(inv.final_amount),
                'پرداخت شده' if inv.is_paid else 'پرداخت نشده'
            ]
            for col, val in enumerate(data, 1):
                cell = ws.cell(row=row, column=col, value=val)
                cell.border = border

        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 18

    elif report_type == 'items':
        ws = wb.active
        ws.title = 'Invoice Items'
        headers = ['شماره فاکتور', 'نام کالا', 'تعداد', 'قیمت واحد', 'مالیات', 'مبلغ کل']
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border

        row = 2
        for inv in invoices:
            for item in inv.items.all():
                data = [
                    inv.invoice_number, item.product_name, float(item.quantity),
                    float(item.unit_price), float(item.tax_amount), float(item.total_price)
                ]
                for col, val in enumerate(data, 1):
                    cell = ws.cell(row=row, column=col, value=val)
                    cell.border = border
                row += 1

        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 18

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="cat_invoice_export.xlsx"'
    wb.save(response)
    return response
