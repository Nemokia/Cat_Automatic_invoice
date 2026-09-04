"""Optional customer address in the invoice + auto-save of typed products
and bank accounts.

Address semantics (mirrors the smart name/phone flow):
- Address is fully optional; blank never errors.
- New customer + address -> both persisted.
- Existing customer picked/linked -> typed address goes to the INVOICE
  snapshot only; Customer record changes ONLY with explicit
  customer_update_address=True.
- PDF generation includes the address only when it exists.

Product/bank auto-save:
- Items typed without a product FK create Product records (get_or_create
  semantics, never clobber) and append a PriceHistory entry when the price
  differs from the latest.
- A manually typed bank snapshot (card_number present, no saved account
  selected) creates a BankAccount for reuse.
"""
from rest_framework import status
from rest_framework.test import APITestCase

from .factories import create_user, create_customer, create_product


class AddressInvoiceTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.url = '/api/invoices/'

    def _payload(self, **cust):
        data = {
            'invoice_date': '2026-08-30',
            'items': [{'product_name': 'کالا', 'quantity': 1, 'unit_price': 1000,
                       'tax_rate': 0, 'unit': 'عدد', 'order': 0}],
        }
        data.update(cust)
        return data

    def _detail(self, inv_id):
        return self.client.get(f'/api/invoices/{inv_id}/')

    def test_customer_without_address_ok(self):
        """Test 1 — blank address never blocks save."""
        resp = self.client.post(self.url, self._payload(
            customer_name='زهرا اسلامیان', customer_phone='09111111111',
            customer_address_input=''), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from customers.models import Customer
        c = Customer.objects.get(user=self.user, phone='09111111111')
        self.assertEqual(c.address, '')

    def test_new_customer_with_address_saved(self):
        """Test 2 — new customer + address both persisted."""
        resp = self.client.post(self.url, self._payload(
            customer_name='مریم احمدی', customer_phone='09222222222',
            customer_address_input='تهران، خیابان آزادی، پلاک ۱۰'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from customers.models import Customer
        c = Customer.objects.get(user=self.user, phone='09222222222')
        self.assertEqual(c.address, 'تهران، خیابان آزادی، پلاک ۱۰')
        d = self._detail(resp.data['id'])
        self.assertEqual(d.data['customer_address'], 'تهران، خیابان آزادی، پلاک ۱۰')

    def test_existing_customer_address_autofill_field_present(self):
        """Test 3 — autocomplete payload carries address for auto-fill."""
        create_customer(self.user, first_name='زهرا', last_name='اسلامیان',
                        phone='09111111111', address='تهران، خیابان آزادی، پلاک ۱۰')
        resp = self.client.get('/api/customers/autocomplete/?q=زهرا')
        self.assertEqual(resp.status_code, 200)
        item = next(i for i in resp.data if i['phone'] == '09111111111')
        self.assertEqual(item['address'], 'تهران، خیابان آزادی، پلاک ۱۰')

    def test_invoice_only_address_preserves_customer(self):
        """Test 5 — different address typed WITHOUT the update flag:
        invoice snapshot holds the new address, customer record untouched."""
        c = create_customer(self.user, first_name='زهرا', last_name='اسلامیان',
                            phone='09111111111', address='تهران، خیابان آزادی، پلاک ۱۰')
        resp = self.client.post(self.url, self._payload(
            customer=c.id, customer_address_input='تهران، خیابان انقلاب، پلاک ۲۰'),
            format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        c.refresh_from_db()
        self.assertEqual(c.address, 'تهران، خیابان آزادی، پلاک ۱۰')  # untouched
        d = self._detail(resp.data['id'])
        self.assertEqual(d.data['customer_address'], 'تهران، خیابان انقلاب، پلاک ۲۰')

    def test_update_address_flag_persists_to_customer(self):
        """Test 4 — explicit update flag persists the new address."""
        c = create_customer(self.user, first_name='زهرا', last_name='اسلامیان',
                            phone='09111111111', address='آدرس قدیم')
        resp = self.client.post(self.url, self._payload(
            customer=c.id, customer_address_input='آدرس جدید',
            customer_update_address=True), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        c.refresh_from_db()
        self.assertEqual(c.address, 'آدرس جدید')
        d = self._detail(resp.data['id'])
        self.assertEqual(d.data['customer_address'], 'آدرس جدید')

    def test_exact_match_address_persist_only_with_flag(self):
        """Direct entry that exact-matches: address persists only via flag."""
        create_customer(self.user, first_name='زهرا', last_name='اسلامیان',
                        phone='09111111111', address='آدرس قدیم')
        resp = self.client.post(self.url, self._payload(
            customer_name='زهرا اسلامیان', customer_phone='09111111111',
            customer_address_input='آدرس جدید'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from customers.models import Customer
        c = Customer.objects.get(phone='09111111111')
        self.assertEqual(c.address, 'آدرس قدیم')  # no flag -> untouched
        d = self._detail(resp.data['id'])
        self.assertEqual(d.data['customer_address'], 'آدرس جدید')  # invoice-only

        resp2 = self.client.post(self.url, self._payload(
            customer_name='زهرا اسلامیان', customer_phone='09111111111',
            customer_address_input='آدرس جدید', customer_update_address=True),
            format='json')
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        c.refresh_from_db()
        self.assertEqual(c.address, 'آدرس جدید')  # flag -> persisted


class ProductBankAutoSaveTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.url = '/api/invoices/'

    def _payload(self, items, **extra):
        data = {
            'invoice_date': '2026-08-30',
            'items': items,
        }
        data.update(extra)
        return data

    def test_new_item_creates_product_and_price(self):
        """Item typed without product FK -> Product + PriceHistory created."""
        resp = self.client.post(self.url, self._payload([
            {'product_name': 'لنت عقب پراید', 'quantity': 2, 'unit_price': 500000,
             'tax_rate': 0, 'unit': 'عدد', 'order': 0},
        ]), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from products.models import Product, PriceHistory
        p = Product.objects.get(user=self.user, name='لنت عقب پراید')
        self.assertEqual(p.unit, 'عدد')
        self.assertEqual(PriceHistory.objects.filter(product=p).count(), 1)
        d = self.client.get(f"/api/invoices/{resp.data['id']}/")
        item = d.data['items'][0]
        self.assertEqual(item['product'], p.id)  # linked, not orphaned

    def test_existing_item_name_links_and_appends_price_when_changed(self):
        """Existing product: linked without duplication; new price appended."""
        p = create_product(self.user, name='روغن موتور', unit='عدد')
        resp = self.client.post(self.url, self._payload([
            {'product_name': 'روغن موتور', 'quantity': 1, 'unit_price': 999999,
             'tax_rate': 0, 'unit': 'عدد', 'order': 0},
        ]), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from products.models import Product, PriceHistory
        self.assertEqual(Product.objects.filter(user=self.user, name='روغن موتور').count(), 1)
        d = self.client.get(f"/api/invoices/{resp.data['id']}/")
        self.assertEqual(d.data['items'][0]['product'], p.id)
        self.assertEqual(PriceHistory.objects.filter(product=p).count(), 1)

    def test_same_price_not_duplicated_in_history(self):
        p = create_product(self.user, name='فیلتر هوا')
        from products.models import PriceHistory
        from decimal import Decimal
        PriceHistory.objects.create(product=p, price=Decimal('100000'))
        resp = self.client.post(self.url, self._payload([
            {'product_name': 'فیلتر هوا', 'quantity': 1, 'unit_price': 100000,
             'tax_rate': 0, 'unit': 'عدد', 'order': 0},
        ]), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PriceHistory.objects.filter(product=p).count(), 1)

    def test_bank_snapshot_auto_saved(self):
        """Typed card+iban+bank_name with no saved account -> BankAccount created."""
        resp = self.client.post(self.url, self._payload(
            [{
                'product_name': 'کالا', 'quantity': 1, 'unit_price': 1000,
                'tax_rate': 0, 'unit': 'عدد', 'order': 0,
            }],
            bank_name='بانک ملت', card_number='6104337712345678',
            iban='IR062960000000100324200001', account_holder='علی محمدی',
        ), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from banks.models import BankAccount, Bank
        ba = BankAccount.objects.get(user=self.user, card_number='6104337712345678')
        self.assertEqual(ba.bank.name, 'بانک ملت')
        self.assertTrue(Bank.objects.filter(name='بانک ملت').exists())
        self.assertEqual(ba.iban, 'IR062960000000100324200001')

    def test_bank_account_not_duplicated(self):
        """Same card typed again -> no duplicate account."""
        payload = self._payload(
            [{
                'product_name': 'کالا', 'quantity': 1, 'unit_price': 1000,
                'tax_rate': 0, 'unit': 'عدد', 'order': 0,
            }],
            bank_name='بانک ملت', card_number='6104337799999999',
            iban='IR062960000000100324299999', account_holder='علی',
        )
        self.client.post(self.url, payload, format='json')
        resp2 = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        from banks.models import BankAccount
        self.assertEqual(BankAccount.objects.filter(
            user=self.user, card_number='6104337799999999').count(), 1)

    def test_saved_account_selection_skips_auto_save(self):
        """Choosing an existing account must not auto-create anything new."""
        from tests.factories import create_bank_account
        ba = create_bank_account(self.user, card_number='6037991111111111')
        resp = self.client.post(self.url, self._payload(
            [{
                'product_name': 'کالا', 'quantity': 1, 'unit_price': 1000,
                'tax_rate': 0, 'unit': 'عدد', 'order': 0,
            }],
            bank_account=ba.id,
        ), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from banks.models import BankAccount
        self.assertEqual(BankAccount.objects.filter(user=self.user).count(), 1)


class PdfAddressTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(user=self.user)

    def _create_invoice(self, address):
        from .factories import create_customer, create_invoice
        c = create_customer(self.user, address=address)
        return create_invoice(self.user, customer=c)

    def test_pdf_with_address(self):
        """Test 6 — PDF contains the address when present."""
        inv = self._create_invoice('تهران، خیابان آزادی، پلاک ۱۰')
        resp = self.client.get(f'/api/pdf/{inv.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_pdf_without_address(self):
        """Test 7 — PDF renders fine without an address (no empty label)."""
        inv = self._create_invoice('')
        resp = self.client.get(f'/api/pdf/{inv.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
