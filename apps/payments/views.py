from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import SubscriptionPlan, UserSubscription, RoyaltyPool, ArtistRoyalty
from apps.accounts.models import CustomUser


def pricing_page(request):
    """Public pricing page — no login required."""
    plans = SubscriptionPlan.objects.filter(is_active=True)
    return render(request, 'payments/pricing.html', {'plans': plans})


@login_required
def subscribe(request, plan_slug):
    """
    Subscription page for a specific plan.
    In production: integrate with Stripe or CinetPay here.
    For demo: simulate payment with a form.
    """
    plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)

    # Check if user already has an active subscription
    existing = UserSubscription.objects.filter(
        user=request.user, status='active'
    ).first()

    if request.method == 'POST':
        billing_cycle  = request.POST.get('billing_cycle', 'monthly')
        payment_method = request.POST.get('payment_method', 'card')

        # Calculate price and expiry
        if billing_cycle == 'yearly':
            amount     = plan.price_yearly
            expires_at = timezone.now() + timedelta(days=365)
        else:
            amount     = plan.price_monthly
            expires_at = timezone.now() + timedelta(days=30)

        # Cancel existing subscription if upgrading
        if existing:
            existing.status = 'cancelled'
            existing.save(update_fields=['status'])

        # Create new subscription
        sub = UserSubscription.objects.create(
            user           = request.user,
            plan           = plan,
            status         = 'active',
            billing_cycle  = billing_cycle,
            expires_at     = expires_at,
            amount_paid    = amount,
            payment_method = payment_method,
            transaction_id = f"DEMO-{request.user.id}-{timezone.now().timestamp():.0f}",
        )

        # Update user flags
        request.user.is_premium = (plan.slug != 'free')
        request.user.premium_until = expires_at
        request.user.save(update_fields=['is_premium', 'premium_until'])

        messages.success(
            request,
            f'Successfully subscribed to {plan.name}! '
            f'Valid until {expires_at.strftime("%B %d, %Y")}.'
        )
        return redirect('subscription_success', sub_id=sub.id)

    return render(request, 'payments/subscribe.html', {
        'plan':     plan,
        'existing': existing,
    })


@login_required
def subscription_success(request, sub_id):
    sub = get_object_or_404(UserSubscription, id=sub_id, user=request.user)
    return render(request, 'payments/success.html', {'sub': sub})


@login_required
def my_subscription(request):
    """User's current subscription + billing history."""
    active = UserSubscription.objects.filter(
        user=request.user, status='active'
    ).select_related('plan').first()

    history = UserSubscription.objects.filter(
        user=request.user
    ).select_related('plan').order_by('-created_at')[:10]

    return render(request, 'payments/my_subscription.html', {
        'active':  active,
        'history': history,
    })


@login_required
def cancel_subscription(request):
    """Cancel current active subscription."""
    if request.method == 'POST':
        sub = UserSubscription.objects.filter(
            user=request.user, status='active'
        ).first()
        if sub:
            sub.status     = 'cancelled'
            sub.auto_renew = False
            sub.save(update_fields=['status', 'auto_renew'])

            request.user.is_premium    = False
            request.user.premium_until = None
            request.user.save(update_fields=['is_premium', 'premium_until'])

            messages.info(request,
                f'Subscription cancelled. You will keep access until '
                f'{sub.expires_at.strftime("%B %d, %Y")}.')
        return redirect('my_subscription')
    return redirect('my_subscription')

def pricing(request):
    """Pricing page with all 5 plans and correct prices."""
    free_features = [
        'Stream all tracks (128kbps)',
        'Create playlists',
        'Follow artists',
        'Search & discover',
        'Ad-supported',
    ]
    premium_features = [
        'Everything in Free',
        'Ad-free streaming (320kbps MP3)',
        'Offline downloads (30 days)',
        'Supports artists directly',
        'Priority support',
    ]
    pro_features = [
        'Everything in Premium',
        'FLAC lossless streaming',
        'Offline downloads (30 days)',
        'Early access (48h before release)',
        'Custom equalizer per genre',
        'Private listening stats',
    ]
    artist_pro_features = [
        'Unlimited track uploads',
        'Priority fingerprint review',
        'Detailed analytics dashboard',
        'Artist announcements',
        'Custom artist page',
        'Earn from stream 1',
        'Monthly royalty statement',
    ]
    label_features = [
        'Manage up to 10 artist profiles',
        'Bulk upload (500 tracks/month)',
        'Advanced royalty CSV export',
        '2-hour fingerprint review',
        'Featured on genre pages',
        'Custom page branding',
        'Dedicated account manager',
        'Earn from stream 1',
    ]
    return render(request, 'payments/pricing.html', {
        'free_features':     free_features,
        'premium_features':  premium_features,
        'pro_features':      pro_features,
        'artist_pro_features': artist_pro_features,
        'label_features':    label_features,
    })


