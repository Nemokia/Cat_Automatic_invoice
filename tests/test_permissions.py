"""Tests for user isolation and unauthenticated access."""
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from tests.factories import (
    create_user, create_user2, create_customer, create_product,
    create_bank, create_bank_account, create_invoice,
)

User = get_user_model()


class TestUserIsolation(TestCase):
    """User A's data must be invisible to User B across all resource types."""

    def setUp(self):
        self.client = APIClient()
        self.user_a = create_user(
            username='isolation_a', password='PassA123!',
            email='a@iso.test',
        )
        self.user_b = create_user2(
            username='isolation_b',
            password='PassB123!',
            email='b@iso.test',
        )

    # ── Customers ──────────────────────────────────────────────────────

    def test_user_b_cannot_get_user_a_customer(self):
        cust = create_customer(self.user_a, first_name='زهرا', last_name='نوری',
                               phone='09121000001')
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get(f'/api/customers/{cust.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_update_user_a_customer(self):
        cust = create_customer(self.user_a, first_name='زهرا', last_name='نوری',
                               phone='09121000002')
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.put(f'/api/customers/{cust.pk}/', {
            'first_name': 'هکر', 'last_name': 'بدهکار',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_delete_user_a_customer(self):
        cust = create_customer(self.user_a, first_name='زهرا', last_name='نوری',
                               phone='09121000003')
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.delete(f'/api/customers/{cust.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_search_for_user_a_customer(self):
        create_customer(self.user_a, first_name='زهرا', last_name='نوری',
                        phone='09121000004')
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get('/api/customers/autocomplete/', {'q': 'زهرا'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    # ── Products ───────────────────────────────────────────────────────

    def test_user_b_cannot_get_user_a_product(self):
        prod = create_product(self.user_a, name='فیلتر روغن')
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get(f'/api/products/{prod.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_update_user_a_product(self):
        prod = create_product(self.user_a, name='فیلتر روغن')
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.patch(f'/api/products/{prod.pk}/', {
            'name': 'محصول هکر',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_delete_user_a_product(self):
        prod = create_product(self.user_a, name='فیلتر روغن')
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.delete(f'/api/products/{prod.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_search_for_user_a_product(self):
        create_product(self.user_a, name='فیلتر روغن')
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get('/api/products/autocomplete/', {'q': 'فیلتر'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    # ── Invoices ───────────────────────────────────────────────────────

    def test_user_b_cannot_get_user_a_invoice(self):
        inv = create_invoice(self.user_a)
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get(f'/api/invoices/{inv.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_update_user_a_invoice(self):
        inv = create_invoice(self.user_a)
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.patch(f'/api/invoices/{inv.pk}/', {
            'notes': 'هک شده',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_delete_user_a_invoice(self):
        inv = create_invoice(self.user_a)
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.delete(f'/api/invoices/{inv.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ── Bank Accounts ──────────────────────────────────────────────────

    def test_user_b_cannot_get_user_a_bank_account(self):
        ba = create_bank_account(self.user_a, card_number='6037991000000001')
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get(f'/api/banks/accounts/{ba.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_update_user_a_bank_account(self):
        ba = create_bank_account(self.user_a, card_number='6037991000000002')
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.patch(f'/api/banks/accounts/{ba.pk}/', {
            'card_number': '6037999999999999',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_delete_user_a_bank_account(self):
        ba = create_bank_account(self.user_a, card_number='6037991000000003')
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.delete(f'/api/banks/accounts/{ba.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class TestUnauthenticatedAccess(TestCase):
    """All protected endpoints must return 401 without a token."""

    def setUp(self):
        self.client = APIClient()
        # No authentication

    def test_profile_returns_401(self):
        resp = self.client.get('/api/auth/profile/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_seller_profile_returns_401(self):
        resp = self.client.get('/api/auth/seller-profile/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_returns_401(self):
        resp = self.client.post('/api/auth/change-password/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_returns_401(self):
        resp = self.client.get('/api/auth/dashboard/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customers_list_returns_401(self):
        resp = self.client.get('/api/customers/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customers_create_returns_401(self):
        resp = self.client.post('/api/customers/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_products_list_returns_401(self):
        resp = self.client.get('/api/products/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_products_create_returns_401(self):
        resp = self.client.post('/api/products/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invoices_list_returns_401(self):
        resp = self.client.get('/api/invoices/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invoices_create_returns_401(self):
        resp = self.client.post('/api/invoices/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_banks_accounts_list_returns_401(self):
        resp = self.client.get('/api/banks/accounts/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reports_sales_returns_401(self):
        resp = self.client.get('/api/reports/sales/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reports_customers_returns_401(self):
        resp = self.client.get('/api/reports/customers/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reports_products_returns_401(self):
        resp = self.client.get('/api/reports/products/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
