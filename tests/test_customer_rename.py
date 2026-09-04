"""Customer rename semantics.

When the user confirms a rename (update_existing flow), old invoices keep
their original snapshot (zero data loss) but every read path shows the
live name, and the detail endpoint flags the change so the UI can inform
the user. Invoices of unlinked customers never drift.
"""
from rest_framework import status
from rest_framework.test import APITestCase

from .factories import create_user, create_customer, create_invoice


def _item(name='کالا', price=1000):
    return {'product_name': name, 'quantity': 1, 'unit_price': price,
            'tax_rate': 0, 'unit': 'عدد', 'order': 0}


class CustomerRenamePropagationTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_authenticate(user=self.user)
        self.url = '/api/invoices/'

    def _create_with_update_existing(self, customer, new_name):
        """Simulate the confirmed-rename flow on an existing invoice."""
        inv = create_invoice(self.user, customer=customer)
        resp = self.client.patch(
            f'/api/invoices/{inv.id}/',
            {
                'customer': customer.id,
                'customer_name': new_name,
                'customer_phone': customer.phone,
                'customer_update_existing': True,
                'invoice_date': '2026-08-30',
                'items': [_item()],
            }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        return inv

    def test_renamed_customer_old_invoices_show_live_name_in_list(self):
        """هیدی کیا -> هیدی کیانژاد: old invoices list the new name."""
        c = create_customer(self.user, first_name='هیدی', last_name='کیا',
                            phone='09335864300')
        inv1 = create_invoice(self.user, customer=c)
        inv2 = create_invoice(self.user, customer=c)
        # snapshot names
        self.assertEqual(inv1.customer_name, 'هیدی کیا')
        self.assertEqual(inv2.customer_name, 'هیدی کیا')

        self._create_with_update_existing(c, 'هیدی کیانژاد')

        c.refresh_from_db()
        self.assertEqual(c.full_name, 'هیدی کیانژاد')

        lst = self.client.get('/api/invoices/').data
        if 'results' in lst:
            lst = lst['results']
        by_id = {row['id']: row for row in lst}
        # old invoices show the NEW live name
        self.assertEqual(by_id[inv1.id]['customer_display_name'], 'هیدی کیانژاد')
        self.assertEqual(by_id[inv2.id]['customer_display_name'], 'هیدی کیانژاد')
        # snapshot untouched
        self.assertEqual(by_id[inv1.id]['customer_name'], 'هیدی کیا')

    def test_detail_flags_name_change(self):
        """customer_name_changed=True + live name in detail after rename."""
        c = create_customer(self.user, first_name='هیدی', last_name='کیا',
                            phone='09335864300')
        inv = create_invoice(self.user, customer=c)
        detail = self.client.get(f'/api/invoices/{inv.id}/').data
        self.assertFalse(detail['customer_name_changed'])
        self.assertEqual(detail['customer_display_name'], 'هیدی کیا')

        self._create_with_update_existing(c, 'هیدی کیانژاد')

        detail = self.client.get(f'/api/invoices/{inv.id}/').data
        self.assertTrue(detail['customer_name_changed'])
        self.assertEqual(detail['customer_display_name'], 'هیدی کیانژاد')
        # DB snapshot preserved
        self.assertEqual(detail['customer_name'], 'هیدی کیا')

    def test_no_false_flag_without_rename(self):
        c = create_customer(self.user, first_name='هیدی', last_name='کیا',
                            phone='09335864300')
        inv = create_invoice(self.user, customer=c)
        detail = self.client.get(f'/api/invoices/{inv.id}/').data
        self.assertFalse(detail['customer_name_changed'])

    def test_unlinked_invoice_never_drifts(self):
        """Invoice without customer FK keeps its snapshot name forever."""
        c = create_customer(self.user, first_name='مشتری', last_name='قدیمی')
        inv = create_invoice(self.user, customer=c)
        # Detach: simulate an invoice whose customer record was deleted
        inv.customer = None
        inv.save()
        detail = self.client.get(f'/api/invoices/{inv.id}/').data
        self.assertEqual(detail['customer_name'], 'مشتری قدیمی')
        self.assertEqual(detail['customer_display_name'], 'مشتری قدیمی')
        self.assertFalse(detail['customer_name_changed'])
        lst = self.client.get('/api/invoices/').data
        if 'results' in lst:
            lst = lst['results']
        row = next(r for r in lst if r['id'] == inv.id)
        self.assertEqual(row['customer_display_name'], 'مشتری قدیمی')
