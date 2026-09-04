"""Smart customer registration/selection in the invoice form.

Covers:
- /api/customers/check-match/ statuses: exact / phone_conflict / name_conflict / similar / none
- Invoice create with direct customer entry: auto-create / auto-link exact
- Invoice create with explicit user decisions (create_new / update_existing)
- Snapshot consistency (customer FK fields always win in the snapshot)
- Old flow (customer FK without direct entry) still works
"""
from rest_framework import status
from rest_framework.test import APITestCase

from .factories import create_user, create_customer, create_invoice


class CheckMatchEndpointTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.url = '/api/customers/check-match/'

    def _post(self, name, phone):
        return self.client.post(self.url, {'full_name': name, 'phone': phone}, format='json')

    def test_no_match(self):
        resp = self._post('علی جدید', '09120000000')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'none')
        self.assertIsNone(resp.data['primary'])

    def test_exact_match_name_and_phone(self):
        create_customer(self.user, first_name='زهرا', last_name='اسلامیان', phone='09111111111')
        resp = self._post('زهرا اسلامیان', '09111111111')
        self.assertEqual(resp.data['status'], 'exact')
        self.assertEqual(resp.data['primary']['full_name'], 'زهرا اسلامیان')

    def test_phone_conflict_same_phone_different_name(self):
        create_customer(self.user, first_name='زهرا', last_name='اسلامیان', phone='09111111111')
        resp = self._post('مریم احمدی', '09111111111')
        self.assertEqual(resp.data['status'], 'phone_conflict')
        self.assertEqual(resp.data['primary']['phone'], '09111111111')

    def test_name_conflict_same_name_different_phone(self):
        create_customer(self.user, first_name='زهرا', last_name='اسلامیان', phone='09111111111')
        resp = self._post('زهرا اسلامیان', '09222222222')
        self.assertEqual(resp.data['status'], 'name_conflict')
        self.assertEqual(resp.data['primary']['full_name'], 'زهرا اسلامیان')

    def test_similar_name_fuzzy(self):
        create_customer(self.user, first_name='زهرا', last_name='اسلامیان', phone='09111111111')
        resp = self._post('زهرا اسلامی', '09333333333')
        self.assertEqual(resp.data['status'], 'similar')

    def test_phone_normalization_98_prefix(self):
        create_customer(self.user, first_name='زهرا', last_name='اسلامیان', phone='09111111111')
        resp = self._post('زهرا اسلامیان', '+989111111111')
        self.assertEqual(resp.data['status'], 'exact')

    def test_user_isolation(self):
        other = create_user(username='other', email='o@x.com', password='x12345678')
        create_customer(other, first_name='زهرا', last_name='اسلامیان', phone='09111111111')
        resp = self._post('زهرا اسلامیان', '09111111111')
        self.assertEqual(resp.data['status'], 'none')

    def test_empty_input(self):
        resp = self._post('', '')
        self.assertEqual(resp.data['status'], 'none')


class InvoiceDirectCustomerEntryTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.url = '/api/invoices/'

    def _payload(self, **cust):
        data = {
            'invoice_date': '2026-08-30',
            'invoice_tax_rate': 0,
            'discount_type': '',
            'discount_value': 0,
            'items': [{'product_name': 'کالا', 'quantity': 1, 'unit_price': 1000,
                       'tax_rate': 0, 'unit': 'عدد', 'order': 0}],
        }
        data.update(cust)
        return data

    def test_new_customer_auto_created_on_save(self):
        resp = self.client.post(self.url, self._payload(
            customer_name='زهرا اسلامیان', customer_phone='09111111111'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from customers.models import Customer
        c = Customer.objects.filter(user=self.user, phone='09111111111').first()
        self.assertIsNotNone(c)
        self.assertEqual(c.full_name, 'زهرا اسلامیان')
        inv_id = resp.data['id']
        detail = self.client.get(f'/api/invoices/{inv_id}/')
        self.assertEqual(detail.data['customer'], c.id)
        self.assertEqual(detail.data['customer_name'], 'زهرا اسلامیان')
        self.assertEqual(detail.data['customer_phone'], '09111111111')

    def test_exact_match_auto_links_existing_customer(self):
        existing = create_customer(self.user, first_name='زهرا', last_name='اسلامیان', phone='09111111111')
        resp = self.client.post(self.url, self._payload(
            customer_name='زهرا اسلامیان', customer_phone='09111111111'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from customers.models import Customer
        self.assertEqual(Customer.objects.filter(user=self.user).count(), 1)
        detail = self.client.get(f"/api/invoices/{resp.data['id']}/")
        self.assertEqual(detail.data['customer'], existing.id)

    def test_conflict_unresolved_creates_new_customer(self):
        """Popup declined/cancelled then saved -> typed info becomes a NEW customer; old untouched."""
        existing = create_customer(self.user, first_name='زهرا', last_name='اسلامیان', phone='09111111111')
        resp = self.client.post(self.url, self._payload(
            customer_name='مریم احمدی', customer_phone='09111111111'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from customers.models import Customer
        existing.refresh_from_db()
        self.assertEqual(existing.full_name, 'زهرا اسلامیان')  # untouched
        new_c = Customer.objects.filter(user=self.user, first_name='مریم').first()
        self.assertIsNotNone(new_c)
        detail = self.client.get(f"/api/invoices/{resp.data['id']}/")
        self.assertEqual(detail.data['customer'], new_c.id)
        self.assertEqual(detail.data['customer_name'], 'مریم احمدی')

    def test_update_existing_choice_updates_customer(self):
        existing = create_customer(self.user, first_name='زهرا', last_name='اسلامیان', phone='09111111111')
        resp = self.client.post(self.url, self._payload(
            customer_name='مریم احمدی', customer_phone='09111111111',
            customer_update_existing=True, customer=existing.id), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        existing.refresh_from_db()
        self.assertEqual(existing.full_name, 'مریم احمدی')  # updated per user choice
        from customers.models import Customer
        self.assertEqual(Customer.objects.filter(user=self.user).count(), 1)
        detail = self.client.get(f"/api/invoices/{resp.data['id']}/")
        self.assertEqual(detail.data['customer'], existing.id)
        self.assertEqual(detail.data['customer_name'], 'مریم احمدی')

    def test_create_new_choice_despite_exact_match(self):
        """Forcing 'new' with IDENTICAL data links to the existing customer
        (a literal duplicate is impossible by unique_together)."""
        existing = create_customer(self.user, first_name='زهرا', last_name='اسلامیان', phone='09111111111')
        resp = self.client.post(self.url, self._payload(
            customer_name='زهرا اسلامیان', customer_phone='09111111111',
            customer_create_new=True), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from customers.models import Customer
        self.assertEqual(Customer.objects.filter(user=self.user, first_name='زهرا').count(), 1)
        detail = self.client.get(f"/api/invoices/{resp.data['id']}/")
        self.assertEqual(detail.data['customer'], existing.id)

    def test_create_new_choice_with_conflicting_data_creates_customer(self):
        """Forcing 'new' with a phone CONFLICT really creates a new customer."""
        create_customer(self.user, first_name='زهرا', last_name='اسلامیان', phone='09111111111')
        resp = self.client.post(self.url, self._payload(
            customer_name='مریم احمدی', customer_phone='09111111111',
            customer_create_new=True), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from customers.models import Customer
        self.assertEqual(Customer.objects.filter(user=self.user).count(), 2)
        detail = self.client.get(f"/api/invoices/{resp.data['id']}/")
        self.assertEqual(detail.data['customer_name'], 'مریم احمدی')

    def test_classic_fk_flow_still_works(self):
        existing = create_customer(self.user, first_name='زهرا', last_name='اسلامیان', phone='09111111111')
        resp = self.client.post(self.url, self._payload(customer=existing.id), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from customers.models import Customer
        self.assertEqual(Customer.objects.filter(user=self.user).count(), 1)
        detail = self.client.get(f"/api/invoices/{resp.data['id']}/")
        self.assertEqual(detail.data['customer_name'], 'زهرا اسلامیان')

    def test_blank_customer_ok(self):
        resp = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_edit_invoice_with_direct_entry_relinks(self):
        inv = create_invoice(self.user, customer=create_customer(self.user, first_name='قدیم', last_name='قدیمی', phone='09000000000'))
        resp = self.client.patch(f'/api/invoices/{inv.id}/', self._payload(
            customer_name='زهرا اسلامیان', customer_phone='09111111111'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        detail = self.client.get(f'/api/invoices/{inv.id}/')
        self.assertEqual(detail.data['customer_name'], 'زهرا اسلامیان')
        self.assertEqual(detail.data['customer_phone'], '09111111111')
        from customers.models import Customer
        self.assertTrue(Customer.objects.filter(user=self.user, phone='09111111111').exists())
