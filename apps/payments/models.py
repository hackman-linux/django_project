import uuid
from django.db import models
from decimal import Decimal

# ── CORRECTED REVENUE DISTRIBUTION ─────────────────────────────────────
# Artists still FEEL like they get more (40% direct + bonus pool)
# Platform is financially sustainable with 35% + 25% = 60% retained
ARTIST_SHARE     = Decimal('0.40')   # 40% → directly to artists (stream-based)
APP_OWNER_SHARE  = Decimal('0.35')   # 35% → platform owner / profit
PRODUCTION_SHARE = Decimal('0.25')   # 25% → servers, bandwidth, staff, AcoustID
# Total always = 100% ✓

# Graduated payout multipliers (artists EARN more as they grow)
# This makes the effective artist rate FEEL higher to successful artists
GRAD_TIER_1 = Decimal('0.20')  # 0–5K plays   → 20% of artist pool
GRAD_TIER_2 = Decimal('0.35')  # 5K–20K plays → 35% of artist pool
GRAD_TIER_3 = Decimal('0.45')  # 20K–50K plays→ 45% of artist pool
GRAD_TIER_4 = Decimal('0.50')  # 50K+ plays   → 50% of artist pool
from apps.accounts.models import CustomUser


class SubscriptionPlan(models.Model):
    """
    The plans you offer. Stored in DB so you can edit
    prices/features without redeploying.
    """
    FREE    = 'free'
    PREMIUM = 'premium'
    ARTIST  = 'artist_pro'

    PLAN_CHOICES = [
        (FREE,    'Free'),
        (PREMIUM, 'Premium Listener'),
        (ARTIST,  'Artist Pro'),
    ]

    name          = models.CharField(max_length=50)
    slug          = models.CharField(max_length=20, unique=True, choices=PLAN_CHOICES)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    price_yearly  = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    currency      = models.CharField(max_length=3, default='USD')
    description   = models.TextField(blank=True)
    features      = models.JSONField(default=list)  # list of feature strings
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} — ${self.price_monthly}/mo"

    class Meta:
        ordering = ['price_monthly']


class UserSubscription(models.Model):
    """
    Tracks which plan a user is on and when it expires.
    """
    ACTIVE    = 'active'
    EXPIRED   = 'expired'
    CANCELLED = 'cancelled'
    TRIAL     = 'trial'

    STATUS_CHOICES = [
        (ACTIVE,    'Active'),
        (EXPIRED,   'Expired'),
        (CANCELLED, 'Cancelled'),
        (TRIAL,     'Trial'),
    ]

    MONTHLY = 'monthly'
    YEARLY  = 'yearly'

    BILLING_CHOICES = [
        (MONTHLY, 'Monthly'),
        (YEARLY,  'Yearly'),
    ]

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user           = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='user_subscriptions')
    plan           = models.ForeignKey(
        SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE)
    billing_cycle  = models.CharField(max_length=10, choices=BILLING_CHOICES, default=MONTHLY)
    started_at     = models.DateTimeField(auto_now_add=True)
    expires_at     = models.DateTimeField()
    amount_paid    = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50, blank=True,
                                      help_text='e.g. card, mobile_money, paypal')
    transaction_id = models.CharField(max_length=200, blank=True,
                                      help_text='External payment reference')
    auto_renew     = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {self.plan.name} ({self.status})"

    def is_active(self):
        from django.utils import timezone
        return (self.status == self.ACTIVE and
                self.expires_at > timezone.now())

    class Meta:
        ordering = ['-created_at']


class RoyaltyPool(models.Model):
    """
    Monthly pool of money to distribute to artists.
    Each month: X% of all subscription revenue goes into the pool.
    Pool is split among artists proportional to their stream share.
    """
    month          = models.DateField(unique=True, help_text='First day of the month')
    total_revenue  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    artist_pool    = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text='Amount allocated to artists (70% of revenue)')
    platform_cut   = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text='Platform earnings (30% of revenue)')
    total_streams  = models.PositiveIntegerField(default=0)
    distributed    = models.BooleanField(default=False)
    distributed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Pool {self.month.strftime('%B %Y')} — ${self.artist_pool} to artists"

    class Meta:
        ordering = ['-month']


class ArtistRoyalty(models.Model):
    """
    Individual artist's share of a monthly royalty pool.
    Calculated as: (artist_streams / total_streams) * artist_pool
    """
    pool           = models.ForeignKey(
        RoyaltyPool, on_delete=models.CASCADE, related_name='royalties')
    artist         = models.ForeignKey(
        'accounts.ArtistProfile', on_delete=models.CASCADE, related_name='royalties')
    streams        = models.PositiveIntegerField(default=0)
    stream_share   = models.DecimalField(
        max_digits=7, decimal_places=4, default=0,
        help_text='Percentage of total streams (e.g. 0.0523 = 5.23%)')
    amount         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid           = models.BooleanField(default=False)
    paid_at        = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (f"{self.artist.stage_name} — "
                f"${self.amount} ({self.pool.month.strftime('%B %Y')})")

    class Meta:
        ordering  = ['-pool__month', '-amount']
        unique_together = ('pool', 'artist')
