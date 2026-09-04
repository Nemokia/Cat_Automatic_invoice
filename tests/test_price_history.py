"""Tests for price history: adding prices, persistence across invoices, and listing."""
from decimal import Decimal
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from tests.factories import create_user, create_product, create_customer, create_invoice, create_price_history


class TestPriceHistoryAdd(APITestCase):
    """Adding a price entry via API returns 201 and updates latest_price."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.product = create_product(self.user)

    def test_add_price_entry(self):
        response = self.client.post(
            f'/api/products/{self.product.id}/price/',
            {'price': '150000'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data['price']), Decimal('150000'))

    def test_latest_price_updates_after_add(self):
        self.client.post(
            f'/api/products/{self.product.id}/price/',
            {'price': '150000'},
            format='json',
        )
        # Refresh product
        self.product.refresh_from_db()
        self.assertEqual(self.product.latest_price, Decimal('150000'))


class TestPriceHistoryMultiple(APITestCase):
    """Adding 3 prices; latest_price is the most recent."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.product = create_product(self.user)

    def test_most_recent_price_wins(self):
        self.client.post(
            f'/api/products/{self.product.id}/price/',
            {'price': '100000'},
            format='json',
        )
        self.client.post(
            f'/api/products/{self.product.id}/price/',
            {'price': '120000'},
            format='json',
        )
        self.client.post(
            f'/api/products/{self.product.id}/price/',
            {'price': '110000'},
            format='json',
        )
        self.product.refresh_from_db()
        # Most recent = last added = 110000
        self.assertEqual(self.product.latest_price, Decimal('110000'))


class TestPriceHistoryPersistence(APITestCase):
    """Invoice snapshots the price; changing product price later doesn't affect old invoices."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.product = create_product(self.user)
        self.customer = create_customer(self.user)

    def test_invoice_preserves_old_price(self):
        # Create invoice at price=100000
        invoice = create_invoice(
            self.user,
            customer=self.customer,
            items_data=[{
                'product': self.product.id,
                'product_name': self.product.name,
                'quantity': Decimal('1'),
                'unit_price': Decimal('100000'),
                'tax_rate': Decimal('0'),
                'unit': self.product.unit,
            }],
        )
        # Snapshot: invoice item should have 100000
        item = invoice.items.first()
        self.assertEqual(item.unit_price, Decimal('100000'))
        self.assertEqual(item.total_price, Decimal('100000'))

        # Change product price to 120000
        self.client.post(
            f'/api/products/{self.product.id}/price/',
            {'price': '120000'},
            format='json',
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.latest_price, Decimal('120000'))

        # Old invoice item still at 100000
        invoice.refresh_from_db()
        item = invoice.items.first()
        self.assertEqual(item.unit_price, Decimal('100000'))


class TestPriceHistoryList(APITestCase):
    """Product detail endpoint includes price_history list."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.product = create_product(self.user)

    def test_product_detail_includes_price_history(self):
        create_price_history(self.product, Decimal('100000'))
        create_price_history(self.product, Decimal('150000'))

        response = self.client.get(f'/api/products/{self.product.id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('price_history', response.data)
        self.assertEqual(len(response.data['price_history']), 2)

    def test_price_history_ordered_most_recent_first(self):
        create_price_history(self.product, Decimal('100000'))
        create_price_history(self.product, Decimal('200000'))

        response = self.client.get(f'/api/products/{self.product.id}/', format='json')
        prices = [Decimal(p['price']) for p in response.data['price_history']]
        # Order is ['-date', '-id'] — same date, so -id means last created first
        self.assertEqual(prices[0], Decimal('200000'))
        self.assertEqual(prices[1], Decimal('100000'))
