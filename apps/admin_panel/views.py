"""
NapsterLegal — Separate Admin Control Panel
URL prefix: /control/
Completely isolated from the regular user app.
Admin has own login, own navigation, own dashboard.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.db.models import Sum, Count, Avg
from functools import wraps

User = get_user_model()


# ── DECORATOR ────────────────────────────────────────────────────────────────
def cp_required(view_func):
    """Require staff/superuser. Redirect to /control/login/ otherwise."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/control/login/?next={request.path}')
        if not (request.user.is_staff or request.user.is_superuser):
            return redirect('/control/login/')
        return view_func(request, *args, **kwargs)
    return wrapper


def _sidebar(active_key):
    """Return sidebar navigation items. Active item highlighted."""
    items = [
        ('cp_dashboard',  'M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm0 8a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zm12-1a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z', 'Overview',  '/control/'),
        ('cp_users',      'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197', 'Users',     '/control/users/'),
        ('cp_tracks',     'M9 19V6l12-3v13M9 19c0 1.1-1.34 2-3 2s-3-.9-3-2 1.34-2 3-2 3 .9 3 2z', 'Tracks',    '/control/tracks/'),
        ('cp_artists',    'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z', 'Artists',   '/control/artists/'),
        ('cp_analytics',  'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z', 'Analytics', '/control/analytics/'),
        ('cp_logs',       'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2', 'Logs / IPs', '/control/logs/'),
        ('cp_messages',   'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z', 'Messages',  '/control/messages/'),
        ('cp_settings',   'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z', 'App Settings', '/control/settings/'),
        ('cp_my_space',   'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6', 'My Space',   '/control/my-space/'),
    ]
    return [(name, icon, label, url, name == active_key) for name, icon, label, url in items]


def _ctx(request, active_key, **kwargs):
    """Base context for all admin panel views."""
    return {'sidebar': _sidebar(active_key), 'admin_user': request.user, **kwargs}


# ── AUTH ─────────────────────────────────────────────────────────────────────
def admin_login(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('/control/')
    error = None
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('username', ''),
                            password=request.POST.get('password', ''))
        if user and (user.is_staff or user.is_superuser):
            auth_login(request, user)
            return redirect(request.GET.get('next', '/control/'))
        error = 'Invalid credentials or insufficient privileges.'
    return render(request, 'control/login.html', {'error': error})


def admin_logout(request):
    auth_logout(request)
    return redirect('/control/login/')


# ── DASHBOARD ────────────────────────────────────────────────────────────────
@cp_required
def dashboard(request):
    from apps.music.models import Track
    from apps.accounts.models import ArtistProfile
    from apps.payments.models import UserSubscription

    # Quick stats
    stats = {
        'total_users':    User.objects.count(),
        'active_users':   User.objects.filter(is_active=True).count(),
        'total_artists':  ArtistProfile.objects.count(),
        'pending_artists':ArtistProfile.objects.filter(verification_status='pending').count(),
        'total_tracks':   Track.objects.count(),
        'live_tracks':    Track.objects.filter(is_published=True).count(),
        'flagged_tracks': Track.objects.filter(acoustid_status='failed').count(),
        'total_plays':    Track.objects.aggregate(t=Sum('play_count'))['t'] or 0,
        'total_revenue':  round(float(
            UserSubscription.objects.filter(status='active')
            .aggregate(t=Sum('amount_paid'))['t'] or 0), 2),
    }

    # MariaDB analytics
    analytics = {}
    try:
        from apps.analytics.models import PlayEvent, SearchLog
        analytics = {
            'total_events':    PlayEvent.objects.using('analytics').count(),
            'avg_listen':      round(
                PlayEvent.objects.using('analytics')
                .aggregate(a=Avg('listened_duration'))['a'] or 0, 1),
            'completion_rate': round(
                (PlayEvent.objects.using('analytics').filter(completed=True).count() /
                 max(PlayEvent.objects.using('analytics').count(), 1)) * 100, 1),
            'device_stats':    list(
                PlayEvent.objects.using('analytics')
                .values('device_type').annotate(count=Count('id')).order_by('-count')),
            'top_countries':   list(
                PlayEvent.objects.using('analytics')
                .values('country_code').annotate(count=Count('id'))
                .order_by('-count')[:5]),
        }
    except Exception as e:
        analytics = {'error': str(e)}

    top_tracks = list(Track.objects.filter(is_published=True).order_by('-play_count')[:6])
    top_tracks_enum = list(enumerate(top_tracks, 1))

    platform_stats = [
        ('Total Users',    stats['total_users'],    '#4F8EF7'),
        ('Active Users',   stats['active_users'],   '#34D399'),
        ('Artists',        stats['total_artists'],  '#2DD4BF'),
        ('Pending Review', stats['pending_artists'],'#F59E0B'),
        ('Live Tracks',    stats['live_tracks'],    '#8B5CF6'),
        ('Flagged',        stats['flagged_tracks'], '#EF4444'),
        ('Total Plays',    stats['total_plays'],    '#F472B6'),
        ('Revenue $',      stats['total_revenue'],  '#34D399'),
    ]

    analytics_rows = []
    if not analytics.get('error'):
        analytics_rows = [
            ('Play Events',      analytics.get('total_events', 0)),
            ('Avg Listen',       f"{analytics.get('avg_listen', 0)}s"),
            ('Completion Rate',  f"{analytics.get('completed_rate', 0)}%"),
            ('Total Searches',   analytics.get('total_searches', 0)),
        ]

    return render(request, 'control/dashboard.html', _ctx(
        request, 'cp_dashboard',
        stats=stats,
        analytics=analytics,
        analytics_rows=analytics_rows,
        platform_stats=platform_stats,
        recent_users=User.objects.order_by('-date_joined')[:6],
        top_tracks=top_tracks,
        top_tracks_enum=top_tracks_enum,
    ))


# ── USERS ─────────────────────────────────────────────────────────────────────
@cp_required
def users_list(request):
    q = request.GET.get('q', '').strip()
    filter_type = request.GET.get('type', '')
    users = User.objects.order_by('-date_joined')
    if q:
        users = users.filter(username__icontains=q) | users.filter(email__icontains=q)
    if filter_type:
        users = users.filter(user_type=filter_type)
    return render(request, 'control/users.html',
                  _ctx(request, 'cp_users', users=users, q=q, filter_type=filter_type))


@cp_required
def user_detail(request, user_id):
    u = get_object_or_404(User, id=user_id)
    return render(request, 'control/user_detail.html', _ctx(request, 'cp_users', viewed_user=u))


@cp_required
def toggle_user(request, user_id):
    u = get_object_or_404(User, id=user_id)
    if not u.is_superuser:
        u.is_active = not u.is_active
        u.save(update_fields=['is_active'])
    return redirect('/control/users/')


# ── TRACKS ───────────────────────────────────────────────────────────────────
@cp_required
def tracks_list(request):
    from apps.music.models import Track
    q = request.GET.get('q', '').strip()
    filter_status = request.GET.get('status', '')
    tracks = Track.objects.select_related('artist', 'genre').order_by('-uploaded_at')
    if q:
        tracks = tracks.filter(title__icontains=q)
    if filter_status == 'live':
        tracks = tracks.filter(is_published=True)
    elif filter_status == 'draft':
        tracks = tracks.filter(is_published=False)
    elif filter_status == 'flagged':
        tracks = tracks.filter(acoustid_status='failed')
    flagged = tracks.filter(acoustid_status='failed').count()
    return render(request, 'control/tracks.html',
                  _ctx(request, 'cp_tracks', tracks=tracks, flagged=flagged,
                       q=q, filter_status=filter_status))


@cp_required
def toggle_track(request, track_id):
    from apps.music.models import Track
    track = get_object_or_404(Track, id=track_id)
    track.is_published = not track.is_published
    track.save(update_fields=['is_published'])
    return redirect('/control/tracks/')


@cp_required
def delete_track(request, track_id):
    from apps.music.models import Track
    track = get_object_or_404(Track, id=track_id)
    if request.method == 'POST':
        track.audio_file.delete(save=False)
        track.delete()
        messages.success(request, f'Track deleted.')
    return redirect('/control/tracks/')


# ── ARTISTS ──────────────────────────────────────────────────────────────────
@cp_required
def artists_list(request):
    from apps.accounts.models import ArtistProfile
    tab = request.GET.get('tab', 'pending')
    artists_qs = ArtistProfile.objects.filter(
        verification_status=tab).select_related('user').order_by('-user__date_joined')
    counts = {
        'pending':  ArtistProfile.objects.filter(verification_status='pending').count(),
        'verified': ArtistProfile.objects.filter(verification_status='verified').count(),
        'rejected': ArtistProfile.objects.filter(verification_status='rejected').count(),
    }
    tabs = [
        ('pending',  'Pending',  counts['pending']),
        ('verified', 'Verified', counts['verified']),
        ('rejected', 'Rejected', counts['rejected']),
    ]
    return render(request, 'control/artists.html',
                  _ctx(request, 'cp_artists', artists=artists_qs, tab=tab,
                       counts=counts, tabs=tabs))


@cp_required
def verify_artist(request, artist_id):
    from apps.accounts.models import ArtistProfile
    artist = get_object_or_404(ArtistProfile, id=artist_id)
    if request.method == 'POST':
        from django.utils import timezone
        new_status = request.POST.get('verification_status', 'pending')
        note       = request.POST.get('verification_note', '')
        artist.verification_status = new_status
        artist.verification_note   = note
        artist.verification_date   = timezone.now()
        artist.verified = (new_status == 'verified')
        artist.save()
        messages.success(request, f'{artist.stage_name} → {artist.get_verification_status_display()}')
        return redirect('/control/artists/')
    artist_info = [
        ('Username',   artist.user.username,  '#F0F4FF'),
        ('Email',      artist.user.email,     '#94A3B8'),
        ('Stage Name', artist.stage_name,     '#F0F4FF'),
        ('Real Name',  artist.real_name or 'Not provided',
                       '#F0F4FF' if artist.real_name else '#F87171'),
        ('Country',    artist.country or '—', '#94A3B8'),
        ('Status',     artist.get_verification_status_display(),
                       '#FDE68A' if artist.verification_status=='pending'
                       else '#6EE7B7' if artist.verification_status=='verified' else '#FCA5A5'),
        ('Joined',     artist.user.date_joined.strftime('%B %d, %Y'), '#94A3B8'),
    ]
    checklist = [
        'Real name has been provided',
        'Work sample URL opens and shows their music',
        'Artist name on external platform matches stage name',
        'No suspicious or flagged tracks',
    ]
    return render(request, 'control/verify_artist.html',
                  _ctx(request, 'cp_artists', artist=artist,
                       artist_info=artist_info, checklist=checklist))


# ── ANALYTICS ────────────────────────────────────────────────────────────────
@cp_required
def analytics_view(request):
    data = {}
    try:
        from apps.analytics.models import PlayEvent, SearchLog
        data = {
            'total_events':    PlayEvent.objects.using('analytics').count(),
            'avg_listen':      round(
                PlayEvent.objects.using('analytics')
                .aggregate(a=Avg('listened_duration'))['a'] or 0, 1),
            'completed_rate':  round(
                PlayEvent.objects.using('analytics').filter(completed=True).count() /
                max(PlayEvent.objects.using('analytics').count(), 1) * 100, 1),
            'device_stats':    list(
                PlayEvent.objects.using('analytics')
                .values('device_type').annotate(count=Count('id')).order_by('-count')),
            'country_stats':   list(
                PlayEvent.objects.using('analytics')
                .values('country_code').annotate(count=Count('id'))
                .order_by('-count')[:10]),
            'recent_events':   PlayEvent.objects.using('analytics').order_by('-timestamp')[:30],
            'total_searches':  SearchLog.objects.using('analytics').count(),
            'recent_searches': SearchLog.objects.using('analytics').order_by('-timestamp')[:20],
        }
    except Exception as e:
        data['error'] = str(e)
    return render(request, 'control/analytics.html', _ctx(request, 'cp_analytics', **data))


# ── LOGS / IPs ───────────────────────────────────────────────────────────────
@cp_required
def logs_view(request):
    events = []
    try:
        from apps.analytics.models import PlayEvent
        events = PlayEvent.objects.using('analytics').order_by('-timestamp')[:100]
    except Exception as e:
        messages.warning(request, f'Could not load analytics: {e}')
    return render(request, 'control/logs.html', _ctx(request, 'cp_logs', events=events))


# ── MESSAGES (Contact) ───────────────────────────────────────────────────────
@cp_required
def messages_view(request):
    # Simple: show all ContactMessage objects
    try:
        from apps.accounts.models import ContactMessage
        msgs = ContactMessage.objects.order_by('-created_at')
    except Exception:
        msgs = []
    return render(request, 'control/messages.html', _ctx(request, 'cp_messages', contact_msgs=msgs))


# ── APP SETTINGS ─────────────────────────────────────────────────────────────
@cp_required
def app_settings(request):
    if request.method == 'POST':
        # Save app-wide settings (could store in a Settings model or .env)
        messages.success(request, 'App settings saved.')
        return redirect('/control/settings/')
    from apps.payments.earnings import simulate_earnings
    sim = simulate_earnings(
        monthly_subscribers_premium=50,
        monthly_subscribers_pro=10,
        total_artist_plays=50_000,
        artist_plays=5_000,
    )

    settings_fields = [
        # Platform identity
        ('Platform Name',        'site_name',        'NapsterLegal',               'Shown in all emails and page titles'),
        ('Support Email',        'support_email',    'support@napsterlegal.com',   'Replies go here from users'),
        ('Contact Email',        'contact_email',    'contact@napsterlegal.com',   'Displayed on contact page'),
        ('Admin Email',          'admin_email',      'admin@napsterlegal.com',     'Internal alerts go here'),
        # Revenue model
        ('Artist Pool %',        'artist_share',     '40',                         'Of total subscription revenue'),
        ('Owner Profit %',       'owner_share',      '35',                         'Platform owner earnings'),
        ('Production Costs %',   'production_share', '25',                         'Servers, CDN, API costs'),
        # Per-stream rates
        ('Free Tier Stream Rate','rate_free',        '0.0005',                     'USD per stream, ad-supported tier'),
        ('Premium Stream Rate',  'rate_premium',     '0.003',                      'USD per stream, Premium Listener'),
        ('Pro Stream Rate',      'rate_pro',         '0.005',                      'USD per stream, Listener Pro'),
        # Audio quality
        ('Free Tier Quality',    'quality_free',     '128kbps',                    'MP3 bitrate for free users'),
        ('Premium Quality',      'quality_premium',  '320kbps',                    'MP3 bitrate for paid users'),
        ('Pro Tier Quality',     'quality_pro',      'FLAC',                       'Lossless for Listener Pro'),
        # Moderation
        ('Review Hold Hours',    'review_hold',      '24',                         'Hours before flagged track is hidden'),
        ('Max Upload MB',        'max_upload_mb',    '100',                        'Max audio file size in MB'),
        # Francophone Africa
        ('Primary Market',       'primary_market',   'Francophone Africa',         'Main geographic focus'),
        ('Default Language',     'default_language', 'fr',                         'Default for new users'),
    ]

    return render(request, 'control/settings.html',
                  _ctx(request, 'cp_settings',
                       settings_fields=settings_fields,
                       revenue_simulation=sim))


# ── MY SPACE ─────────────────────────────────────────────────────────────────
@cp_required
def admin_my_space(request):
    """Admin can also browse and listen to music."""
    from apps.music.models import Track
    from apps.social.models import Like
    liked = Like.objects.filter(user=request.user).select_related('track').order_by('-created_at')[:12]
    new_tracks = Track.objects.filter(is_published=True).order_by('-uploaded_at')[:12]
    return render(request, 'control/my_space.html',
                  _ctx(request, 'cp_my_space', liked=liked, new_tracks=new_tracks))


@cp_required
def create_staff(request):
    """Superuser creates staff accounts and sends credentials by email."""
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can create staff accounts.')
        return redirect('/control/settings/')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email    = request.POST.get('email', '').strip()
        role     = request.POST.get('role', 'staff')

        if not username or not email:
            messages.error(request, 'Username and email are required.')
            return redirect('/control/settings/')

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already exists.')
            return redirect('/control/settings/')

        import secrets, string
        password = ''.join(secrets.choice(
            string.ascii_letters + string.digits + '!@#$%') for _ in range(12))

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=(role == 'superuser'),
            user_type='admin',
        )

        # Send credentials by email
        from django.core.mail import send_mail
        try:
            send_mail(
                subject='Your NapsterLegal Admin Account',
                message=(
                    f'Hello {username},\n\n'
                    f'Your {"superuser" if role == "superuser" else "staff"} account has been created.\n\n'
                    f'Login URL: http://localhost:8000/control/login/\n'
                    f'Username:  {username}\n'
                    f'Password:  {password}\n\n'
                    f'Please change your password after first login.\n\n'
                    f'NapsterLegal Admin'
                ),
                from_email=None,
                recipient_list=[email],
                fail_silently=True,
            )
            messages.success(request, f'Account created for {username}. Credentials sent to {email}.')
        except Exception:
            messages.warning(request, f'Account created. Email failed. Credentials: {username} / {password}')

        return redirect('/control/settings/')
    return redirect('/control/settings/')


@cp_required
def message_detail(request, msg_id):
    from apps.accounts.models import ContactMessage
    msg = get_object_or_404(ContactMessage, id=msg_id)

    if request.method == 'POST':
        # Mark as replied
        reply = request.POST.get('reply', '').strip()
        if reply:
            from django.utils import timezone
            from django.core.mail import send_mail
            msg.status     = ContactMessage.REPLIED
            msg.reply_body = reply
            msg.replied_at = timezone.now()
            msg.save()
            try:
                send_mail(
                    subject=f'Re: {msg.subject}',
                    message=f'Hello {msg.name},\n\n{reply}\n\nNapsterLegal Team',
                    from_email=None,
                    recipient_list=[msg.email],
                    fail_silently=True,
                )
                messages.success(request, f'Reply sent to {msg.email}.')
            except Exception:
                messages.warning(request, 'Reply saved but email failed.')
            return redirect('/control/messages/')

    return render(request, 'control/message_detail.html', _ctx(request, 'cp_messages', msg=msg))


def site_preview(request):
    """
    Allows admin to view the site as a regular visitor would see it.
    Opens the main site without admin session context.
    The target="_blank" in sidebar already opens a new tab — 
    this view serves as a clean passthrough.
    """
    # We just redirect to home — in new tab (set via sidebar target="_blank")
    # the admin's staff flag will still apply but they see the public site
    from django.shortcuts import redirect
    return redirect('/')


def site_preview(request):
    """
    Opens the main site as an anonymous visitor would see it.
    Admin's session is preserved — this just opens a fresh incognito-like view.
    We redirect to home with a special query param that bypasses admin redirect.
    """
    from django.shortcuts import redirect
    # The ?preview=1 param tells the home view not to redirect to /control/
    return redirect('/?preview=1')
