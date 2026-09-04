from rest_framework import serializers
from .models import Bank, BankAccount


class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = ['id', 'name', 'code']


class BankAccountSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank.name', read_only=True)
    # Optional: may be provided via PK or via bank_name_input (typed name)
    bank = serializers.PrimaryKeyRelatedField(queryset=Bank.objects.all(), required=False)
    # Write-only: allows creating/updating an account by typing a bank name.
    # If the name doesn't exist, a new Bank record is created (custom banks allowed).
    bank_name_input = serializers.CharField(write_only=True, required=False, max_length=100)

    class Meta:
        model = BankAccount
        fields = [
            'id', 'bank', 'bank_name', 'bank_name_input', 'card_number', 'iban',
            'account_holder', 'account_number', 'is_default',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        """bank (FK) or bank_name_input (text) must resolve to a bank.
        On partial updates, the existing instance's bank counts too."""
        bank_name_input = (attrs.pop('bank_name_input', None) or '').strip()
        if bank_name_input:
            bank, _ = Bank.objects.get_or_create(name=bank_name_input)
            attrs['bank'] = bank
        elif not attrs.get('bank'):
            has_bank = getattr(self.instance, 'bank_id', None) is not None
            if not has_bank:
                raise serializers.ValidationError({
                    'bank_name': 'نام بانک الزامی است.'
                })
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class BankAccountSelectSerializer(serializers.ModelSerializer):
    """Lightweight for dropdowns."""
    bank_name = serializers.CharField(source='bank.name', read_only=True)

    class Meta:
        model = BankAccount
        fields = ['id', 'bank_name', 'card_number', 'iban', 'account_holder', 'account_number', 'is_default']
