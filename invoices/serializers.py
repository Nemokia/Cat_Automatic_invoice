from rest_framework import serializers
from .models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'product', 'product_name', 'quantity', 'unit_price',
            'tax_rate', 'total_price', 'tax_amount', 'unit', 'order'
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
    """Lightweight serializer for list views."""
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'customer_name', 'customer_phone',
            'invoice_date', 'final_amount', 'is_paid', 'item_count',
            'created_at'
        ]

    def get_item_count(self, obj):
        return obj.items.count() if hasattr(obj, 'items') else 0


class InvoiceDetailSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number',
            'customer', 'customer_name', 'customer_phone', 'customer_address',
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


class InvoiceCreateSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)

    class Meta:
        model = Invoice
        fields = [
            'customer', 'invoice_date', 'due_date',
            'invoice_tax_rate', 'discount_type', 'discount_value',
            'bank_account', 'notes', 'items'
        ]
        extra_kwargs = {
            'bank_account': {'required': False, 'write_only': True}
        }

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        bank_account_id = validated_data.pop('bank_account', None)

        user = self.context['request'].user
        from .models import InvoiceNumberSequence
        validated_data['user'] = user
        validated_data['invoice_number'] = InvoiceNumberSequence.get_next_number(user)

        # Snapshot customer info
        customer = validated_data.get('customer')
        if customer:
            validated_data['customer_name'] = customer.full_name
            validated_data['customer_phone'] = customer.phone
            validated_data['customer_address'] = customer.address

        # Snapshot seller info
        profile = getattr(user, 'seller_profile', None)
        if profile:
            validated_data['seller_name'] = user.get_full_name()
            validated_data['seller_business'] = profile.business_name
            validated_data['seller_address'] = profile.address
            validated_data['seller_phone'] = profile.phone

        # Snapshot bank info
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

        # Save invoice
        invoice = Invoice.objects.create(**validated_data)

        # Create items
        for idx, item_data in enumerate(items_data):
            product = item_data.get('product')
            if product:
                item_data['product_name'] = product.name
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

        # Update bank snapshot
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

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
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
