"""Test smart customer integration in the invoice form.
Covers the frontend view POST handlers for customer_update_existing,
customer_create_new, auto-link exact match, and new customer creation.
Also covers the ?share=1 redirect flow.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from customers.models import Customer
from invoices.models import Invoice

User = get_user_model()


class TestSmartCustomer22(TestCase):
    """Client tests for smart customer entry + share flow."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='smart22', password='testpass123', email='s22@t.com'
        )
        self.client = Client()
        self.client.login(username='smart22', password='testpass123')
        self.customer = Customer.objects.create(
            user=self.user, first_name='زهرا', last_name='اسلامیان',
            phone='09111111111', address='مازندران'
        )
        self.base_data = {
            'invoice_date': '2026-09-01',
            'invoice_tax_rate': '0',
            'discount_type': '',
            'discount_value': '0',
            'item_product_name[]': ['کالای تست'],
            'item_quantity[]': ['1'],
            'item_unit_price[]': ['10000'],
            'item_tax_rate[]': ['0'],
            'item_unit[]': ['عدد'],
            'item_frequency[]': [''],
        }

    def test_check_similar_exact_match(self):
        resp = self.client.get('/search/customers/check-similar/', {
            'name': 'زهرا اسلامیان', 'phone': '09111111111'
        })
        data = resp.json()
        self.assertEqual(data['status'], 'exact')
        self.assertEqual(data['primary']['full_name'], 'زهرا اسلامیان')

    def test_check_similar_phone_conflict(self):
        resp = self.client.get('/search/customers/check-similar/', {
            'name': 'مریم احمدی', 'phone': '09111111111'
        })
        self.assertEqual(resp.json()['status'], 'phone_conflict')

    def test_check_similar_name_conflict(self):
        resp = self.client.get('/search/customers/check-similar/', {
            'name': 'زهرا اسلامیان', 'phone': '09222222222'
        })
        self.assertEqual(resp.json()['status'], 'name_conflict')

    def test_check_similar_no_match(self):
        resp = self.client.get('/search/customers/check-similar/', {
            'name': 'علی نو', 'phone': '09999999999'
        })
        self.assertEqual(resp.json()['status'], 'none')

    def test_update_existing_renames_customer(self):
        resp = self.client.post('/invoices/new/', {
            **self.base_data,
            'customer': str(self.customer.id),
            'customer_name': 'مریم احمدی',
            'customer_phone': '09111111111',
            'customer_update_existing': '1',
            'customer_create_new': '',
        })
        self.assertEqual(resp.status_code, 302)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.full_name, 'مریم احمدی')

    def test_create_new_forces_new_customer(self):
        c_before = Customer.objects.filter(user=self.user).count()
        resp = self.client.post('/invoices/new/', {
            **self.base_data,
            'customer': '',
            'customer_name': 'نوید جدید',
            'customer_phone': '09888888888',
            'customer_address': '',
            'customer_update_existing': '',
            'customer_create_new': '1',
        })
        self.assertEqual(resp.status_code, 302)
        c_after = Customer.objects.filter(user=self.user).count()
        self.assertGreater(c_after, c_before)

    def test_auto_link_exact_match(self):
        resp = self.client.post('/invoices/new/', {
            **self.base_data,
            'customer': '',
            'customer_name': 'زهرا اسلامیان',
            'customer_phone': '09111111111',
            'customer_address': '',
            'customer_update_existing': '',
            'customer_create_new': '',
        })
        self.assertEqual(resp.status_code, 302)
        inv = Invoice.objects.filter(user=self.user).order_by('-id').first()
        self.assertEqual(inv.customer_id, self.customer.id)

    def test_new_customer_no_match_creates(self):
        c_before = Customer.objects.filter(user=self.user).count()
        resp = self.client.post('/invoices/new/', {
            **self.base_data,
            'customer': '',
            'customer_name': 'someone new',
            'customer_phone': '09777777777',
            'customer_address': '',
            'customer_update_existing': '',
            'customer_create_new': '',
        })
        self.assertEqual(resp.status_code, 302)
        c_after = Customer.objects.filter(user=self.user).count()
        self.assertGreater(c_after, c_before)

    def test_share_ajax_new_invoice(self):
        """AJAX save&share: stays on page, returns JSON with pdf_url."""
        resp = self.client.post('/invoices/new/?share=1', {
            **self.base_data,
            'customer_name': 'مشتری تست',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertIn('pdf_url', data)
        self.assertIn(str(data['invoice_id']), data['pdf_url'])

    def test_share_redirect_new_invoice(self):
        """Non-AJAX ?share=1 keeps legacy redirect behaviour."""
        resp = self.client.post('/invoices/new/?share=1', {
            **self.base_data,
            'customer_name': 'مشتری تست',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn('share=1', resp.url)

    def test_share_redirect_edit_invoice(self):
        inv = Invoice.objects.create(
            user=self.user, invoice_number='INV-TEST-001',
            customer_name='تست', customer_phone='09000000000',
            invoice_date='2026-09-01', final_amount=0,
        )
        resp = self.client.post(f'/invoices/{inv.id}/edit/?share=1', {
            **self.base_data,
            'customer': '',
            'customer_name': 'تست',
            'customer_phone': '09000000000',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertIn(str(inv.id), data['pdf_url'])

    def test_detail_page_share_modal(self):
        inv = Invoice.objects.create(
            user=self.user, invoice_number='INV-TEST-002',
            customer_name='تست', customer_phone='09000000000',
            invoice_date='2026-09-01', final_amount=0,
        )
        resp = self.client.get(f'/invoices/{inv.id}/?share=1')
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('shareModal', html)
        self.assertIn('shareWhatsApp', html)
        self.assertIn('shareTelegram', html)

    def test_create_form_has_share_button(self):
        resp = self.client.get('/invoices/new/')
        html = resp.content.decode()
        self.assertIn('📤 ذخیره و ارسال', html)
        self.assertIn('?share=1', html)
        self.assertIn('data-share="1"', html)

    def test_edit_form_has_share_button(self):
        inv = Invoice.objects.create(
            user=self.user, invoice_number='INV-TEST-003',
            customer_name='تست', customer_phone='09000000000',
            invoice_date='2026-09-01', final_amount=0,
        )
        resp = self.client.get(f'/invoices/{inv.id}/edit/')
        html = resp.content.decode()
        self.assertIn('📤 به‌روزرسانی و ارسال', html)
        self.assertIn('?share=1', html)
        self.assertIn('data-share="1"', html)

    def test_share_validation_error_returns_json(self):
        """AJAX save&share with missing item names → 400 JSON, no redirect."""
        resp = self.client.post('/invoices/new/?share=1', {
            'invoice_date': '2026-09-01',
            'customer_name': 'بدون قلم',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()['ok'])

    def test_invoice_pdf_session_auth(self):
        """Session-auth PDF endpoint used by save&share returns real PDF."""
        inv = Invoice.objects.create(
            user=self.user, invoice_number='INV-TEST-004',
            customer_name='تست', customer_phone='09000000000',
            invoice_date='2026-09-01', final_amount=0,
        )
        resp = self.client.get(f'/invoices/{inv.id}/pdf/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content[:4] == b'%PDF')
