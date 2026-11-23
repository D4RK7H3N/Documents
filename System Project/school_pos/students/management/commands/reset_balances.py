from django.core.management.base import BaseCommand
from students.models import Student

class Command(BaseCommand):
    help = "Reset all student tuition balances to zero"

    def handle(self, *args, **kwargs):
        updated = Student.objects.update(tuition_balance=0)
        self.stdout.write(self.style.SUCCESS(f"Successfully reset {updated} tuition balances to ₱0.00"))
