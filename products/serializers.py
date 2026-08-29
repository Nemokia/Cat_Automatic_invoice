from rest_framework import serializers
from .models import Product, PriceHistory


class PriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceHistory
        fields = ['id', 'price', 'date']
        read_only_fields = ['date']


class ProductSerializer(serializers.ModelSerializer):
    latest_price = serializers.ReadOnlyField()
    latest_price_date = serializers.ReadOnlyField()
    total_sold = serializers.ReadOnlyField()
    total_revenue = serializers.ReadOnlyField()
    price_history = PriceHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'unit', 'frequency', 'description', 'latest_price',
            'latest_price_date', 'total_sold', 'total_revenue',
            'price_history', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ProductAutocompleteSerializer(serializers.ModelSerializer):
    """Lightweight for autocomplete."""
    latest_price = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'unit', 'latest_price']
