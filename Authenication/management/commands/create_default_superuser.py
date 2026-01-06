from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Creates a default superuser non-interactively'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        email = 'kenjicladia@gmail.com'
        password = '@kenji001'
        username = 'kenji'  # Username is required since it's in REQUIRED_FIELDS
        
        if not User.objects.filter(email=email).exists():
            # Create superuser with all required fields for your custom model
            User.objects.create_superuser(
                email=email,
                password=password,
                username=username,
                first_name='Kenji',  # Optional but good to set
                last_name='Admin',   # Optional but good to set
                user_type='admin',   # Set user_type to admin
                is_staff=True,       # Required for admin access
                is_superuser=True,   # Superuser flag
                is_active=True       # Ensure active
            )
            self.stdout.write(self.style.SUCCESS(f'Superuser {email} created with admin privileges'))
        else:
            # Update existing user to ensure they have admin privileges
            user = User.objects.get(email=email)
            user.is_staff = True
            user.is_superuser = True
            user.user_type = 'admin'
            user.save()
            self.stdout.write(self.style.WARNING(f'Superuser {email} already exists - updated to admin'))