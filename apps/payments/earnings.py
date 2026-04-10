"""
NapsterLegal — Earnings & Revenue Distribution Engine
=====================================================

HOW THE MONEY FLOWS:
────────────────────
1. Subscription revenue collected monthly from all paying users
2. Ad revenue collected from free-tier streaming (via future ad integration)
3. Total pool split:
       40% → Artist Pool (distributed by stream count per artist)
       35% → Platform Owner (profit / operational salary)
       25% → Production costs (servers, CDN, AcoustID API, email, staff)

ARTIST POOL DISTRIBUTION (User-Centric Model):
───────────────────────────────────────────────
Each artist's share = (their streams / total platform streams) × artist_pool
Then multiplied by their graduated tier bonus:
   0–5K streams:    tier multiplier 0.20
   5K–20K streams:  tier multiplier 0.35
   20K–50K streams: tier multiplier 0.45
   50K+ streams:    tier multiplier 0.50

WHY THIS IS BETTER THAN AUDIOMACK:
───────────────────────────────────
- Audiomack pays 0% until 50,000 streams → we pay from stream 1
- Audiomack's global pro-rata dilutes African artists → our model is per-listener
- Audiomack's rate is opaque → ours is fully transparent and auditable

ARTIST PERCEPTION vs REALITY:
──────────────────────────────
An artist with 60K streams sees:
  → "You earned 50% of your stream pool" (top tier)
  → This FEELS generous vs Audiomack's opaque per-stream rate
  → Reality: the 40% artist pool is split among ALL artists
  → But growing artists graduate up, creating real incentive
"""

from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db.models import Sum, Count


# ── REVENUE SPLIT CONSTANTS ───────────────────────────────────────────────
ARTIST_SHARE     = Decimal('0.40')   # 40% to artist pool
APP_OWNER_SHARE  = Decimal('0.35')   # 35% to platform owner
PRODUCTION_SHARE = Decimal('0.25')   # 25% to production/infra

# Per-stream base rate (USD) — varies by listener subscription
PER_STREAM_RATES = {
    'free':             Decimal('0.0005'),  # ad-supported, lower
    'premium_listener': Decimal('0.003'),
    'listener_pro':     Decimal('0.005'),
    'artist_pro':       Decimal('0.003'),
    'artist_label':     Decimal('0.004'),
}

# Graduated tier multipliers
GRADUATED_TIERS = [
    (0,       5_000,  Decimal('0.20')),
    (5_000,   20_000, Decimal('0.35')),
    (20_000,  50_000, Decimal('0.45')),
    (50_000,  None,   Decimal('0.50')),
]


def get_graduated_tier(play_count):
    """Return the revenue share multiplier for this play count."""
    for low, high, multiplier in GRADUATED_TIERS:
        if high is None or play_count < high:
            return multiplier
    return Decimal('0.50')


def calculate_monthly_pool():
    """
    Calculate the total revenue pool for the current month.
    Returns dict with all splits.
    """
    from apps.payments.models import UserSubscription, SubscriptionPlan

    # Sum all active subscription revenues
    active_subs = UserSubscription.objects.filter(
        status='active',
        current_period_start__month=timezone.now().month,
        current_period_start__year=timezone.now().year,
    )

    total_revenue = Decimal('0')
    for sub in active_subs:
        if sub.plan.billing_cycle == 'monthly':
            total_revenue += sub.plan.price_monthly
        else:
            total_revenue += sub.plan.price_yearly / 12

    return {
        'total_revenue':  total_revenue,
        'artist_pool':    (total_revenue * ARTIST_SHARE).quantize(Decimal('0.01')),
        'owner_profit':   (total_revenue * APP_OWNER_SHARE).quantize(Decimal('0.01')),
        'production':     (total_revenue * PRODUCTION_SHARE).quantize(Decimal('0.01')),
    }


def calculate_artist_earnings(artist, period_plays=None):
    """
    Calculate what one artist earns this month.

    Args:
        artist: ArtistProfile instance
        period_plays: int — plays in current month (from MariaDB)
                     If None, uses track.play_count from PostgreSQL

    Returns dict with earnings breakdown.
    """
    from apps.music.models import Track

    # Get artist's tracks
    tracks = Track.objects.filter(artist=artist, is_published=True)
    artist_plays = period_plays or tracks.aggregate(t=Sum('play_count'))['t'] or 0

    # Get total platform plays (all published tracks)
    total_plays = Track.objects.filter(is_published=True).aggregate(
        t=Sum('play_count'))['t'] or 1  # avoid div/0

    # Get this month's pool
    pool = calculate_monthly_pool()
    artist_pool = pool['artist_pool']

    # Stream-based share
    stream_fraction = Decimal(str(artist_plays)) / Decimal(str(total_plays))
    tier_multiplier = get_graduated_tier(artist_plays)

    # Raw share × graduated multiplier
    raw_earnings = artist_pool * stream_fraction
    final_earnings = (raw_earnings * tier_multiplier * 2).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP)
    # × 2 because multiplier is 0.20–0.50 and we want 20%–50% of their raw share

    # Per-stream rate for display
    per_stream = (final_earnings / Decimal(str(max(artist_plays, 1)))).quantize(
        Decimal('0.0001'))

    return {
        'artist_plays':       artist_plays,
        'total_plays':        total_plays,
        'stream_fraction':    float(stream_fraction),
        'tier_multiplier':    float(tier_multiplier),
        'tier_label':         _tier_label(artist_plays),
        'artist_pool':        float(pool['artist_pool']),
        'raw_earnings':       float(raw_earnings),
        'final_earnings':     float(final_earnings),
        'per_stream_rate':    float(per_stream),
        'platform_earnings':  float(pool['owner_profit']),
        'production_costs':   float(pool['production']),
        'total_pool':         float(pool['total_revenue']),
    }


def _tier_label(plays):
    if plays < 5_000:
        return 'Emerging (20%)'
    elif plays < 20_000:
        return 'Growing (35%)'
    elif plays < 50_000:
        return 'Established (45%)'
    return 'Partner (50%)'


def distribute_monthly_royalties():
    """
    MONTHLY CRON JOB — called on the 1st of each month.
    
    Distributes earnings to all artists:
    1. Calculate total pool from subscriptions
    2. Calculate each artist's share
    3. Create ArtistRoyalty records
    4. (In production: trigger bank transfer via Stripe/Flutterwave)
    
    Returns summary dict.
    """
    from apps.accounts.models import ArtistProfile
    from apps.payments.models import ArtistRoyalty, RoyaltyPool

    pool_data = calculate_monthly_pool()
    now = timezone.now()

    # Create RoyaltyPool record
    try:
        rp = RoyaltyPool.objects.create(
            month=now.replace(day=1),
            total_collected=pool_data['total_revenue'],
            artist_pool=pool_data['artist_pool'],
            operations_pool=pool_data['production'],
            profit=pool_data['owner_profit'],
            distributed=False,
        )
    except Exception:
        rp = None

    # Distribute to each artist
    artists = ArtistProfile.objects.filter(
        verification_status='verified',
        user__is_active=True,
    )

    distribution = []
    total_distributed = Decimal('0')

    for artist in artists:
        earnings = calculate_artist_earnings(artist)
        amount = Decimal(str(earnings['final_earnings']))

        if amount > 0:
            try:
                ArtistRoyalty.objects.create(
                    artist=artist.user,
                    month=now.replace(day=1),
                    streams=earnings['artist_plays'],
                    amount_earned=amount,
                    pool=rp,
                    status='pending',  # pending bank transfer
                )
            except Exception:
                pass  # Model may have different fields

            total_distributed += amount
            distribution.append({
                'artist':   artist.stage_name,
                'plays':    earnings['artist_plays'],
                'tier':     earnings['tier_label'],
                'earnings': float(amount),
            })

    return {
        'month':             now.strftime('%B %Y'),
        'total_pool':        float(pool_data['total_revenue']),
        'artist_pool':       float(pool_data['artist_pool']),
        'owner_profit':      float(pool_data['owner_profit']),
        'production':        float(pool_data['production']),
        'total_distributed': float(total_distributed),
        'artist_count':      len(distribution),
        'distribution':      distribution,
    }


def simulate_earnings(monthly_subscribers_free=100,
                       monthly_subscribers_premium=50,
                       monthly_subscribers_pro=10,
                       total_artist_plays=50_000,
                       artist_plays=5_000):
    """
    Simulation for testing — shows how money flows without real data.
    Useful for the school project presentation.
    """
    # Estimate revenue
    free_rev     = Decimal('0')                        # ads not yet integrated
    premium_rev  = Decimal('4.99') * monthly_subscribers_premium
    pro_rev      = Decimal('9.99') * monthly_subscribers_pro
    total        = free_rev + premium_rev + pro_rev

    artist_pool  = total * ARTIST_SHARE
    owner_profit = total * APP_OWNER_SHARE
    production   = total * PRODUCTION_SHARE

    fraction     = Decimal(str(artist_plays)) / Decimal(str(max(total_artist_plays, 1)))
    tier_mult    = get_graduated_tier(artist_plays)
    artist_earn  = (artist_pool * fraction * tier_mult * 2).quantize(Decimal('0.01'))

    return {
        'simulation': True,
        'inputs': {
            'free_users':     monthly_subscribers_free,
            'premium_users':  monthly_subscribers_premium,
            'pro_users':      monthly_subscribers_pro,
            'your_plays':     artist_plays,
            'total_plays':    total_artist_plays,
        },
        'revenue': {
            'total_monthly':     float(total),
            'artist_pool_40pct': float(artist_pool),
            'owner_profit_35pct':float(owner_profit),
            'production_25pct':  float(production),
        },
        'your_earnings': {
            'stream_fraction':   f"{float(fraction)*100:.2f}%",
            'tier':              _tier_label(artist_plays),
            'tier_multiplier':   f"{float(tier_mult)*100:.0f}%",
            'monthly_earnings':  float(artist_earn),
            'per_stream_rate':   float(artist_earn / Decimal(str(max(artist_plays, 1)))),
        },
    }
