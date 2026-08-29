from rest_framework import serializers
from .models import Bank, BankAccount


class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = ['id', 'name', 'code']


class BankAccountSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank.name', read_only=True)

    class Meta:
        model = BankAccount
        fields = [
            'id', 'bank', 'bank_name', 'card_number', 'iban',
            'account_holder', 'account_number', 'is_default',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class BankAccountSelectSerializer(serializers.ModelSerializer):
    """Lightweight for dropdowns."""
    bank_name = serializers.CharField(source='bank.name', read_only=True)

    class Meta:
        model = BankAccount
        fields = ['id', 'bank_name', 'card_number', 'iban', 'account_holder', 'is_default']
