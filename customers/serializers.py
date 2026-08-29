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

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class CustomerAutocompleteSerializer(serializers.ModelSerializer):
    """Lightweight serializer for autocomplete."""
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Customer
        fields = ['id', 'first_name', 'last_name', 'full_name', 'phone']
