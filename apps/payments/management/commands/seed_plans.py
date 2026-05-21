"""
python manage.py seed_plans
Seeds all 5 subscription plans with correct slugs and prices.
"""
from django.core.management.base import BaseCommand
from apps.payments.models import SubscriptionPlan
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seed subscription plans'

    def handle(self, *args, **options):
        plans = [
            {
                'slug':           'free',
                'name':           'Free',
                'price_monthly':  Decimal('0.00'),
                'price_yearly':   Decimal('0.00'),
                'description':    'Discover unlimited music with ads.',
                'features':       ['Stream all tracks (128kbps)', 'Create playlists',
                                   'Follow artists', 'Search & discover'],
                'is_active':      True,
            },
            {
                'slug':           'premium_listener',
                'name':           'Premium Listener',
                'price_monthly':  Decimal('4.99'),
                'price_yearly':   Decimal('39.99'),
                'description':    'Ad-free listening with offline downloads.',
                'features':       ['Ad-free streaming (320kbps)', 'Offline downloads (30 days)',
                                   'All Free features', 'Priority support'],
                'is_active':      True,
            },
            {
                'slug':           'listener_pro',
                'name':           'Listener Pro',
                'price_monthly':  Decimal('9.99'),
                'price_yearly':   Decimal('79.99'),
                'description':    'Lossless FLAC quality — the audiophile plan.',
                'features':       ['FLAC lossless streaming', 'Offline downloads (30 days)',
                                   'Early access 48h before release', 'Custom equalizer per genre',
                                   'All Premium features'],
                'is_active':      True,
            },
            {
                'slug':           'artist_pro',
                'name':           'Artist Pro',
                'price_monthly':  Decimal('9.99'),
                'price_yearly':   Decimal('79.99'),
                'description':    'Professional tools for independent artists.',
                'features':       ['Unlimited track uploads', 'Priority fingerprint review',
                                   'Detailed analytics', 'Custom artist page',
                                   'Earn from stream 1', 'Monthly royalty statement'],
                'is_active':      True,
            },
            {
                'slug':           'artist_label',
                'name':           'Artist Label',
                'price_monthly':  Decimal('29.99'),
                'price_yearly':   Decimal('249.99'),
                'description':    'For labels and multi-artist operations.',
                'features':       ['Manage up to 10 artist profiles',
                                   'Bulk upload (500 tracks/month)',
                                   'Advanced royalty CSV export',
                                   '2-hour fingerprint review',
                                   'Featured on genre pages',
                                   'Dedicated account manager'],
                'is_active':      True,
            },
        ]

        for data in plans:
            features = data.pop('features')
            obj, created = SubscriptionPlan.objects.update_or_create(
                slug=data['slug'],
                defaults={**data, 'features': features}
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'  {status}: {obj.name} (${obj.price_monthly}/mo)'))

        self.stdout.write(self.style.SUCCESS('\n=== Plans seeded ==='))
