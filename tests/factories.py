"""Shared test factories for Cat_Automatic_invoice.

Provides simple helper functions to create test data. Each function creates
independent data — no shared state between tests.
"""
from decimal import Decimal
from datetime import date
from django.contrib.auth import get_user_model

User = get_user_model()


def create_user(username='testuser', password='TestPass123!', email='test@example.com', **kwargs):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email, 'first_name': 'Test', 'last_name': 'User', **kwargs}
    )
    if created:
        user.set_password(password)
        user.save()
    return user


def create_user2(username='testuser2', password='TestPass456!', email='test2@example.com'):
    return create_user(username=username, password=password, email=email,
                       first_name='Second', last_name='User')


def create_customer(user, first_name='علی', last_name='محمدی', phone='09123456789', **kwargs):
    from customers.models import Customer
    return Customer.objects.create(
        user=user, first_name=first_name, last_name=last_name, phone=phone, **kwargs
    )


def create_product(user, name='لنت جلو', unit='عدد', **kwargs):
    from products.models import Product
    return Product.objects.create(user=user, name=name, unit=unit, **kwargs)


def create_bank(name='بانک ملی', code='01'):
    from banks.models import Bank
    return Bank.objects.get_or_create(name=name, defaults={'code': code})[0]


def create_bank_account(user, bank=None, card_number='6104337770012345',
                        iban='IR062960000000100324200001', account_holder='علی محمدی', **kwargs):
    from banks.models import BankAccount
    if bank is None:
        bank = create_bank()
    return BankAccount.objects.create(
        user=user, bank=bank, card_number=card_number,
        iban=iban, account_holder=account_holder, **kwargs
    )


def create_invoice(user, customer=None, items_data=None, **kwargs):
    """Create an invoice with items. Returns the saved invoice with totals calculated."""
    from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence

    if customer is None:
        customer = create_customer(user)

    invoice = Invoice.objects.create(
        user=user,
        invoice_number=InvoiceNumberSequence.get_next_number(user),
        customer=customer,
        customer_name=customer.full_name,
        customer_phone=customer.phone,
        customer_address=customer.address,
        invoice_date=kwargs.pop('invoice_date', date.today()),
        due_date=kwargs.pop('due_date', None),
        invoice_tax_rate=kwargs.pop('invoice_tax_rate', Decimal('0')),
        discount_type=kwargs.pop('discount_type', ''),
        discount_value=kwargs.pop('discount_value', Decimal('0')),
        notes=kwargs.pop('notes', ''),
        **kwargs
    )

    if items_data:
        for idx, item in enumerate(items_data):
            InvoiceItem.objects.create(
                invoice=invoice,
                product_name=item.get('product_name', 'Test Item'),
                quantity=item.get('quantity', Decimal('1')),
                unit_price=item.get('unit_price', Decimal('10000')),
                tax_rate=item.get('tax_rate', Decimal('0')),
                unit=item.get('unit', 'عدد'),
                order=idx,
            )
    invoice.calculate_totals()
    invoice.save()
    return invoice


def create_price_history(product, price):
    from products.models import PriceHistory
    return PriceHistory.objects.create(product=product, price=price)
