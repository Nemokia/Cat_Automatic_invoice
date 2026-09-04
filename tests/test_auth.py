"""Tests for authentication, JWT, profile, and dashboard endpoints."""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import (
    create_user, create_user2, create_customer,
    create_product, create_invoice,
)

User = get_user_model()


class TestRegistration(TestCase):
    """POST /api/auth/register/"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/register/'
        self.valid_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'علی',
            'last_name': 'رضا',
            'phone': '09121111111',
            'password': 'StrongPass1!',
            'password_confirm': 'StrongPass1!',
        }

    def test_valid_registration_returns_201_with_tokens(self):
        resp = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', resp.data)
        self.assertIn('access', resp.data['tokens'])
        self.assertIn('refresh', resp.data['tokens'])
        self.assertIn('user', resp.data)
        self.assertEqual(resp.data['user']['username'], 'newuser')
        # User was actually created
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_password_mismatch_returns_400(self):
        data = self.valid_data.copy()
        data['password_confirm'] = 'DifferentPass1!'
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_short_password_returns_400(self):
        data = self.valid_data.copy()
        data['password'] = 'abc'
        data['password_confirm'] = 'abc'
        resp = self.client.post(self.url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_username_returns_400(self):
        create_user(username='newuser', password='irrelevant')
        resp = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_fields_returns_400(self):
        resp = self.client.post(self.url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # Should have errors for required fields
        self.assertTrue(len(resp.data) > 0)


class TestLogin(TestCase):
    """POST /api/auth/login/"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/login/'
        self.user = create_user(
            username='logintest', password='LoginPass1!',
            email='login@example.com',
        )

    def test_valid_credentials_returns_200_with_tokens(self):
        resp = self.client.post(self.url, {
            'username': 'logintest',
            'password': 'LoginPass1!',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', resp.data)
        self.assertIn('access', resp.data['tokens'])
        self.assertIn('refresh', resp.data['tokens'])

    def test_wrong_password_returns_401(self):
        resp = self.client.post(self.url, {
            'username': 'logintest',
            'password': 'WrongPassword1!',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unknown_user_returns_401(self):
        resp = self.client.post(self.url, {
            'username': 'nonexistent',
            'password': 'Whatever123!',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class TestJWT(TestCase):
    """Test JWT token access, refresh, rotation, and rejection."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            username='jwttest', password='JwtPass123!',
            email='jwt@example.com',
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.access_token = str(self.refresh.access_token)

    def test_access_token_works(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        resp = self.client.get('/api/auth/profile/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], 'jwttest')

    def test_refresh_token_works(self):
        resp = self.client.post('/api/token/refresh/', {
            'refresh': str(self.refresh),
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)

    def test_token_rotation_on_refresh(self):
        """When ROTATE_REFRESH_TOKENS=True, refresh should return a new refresh token."""
        old_refresh = str(self.refresh)
        resp = self.client.post('/api/token/refresh/', {
            'refresh': old_refresh,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('refresh', resp.data)
        new_refresh = resp.data['refresh']
        # New refresh token should differ from original
        self.assertNotEqual(old_refresh, new_refresh)

    def test_invalid_token_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid.token.here')
        resp = self.client.get('/api/auth/profile/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class TestProfile(TestCase):
    """GET/PUT /api/auth/profile/, POST /api/auth/change-password/"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            username='profiletest', password='ProfilePass1!',
            email='profile@example.com', first_name='علی',
            last_name='محمدی', phone='09129999999',
        )
        self.client.force_authenticate(user=self.user)

    def test_get_profile(self):
        resp = self.client.get('/api/auth/profile/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], 'profiletest')
        self.assertEqual(resp.data['first_name'], 'علی')

    def test_update_profile(self):
        resp = self.client.patch('/api/auth/profile/', {
            'first_name': 'حسن',
            'last_name': 'علی',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['first_name'], 'حسن')
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'حسن')

    def test_change_password_correct_old(self):
        resp = self.client.post('/api/auth/change-password/', {
            'old_password': 'ProfilePass1!',
            'new_password': 'NewSecure123!',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecure123!'))

    def test_change_password_wrong_old(self):
        resp = self.client.post('/api/auth/change-password/', {
            'old_password': 'WrongOldPass!',
            'new_password': 'NewSecure123!',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TestDashboard(TestCase):
    """GET /api/auth/dashboard/"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            username='dashtest', password='DashPass123!',
            email='dash@example.com',
        )
        self.client.force_authenticate(user=self.user)

    def test_returns_stats_for_authenticated_user(self):
        # Create some data for this user; pass customer explicitly to
        # create_invoice so it doesn't create a second one internally.
        customer = create_customer(self.user, first_name='سپیده',
                                   last_name='کریمی', phone='09128888888')
        create_product(self.user, name='لنت جلو', unit='عدد')
        create_invoice(self.user, customer=customer, items_data=[
            {'product_name': 'لنت', 'quantity': Decimal('2'),
             'unit_price': Decimal('50000'), 'tax_rate': Decimal('0'),
             'unit': 'عدد'},
        ])

        resp = self.client.get('/api/auth/dashboard/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('total_invoices', resp.data)
        self.assertIn('total_revenue', resp.data)
        self.assertIn('total_products', resp.data)
        self.assertIn('total_customers', resp.data)
        self.assertEqual(resp.data['total_customers'], 1)
        self.assertEqual(resp.data['total_products'], 1)
        self.assertEqual(resp.data['total_invoices'], 1)
