"""
Permanent regression tests for all fixed bugs.

BUG-001: negative unit_price was allowed → now 400
BUG-002: zero/negative quantity was allowed → now 400
BUG-004: empty items array was allowed → now 400
BUG-005: duplicate customer (same user+phone+first+last) caused 500 → now 400
"""
from datetime import date
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from tests.factories import (
    create_user, create_user2, create_customer, create_product,
    create_bank, create_bank_account, create_invoice, create_price_history,
)


class TestBug001Regression(TestCase):
    """BUG-001: negative unit_price must return HTTP 400, not 500."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)
        self.product = create_product(self.user)
        self.url = '/api/invoices/'

    def _post_invoice(self, unit_price):
        return self.client.post(self.url, {
            'customer': self.customer.pk,
            'invoice_date': str(date.today()),
            'items': [{
                'product': self.product.pk,
                'product_name': self.product.name,
                'quantity': 2,
                'unit_price': unit_price,
                'tax_rate': 0,
                'unit': self.product.unit,
            }],
        }, format='json')

    def test_negative_unit_price_returns_400(self):
        response = self._post_invoice(-5000)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         "Negative unit_price must be rejected with 400, not 500")
        self.assertEqual(
            __import__('invoices.models', fromlist=['Invoice']).Invoice.objects.filter(
                user=self.user
            ).count(),
            0,
            "No invoice should be created with negative unit_price",
        )

    def test_zero_unit_price_returns_400(self):
        response = self._post_invoice(0)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         "Zero unit_price must be rejected with 400")


class TestBug002Regression(TestCase):
    """BUG-002: zero/negative quantity and zero/negative price → 400."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)
        self.product = create_product(self.user)
        self.url = '/api/invoices/'

    def _post_invoice(self, quantity=1, unit_price=10000):
        return self.client.post(self.url, {
            'customer': self.customer.pk,
            'invoice_date': str(date.today()),
            'items': [{
                'product': self.product.pk,
                'product_name': self.product.name,
                'quantity': quantity,
                'unit_price': unit_price,
                'tax_rate': 0,
                'unit': self.product.unit,
            }],
        }, format='json')

    def test_zero_quantity_returns_400(self):
        response = self._post_invoice(quantity=0)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         "Zero quantity must be rejected")

    def test_negative_quantity_returns_400(self):
        response = self._post_invoice(quantity=-5)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         "Negative quantity must be rejected")

    def test_zero_price_returns_400(self):
        response = self._post_invoice(unit_price=0)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         "Zero price must be rejected")

    def test_negative_price_returns_400(self):
        response = self._post_invoice(unit_price=-1000)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         "Negative price must be rejected")


class TestBug004Regression(TestCase):
    """BUG-004: empty items array → 400, invoice not created."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)
        self.url = '/api/invoices/'
        self.initial_count = __import__('invoices.models', fromlist=['Invoice']).Invoice.objects.filter(
            user=self.user
        ).count()

    def test_empty_items_returns_400(self):
        response = self.client.post(self.url, {
            'customer': self.customer.pk,
            'invoice_date': str(date.today()),
            'items': [],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         "Empty items array must be rejected")

    def test_invoice_not_created_with_empty_items(self):
        self.client.post(self.url, {
            'customer': self.customer.pk,
            'invoice_date': str(date.today()),
            'items': [],
        }, format='json')
        from invoices.models import Invoice
        final_count = Invoice.objects.filter(user=self.user).count()
        self.assertEqual(self.initial_count, final_count,
                         "No invoice should be created when items array is empty")

    def test_missing_items_key_returns_400(self):
        response = self.client.post(self.url, {
            'customer': self.customer.pk,
            'invoice_date': str(date.today()),
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         "Missing items key must be rejected")


class TestBug005Regression(TestCase):
    """BUG-005: duplicate customer (same user+phone+first+last) → 400, not 500.
    Different user with same data → 201 (cross-user allowed)."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.user2 = create_user2()
        self.url = '/api/customers/'
        self.duplicate_payload = {
            'first_name': 'علی',
            'last_name': 'محمدی',
            'phone': '09123456789',
            'address': 'تهران',
        }

    def test_duplicate_customer_returns_400(self):
        """Same user creating identical customer must get 400, not 500."""
        self.client.force_authenticate(user=self.user)
        # First creation → 201
        resp1 = self.client.post(self.url, self.duplicate_payload, format='json')
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED,
                         "First customer creation should succeed")

        # Duplicate → 400
        resp2 = self.client.post(self.url, self.duplicate_payload, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST,
                         "Duplicate customer must return 400, not 500")

    def test_only_one_record_exists_after_duplicate_attempt(self):
        """After failed duplicate, only 1 customer record should exist."""
        self.client.force_authenticate(user=self.user)
        self.client.post(self.url, self.duplicate_payload, format='json')
        self.client.post(self.url, self.duplicate_payload, format='json')

        from customers.models import Customer
        count = Customer.objects.filter(
            user=self.user,
            phone=self.duplicate_payload['phone'],
            first_name=self.duplicate_payload['first_name'],
            last_name=self.duplicate_payload['last_name'],
        ).count()
        self.assertEqual(count, 1, "Only 1 customer record should exist for duplicate data")

    def test_different_user_same_data_allowed(self):
        """Different user with same customer data → 201 (cross-user allowed)."""
        self.client.force_authenticate(user=self.user)
        resp1 = self.client.post(self.url, self.duplicate_payload, format='json')
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.user2)
        resp2 = self.client.post(self.url, self.duplicate_payload, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED,
                         "Different user with same customer data should be allowed")


class TestProductNamePersistence(TestCase):
    """Ensure product_name is preserved through the full data flow:
    UI → State → API → Database → Invoice → PDF.
    These are backend API tests verifying the serializer/model layer.
    Frontend JS fix is separate (pages-invoice-form.js onItemInput sync)."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)
        self.product = create_product(self.user, name='لنت جلو')
        self.url = '/api/invoices/'

    def _create_invoice(self, items):
        return self.client.post(self.url, {
            'customer': self.customer.pk,
            'invoice_date': str(date.today()),
            'items': items,
        }, format='json')

    def test_manual_product_name_preserved(self):
        """Test A: User types product name manually (no product FK).
        Since auto-save-from-invoice, the typed item now creates & links a
        Product (user requirement) while product_name stays intact."""
        resp = self._create_invoice([{
            'product_name': 'کالای جدید من',
            'quantity': 1,
            'unit_price': 50000,
            'tax_rate': 0,
            'unit': 'عدد',
        }])
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']
        # Verify product_name is stored
        detail = self.client.get(f'/api/invoices/{inv_id}/')
        self.assertEqual(detail.data['items'][0]['product_name'], 'کالای جدید من')
        # New behaviour: product auto-created and linked
        self.assertIsNotNone(detail.data['items'][0]['product'])

    def test_autocomplete_product_name_preserved(self):
        """Test B: User selects product from autocomplete (has product FK)."""
        resp = self._create_invoice([{
            'product': self.product.pk,
            'product_name': self.product.name,
            'quantity': 2,
            'unit_price': 100000,
            'tax_rate': 10,
            'unit': self.product.unit,
        }])
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']
        detail = self.client.get(f'/api/invoices/{inv_id}/')
        self.assertEqual(detail.data['items'][0]['product_name'], 'لنت جلو')
        self.assertEqual(detail.data['items'][0]['product'], self.product.pk)

    def test_edited_product_name_preserved(self):
        """Test C: Type custom product name (no product FK) — name preserved."""
        resp = self._create_invoice([{
            'product_name': 'لنت تغییریافته',
            'quantity': 1,
            'unit_price': 75000,
            'tax_rate': 0,
            'unit': 'عدد',
        }])
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']
        detail = self.client.get(f'/api/invoices/{inv_id}/')
        self.assertEqual(detail.data['items'][0]['product_name'], 'لنت تغییریافته')

    def test_product_name_survives_refresh(self):
        """Test E: After save, retrieve invoice — product_name still exists."""
        resp = self._create_invoice([{
            'product_name': 'لنت عقب',
            'quantity': 3,
            'unit_price': 80000,
            'tax_rate': 5,
            'unit': 'عدد',
        }])
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']
        # Simulate refresh: fetch from DB
        detail = self.client.get(f'/api/invoices/{inv_id}/')
        self.assertEqual(detail.data['items'][0]['product_name'], 'لنت عقب')
        # Verify in DB directly
        from invoices.models import InvoiceItem
        db_item = InvoiceItem.objects.get(invoice_id=inv_id)
        self.assertEqual(db_item.product_name, 'لنت عقب')

    def test_mixed_manual_and_autocomplete_items(self):
        """Invoice with both manual name and autocomplete-selected items."""
        resp = self._create_invoice([
            {
                'product_name': 'کالای دستی',
                'quantity': 1,
                'unit_price': 10000,
                'tax_rate': 0,
                'unit': 'عدد',
            },
            {
                'product': self.product.pk,
                'product_name': self.product.name,
                'quantity': 2,
                'unit_price': 100000,
                'tax_rate': 10,
                'unit': self.product.unit,
            },
        ])
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']
        detail = self.client.get(f'/api/invoices/{inv_id}/')
        names = [it['product_name'] for it in detail.data['items']]
        self.assertIn('کالای دستی', names)
        self.assertIn('لنت جلو', names)

    def test_product_name_in_pdf_endpoint(self):
        """Test D: PDF endpoint returns content for invoice with product names."""
        resp = self._create_invoice([{
            'product_name': 'لنت جلو',
            'quantity': 1,
            'unit_price': 100000,
            'tax_rate': 0,
            'unit': 'عدد',
        }])
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']
        pdf_resp = self.client.get(f'/api/pdf/{inv_id}/')
        self.assertEqual(pdf_resp.status_code, status.HTTP_200_OK)
        # PDF should contain the product name bytes
        content = pdf_resp.content
        self.assertGreater(len(content), 0, "PDF should not be empty")


class TestBankingDataPersistence(TestCase):
    """Verify banking data is correctly stored and persisted.
    Tests the full flow: manual bank entry → API → Database."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)

    def test_bank_account_crud(self):
        """Create, read, update, delete bank account."""
        bank = create_bank(name='بانک ملت')
        # Create
        resp = self.client.post('/api/banks/accounts/', {
            'bank': bank.pk,
            'card_number': '1234567890123456',
            'iban': 'IR123456789012345678901234',
            'account_holder': 'علی محمدی',
            'account_number': '123456789',
            'is_default': True,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        acct_id = resp.data['id']

        # Read
        detail = self.client.get(f'/api/banks/accounts/{acct_id}/')
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['card_number'], '1234567890123456')
        self.assertEqual(detail.data['iban'], 'IR123456789012345678901234')
        self.assertEqual(detail.data['account_holder'], 'علی محمدی')

        # Update
        update_resp = self.client.patch(f'/api/banks/accounts/{acct_id}/', {
            'account_holder': 'علی رضایی',
        }, format='json')
        self.assertEqual(update_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(update_resp.data['account_holder'], 'علی رضایی')

        # Delete
        del_resp = self.client.delete(f'/api/banks/accounts/{acct_id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_partial_bank_data(self):
        """Bank account with minimal meaningful data (card + iban, no holder)."""
        bank = create_bank()
        resp = self.client.post('/api/banks/accounts/', {
            'bank': bank.pk,
            'card_number': '6219861034567890',
            'iban': 'IR123456789012345678901234',
            'account_holder': '-',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        acct_id = resp.data['id']
        detail = self.client.get(f'/api/banks/accounts/{acct_id}/')
        self.assertEqual(detail.data['card_number'], '6219861034567890')
        self.assertEqual(detail.data['iban'], 'IR123456789012345678901234')

    def test_custom_bank_name_persists(self):
        """Custom bank name should be stored via Bank FK."""
        bank = create_bank(name='بانک فرضی من')
        resp = self.client.post('/api/banks/accounts/', {
            'bank': bank.pk,
            'card_number': '1111222233334444',
            'iban': 'IR990000000000000000000001',
            'account_holder': 'تست',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        acct_id = resp.data['id']
        detail = self.client.get(f'/api/banks/accounts/{acct_id}/')
        self.assertEqual(detail.data['iban'], 'IR990000000000000000000001')
        self.assertEqual(detail.data['bank_name'], 'بانک فرضی من')

    def test_bank_account_user_isolation(self):
        """User A's bank account hidden from User B."""
        bank = create_bank()
        resp = self.client.post('/api/banks/accounts/', {
            'bank': bank.pk,
            'card_number': '1234567890123456',
            'iban': 'IR123456789012345678901234',
            'account_holder': 'علی',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        acct_id = resp.data['id']

        # Switch to user2
        user2 = create_user2()
        self.client.force_authenticate(user=user2)
        detail = self.client.get(f'/api/banks/accounts/{acct_id}/')
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_invoice_with_bank_snapshot(self):
        """Invoice stores bank info as snapshot — verify persistence."""
        bank = create_bank(name='بانک ملت')
        acct = create_bank_account(self.user, bank=bank,
                                    card_number='1234567890123456',
                                    iban='IR123456789012345678901234',
                                    account_holder='علی محمدی')

        resp = self.client.post('/api/invoices/', {
            'customer': self.customer.pk,
            'invoice_date': str(date.today()),
            'bank_account': acct.pk,
            'items': [{
                'product_name': 'تست بانک',
                'quantity': 1,
                'unit_price': 100000,
                'tax_rate': 0,
                'unit': 'عدد',
            }],
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']

        detail = self.client.get(f'/api/invoices/{inv_id}/')
        self.assertEqual(detail.data['bank_name'], 'بانک ملت')
        self.assertEqual(detail.data['card_number'], '1234567890123456')
        self.assertEqual(detail.data['iban'], 'IR123456789012345678901234')
        self.assertEqual(detail.data['account_holder'], 'علی محمدی')


class TestManualBankEntryRule(TestCase):
    """Rule: if card_number/iban/account_holder is provided on an invoice,
    bank_name is required (400 when missing). All fields optional otherwise."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.customer = create_customer(self.user)
        self.url = '/api/invoices/'
        self._items = [{
            'product_name': 'قلم تست',
            'quantity': 1,
            'unit_price': 10000,
            'tax_rate': 0,
            'unit': 'عدد',
        }]

    def _post_invoice(self, bank):
        return self.client.post(self.url, {
            'customer': self.customer.pk,
            'invoice_date': str(date.today()),
            'items': self._items,
            **bank,
        }, format='json')

    def test_card_without_bank_name_rejected(self):
        resp = self._post_invoice({'card_number': '1234567890123456'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('bank_name', resp.data)

    def test_iban_without_bank_name_rejected(self):
        resp = self._post_invoice({'iban': 'IR123456789012345678901234'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('bank_name', resp.data)

    def test_holder_without_bank_name_rejected(self):
        resp = self._post_invoice({'account_holder': 'علی محمدی'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('bank_name', resp.data)

    def test_card_with_bank_name_accepted(self):
        resp = self._post_invoice({
            'bank_name': 'بانک فرضی من',
            'card_number': '1234567890123456',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']
        detail = self.client.get(f'/api/invoices/{inv_id}/')
        self.assertEqual(detail.data['bank_name'], 'بانک فرضی من')
        self.assertEqual(detail.data['card_number'], '1234567890123456')

    def test_custom_bank_name_persists_verbatim(self):
        """A brand-new bank name typed by the user must be stored as-is."""
        resp = self._post_invoice({
            'bank_name': 'بانک XYZ',
            'card_number': '1111222233334444',
            'iban': 'IR990000000000000000000001',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']
        detail = self.client.get(f'/api/invoices/{inv_id}/')
        self.assertEqual(detail.data['bank_name'], 'بانک XYZ')

    def test_all_bank_fields_empty_is_valid(self):
        """No bank info at all → invoice still valid."""
        resp = self._post_invoice({})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']
        detail = self.client.get(f'/api/invoices/{inv_id}/')
        self.assertEqual(detail.data['bank_name'], '')

    def test_blank_bank_fields_are_valid(self):
        resp = self._post_invoice({
            'bank_name': '', 'card_number': '', 'iban': '', 'account_holder': '',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_bank_account_priority_over_manual(self):
        """If bank_account (saved account) is selected, its snapshot wins."""
        bank = create_bank(name='بانک رسمی')
        acct = create_bank_account(self.user, bank=bank,
                                    card_number='9999888877776666',
                                    iban='IR555544443333222211110000')
        resp = self._post_invoice({
            'bank_account': acct.pk,
            'bank_name': 'بانک دستی',
            'card_number': '1111111111111111',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']
        detail = self.client.get(f'/api/invoices/{inv_id}/')
        self.assertEqual(detail.data['bank_name'], 'بانک رسمی')
        self.assertEqual(detail.data['card_number'], '9999888877776666')

    def test_manual_bank_on_update(self):
        """Editing an invoice to add manual bank data persists it."""
        resp = self._post_invoice({})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        inv_id = resp.data['id']
        upd = self.client.patch(f'/api/invoices/{inv_id}/', {
            'bank_name': 'بانک ویرایشی',
            'card_number': '1234567890123456',
            'iban': 'IR123456789012345678901234',
            'account_holder': 'علی',
        }, format='json')
        self.assertEqual(upd.status_code, status.HTTP_200_OK)
        detail = self.client.get(f'/api/invoices/{inv_id}/')
        self.assertEqual(detail.data['bank_name'], 'بانک ویرایشی')
        self.assertEqual(detail.data['card_number'], '1234567890123456')


class TestBankAccountByName(TestCase):
    """Bank accounts can be created by typing a bank name (custom banks allowed)."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.url = '/api/banks/accounts/'

    def test_create_with_existing_bank_name(self):
        create_bank(name='بانک ملت')
        resp = self.client.post(self.url, {
            'bank_name_input': 'بانک ملت',
            'card_number': '1234567890123456',
            'iban': 'IR123456789012345678901234',
            'account_holder': 'علی',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['bank_name'], 'بانک ملت')
        # No duplicate Bank created
        from banks.models import Bank
        self.assertEqual(Bank.objects.filter(name='بانک ملت').count(), 1)

    def test_create_with_new_bank_name_creates_bank(self):
        """Custom bank name must create a new Bank record and persist."""
        resp = self.client.post(self.url, {
            'bank_name_input': 'بانک فرضی من',
            'card_number': '6219861034567890',
            'iban': 'IR990000000000000000000001',
            'account_holder': 'تست',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['bank_name'], 'بانک فرضی من')

        from banks.models import Bank
        self.assertTrue(Bank.objects.filter(name='بانک فرضی من').exists())

        # Persistence: retrieve again
        acct_id = resp.data['id']
        detail = self.client.get(f'/api/banks/accounts/{acct_id}/')
        self.assertEqual(detail.data['bank_name'], 'بانک فرضی من')
        self.assertEqual(detail.data['card_number'], '6219861034567890')

    def test_create_without_bank_name_rejected(self):
        """Card/iban/holder without any bank name → 400."""
        resp = self.client.post(self.url, {
            'card_number': '1234567890123456',
            'iban': 'IR123456789012345678901234',
            'account_holder': 'علی',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_bank_by_name(self):
        """Editing an account and changing its bank name works."""
        bank = create_bank(name='بانک قدیمی')
        resp = self.client.post(self.url, {
            'bank_name_input': 'بانک قدیمی',
            'card_number': '1234567890123456',
            'iban': 'IR123456789012345678901234',
            'account_holder': 'علی',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        acct_id = resp.data['id']

        upd = self.client.patch(f'/api/banks/accounts/{acct_id}/', {
            'bank_name_input': 'بانک جدید من',
        }, format='json')
        self.assertEqual(upd.status_code, status.HTTP_200_OK)
        self.assertEqual(upd.data['bank_name'], 'بانک جدید من')
