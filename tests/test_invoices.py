"""Tests for invoice API: creation, validation, CRUD, duplicate, numbering,
search, date filtering, and data persistence/snapshot behavior."""
from decimal import Decimal
from datetime import date, timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from tests.factories import (
    create_user, create_user2, create_customer,
    create_product, create_bank, create_bank_account, create_invoice,
)


class TestInvoiceCreate(APITestCase):
    """Creating invoices with 1, 5, and 10 items; verify totals."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)

    def _make_items(self, count):
        return [
            {
                'product_name': f'Item {i}',
                'quantity': str(Decimal('2')),
                'unit_price': str(Decimal('100000')),
                'tax_rate': '0',
                'unit': 'عدد',
            }
            for i in range(count)
        ]

    def _create_and_get(self, items):
        resp = self.client.post('/api/invoices/', {
            'customer': self.customer.id,
            'invoice_date': '2026-01-01',
            'items': items,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']
        detail = self.client.get(f'/api/invoices/{inv_id}/', format='json')
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        return detail.data

    def test_create_with_one_item(self):
        data = self._create_and_get(self._make_items(1))
        self.assertEqual(Decimal(data['subtotal']), Decimal('200000'))
        self.assertEqual(Decimal(data['final_amount']), Decimal('200000'))

    def test_create_with_five_items(self):
        data = self._create_and_get(self._make_items(5))
        self.assertEqual(Decimal(data['subtotal']), Decimal('1000000'))
        self.assertEqual(len(data['items']), 5)

    def test_create_with_ten_items(self):
        data = self._create_and_get(self._make_items(10))
        self.assertEqual(Decimal(data['subtotal']), Decimal('2000000'))
        self.assertEqual(len(data['items']), 10)

    def test_invoice_number_auto_generated(self):
        data = self._create_and_get(self._make_items(1))
        self.assertIn('INV-', data['invoice_number'])


class TestInvoiceCreateValidation(APITestCase):
    """Invalid data returns 400."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)

    def test_negative_quantity(self):
        response = self.client.post('/api/invoices/', {
            'customer': self.customer.id,
            'invoice_date': '2026-01-01',
            'items': [{
                'product_name': 'Bad',
                'quantity': '-1',
                'unit_price': '100000',
                'tax_rate': '0',
                'unit': 'عدد',
            }],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zero_quantity(self):
        response = self.client.post('/api/invoices/', {
            'customer': self.customer.id,
            'invoice_date': '2026-01-01',
            'items': [{
                'product_name': 'Bad',
                'quantity': '0',
                'unit_price': '100000',
                'tax_rate': '0',
                'unit': 'عدد',
            }],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_price(self):
        response = self.client.post('/api/invoices/', {
            'customer': self.customer.id,
            'invoice_date': '2026-01-01',
            'items': [{
                'product_name': 'Bad',
                'quantity': '1',
                'unit_price': '-100000',
                'tax_rate': '0',
                'unit': 'عدد',
            }],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zero_price(self):
        response = self.client.post('/api/invoices/', {
            'customer': self.customer.id,
            'invoice_date': '2026-01-01',
            'items': [{
                'product_name': 'Bad',
                'quantity': '1',
                'unit_price': '0',
                'tax_rate': '0',
                'unit': 'عدد',
            }],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_items_array(self):
        response = self.client.post('/api/invoices/', {
            'customer': self.customer.id,
            'invoice_date': '2026-01-01',
            'items': [],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_items_field(self):
        response = self.client.post('/api/invoices/', {
            'customer': self.customer.id,
            'invoice_date': '2026-01-01',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestInvoiceCRUD(APITestCase):
    """Create, list, retrieve, update, delete."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)

    def _create_invoice(self):
        response = self.client.post('/api/invoices/', {
            'customer': self.customer.id,
            'invoice_date': '2026-01-01',
            'items': [{
                'product_name': 'Item',
                'quantity': '1',
                'unit_price': '100000',
                'tax_rate': '0',
                'unit': 'عدد',
            }],
        }, format='json')
        return response.data['id']

    def test_create_and_list(self):
        inv_id = self._create_invoice()
        response = self.client.get('/api/invoices/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['id'], inv_id)

    def test_retrieve(self):
        inv_id = self._create_invoice()
        response = self.client.get(f'/api/invoices/{inv_id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], inv_id)

    def test_update_notes(self):
        inv_id = self._create_invoice()
        response = self.client.patch(f'/api/invoices/{inv_id}/', {
            'notes': 'یادداشت جدید',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['notes'], 'یادداشت جدید')

    def test_update_invoice_fields_via_detail(self):
        """Retrieve with full data, then verify detail serializer returns all fields."""
        inv_id = self._create_invoice()
        response = self.client.get(f'/api/invoices/{inv_id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['subtotal']), Decimal('100000'))
        self.assertEqual(Decimal(response.data['discount_amount']), Decimal('0'))

    def test_delete(self):
        inv_id = self._create_invoice()
        response = self.client.delete(f'/api/invoices/{inv_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(f'/api/invoices/{inv_id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestInvoiceDuplicate(APITestCase):
    """Duplicating an invoice creates a new one with a new number but same data."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)

    def test_duplicate_creates_new_invoice(self):
        create_resp = self.client.post('/api/invoices/', {
            'customer': self.customer.id,
            'invoice_date': '2026-01-01',
            'items': [{
                'product_name': 'Item A',
                'quantity': '2',
                'unit_price': '100000',
                'tax_rate': '10',
                'unit': 'عدد',
            }],
        }, format='json')
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        original_id = create_resp.data['id']

        # GET original to get full data
        original = self.client.get(f'/api/invoices/{original_id}/', format='json').data
        original_number = original['invoice_number']

        # Duplicate
        dup_resp = self.client.post(f'/api/invoices/{original_id}/duplicate/', format='json')
        self.assertEqual(dup_resp.status_code, status.HTTP_201_CREATED)
        dup = dup_resp.data

        self.assertNotEqual(dup['invoice_number'], original_number)
        self.assertIn('INV-', dup['invoice_number'])
        self.assertEqual(Decimal(dup['subtotal']), Decimal(original['subtotal']))
        self.assertEqual(Decimal(dup['final_amount']), Decimal(original['final_amount']))
        self.assertEqual(len(dup['items']), 1)
        self.assertEqual(dup['items'][0]['product_name'], 'Item A')

    def test_duplicate_different_customer_snapshot(self):
        """Duplicate preserves customer snapshot from original."""
        create_resp = self.client.post('/api/invoices/', {
            'customer': self.customer.id,
            'invoice_date': '2026-03-15',
            'items': [{
                'product_name': 'Widget',
                'quantity': '1',
                'unit_price': '50000',
                'tax_rate': '0',
                'unit': 'عدد',
            }],
        }, format='json')
        original_id = create_resp.data['id']
        original = self.client.get(f'/api/invoices/{original_id}/', format='json').data

        dup_resp = self.client.post(f'/api/invoices/{original_id}/duplicate/', format='json')
        self.assertEqual(dup_resp.data['customer_name'], original['customer_name'])
        self.assertEqual(dup_resp.data['customer_phone'], original['customer_phone'])


class TestInvoiceNumber(APITestCase):
    """Creating 25 invoices all get unique sequential numbers."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)

    def test_25_unique_numbers(self):
        numbers = set()
        for i in range(25):
            resp = self.client.post('/api/invoices/', {
                'customer': self.customer.id,
                'invoice_date': '2026-01-01',
                'items': [{
                    'product_name': f'Item {i}',
                    'quantity': '1',
                    'unit_price': '10000',
                    'tax_rate': '0',
                    'unit': 'عدد',
                }],
            }, format='json')
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
            inv_id = resp.data['id']
            detail = self.client.get(f'/api/invoices/{inv_id}/', format='json')
            inv_num = detail.data['invoice_number']
            self.assertIn('INV-', inv_num)
            self.assertNotIn(inv_num, numbers)
            numbers.add(inv_num)
        self.assertEqual(len(numbers), 25)


class TestInvoiceSearch(APITestCase):
    """Search by invoice_number, customer_name, customer_phone, product_name."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(
            self.user, first_name='علی', last_name='محمدی', phone='09121234567',
        )
        self.invoice = create_invoice(
            self.user, customer=self.customer,
            items_data=[{
                'product_name': 'لنت جلو', 'quantity': Decimal('1'),
                'unit_price': Decimal('100000'), 'tax_rate': Decimal('0'), 'unit': 'عدد',
            }],
        )

    def test_search_by_invoice_number(self):
        response = self.client.get(
            f'/api/invoices/?search={self.invoice.invoice_number}', format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_by_customer_name(self):
        response = self.client.get('/api/invoices/?search=علی', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_by_customer_phone(self):
        response = self.client.get('/api/invoices/?search=09121234567', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_by_product_name(self):
        response = self.client.get('/api/invoices/?search=لنت', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_no_match(self):
        response = self.client.get('/api/invoices/?search=ZZZZZ', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)


class TestInvoiceDateFilter(APITestCase):
    """Filter invoices by date_from and date_to."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)

    def test_date_from(self):
        create_invoice(self.user, customer=self.customer, invoice_date=date(2026, 1, 15))
        create_invoice(self.user, customer=self.customer, invoice_date=date(2026, 6, 15))
        response = self.client.get('/api/invoices/?date_from=2026-03-01', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_date_to(self):
        create_invoice(self.user, customer=self.customer, invoice_date=date(2026, 1, 15))
        create_invoice(self.user, customer=self.customer, invoice_date=date(2026, 6, 15))
        response = self.client.get('/api/invoices/?date_to=2026-03-01', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_date_range(self):
        create_invoice(self.user, customer=self.customer, invoice_date=date(2026, 1, 1))
        create_invoice(self.user, customer=self.customer, invoice_date=date(2026, 3, 15))
        create_invoice(self.user, customer=self.customer, invoice_date=date(2026, 12, 31))
        response = self.client.get(
            '/api/invoices/?date_from=2026-02-01&date_to=2026-06-01', format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class TestInvoicePersistence(APITestCase):
    """After creation, changing customer name doesn't affect the invoice snapshot."""

    def test_snapshot_persists_after_customer_change(self):
        user = create_user()
        client = APIClient()
        client.force_authenticate(user=user)

        customer = create_customer(user, first_name='علی', last_name='محمدی')
        invoice = create_invoice(
            user, customer=customer,
            items_data=[{
                'product_name': 'Item', 'quantity': Decimal('1'),
                'unit_price': Decimal('100000'), 'tax_rate': Decimal('0'), 'unit': 'عدد',
            }],
        )
        original_name = invoice.customer_name
        original_phone = invoice.customer_phone

        # Modify customer directly
        customer.first_name = 'محمد'
        customer.save()

        # Reload invoice
        invoice.refresh_from_db()
        self.assertEqual(invoice.customer_name, original_name)
        self.assertEqual(invoice.customer_phone, original_phone)
        self.assertEqual(invoice.customer_name, 'علی محمدی')


class TestInvoiceSnapshot(APITestCase):
    """All snapshot fields (customer, seller, bank) are preserved after source changes."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(
            self.user, first_name='علی', last_name='محمدی', phone='09121234567',
        )
        self.bank = create_bank()
        self.bank_account = create_bank_account(
            self.user, bank=self.bank,
            card_number='6104337770012345',
            iban='IR062960000000100324200001',
            account_holder='علی محمدی',
        )

    def test_customer_snapshot_preserved(self):
        invoice = create_invoice(
            self.user, customer=self.customer,
            items_data=[{
                'product_name': 'Item', 'quantity': Decimal('1'),
                'unit_price': Decimal('100000'), 'tax_rate': Decimal('0'), 'unit': 'عدد',
            }],
        )
        original_name = invoice.customer_name
        original_phone = invoice.customer_phone

        self.customer.first_name = 'محمد'
        self.customer.phone = '09999999999'
        self.customer.save()

        invoice.refresh_from_db()
        self.assertEqual(invoice.customer_name, original_name)
        self.assertEqual(invoice.customer_phone, original_phone)

    def test_bank_snapshot_preserved(self):
        """Bank snapshot on invoice preserved after bank account changes."""
        resp = self.client.post('/api/invoices/', {
            'customer': self.customer.id,
            'invoice_date': '2026-01-01',
            'bank_account': self.bank_account.id,
            'items': [{
                'product_name': 'Item', 'quantity': '1',
                'unit_price': '100000', 'tax_rate': '0', 'unit': 'عدد',
            }],
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']

        # GET full details
        detail = self.client.get(f'/api/invoices/{inv_id}/', format='json').data
        self.assertEqual(detail['bank_name'], self.bank.name)
        self.assertEqual(detail['card_number'], '6104337770012345')
        self.assertEqual(detail['iban'], 'IR062960000000100324200001')
        self.assertEqual(detail['account_holder'], 'علی محمدی')

        # Change bank account
        self.bank_account.card_number = '9999999999999999'
        self.bank_account.iban = 'IR000000000000000000000000'
        self.bank_account.save()

        # Invoice snapshot should still have old values
        detail = self.client.get(f'/api/invoices/{inv_id}/', format='json').data
        self.assertEqual(detail['card_number'], '6104337770012345')
        self.assertEqual(detail['iban'], 'IR062960000000100324200001')

    def test_seller_snapshot_preserved(self):
        """Seller snapshot fields preserved after profile changes."""
        from accounts.models import SellerProfile
        profile = SellerProfile.objects.create(
            user=self.user, business_name='فروشگاه تست',
            address='تهران', phone='02112345678',
        )
        resp = self.client.post('/api/invoices/', {
            'customer': self.customer.id,
            'invoice_date': '2026-01-01',
            'items': [{
                'product_name': 'Item', 'quantity': '1',
                'unit_price': '100000', 'tax_rate': '0', 'unit': 'عدد',
            }],
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']

        detail = self.client.get(f'/api/invoices/{inv_id}/', format='json').data
        self.assertEqual(detail['seller_name'], 'Test User')
        self.assertEqual(detail['seller_business'], 'فروشگاه تست')

        # Change profile
        profile.business_name = 'فروشگاه جدید'
        profile.save()

        # Invoice snapshot unchanged
        detail = self.client.get(f'/api/invoices/{inv_id}/', format='json').data
        self.assertEqual(detail['seller_business'], 'فروشگاه تست')
