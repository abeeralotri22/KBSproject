from django.core.management.base import BaseCommand
from api_app.models import CustomUser

class Command(BaseCommand):
    help = 'Seeds the database with an initial Admin user'

    def handle(self, *args, **kwargs):
        admin_email = "admin@admin.com"
        admin_password = "admin"
        if CustomUser.objects.filter(email=admin_email).exists():
            self.stdout.write(self.style.WARNING(f'Admin "{admin_email}" already exists. No action taken.'))
            return

        CustomUser.objects.create_superuser(
            username=admin_email,
            email=admin_email,
            password=admin_password,
            role='admin'
        )
        self.stdout.write(self.style.SUCCESS(f'SUCCESS: Admin user "{admin_email}" created successfully!'))