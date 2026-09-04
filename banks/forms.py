from django import forms
from .models import BankAccount


class BankAccountForm(forms.ModelForm):
    """Bank name is free text; the view get_or_create()s the Bank row."""

    bank_name = forms.CharField(
        label='نام بانک',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'list': 'bank-names',
            'placeholder': 'نام بانک را بنویسید…',
            'autocomplete': 'off',
        }),
    )

    class Meta:
        model = BankAccount
        fields = ['card_number', 'iban', 'account_holder', 'account_number', 'is_default']
        labels = {
            'card_number': 'شماره کارت',
            'iban': 'شماره شبا',
            'account_holder': 'صاحب حساب',
            'account_number': 'شماره حساب (اختیاری)',
            'is_default': 'حساب پیش‌فرض',
        }
        widgets = {
            'card_number': forms.TextInput(attrs={
                'class': 'form-input', 'dir': 'ltr', 'style': 'text-align:left;',
                'placeholder': '6037997512345678', 'inputmode': 'numeric', 'maxlength': '16',
            }),
            'iban': forms.TextInput(attrs={
                'class': 'form-input', 'dir': 'ltr', 'style': 'text-align:left;',
                'placeholder': 'IR……', 'maxlength': '30',
            }),
            'account_holder': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'نام و نام خانوادگی صاحب حساب',
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-input', 'dir': 'ltr', 'style': 'text-align:left;',
            }),
            'is_default': forms.CheckboxInput(),
        }
