"""Tests for customer CRUD, validation, and autocomplete endpoints."""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from tests.factories import create_user, create_customer

User = get_user_model()


class TestCustomerCRUD(TestCase):
    """Full CRUD lifecycle for customers."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            username='cust_crud', password='CrudPass1!',
            email='cust_crud@test.com',
        )
        self.client.force_authenticate(user=self.user)

    def test_create_customer_201(self):
        resp = self.client.post('/api/customers/', {
            'first_name': 'زهرا',
            'last_name': 'احمدی',
            'phone': '09122000001',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['first_name'], 'زهرا')
        self.assertEqual(resp.data['last_name'], 'احمدی')

    def test_list_customers_200_paginated(self):
        create_customer(self.user, first_name='اول', phone='09123000001')
        create_customer(self.user, first_name='دوم', phone='09123000002')
        resp = self.client.get('/api/customers/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # DRF PageNumberPagination returns {count, next, previous, results}
        self.assertIn('results', resp.data)
        self.assertEqual(resp.data['count'], 2)
        self.assertEqual(len(resp.data['results']), 2)

    def test_retrieve_customer_200(self):
        cust = create_customer(self.user, first_name='رضا', phone='09124000001')
        resp = self.client.get(f'/api/customers/{cust.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['first_name'], 'رضا')

    def test_update_customer_200(self):
        cust = create_customer(self.user, first_name='مریم', phone='09125000001')
        resp = self.client.patch(f'/api/customers/{cust.pk}/', {
            'last_name': 'فاطمی',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['last_name'], 'فاطمی')

    def test_delete_customer_204(self):
        cust = create_customer(self.user, first_name='نیما', phone='09126000001')
        resp = self.client.delete(f'/api/customers/{cust.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        # Verify it's gone
        resp2 = self.client.get(f'/api/customers/{cust.pk}/')
        self.assertEqual(resp2.status_code, status.HTTP_404_NOT_FOUND)


class TestCustomerValidation(TestCase):
    """Edge-case validation for customer creation."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            username='cust_val', password='ValPass1!',
            email='cust_val@test.com',
        )
        self.client.force_authenticate(user=self.user)

    def test_missing_first_name_returns_400(self):
        resp = self.client.post('/api/customers/', {
            'last_name': 'احمدی',
            'phone': '09127000001',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('first_name', resp.data)

    def test_missing_last_name_returns_400(self):
        resp = self.client.post('/api/customers/', {
            'first_name': 'زهرا',
            'phone': '09127000002',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('last_name', resp.data)

    def test_duplicate_customer_returns_400_not_500(self):
        """unique_together violation must return a clean 400, not a 500."""
        create_customer(self.user, first_name='علی', last_name='محمدی',
                        phone='09127000003')
        resp = self.client.post('/api/customers/', {
            'first_name': 'علی',
            'last_name': 'محمدی',
            'phone': '09127000003',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TestCustomerAutocomplete(TestCase):
    """GET /api/customers/autocomplete/?q=..."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            username='cust_auto', password='AutoPass1!',
            email='cust_auto@test.com',
        )
        self.client.force_authenticate(user=self.user)
        create_customer(self.user, first_name='سپیده', last_name='کریمی',
                        phone='09128000001')
        create_customer(self.user, first_name='امیر', last_name='گلی',
                        phone='09128000002')

    def test_search_by_first_name(self):
        resp = self.client.get('/api/customers/autocomplete/', {'q': 'سپیده'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['first_name'], 'سپیده')

    def test_search_by_last_name(self):
        resp = self.client.get('/api/customers/autocomplete/', {'q': 'گلی'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['last_name'], 'گلی')

    def test_search_by_phone(self):
        resp = self.client.get('/api/customers/autocomplete/', {'q': '09128000001'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_partial_match(self):
        resp = self.client.get('/api/customers/autocomplete/', {'q': 'سپید'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_empty_search_returns_empty_list(self):
        resp = self.client.get('/api/customers/autocomplete/', {'q': ''})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_no_results_for_non_match(self):
        resp = self.client.get('/api/customers/autocomplete/', {'q': 'ناموجود'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)
