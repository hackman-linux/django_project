"""
NapsterLegal — Payments Views
Handles subscription plans, Stripe checkout, and webhook.
"""
import os
from django.shortcuts   import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib     import messages
from django.http        import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils       import timezone

from .models import SubscriptionPlan, UserSubscription


# ── PRICING PAGE ──────────────────────────────────────────────────────────────

def pricing(request):
    free_features     = ['Stream all tracks (128kbps)', 'Create playlists',
                         'Follow artists', 'Search & discover', 'Ad-supported']
    premium_features  = ['Ad-free streaming (320kbps)', 'Offline downloads (30 days)',
                         'All Free features', 'Priority support',
                         'Supports artists directly']
    pro_features      = ['FLAC lossless streaming', 'Offline downloads (30 days)',
                         'Early access 48h before release', 'Custom equalizer per genre',
                         'All Premium features', 'Private listening stats']
    artist_pro_features= ['Unlimited uploads', 'Priority fingerprint review',
                          'Detailed analytics', 'Custom artist page',
                          'Earn from stream 1', 'Monthly royalty statement']
    label_features    = ['Manage up to 10 artist profiles',
                         'Bulk upload (500 tracks/month)',
                         'Advanced royalty CSV export',
                         '2-hour fingerprint review',
                         'Featured on genre pages',
                         'Dedicated account manager']

    faq_items = [
        ('Do artists earn from stream 1?',
         'Yes. Unlike Audiomack which requires 50,000 streams before any payout, '
         'NapsterLegal pays artists from their very first stream. The more streams you get, '
         'the higher your revenue share tier (20% → 35% → 45% → 50%).'),
        ('How is the 40% artist pool calculated?',
         'Every month, 40% of total subscription revenue goes into the artist pool. '
         'Each artist receives a share proportional to their streams. '
         'The calculation is transparent and visible in your artist dashboard.'),
        ('Can I cancel my subscription anytime?',
         'Yes. Cancel from your account settings at any time. '
         'You keep access until the end of your billing period. No penalties, no questions.'),
        ('What audio quality do I get?',
         'Free: 128kbps streaming. Premium Listener ($4.99): 320kbps + offline downloads. '
         'Listener Pro ($9.99): FLAC lossless + all Premium features.'),
        ('How does the AcoustID fingerprint work?',
         'Every uploaded track is compared against millions of known recordings. '
         'If a match is found by a different artist with >70% confidence, the track is held '
         'for admin review — not deleted. The artist is notified and given 24 hours for the '
         'admin to investigate. Original works publish immediately.'),
        ('Is this platform legal?',
         'Yes. NapsterLegal licenses music through artist agreements, pays royalties transparently, '
         'and operates under DMCA-compliant takedown procedures. All uploads are fingerprinted '
         'for copyright compliance.'),
        ('What is the difference between Artist Pro and Artist Label?',
         'Artist Pro ($9.99) is for individual independent artists — unlimited uploads, '
         'analytics, custom page. Artist Label ($29.99) is for labels managing up to 10 '
         'artist profiles, with bulk upload, advanced royalty CSV export, and a dedicated '
         'account manager.'),
        ('Why is there a 24-hour review period for flagged tracks?',
         'We believe in good faith moderation. No track is suspended without a human '
         'reviewing the evidence. This protects artists from false positives. '
         'Audiomack auto-suspends without human review — we never do that.'),
    ]

    return render(request, 'payments/pricing.html', {
        'free_features':       free_features,
        'premium_features':    premium_features,
        'pro_features':        pro_features,
        'artist_pro_features': artist_pro_features,
        'label_features':      label_features,
    })


# ── SUBSCRIBE ─────────────────────────────────────────────────────────────────

@login_required
def subscribe(request, plan_slug):
    """
    Stripe Checkout session.
    If STRIPE_SECRET_KEY is set → real Stripe checkout.
    Otherwise → demo flow (for school project).
    """
    plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)

    if plan.price_monthly == 0:
        # Free plan — just activate it
        _activate_plan(request.user, plan, 'free')
        messages.success(request, f'You are now on the {plan.name} plan.')
        return redirect('pricing')

    stripe_key = os.environ.get('STRIPE_SECRET_KEY', '')

    if stripe_key:
        # ── REAL STRIPE CHECKOUT ──────────────────────────────────────────
        return _stripe_checkout(request, plan, stripe_key)
    else:
        # ── DEMO FLOW (no Stripe key configured) ─────────────────────────
        return render(request, 'payments/subscribe_demo.html', {
            'plan': plan,
        })


@login_required
def subscribe_demo_confirm(request, plan_slug):
    """Demo subscription confirmation (used when Stripe not configured)."""
    if request.method != 'POST':
        return redirect('subscribe', plan_slug=plan_slug)

    plan = get_object_or_404(SubscriptionPlan, slug=plan_slug, is_active=True)
    billing = request.POST.get('billing', 'monthly')

    _activate_plan(request.user, plan, billing)
    messages.success(request,
        f'🎉 Subscribed to {plan.name}! '
        f'In production this would charge your card.')
    return redirect('my_subscription')


def _stripe_checkout(request, plan, stripe_key):
    """Create a Stripe Checkout session and redirect to it."""
    try:
        import stripe
        stripe.api_key = stripe_key

        billing = request.GET.get('billing', 'monthly')
        price   = plan.price_monthly if billing == 'monthly' else plan.price_yearly / 12
        amount  = int(price * 100)  # Stripe uses cents

        session = stripe.checkout.Session.create(
            payment_method_types = ['card'],
            line_items=[{
                'price_data': {
                    'currency':     'usd',
                    'unit_amount':  amount,
                    'recurring':    {'interval': 'month'},
                    'product_data': {
                        'name':        plan.name,
                        'description': plan.description,
                    },
                },
                'quantity': 1,
            }],
            mode                 = 'subscription',
            success_url          = request.build_absolute_uri(
                f'/pricing/success/?plan={plan.slug}&billing={billing}'),
            cancel_url           = request.build_absolute_uri('/pricing/'),
            metadata             = {
                'user_id':   str(request.user.id),
                'plan_slug': plan.slug,
                'billing':   billing,
            },
        )
        return redirect(session.url, permanent=False)

    except Exception as e:
        messages.error(request, f'Payment error: {e}')
        return redirect('pricing')


@login_required
def subscribe_success(request):
    """Stripe redirects here after successful payment."""
    plan_slug = request.GET.get('plan', '')
    billing   = request.GET.get('billing', 'monthly')

    if plan_slug:
        try:
            plan = SubscriptionPlan.objects.get(slug=plan_slug)
            _activate_plan(request.user, plan, billing)
        except SubscriptionPlan.DoesNotExist:
            pass

    messages.success(request, '🎉 Payment successful! Your subscription is now active.')
    return redirect('my_subscription')


def _activate_plan(user, plan, billing='monthly'):
    """Create or update UserSubscription record."""
    from django.utils import timezone
    from datetime import timedelta

    period_end = (timezone.now() + timedelta(days=365)
                  if billing == 'yearly'
                  else timezone.now() + timedelta(days=30))

    UserSubscription.objects.update_or_create(
        user = user,
        defaults={
            'plan':                  plan,
            'status':                'active',
            'billing_cycle':         billing,
            'current_period_start':  timezone.now(),
            'current_period_end':    period_end,
            'amount_paid':           plan.price_yearly if billing == 'yearly'
                                     else plan.price_monthly,
        }
    )
    # Update user premium flag
    user.is_premium = plan.price_monthly > 0
    user.save(update_fields=['is_premium'])


# ── STRIPE WEBHOOK ───────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Stripe sends events here.
    Handles: checkout.session.completed, customer.subscription.deleted
    Configure in Stripe Dashboard → Webhooks → Add endpoint:
      https://yourdomain.com/pricing/webhook/
    """
    stripe_key    = os.environ.get('STRIPE_SECRET_KEY', '')
    webhook_secret= os.environ.get('STRIPE_WEBHOOK_SECRET', '')

    if not stripe_key:
        return HttpResponse('Stripe not configured', status=200)

    try:
        import stripe
        stripe.api_key = stripe_key

        payload   = request.body
        sig       = request.headers.get('Stripe-Signature', '')

        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
        else:
            event = stripe.Event.construct_from(
                __import__('json').loads(payload), stripe_key)

        if event['type'] == 'checkout.session.completed':
            session  = event['data']['object']
            meta     = session.get('metadata', {})
            user_id  = meta.get('user_id')
            plan_slug= meta.get('plan_slug')
            billing  = meta.get('billing', 'monthly')

            if user_id and plan_slug:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.get(id=user_id)
                    plan = SubscriptionPlan.objects.get(slug=plan_slug)
                    _activate_plan(user, plan, billing)
                except Exception:
                    pass

        elif event['type'] == 'customer.subscription.deleted':
            # Subscription cancelled — downgrade to free
            session  = event['data']['object']
            meta     = session.get('metadata', {})
            user_id  = meta.get('user_id')
            if user_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.get(id=user_id)
                    free_plan = SubscriptionPlan.objects.get(slug='free')
                    _activate_plan(user, free_plan, 'monthly')
                except Exception:
                    pass

    except Exception as e:
        return HttpResponse(str(e), status=400)

    return HttpResponse(status=200)


# ── MY SUBSCRIPTION ───────────────────────────────────────────────────────────

@login_required
def my_subscription(request):
    subscription = None
    try:
        subscription = UserSubscription.objects.select_related('plan').get(
            user=request.user, status='active')
    except UserSubscription.DoesNotExist:
        pass

    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly')

    return render(request, 'payments/my_subscription.html', {
        'subscription': subscription,
        'plans':        plans,
    })


@login_required
def cancel_subscription(request):
    if request.method == 'POST':
        try:
            sub = UserSubscription.objects.get(user=request.user, status='active')
            sub.status = 'cancelled'
            sub.save(update_fields=['status'])
            request.user.is_premium = False
            request.user.save(update_fields=['is_premium'])
            messages.success(request, 'Subscription cancelled. You will keep access until the end of the billing period.')
        except UserSubscription.DoesNotExist:
            messages.error(request, 'No active subscription found.')
    return redirect('my_subscription')
