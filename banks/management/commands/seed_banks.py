from django.core.management.base import BaseCommand
from banks.models import Bank


class Command(BaseCommand):
    help = 'Seed initial Iranian bank data'

    def handle(self, *args, **options):
        banks = [
            'بانک ملی', 'بانک صادرات', 'بانک تجارت', 'بانک ملت',
            'بانک رفاه', 'بانک کشاورزی', 'بانک مسکن', 'بانک سپه',
            'بانک پاسارگاد', 'بانک سامان', 'بانک پارسیان',
            'بانک کارآفرین', 'بانک اقتصاد نوین', 'بانک شهر',
            'بانک دی', 'بانک آینده', 'بانک سرمایه',
            'بانک خاورمیانه', 'پست بانک', 'بانک توسعه تعاون',
        ]
        created = 0
        for name in banks:
            _, was_created = Bank.objects.get_or_create(name=name)
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(f'Seeded {created} banks ({len(banks)} total)')
        )
