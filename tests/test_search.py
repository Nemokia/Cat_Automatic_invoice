"""
Tests for search, filtering, and autocomplete endpoints.

Invoice search: /api/invoices/?search=...
Invoice filters: date_from, date_to, customer_id
Product autocomplete: /api/products/autocomplete/?q=...
Customer autocomplete: /api/customers/autocomplete/?q=...
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from tests.factories import (
    create_user, create_user2, create_customer, create_product,
    create_bank, create_bank_account, create_invoice, create_price_history,
)


class TestInvoiceSearch(TestCase):
    """Search invoices by invoice_number, customer_name, customer_phone, product_name, bank_name."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)

        self.customer = create_customer(
            self.user,
            first_name='علی',
            last_name='محمدی',
            phone='09123456789',
        )
        self.product = create_product(self.user, name='لنت جلو')
        self.bank = create_bank(name='بانک ملت', code='12')
        self.bank_account = create_bank_account(
            self.user, bank=self.bank,
            card_number='6104337770012345',
        )
        # Create invoice with bank snapshot data and notes
        self.invoice = create_invoice(
            self.user,
            customer=self.customer,
            items_data=[
                {'product_name': 'لنت جلو', 'quantity': 4, 'unit_price': 35000, 'tax_rate': 10},
            ],
            notes='فاکتور آزمایشی',
        )
        # Manually set bank snapshot fields (normally done via serializer)
        self.invoice.bank_name = 'بانک ملت'
        self.invoice.card_number = '6104337770012345'
        self.invoice.save()

        self.url = '/api/invoices/'

    def test_search_by_invoice_number(self):
        response = self.client.get(self.url, {'search': self.invoice.invoice_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1,
                         "Should find invoice by invoice_number")

    def test_search_by_customer_name(self):
        response = self.client.get(self.url, {'search': 'علی'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1,
                                "Should find invoice by customer first_name")

    def test_search_by_customer_phone(self):
        response = self.client.get(self.url, {'search': '09123456789'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1,
                                "Should find invoice by customer_phone")

    def test_search_by_product_name(self):
        response = self.client.get(self.url, {'search': 'لنت جلو'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1,
                                "Should find invoice by product_name in items")

    def test_search_by_bank_name(self):
        response = self.client.get(self.url, {'search': 'بانک ملت'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1,
                                "Should find invoice by bank_name")

    def test_search_by_notes(self):
        response = self.client.get(self.url, {'search': 'آزمایشی'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1,
                                "Should find invoice by notes")


class TestInvoiceSearchPartialMatch(TestCase):
    """Partial matches should work for invoice search."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user, first_name='علی', last_name='احمدی', phone='09120001111')
        self.invoice = create_invoice(
            self.user,
            customer=self.customer,
            items_data=[{'product_name': 'روغن موتور ۱۰W-40', 'quantity': 2, 'unit_price': 80000}],
        )
        self.url = '/api/invoices/'

    def test_partial_invoice_number_match(self):
        # Search with a partial invoice number
        partial = self.invoice.invoice_number[:10]
        response = self.client.get(self.url, {'search': partial})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_partial_customer_name_match(self):
        response = self.client.get(self.url, {'search': 'احمد'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_partial_product_name_match(self):
        response = self.client.get(self.url, {'search': 'روغن'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)


class TestInvoiceSearchNoResults(TestCase):
    """Non-matching queries return empty list."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)
        self.invoice = create_invoice(
            self.user,
            customer=self.customer,
            items_data=[{'product_name': 'لنت', 'quantity': 1, 'unit_price': 50000}],
        )
        self.url = '/api/invoices/'

    def test_non_matching_query_returns_empty(self):
        response = self.client.get(self.url, {'search': 'ZZZZNOTEXIST999'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0,
                         "Non-matching search should return empty results")


class TestInvoiceSearchIsolation(TestCase):
    """User A's search doesn't return User B's invoices."""

    def setUp(self):
        self.client = APIClient()
        self.user_a = create_user(username='user_a', email='a@test.com')
        self.user_b = create_user(username='user_b', email='b@test.com')

        self.customer_a = create_customer(self.user_a, first_name='علی', last_name='A', phone='09111111111')
        self.customer_b = create_customer(self.user_b, first_name='علی', last_name='B', phone='09222222222')

        self.product_a = create_product(self.user_a, name='محصول A')
        self.product_b = create_product(self.user_b, name='محصول B')

        self.invoice_a = create_invoice(
            self.user_a, customer=self.customer_a,
            items_data=[{'product_name': 'محصول A', 'quantity': 1, 'unit_price': 50000}],
        )
        self.invoice_b = create_invoice(
            self.user_b, customer=self.customer_b,
            items_data=[{'product_name': 'محصول B', 'quantity': 1, 'unit_price': 60000}],
        )

    def test_user_a_search_doesnt_see_user_b(self):
        self.client.force_authenticate(user=self.user_a)
        # Search by user_b's customer last_name
        response = self.client.get('/api/invoices/', {'search': 'B'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0,
                         "User A should not see User B's invoices")

    def test_user_b_search_doesnt_see_user_a(self):
        self.client.force_authenticate(user=self.user_b)
        response = self.client.get('/api/invoices/', {'search': 'محصول A'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0,
                         "User B should not see User A's invoices")

    def test_user_a_finds_own_invoices(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get('/api/invoices/', {'search': 'محصول A'})
        self.assertEqual(len(response.data['results']), 1)


class TestProductSearch(TestCase):
    """Product search by name via autocomplete endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.product = create_product(self.user, name='لنت ترمز جلو')
        self.product2 = create_product(self.user, name='روغن موتور')
        self.url = '/api/products/autocomplete/'

    def test_search_product_by_name(self):
        response = self.client.get(self.url, {'q': 'لنت'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'لنت ترمز جلو')

    def test_search_product_partial_match(self):
        response = self.client.get(self.url, {'q': 'روغن'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'روغن موتور')

    def test_search_product_no_match(self):
        response = self.client.get(self.url, {'q': 'NOTEXIST'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_search_product_empty_query(self):
        response = self.client.get(self.url, {'q': ''})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class TestCustomerSearch(TestCase):
    """Customer search by first_name, last_name, phone via autocomplete endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(
            self.user,
            first_name='علی',
            last_name='محمدی',
            phone='09123456789',
        )
        self.customer2 = create_customer(
            self.user,
            first_name='حسین',
            last_name='رضايی',
            phone='09351112233',
        )
        self.url = '/api/customers/autocomplete/'

    def test_search_by_first_name(self):
        response = self.client.get(self.url, {'q': 'علی'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        names = [c['first_name'] for c in response.data]
        self.assertIn('علی', names)

    def test_search_by_last_name(self):
        response = self.client.get(self.url, {'q': 'رضايی'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        last_names = [c['last_name'] for c in response.data]
        self.assertIn('رضايی', last_names)

    def test_search_by_phone(self):
        response = self.client.get(self.url, {'q': '0935111'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        phones = [c['phone'] for c in response.data]
        self.assertIn('09351112233', phones)

    def test_search_no_match(self):
        response = self.client.get(self.url, {'q': 'ZZZZNOTEXIST'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class TestCombinedFilters(TestCase):
    """Combined date_from + date_to filters work together."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)
        self.product = create_product(self.user)

        # Invoice on day 0
        self.invoice_day0 = create_invoice(
            self.user,
            customer=self.customer,
            items_data=[{'product_name': 'Item Day0', 'quantity': 1, 'unit_price': 10000}],
            invoice_date=date.today(),
        )
        # Invoice 7 days ago
        self.invoice_day7 = create_invoice(
            self.user,
            customer=self.customer,
            items_data=[{'product_name': 'Item Day7', 'quantity': 1, 'unit_price': 20000}],
            invoice_date=date.today() - timedelta(days=7),
        )
        # Invoice 30 days ago
        self.invoice_day30 = create_invoice(
            self.user,
            customer=self.customer,
            items_data=[{'product_name': 'Item Day30', 'quantity': 1, 'unit_price': 30000}],
            invoice_date=date.today() - timedelta(days=30),
        )

    def test_combined_date_filter(self):
        date_from = (date.today() - timedelta(days=10)).isoformat()
        date_to = date.today().isoformat()
        response = self.client.get('/api/invoices/', {
            'date_from': date_from,
            'date_to': date_to,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        # Should include day0 and day7, but not day30
        invoice_numbers = [r['invoice_number'] for r in results]
        self.assertIn(self.invoice_day0.invoice_number, invoice_numbers)
        self.assertIn(self.invoice_day7.invoice_number, invoice_numbers)
        self.assertNotIn(self.invoice_day30.invoice_number, invoice_numbers)

    def test_date_from_only(self):
        date_from = (date.today() - timedelta(days=8)).isoformat()
        response = self.client.get('/api/invoices/', {'date_from': date_from})
        results = response.data['results']
        invoice_numbers = [r['invoice_number'] for r in results]
        self.assertIn(self.invoice_day0.invoice_number, invoice_numbers)
        self.assertIn(self.invoice_day7.invoice_number, invoice_numbers)
        self.assertNotIn(self.invoice_day30.invoice_number, invoice_numbers)

    def test_date_to_only(self):
        date_to = (date.today() - timedelta(days=29)).isoformat()
        response = self.client.get('/api/invoices/', {'date_to': date_to})
        results = response.data['results']
        invoice_numbers = [r['invoice_number'] for r in results]
        self.assertNotIn(self.invoice_day0.invoice_number, invoice_numbers)
        self.assertNotIn(self.invoice_day7.invoice_number, invoice_numbers)
        self.assertIn(self.invoice_day30.invoice_number, invoice_numbers)


class TestCustomerFilter(TestCase):
    """customer_id param filters invoices to specific customer."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)

        self.customer_a = create_customer(
            self.user, first_name='علی', last_name='محمدی', phone='09111111111',
        )
        self.customer_b = create_customer(
            self.user, first_name='حسین', last_name='رضايی', phone='09222222222',
        )
        self.product = create_product(self.user)

        self.invoice_a = create_invoice(
            self.user,
            customer=self.customer_a,
            items_data=[{'product_name': 'Item A', 'quantity': 1, 'unit_price': 50000}],
        )
        self.invoice_b = create_invoice(
            self.user,
            customer=self.customer_b,
            items_data=[{'product_name': 'Item B', 'quantity': 1, 'unit_price': 60000}],
        )

    def test_filter_by_customer_id(self):
        response = self.client.get('/api/invoices/', {'customer_id': self.customer_a.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['invoice_number'], self.invoice_a.invoice_number)

    def test_filter_by_different_customer_id(self):
        response = self.client.get('/api/invoices/', {'customer_id': self.customer_b.pk})
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['invoice_number'], self.invoice_b.invoice_number)

    def test_filter_by_nonexistent_customer_returns_empty(self):
        response = self.client.get('/api/invoices/', {'customer_id': 99999})
        results = response.data['results']
        self.assertEqual(len(results), 0)

    def test_no_customer_filter_returns_all(self):
        response = self.client.get('/api/invoices/')
        results = response.data['results']
        self.assertEqual(len(results), 2, "Without customer_id filter, all user's invoices should appear")
