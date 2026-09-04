from decimal import Decimal
from rest_framework import serializers
from .models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    unit_price = serializers.DecimalField(max_digits=15, decimal_places=0, min_value=Decimal('1'))

    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'product', 'product_name', 'quantity', 'unit_price',
            'tax_rate', 'total_price', 'tax_amount', 'unit', 'frequency', 'order'
        ]
        read_only_fields = ['total_price', 'tax_amount']

    def create(self, validated_data):
        validated_data['total_price'] = validated_data['quantity'] * validated_data['unit_price']
        if validated_data.get('tax_rate', 0) > 0:
            validated_data['tax_amount'] = (
                validated_data['total_price'] * validated_data['tax_rate'] / 100
            ).quantize(1)
        else:
            validated_data['tax_amount'] = 0
        return super().create(validated_data)


class InvoiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views.
    customer_display_name: live customer name when the invoice is linked to
    a customer record — reflects renames instantly in the list."""
    item_count = serializers.SerializerMethodField()
    customer_display_name = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'customer_name', 'customer_phone',
            'customer_display_name',
            'invoice_date', 'final_amount', 'is_paid', 'item_count',
            'created_at'
        ]

    def get_item_count(self, obj):
        return obj.items.count() if hasattr(obj, 'items') else 0

    def get_customer_display_name(self, obj):
        if obj.customer_id and obj.customer:
            return obj.customer.full_name
        return obj.customer_name


class InvoiceDetailSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    customer_display_name = serializers.SerializerMethodField()
    customer_name_changed = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number',
            'customer', 'customer_name', 'customer_phone', 'customer_address',
            'customer_display_name', 'customer_name_changed',
            'seller_name', 'seller_business', 'seller_address', 'seller_phone',
            'invoice_date', 'due_date',
            'subtotal', 'item_taxes_total', 'invoice_tax_rate', 'invoice_tax_amount',
            'discount_type', 'discount_value', 'discount_amount', 'final_amount',
            'bank_name', 'card_number', 'iban', 'account_holder',
            'notes', 'seller_signature', 'customer_signature',
            'is_paid', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'subtotal', 'item_taxes_total', 'invoice_tax_amount',
            'discount_amount', 'final_amount', 'created_at', 'updated_at'
        ]

    def get_customer_display_name(self, obj):
        """Live customer name — instantly reflects renames."""
        if obj.customer_id and obj.customer:
            return obj.customer.full_name
        return obj.customer_name

    def get_customer_name_changed(self, obj):
        """True when the live customer name differs from the invoice snapshot."""
        if obj.customer_id and obj.customer:
            return obj.customer.full_name != (obj.customer_name or '')
        return False


class InvoiceCreateSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)
    # IntegerField(required=False) rejects explicit null; allow_null fixes the
    # browser flow which always sends bank_account (null when nothing selected).
    bank_account = serializers.IntegerField(required=False, allow_null=True)
    # Manual bank entry (optional) — used as snapshot when no bank_account is selected
    bank_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    card_number = serializers.CharField(required=False, allow_blank=True, max_length=20)
    iban = serializers.CharField(required=False, allow_blank=True, max_length=30)
    account_holder = serializers.CharField(required=False, allow_blank=True, max_length=200)
    # Smart customer: direct entry in the invoice form
    customer_name = serializers.CharField(required=False, allow_blank=True, max_length=200, write_only=True)
    customer_phone = serializers.CharField(required=False, allow_blank=True, max_length=15, write_only=True)
    # Address typed in the invoice form. Handling mirrors name/phone: if the
    # user explicitly opts to update the customer (customer_update_address),
    # the stored customer address is overwritten; otherwise the typed value is
    # only written to this invoice's snapshot (customer_address), never to the
    # Customer record — existing data is never clobbered silently.
    customer_address_input = serializers.CharField(required=False, allow_blank=True, write_only=True)
    customer_update_address = serializers.BooleanField(required=False, write_only=True)
    # Explicit user decisions from the conflict popup:
    #  - create_new: always create a fresh customer from the typed info
    #  - update_existing: link to existing customer_id and overwrite its name/phone
    customer_create_new = serializers.BooleanField(required=False, write_only=True)
    customer_update_existing = serializers.BooleanField(required=False, write_only=True)

    def _resolve_customer(self, user, attrs):
        """Resolve the customer FK from direct entry.

        Returns (customer_or_None, typed_name, typed_phone).
        Priority: explicit customer FK > create_new flag > auto-link exact
        match > silent auto-create. Conflicts must be resolved by the user
        via the popup BEFORE save; if they reach here unresolved, fall back
        to creating a new customer so no typed data is lost.
        """
        from customers.models import Customer
        from customers.matching import find_customer_match, parse_full_name

        customer = attrs.pop('customer', None)
        name = (self._typed_name or '').strip()
        phone = (self._typed_phone or '').strip()
        address_input = self._typed_address or ''
        update_address = self._update_address
        create_new = self._create_new
        update_existing = self._update_existing
        if customer and not name and not phone:
            # Classic flow: picked from list. Apply address if the user
            # chose to persist it to the customer record.
            self._apply_address(customer.id, address_input, update_address)
            return customer, '', ''

        if not name and not phone:
            return None, '', ''

        match = find_customer_match(user, name, phone)
        primary = match['primary']
        status = match['status']

        if status == 'exact' and primary and not create_new:
            self._apply_address(primary['id'], address_input, update_address)
            return Customer.objects.get(pk=primary['id']), name, phone

        if update_existing and primary and status in ('exact', 'phone_conflict', 'name_conflict', 'similar'):
            c = Customer.objects.get(pk=primary['id'])
            if name:
                first, last = parse_full_name(name)
                c.first_name, c.last_name = first, last
            if phone:
                c.phone = phone
            if address_input:
                c.address = address_input  # explicit user choice from popup
            c.save()
            return c, name, phone

        # New customer (no match, popup "new" choice, or unresolved conflict).
        # get_or_create guards the unique_together: if the user forces "new"
        # but the data is identical to an existing customer, we link instead
        # of crashing — a literal duplicate is impossible.
        first, last = parse_full_name(name)
        c, _created = Customer.objects.get_or_create(
            user=user, first_name=first, last_name=last, phone=phone,
            defaults={'address': address_input},
        )
        if address_input and update_address:
            c.address = address_input
            c.save()
        return c, name, phone

    def _apply_address(self, customer_id, address_input, update_address):
        """For exact-match reuse: persist the typed address to the Customer
        record ONLY when the user explicitly chose to update it."""
        if not address_input or not update_address:
            return
        from customers.models import Customer
        Customer.objects.filter(pk=customer_id).update(address=address_input)

    def _auto_save_product(self, user, item_data):
        """Auto-register a product typed in the invoice that has no catalog
        match. Never overwrites an existing product; price is appended to
        PriceHistory only when it differs from the latest recorded price."""
        from products.models import Product, PriceHistory
        name = (item_data.get('product_name') or '').strip()
        if not name:
            return None
        product = Product.objects.filter(user=user, name=name).first()
        if product is None:
            product = Product.objects.create(
                user=user, name=name, unit=item_data.get('unit') or 'عدد'
            )
        price = item_data.get('unit_price')
        if price is not None and price != product.latest_price:
            PriceHistory.objects.create(product=product, price=price)
        return product

    def _auto_save_bank_account(self, user, bank_snapshot):
        """Auto-register the bank account manually typed in the invoice.
        Matches on card_number (unique in practice); never overwrites."""
        from banks.models import Bank, BankAccount
        card = (bank_snapshot.get('card_number') or '').strip()
        if not card:
            return None
        existing = BankAccount.objects.filter(user=user, card_number=card).first()
        if existing:
            return existing
        bank_name = (bank_snapshot.get('bank_name') or '').strip()
        bank, _ = Bank.objects.get_or_create(name=bank_name)
        return BankAccount.objects.create(
            user=user, bank=bank,
            card_number=card,
            iban=(bank_snapshot.get('iban') or '').strip(),
            account_holder=(bank_snapshot.get('account_holder') or user.get_full_name() or user.username).strip(),
        )

    def validate(self, attrs):
        """Bank rule + pop write-only customer fields so they are available
        in create/update regardless of which resolution path runs."""
        # Bank: any of card/holder/iban -> bank_name required
        manual_fields = ['card_number', 'iban', 'account_holder']
        has_manual_detail = any(attrs.get(f) and attrs[f].strip() for f in manual_fields)
        bank_name = (attrs.get('bank_name') or '').strip()
        if has_manual_detail and not bank_name and not attrs.get('bank_account'):
            raise serializers.ValidationError({
                'bank_name': 'با وارد شدن شماره کارت، صاحب حساب یا شماره شبا، نام بانک الزامی است.'
            })
        # Stash write-only customer inputs as instance state so create() and
        # update() both see them even when the classic FK path runs.
        self._typed_name = attrs.pop('customer_name', '') or ''
        self._typed_phone = attrs.pop('customer_phone', '') or ''
        self._typed_address = (attrs.pop('customer_address_input', '') or '').strip()
        self._update_address = attrs.pop('customer_update_address', False)
        self._create_new = attrs.pop('customer_create_new', False)
        self._update_existing = attrs.pop('customer_update_existing', False)
        return attrs

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError('فاکتور باید حداقل یک قلم داشته باشد.')
        return items

    class Meta:
        model = Invoice
        fields = [
            'id', 'customer', 'invoice_date', 'due_date',
            'invoice_tax_rate', 'discount_type', 'discount_value',
            'bank_account', 'bank_name', 'card_number', 'iban', 'account_holder',
            'customer_name', 'customer_phone', 'customer_address_input', 'customer_update_address',
            'customer_create_new', 'customer_update_existing',
            'notes', 'items'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        bank_account_id = validated_data.pop('bank_account', None)
        manual_bank = {
            f: validated_data.pop(f, '')
            for f in ('bank_name', 'card_number', 'iban', 'account_holder')
        }

        user = self.context['request'].user
        from .models import InvoiceNumberSequence
        validated_data['user'] = user
        validated_data['invoice_number'] = InvoiceNumberSequence.get_next_number(user)

        # Smart customer: direct entry / auto-create / auto-link
        customer, manual_customer_name, manual_customer_phone = self._resolve_customer(user, validated_data)
        validated_data['customer'] = customer

        # Snapshot customer info — resolved customer wins; else typed values
        customer = validated_data.get('customer')
        typed_address = getattr(self, '_typed_address', '') or ''
        if customer:
            validated_data['customer_name'] = customer.full_name
            validated_data['customer_phone'] = customer.phone
            # Address snapshot: persisted update already happened in
            # _resolve_customer; snapshot now reflects whatever the customer
            # holds (updated or original) unless user typed an invoice-only
            # address, which always wins for THIS invoice.
            validated_data['customer_address'] = typed_address or customer.address
        elif manual_customer_name or manual_customer_phone:
            validated_data['customer_name'] = manual_customer_name
            validated_data['customer_phone'] = manual_customer_phone
            if typed_address:
                validated_data['customer_address'] = typed_address

        # Snapshot seller info
        profile = getattr(user, 'seller_profile', None)
        if profile:
            validated_data['seller_name'] = user.get_full_name()
            validated_data['seller_business'] = profile.business_name
            validated_data['seller_address'] = profile.address
            validated_data['seller_phone'] = profile.phone

        # Snapshot bank info — saved account takes priority, else manual entry
        if bank_account_id:
            from banks.models import BankAccount
            try:
                ba = BankAccount.objects.get(id=bank_account_id, user=user)
                validated_data['bank_name'] = ba.bank.name
                validated_data['card_number'] = ba.card_number
                validated_data['iban'] = ba.iban
                validated_data['account_holder'] = ba.account_holder
            except BankAccount.DoesNotExist:
                pass
        else:
            validated_data['bank_name'] = (manual_bank['bank_name'] or '').strip()
            validated_data['card_number'] = (manual_bank['card_number'] or '').strip()
            validated_data['iban'] = (manual_bank['iban'] or '').strip()
            validated_data['account_holder'] = (manual_bank['account_holder'] or '').strip()

        # Save invoice
        invoice = Invoice.objects.create(**validated_data)

        # Auto-save manually typed bank info as a reusable account
        if not bank_account_id and (manual_bank.get('card_number') or '').strip():
            self._auto_save_bank_account(user, manual_bank)

        # Create items (auto-saving products typed without a catalog match)
        for idx, item_data in enumerate(items_data):
            product = item_data.get('product')
            if product:
                item_data['product_name'] = product.name
                item_data['unit'] = product.unit
            else:
                product = self._auto_save_product(user, item_data)
                if product:
                    item_data['product'] = product
                    item_data['unit'] = product.unit
            item_data['order'] = idx
            InvoiceItem.objects.create(invoice=invoice, **item_data)

        # Calculate and save totals
        invoice.calculate_totals()
        invoice.save()

        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        bank_account_id = validated_data.pop('bank_account', None)
        manual_bank = {
            f: validated_data.pop(f, None)
            for f in ('bank_name', 'card_number', 'iban', 'account_holder')
        }

        # Smart customer: direct entry / auto-create / auto-link
        customer, manual_customer_name, manual_customer_phone = self._resolve_customer(
            instance.user, validated_data
        )
        if customer is not None:
            validated_data['customer'] = customer

        # Update bank snapshot — saved account takes priority, else manual entry
        if bank_account_id:
            from banks.models import BankAccount
            try:
                ba = BankAccount.objects.get(id=bank_account_id, user=instance.user)
                instance.bank_name = ba.bank.name
                instance.card_number = ba.card_number
                instance.iban = ba.iban
                instance.account_holder = ba.account_holder
            except BankAccount.DoesNotExist:
                pass
        else:
            for f, v in manual_bank.items():
                if v is not None:
                    setattr(instance, f, v.strip())

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Refresh snapshot if the customer was resolved/changed via direct entry
        typed_address = getattr(self, '_typed_address', '') or ''
        if validated_data.get('customer'):
            instance.customer_name = instance.customer.full_name
            instance.customer_phone = instance.customer.phone
            instance.customer_address = typed_address or instance.customer.address
            instance.save()
        elif (manual_customer_name or manual_customer_phone or typed_address) and not instance.customer:
            if manual_customer_name:
                instance.customer_name = manual_customer_name
            if manual_customer_phone:
                instance.customer_phone = manual_customer_phone
            if typed_address:
                instance.customer_address = typed_address
            instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for idx, item_data in enumerate(items_data):
                product = item_data.get('product')
                if product:
                    item_data['product_name'] = product.name
                    item_data['unit'] = product.unit
                item_data['order'] = idx
                InvoiceItem.objects.create(invoice=instance, **item_data)

        instance.calculate_totals()
        instance.save()
        return instance
