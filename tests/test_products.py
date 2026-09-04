"""Tests for product CRUD, validation, autocomplete, and price history."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from tests.factories import create_user, create_product, create_price_history

User = get_user_model()


class TestProductCRUD(TestCase):
    """Full CRUD lifecycle for products."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            username='prod_crud', password='CrudPass1!',
            email='prod_crud@test.com',
        )
        self.client.force_authenticate(user=self.user)

    def test_create_product_201(self):
        resp = self.client.post('/api/products/', {
            'name': 'لنت عقب',
            'unit': 'عدد',
            'frequency': '',
            'description': 'لنت ترمز عقب خودرو',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['name'], 'لنت عقب')

    def test_list_products(self):
        create_product(self.user, name='لنت جلو')
        create_product(self.user, name='فیلتر روغن')
        resp = self.client.get('/api/products/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('results', resp.data)
        self.assertEqual(resp.data['count'], 2)

    def test_retrieve_product(self):
        prod = create_product(self.user, name='لنت جلو')
        resp = self.client.get(f'/api/products/{prod.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['name'], 'لنت جلو')
        self.assertIn('price_history', resp.data)

    def test_update_product(self):
        prod = create_product(self.user, name='لنت جلو')
        resp = self.client.patch(f'/api/products/{prod.pk}/', {
            'description': 'توضیحات به‌روز شده',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['description'], 'توضیحات به‌روز شده')

    def test_delete_product_204(self):
        prod = create_product(self.user, name='لنت جلو')
        resp = self.client.delete(f'/api/products/{prod.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        resp2 = self.client.get(f'/api/products/{prod.pk}/')
        self.assertEqual(resp2.status_code, status.HTTP_404_NOT_FOUND)


class TestProductValidation(TestCase):
    """Edge-case validation for product creation."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            username='prod_val', password='ValPass1!',
            email='prod_val@test.com',
        )
        self.client.force_authenticate(user=self.user)

    def test_missing_name_returns_400(self):
        resp = self.client.post('/api/products/', {
            'unit': 'عدد',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', resp.data)

    def test_duplicate_name_same_user_raises_integrity_error(self):
        """The product unique_together constraint exists at DB level.

        NOTE: The ProductSerializer lacks a validate() uniqueness check
        (unlike CustomerSerializer), so the DB constraint raises
        IntegrityError instead of returning a clean 400.
        """
        from django.db import IntegrityError
        create_product(self.user, name='لنت جلو')
        with self.assertRaises(IntegrityError):
            self.client.post('/api/products/', {
                'name': 'لنت جلو',
                'unit': 'عدد',
            }, format='json')


class TestProductAutocomplete(TestCase):
    """GET /api/products/autocomplete/?q=..."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            username='prod_auto', password='AutoPass1!',
            email='prod_auto@test.com',
        )
        self.client.force_authenticate(user=self.user)
        create_product(self.user, name='لنت جلو')
        create_product(self.user, name='فیلتر روغن')

    def test_partial_match_search(self):
        resp = self.client.get('/api/products/autocomplete/', {'q': 'لنت'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['name'], 'لنت جلو')

    def test_empty_search_returns_empty_list(self):
        resp = self.client.get('/api/products/autocomplete/', {'q': ''})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_no_results(self):
        resp = self.client.get('/api/products/autocomplete/', {'q': 'ناموجود'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)


class TestPriceHistory(TestCase):
    """POST /api/products/<id>/price/ and price_history on product detail."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            username='price_test', password='PricePass1!',
            email='price@test.com',
        )
        self.client.force_authenticate(user=self.user)
        self.product = create_product(self.user, name='لنت جلو')

    def test_add_price_history_201(self):
        resp = self.client.post(
            f'/api/products/{self.product.pk}/price/',
            {'price': 250000},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(int(resp.data['price']), 250000)

    def test_latest_price_updates(self):
        """After adding a price entry, latest_price should reflect it."""
        # Initially zero (no price history)
        self.assertEqual(self.product.latest_price, Decimal('0'))

        # Add first price
        create_price_history(self.product, Decimal('250000'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.latest_price, Decimal('250000'))

        # Add a newer price
        create_price_history(self.product, Decimal('300000'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.latest_price, Decimal('300000'))

    def test_list_returns_price_history(self):
        """Product detail/list should include price_history entries."""
        create_price_history(self.product, Decimal('250000'))
        create_price_history(self.product, Decimal('300000'))

        resp = self.client.get(f'/api/products/{self.product.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('price_history', resp.data)
        self.assertEqual(len(resp.data['price_history']), 2)
