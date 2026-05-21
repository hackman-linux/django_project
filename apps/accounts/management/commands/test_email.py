"""
python manage.py test_email your@gmail.com
Sends a real test email to verify SMTP is working.
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Send a test email to verify SMTP configuration'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Recipient email address')

    def handle(self, *args, **options):
        to_email = options['email']
        self.stdout.write(f'Sending test email to {to_email}...')
        self.stdout.write(f'Using backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'SMTP Host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')

        try:
            send_mail(
                subject='NapsterLegal — Email Test',
                message=(
                    'This is a test email from NapsterLegal.\n\n'
                    'If you received this, your email configuration is working correctly.\n\n'
                    'Platform: NapsterLegal\n'
                    'Environment: Development\n'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Email sent successfully to {to_email}'))
            self.stdout.write('Check your inbox (and spam folder).')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Email failed: {e}'))
            self.stdout.write('Fix: Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env')
