"""Tests for bank accounts CRUD, validation, isolation, defaults, and IBAN mapping."""
from decimal import Decimal
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from tests.factories import create_user, create_user2, create_bank, create_bank_account
from banks.models import BankAccount


class TestBankAccountCRUD(APITestCase):
    """Full CRUD lifecycle for bank accounts."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.bank = create_bank()
        self.valid_payload = {
            'bank': self.bank.id,
            'card_number': '6104337770012345',
            'iban': 'IR062960000000100324200001',
            'account_holder': 'علی محمدی',
            'account_number': '123456',
            'is_default': False,
        }

    def test_create_bank_account(self):
        response = self.client.post('/api/banks/accounts/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['bank'], self.bank.id)
        self.assertEqual(response.data['card_number'], '6104337770012345')
        self.assertEqual(response.data['iban'], 'IR062960000000100324200001')
        self.assertEqual(response.data['account_holder'], 'علی محمدی')

    def test_list_bank_accounts(self):
        create_bank_account(self.user, card_number='6104337770012345')
        create_bank_account(self.user, card_number='6104337770019999',
                            iban='IR062960000000100324200099')
        response = self.client.get('/api/banks/accounts/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_retrieve_bank_account(self):
        account = create_bank_account(self.user)
        response = self.client.get(f'/api/banks/accounts/{account.id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], account.id)
        self.assertEqual(response.data['card_number'], account.card_number)

    def test_update_bank_account(self):
        account = create_bank_account(self.user)
        response = self.client.patch(
            f'/api/banks/accounts/{account.id}/',
            {'account_holder': 'محمد رضایی'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['account_holder'], 'محمد رضایی')

    def test_delete_bank_account(self):
        account = create_bank_account(self.user)
        response = self.client.delete(f'/api/banks/accounts/{account.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verify it's gone
        response = self.client.get(f'/api/banks/accounts/{account.id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestBankAccountValidation(APITestCase):
    """Missing required fields return 400."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.bank = create_bank()

    def test_missing_bank(self):
        payload = {
            'card_number': '6104337770012345',
            'iban': 'IR062960000000100324200001',
            'account_holder': 'علی محمدی',
        }
        response = self.client.post('/api/banks/accounts/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_card_number(self):
        payload = {
            'bank': self.bank.id,
            'iban': 'IR062960000000100324200001',
            'account_holder': 'علی محمدی',
        }
        response = self.client.post('/api/banks/accounts/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_iban(self):
        payload = {
            'bank': self.bank.id,
            'card_number': '6104337770012345',
            'account_holder': 'علی محمدی',
        }
        response = self.client.post('/api/banks/accounts/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_account_holder(self):
        payload = {
            'bank': self.bank.id,
            'card_number': '6104337770012345',
            'iban': 'IR062960000000100324200001',
        }
        response = self.client.post('/api/banks/accounts/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_payload(self):
        response = self.client.post('/api/banks/accounts/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestBankAccountIsolation(APITestCase):
    """User A's accounts are not visible to User B."""

    def setUp(self):
        self.user_a = create_user(username='user_a', email='a@test.com')
        self.user_b = create_user2()
        self.client_a = APIClient()
        self.client_b = APIClient()
        self.client_a.force_authenticate(user=self.user_a)
        self.client_b.force_authenticate(user=self.user_b)

    def test_user_b_cannot_see_user_a_accounts(self):
        acc = create_bank_account(self.user_a, card_number='1111111111111111')
        response = self.client_b.get('/api/banks/accounts/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_user_b_cannot_retrieve_user_a_account(self):
        acc = create_bank_account(self.user_a, card_number='1111111111111111')
        response = self.client_b.get(f'/api/banks/accounts/{acc.id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_update_user_a_account(self):
        acc = create_bank_account(self.user_a, card_number='1111111111111111')
        response = self.client_b.patch(
            f'/api/banks/accounts/{acc.id}/',
            {'account_holder': 'HACKED'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Verify unchanged
        acc.refresh_from_db()
        self.assertNotEqual(acc.account_holder, 'HACKED')

    def test_user_b_cannot_delete_user_a_account(self):
        acc = create_bank_account(self.user_a, card_number='1111111111111111')
        response = self.client_b.delete(f'/api/banks/accounts/{acc.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Still exists
        self.assertTrue(
            BankAccount.objects.filter(user=self.user_a, pk=acc.id).exists()
        )


class TestBankAccountDefault(APITestCase):
    """Setting is_default=True on one account unsets the previous default."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.bank = create_bank()

    def test_first_default(self):
        acc = create_bank_account(self.user, is_default=True)
        acc.refresh_from_db()
        self.assertTrue(acc.is_default)

    def test_new_default_unsets_old(self):
        acc1 = create_bank_account(self.user, card_number='1111111111111111', is_default=True)
        acc2 = create_bank_account(self.user, card_number='2222222222222222', is_default=True)
        acc1.refresh_from_db()
        acc2.refresh_from_db()
        # acc2 is default
        self.assertTrue(acc2.is_default)
        # acc1 is no longer default
        self.assertFalse(acc1.is_default)

    def test_non_default_does_not_unset(self):
        acc1 = create_bank_account(self.user, card_number='1111111111111111', is_default=True)
        acc2 = create_bank_account(self.user, card_number='2222222222222222', is_default=False)
        acc1.refresh_from_db()
        self.assertTrue(acc1.is_default)


class TestCardToIban(APITestCase):
    """Different card numbers map to different IBANs."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_card_a_returns_iban_a(self):
        acc = create_bank_account(
            self.user,
            card_number='6104337770012345',
            iban='IR062960000000100324200001',
        )
        response = self.client.get(f'/api/banks/accounts/{acc.id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['iban'], 'IR062960000000100324200001')

    def test_different_cards_different_ibans(self):
        acc1 = create_bank_account(
            self.user, card_number='6104337770012345',
            iban='IR062960000000100324200001',
        )
        acc2 = create_bank_account(
            self.user, card_number='6104337770019999',
            iban='IR062960000000100324200099',
        )
        resp1 = self.client.get(f'/api/banks/accounts/{acc1.id}/', format='json')
        resp2 = self.client.get(f'/api/banks/accounts/{acc2.id}/', format='json')
        self.assertEqual(resp1.data['iban'], 'IR062960000000100324200001')
        self.assertEqual(resp2.data['iban'], 'IR062960000000100324200099')
        self.assertNotEqual(resp1.data['iban'], resp2.data['iban'])

    def test_same_card_same_iban(self):
        acc = create_bank_account(
            self.user, card_number='6104337770012345',
            iban='IR062960000000100324200001',
        )
        resp = self.client.get(f'/api/banks/accounts/{acc.id}/', format='json')
        self.assertEqual(resp.data['card_number'], '6104337770012345')
        self.assertEqual(resp.data['iban'], 'IR062960000000100324200001')
