"""Tests for all financial calculation logic in Invoice and InvoiceItem.

Covers: subtotal, item tax, multiple item tax, invoice tax, percentage discount,
amount discount, final amount formula, decimal precision, boundary values,
discount edge cases, and negative floor.
"""
from decimal import Decimal
from rest_framework.test import APITestCase, APIClient
from tests.factories import create_user, create_product, create_customer


class TestSubtotal(APITestCase):
    """Subtotal = sum of all item.total_price."""

    def setUp(self):
        self.user = create_user()
        self.product = create_product(self.user)

    def test_two_items_subtotal(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        customer = create_customer(self.user)
        invoice = Invoice.objects.create(
            user=self.user,
            invoice_number=InvoiceNumberSequence.get_next_number(self.user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
        )
        # Item 1: 2 * 100000 = 200000
        InvoiceItem.objects.create(
            invoice=invoice, product_name='A', quantity=Decimal('2'),
            unit_price=Decimal('100000'), tax_rate=Decimal('0'),
            total_price=Decimal('200000'), tax_amount=Decimal('0'),
            unit='عدد', order=0,
        )
        # Item 2: 3 * 200000 = 600000
        InvoiceItem.objects.create(
            invoice=invoice, product_name='B', quantity=Decimal('3'),
            unit_price=Decimal('200000'), tax_rate=Decimal('0'),
            total_price=Decimal('600000'), tax_amount=Decimal('0'),
            unit='عدد', order=1,
        )
        invoice.calculate_totals()
        self.assertEqual(invoice.subtotal, Decimal('800000'))


class TestItemTax(APITestCase):
    """Item tax: qty=2, price=100000, tax=10% → total_price=200000, tax_amount=20000."""

    def test_single_item_tax(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
        )
        item = InvoiceItem.objects.create(
            invoice=invoice, product_name='Item', quantity=Decimal('2'),
            unit_price=Decimal('100000'), tax_rate=Decimal('10.00'),
            total_price=Decimal('0'), tax_amount=Decimal('0'),
            unit='عدد', order=0,
        )
        # InvoiceItem.save() calculates total_price and tax_amount
        item.refresh_from_db()
        self.assertEqual(item.total_price, Decimal('200000'))
        self.assertEqual(item.tax_amount, Decimal('20000'))


class TestMultipleItemTax(APITestCase):
    """Items with different tax rates each calculated correctly."""

    def test_three_items_different_tax_rates(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
        )
        # Item A: 10% tax, qty=1, price=100000 → tax=10000
        item_a = InvoiceItem.objects.create(
            invoice=invoice, product_name='A', quantity=Decimal('1'),
            unit_price=Decimal('100000'), tax_rate=Decimal('10.00'),
            total_price=Decimal('0'), tax_amount=Decimal('0'),
            unit='عدد', order=0,
        )
        item_a.refresh_from_db()
        self.assertEqual(item_a.tax_amount, Decimal('10000'))

        # Item B: 5% tax, qty=1, price=100000 → tax=5000
        item_b = InvoiceItem.objects.create(
            invoice=invoice, product_name='B', quantity=Decimal('1'),
            unit_price=Decimal('100000'), tax_rate=Decimal('5.00'),
            total_price=Decimal('0'), tax_amount=Decimal('0'),
            unit='عدد', order=1,
        )
        item_b.refresh_from_db()
        self.assertEqual(item_b.tax_amount, Decimal('5000'))

        # Item C: 0% tax → tax=0
        item_c = InvoiceItem.objects.create(
            invoice=invoice, product_name='C', quantity=Decimal('1'),
            unit_price=Decimal('100000'), tax_rate=Decimal('0'),
            total_price=Decimal('0'), tax_amount=Decimal('0'),
            unit='عدد', order=2,
        )
        item_c.refresh_from_db()
        self.assertEqual(item_c.tax_amount, Decimal('0'))

        # Verify invoice totals
        invoice.calculate_totals()
        self.assertEqual(invoice.item_taxes_total, Decimal('15000'))


class TestInvoiceTax(APITestCase):
    """Invoice-level tax: subtotal=1000000, rate=10% → tax=100000."""

    def test_invoice_level_tax(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
            invoice_tax_rate=Decimal('10.00'),
        )
        InvoiceItem.objects.create(
            invoice=invoice, product_name='Item', quantity=Decimal('1'),
            unit_price=Decimal('1000000'), tax_rate=Decimal('0'),
            total_price=Decimal('1000000'), tax_amount=Decimal('0'),
            unit='عدد', order=0,
        )
        invoice.calculate_totals()
        self.assertEqual(invoice.subtotal, Decimal('1000000'))
        self.assertEqual(invoice.invoice_tax_amount, Decimal('100000'))


class TestPercentageDiscount(APITestCase):
    """Percent discount: subtotal=1000000, 10% → discount_amount=100000."""

    def test_percent_discount(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
            discount_type='percent',
            discount_value=Decimal('10'),
        )
        InvoiceItem.objects.create(
            invoice=invoice, product_name='Item', quantity=Decimal('1'),
            unit_price=Decimal('1000000'), tax_rate=Decimal('0'),
            total_price=Decimal('1000000'), tax_amount=Decimal('0'),
            unit='عدد', order=0,
        )
        invoice.calculate_totals()
        self.assertEqual(invoice.discount_amount, Decimal('100000'))


class TestAmountDiscount(APITestCase):
    """Amount discount: subtotal=1000000, discount_value=100000 → discount_amount=100000."""

    def test_amount_discount(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
            discount_type='amount',
            discount_value=Decimal('100000'),
        )
        InvoiceItem.objects.create(
            invoice=invoice, product_name='Item', quantity=Decimal('1'),
            unit_price=Decimal('1000000'), tax_rate=Decimal('0'),
            total_price=Decimal('1000000'), tax_amount=Decimal('0'),
            unit='عدد', order=0,
        )
        invoice.calculate_totals()
        self.assertEqual(invoice.discount_amount, Decimal('100000'))


class TestFinalAmount(APITestCase):
    """Full formula: subtotal + item_taxes + invoice_tax - discount = final_amount."""

    def test_full_formula(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
            invoice_tax_rate=Decimal('10.00'),
            discount_type='percent',
            discount_value=Decimal('10'),
        )
        # 2 items: each qty=1, price=500000, tax=10%
        # Each item: total=500000, tax=50000
        # Subtotal = 1000000
        # Item taxes total = 100000
        # Invoice tax = 1000000 * 10% = 100000
        # Discount = 1000000 * 10% = 100000
        # Final = 1000000 + 100000 + 100000 - 100000 = 1100000
        for i in range(2):
            InvoiceItem.objects.create(
                invoice=invoice, product_name=f'Item {i}',
                quantity=Decimal('1'), unit_price=Decimal('500000'),
                tax_rate=Decimal('10.00'),
                total_price=Decimal('0'), tax_amount=Decimal('0'),
                unit='عدد', order=i,
            )
        invoice.calculate_totals()
        self.assertEqual(invoice.subtotal, Decimal('1000000'))
        self.assertEqual(invoice.item_taxes_total, Decimal('100000'))
        self.assertEqual(invoice.invoice_tax_amount, Decimal('100000'))
        self.assertEqual(invoice.discount_amount, Decimal('100000'))
        self.assertEqual(invoice.final_amount, Decimal('1100000'))


class TestDecimalPrecision(APITestCase):
    """Decimal values that cause floating point errors produce exact results."""

    def test_decimal_precision_basic(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
            invoice_tax_rate=Decimal('7'),
        )
        # Use values that would cause 0.1+0.2 != 0.3 in float
        # 3 items: qty=3, price=33333
        # Each item: total = 3 * 33333 = 99999, tax = 99999 * 7% = 6999.93 → quantized to 7000
        InvoiceItem.objects.create(
            invoice=invoice, product_name='Precise', quantity=Decimal('3'),
            unit_price=Decimal('33333'), tax_rate=Decimal('7.00'),
            total_price=Decimal('0'), tax_amount=Decimal('0'),
            unit='عدد', order=0,
        )
        invoice.calculate_totals()
        self.assertEqual(invoice.subtotal, Decimal('99999'))
        self.assertEqual(invoice.item_taxes_total, Decimal('7000'))
        # Invoice tax: 99999 * 7 / 100 = 6999.93 → quantized to 7000
        self.assertEqual(invoice.invoice_tax_amount, Decimal('7000'))

    def test_decimal_1_over_3(self):
        """3 items at 1/3 each = whole number."""
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
        )
        # 3 items each qty=1, price=33333 → subtotal=99999
        for i in range(3):
            InvoiceItem.objects.create(
                invoice=invoice, product_name=f'P{i}',
                quantity=Decimal('1'), unit_price=Decimal('33333'),
                tax_rate=Decimal('0'),
                total_price=Decimal('0'), tax_amount=Decimal('0'),
                unit='عدد', order=i,
            )
        invoice.calculate_totals()
        self.assertEqual(invoice.subtotal, Decimal('99999'))


class TestBoundaryValues(APITestCase):
    """Boundary values: qty=1/price=1, very large amounts, qty=0.01."""

    def test_minimal_amount(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
        )
        item = InvoiceItem.objects.create(
            invoice=invoice, product_name='Min', quantity=Decimal('1'),
            unit_price=Decimal('1'), tax_rate=Decimal('0'),
            total_price=Decimal('0'), tax_amount=Decimal('0'),
            unit='عدد', order=0,
        )
        item.refresh_from_db()
        self.assertEqual(item.total_price, Decimal('1'))
        invoice.calculate_totals()
        self.assertEqual(invoice.subtotal, Decimal('1'))
        self.assertEqual(invoice.final_amount, Decimal('1'))

    def test_very_large_amounts(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
        )
        item = InvoiceItem.objects.create(
            invoice=invoice, product_name='Large', quantity=Decimal('1'),
            unit_price=Decimal('1000000000000'),  # 10^12
            tax_rate=Decimal('0'),
            total_price=Decimal('0'), tax_amount=Decimal('0'),
            unit='عدد', order=0,
        )
        item.refresh_from_db()
        self.assertEqual(item.total_price, Decimal('1000000000000'))
        invoice.calculate_totals()
        self.assertEqual(invoice.subtotal, Decimal('1000000000000'))
        self.assertEqual(invoice.final_amount, Decimal('1000000000000'))

    def test_fractional_quantity(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
        )
        item = InvoiceItem.objects.create(
            invoice=invoice, product_name='Frac', quantity=Decimal('0.01'),
            unit_price=Decimal('100000'), tax_rate=Decimal('0'),
            total_price=Decimal('0'), tax_amount=Decimal('0'),
            unit='kg', order=0,
        )
        item.refresh_from_db()
        # 0.01 * 100000 = 1000 (Decimal precision)
        self.assertEqual(item.total_price, Decimal('1000'))


class TestDiscountEdgeCases(APITestCase):
    """Discount: 0%, 50%, 99.99%, 100%, >100%, amount=0, amount=subtotal, amount>subtotal."""

    def _make_invoice(self, discount_type, discount_value):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
            discount_type=discount_type,
            discount_value=discount_value,
        )
        InvoiceItem.objects.create(
            invoice=invoice, product_name='Item', quantity=Decimal('1'),
            unit_price=Decimal('1000000'), tax_rate=Decimal('0'),
            total_price=Decimal('1000000'), tax_amount=Decimal('0'),
            unit='عدد', order=0,
        )
        invoice.calculate_totals()
        return invoice

    def test_zero_percent_discount(self):
        inv = self._make_invoice('percent', Decimal('0'))
        self.assertEqual(inv.discount_amount, Decimal('0'))
        # No discount_type, no discount_value → discount_amount stays 0
        self.assertEqual(inv.final_amount, Decimal('1000000'))

    def test_fifty_percent_discount(self):
        inv = self._make_invoice('percent', Decimal('50'))
        self.assertEqual(inv.discount_amount, Decimal('500000'))
        self.assertEqual(inv.final_amount, Decimal('500000'))

    def test_ninety_nine_point_nine_nine_percent_discount(self):
        inv = self._make_invoice('percent', Decimal('99.99'))
        # 1000000 * 99.99 / 100 = 999900
        self.assertEqual(inv.discount_amount, Decimal('999900'))
        self.assertEqual(inv.final_amount, Decimal('100'))

    def test_hundred_percent_discount(self):
        inv = self._make_invoice('percent', Decimal('100'))
        self.assertEqual(inv.discount_amount, Decimal('1000000'))
        self.assertEqual(inv.final_amount, Decimal('0'))

    def test_over_hundred_percent_discount(self):
        inv = self._make_invoice('percent', Decimal('150'))
        # 1000000 * 150 / 100 = 1500000, final = 1000000 - 1500000 = -500000 → floored to 0
        self.assertEqual(inv.final_amount, Decimal('0'))

    def test_amount_discount_zero(self):
        inv = self._make_invoice('amount', Decimal('0'))
        self.assertEqual(inv.discount_amount, Decimal('0'))
        self.assertEqual(inv.final_amount, Decimal('1000000'))

    def test_amount_discount_equals_subtotal(self):
        inv = self._make_invoice('amount', Decimal('1000000'))
        self.assertEqual(inv.discount_amount, Decimal('1000000'))
        self.assertEqual(inv.final_amount, Decimal('0'))

    def test_amount_discount_exceeds_subtotal(self):
        inv = self._make_invoice('amount', Decimal('2000000'))
        self.assertEqual(inv.discount_amount, Decimal('2000000'))
        self.assertEqual(inv.final_amount, Decimal('0'))


class TestNegativeFloor(APITestCase):
    """final_amount never goes below 0."""

    def test_large_discount_floors_to_zero(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
            invoice_tax_rate=Decimal('0'),
            discount_type='amount',
            discount_value=Decimal('5000000'),
        )
        InvoiceItem.objects.create(
            invoice=invoice, product_name='Item', quantity=Decimal('1'),
            unit_price=Decimal('100000'), tax_rate=Decimal('0'),
            total_price=Decimal('100000'), tax_amount=Decimal('0'),
            unit='عدد', order=0,
        )
        invoice.calculate_totals()
        # subtotal=100000, discount=5000000 → raw=-4900000 → floor=0
        self.assertEqual(invoice.final_amount, Decimal('0'))
        self.assertGreaterEqual(invoice.final_amount, Decimal('0'))

    def test_exact_subtotal_discount_floors_to_zero(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
            discount_type='amount',
            discount_value=Decimal('100000'),
        )
        InvoiceItem.objects.create(
            invoice=invoice, product_name='Item', quantity=Decimal('1'),
            unit_price=Decimal('100000'), tax_rate=Decimal('0'),
            total_price=Decimal('100000'), tax_amount=Decimal('0'),
            unit='عدد', order=0,
        )
        invoice.calculate_totals()
        self.assertEqual(invoice.final_amount, Decimal('0'))

    def test_no_discount_positive_final(self):
        from invoices.models import Invoice, InvoiceItem, InvoiceNumberSequence
        user = create_user()
        customer = create_customer(user)
        invoice = Invoice.objects.create(
            user=user,
            invoice_number=InvoiceNumberSequence.get_next_number(user),
            customer=customer,
            customer_name=customer.full_name,
            customer_phone=customer.phone,
            invoice_date='2026-01-01',
        )
        InvoiceItem.objects.create(
            invoice=invoice, product_name='Item', quantity=Decimal('1'),
            unit_price=Decimal('100000'), tax_rate=Decimal('0'),
            total_price=Decimal('100000'), tax_amount=Decimal('0'),
            unit='عدد', order=0,
        )
        invoice.calculate_totals()
        self.assertEqual(invoice.final_amount, Decimal('100000'))
        self.assertGreaterEqual(invoice.final_amount, Decimal('0'))
