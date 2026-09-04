from rest_framework import serializers
from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    total_purchases = serializers.ReadOnlyField()
    invoice_count = serializers.ReadOnlyField()

    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'phone',
            'address', 'national_id', 'total_purchases', 'invoice_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        user = self.context['request'].user
        phone = data.get('phone', getattr(self.instance, 'phone', ''))
        first_name = data.get('first_name', getattr(self.instance, 'first_name', ''))
        last_name = data.get('last_name', getattr(self.instance, 'last_name', ''))
        existing = Customer.objects.filter(
            user=user, phone=phone, first_name=first_name, last_name=last_name
        )
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError({'phone': 'مشتری با این مشخصات قبلاً ثبت شده است.'})
        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class CustomerAutocompleteSerializer(serializers.ModelSerializer):
    """Lightweight serializer for autocomplete."""
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Customer
        fields = ['id', 'first_name', 'last_name', 'full_name', 'phone', 'address']
