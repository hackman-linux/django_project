"""
NapsterLegal — Admin Control Panel Views
=========================================
ROLE SYSTEM:
  Superuser  → Full access to everything
  Staff      → Limited to their assigned role only:
    'users'    → /control/users/ only
    'tracks'   → /control/tracks/ only
    'artists'  → /control/artists/ only
    'messages' → /control/messages/ only
    'analytics'→ /control/analytics/ only

CustomUser.admin_role field (CharField) stores the assigned role.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse

User = get_user_model()


# ── ROLE DEFINITIONS ─────────────────────────────────────────────────────────
ROLE_PERMISSIONS = {
    'users':     ['/control/users/'],
    'tracks':    ['/control/tracks/'],
    'artists':   ['/control/artists/'],
    'messages':  ['/control/messages/'],
    'analytics': ['/control/analytics/', '/control/logs/'],
    'full':      None,  # None = all access
}

ROLE_LABELS = {
    'users':     'User Manager',
    'tracks':    'Content Moderator',
    'artists':   'Artist Reviewer',
    'messages':  'Support Agent',
    'analytics': 'Analytics Viewer',
    'full':      'Full Admin',
}


def cp_required(view_func):
    """Decorator: requires staff/superuser session in control panel."""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('cp_authenticated'):
            return redirect('/control/login/')
        admin_user = _get_cp_user(request)
        if not admin_user:
            request.session.pop('cp_authenticated', None)
            return redirect('/control/login/')
        # Role-based path restriction — only for non-superusers
        if not admin_user.is_superuser:
            # Get role from session (set at login time) or from model
            role = request.session.get('cp_role') or getattr(admin_user, 'admin_role', 'full') or 'full'
            allowed_paths = ROLE_PERMISSIONS.get(role)
            # Always allow My Space and Dashboard overview for everyone
            always_allowed = ['/control/my-space/', '/control/preview/']
            current_path   = request.path
            if allowed_paths is not None:  # None means full access
                if (not any(current_path.startswith(p) for p in allowed_paths) and
                        not any(current_path.startswith(p) for p in always_allowed) and
                        current_path != '/control/'):
                    # Redirect staff to their allowed section
                    return redirect(allowed_paths[0])
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def _get_cp_user(request):
    uid = request.session.get('cp_user_id')
    if not uid:
        return None
    try:
        return User.objects.get(id=uid, is_staff=True)
    except User.DoesNotExist:
        return None


def _sidebar(request):
    """
    Auto-generate sidebar based on user role.
    Superuser sees everything. Staff sees only their section.
    """
    admin_user  = _get_cp_user(request)
    is_super    = admin_user and admin_user.is_superuser
    role        = getattr(admin_user, 'admin_role', 'full') if admin_user else 'full'
    current     = request.path

    ALL_ITEMS = [
        ('dashboard',  'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6z M14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6z M4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2z M14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z',
         'Overview',   '/control/',                     ['full','users','tracks','artists','messages','analytics']),
        ('users',      'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
         'Users',      '/control/users/',               ['full','users']),
        ('tracks',     'M9 19V6l12-3v13M9 19c0 1.1-1.34 2-3 2s-3-.9-3-2z',
         'Tracks',     '/control/tracks/',              ['full','tracks']),
        ('artists',    'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
         'Artists',    '/control/artists/',             ['full','artists']),
        ('messages',   'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
         'Messages',   '/control/messages/',            ['full','messages']),
        ('analytics',  'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
         'Analytics',  '/control/analytics/',           ['full','analytics']),
        ('logs',       'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
         'IP Logs',    '/control/logs/',                ['full','analytics']),
        ('my-space',   'M9 19V6l12-3v13M9 19c0 1.1-1.34 2-3 2s-3-.9-3-2z',
         'My Space',   '/control/my-space/',            ['full','users','tracks','artists','messages','analytics']),
    ]

    # Superuser-only items
    SUPER_ONLY = [
        ('settings', 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
         'Settings',  '/control/settings/', []),
    ]

    items = []
    for key, icon, label, url, allowed_roles in ALL_ITEMS:
        if is_super or role in allowed_roles:
            items.append((key, icon, label, url, current.startswith(url) and url != '/control/' or current == url))

    if is_super:
        for key, icon, label, url, _ in SUPER_ONLY:
            items.append((key, icon, label, url, current.startswith(url)))

    return items


def _ctx(request, active, **kwargs):
    """Build template context with admin user + sidebar."""
    admin_user = _get_cp_user(request)
    return {
        'admin_user': admin_user,
        'sidebar':    _sidebar(request),
        'active':     active,
        'role_label': ROLE_LABELS.get(getattr(admin_user, 'admin_role', 'full') or 'full', ''),
        **kwargs
    }


# ── AUTH ─────────────────────────────────────────────────────────────────────

def admin_login(request):
    if request.session.get('cp_authenticated'):
        return redirect('/control/')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user     = authenticate(request, username=username, password=password)

        if user and (user.is_staff or user.is_superuser):
            request.session['cp_authenticated'] = True
            request.session['cp_user_id']       = str(user.id)
            request.session.set_expiry(28800)  # 8 hours

            # Store role in session for fast access
            role = getattr(user, 'admin_role', 'full') or 'full'
            request.session['cp_role'] = role

            # Redirect based on role
            if user.is_superuser or role == 'full':
                return redirect('/control/')
            allowed = ROLE_PERMISSIONS.get(role, ['/control/'])
            return redirect(allowed[0] if allowed else '/control/')
        else:
            error = 'Invalid credentials or insufficient permissions.'

    return render(request, 'control/login.html', {'error': error})


def admin_logout(request):
    request.session.pop('cp_authenticated', None)
    request.session.pop('cp_user_id', None)
    return redirect('/control/login/')


def site_preview(request):
    """Opens main site as visitor — bypasses admin redirect."""
    return redirect('/?preview=1')


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

@cp_required
def dashboard(request):
    from apps.music.models import Track
    from apps.accounts.models import ArtistProfile, ContactMessage

    try:
        sub_count = User.objects.filter(subscriptions__status='active').distinct().count()
    except Exception:
        sub_count = 0

    try:
        flagged_count = Track.objects.filter(acoustid_status='failed').count()
    except Exception:
        flagged_count = 0

    try:
        open_msgs = ContactMessage.objects.filter(status='open').count()
    except Exception:
        open_msgs = 0

    platform_stats = [
        ('Total Users',       User.objects.count(),                         'linear-gradient(90deg,#4F8EF7,#8B5CF6)'),
        ('Published Tracks',  Track.objects.filter(is_published=True).count(), 'linear-gradient(90deg,#2DD4BF,#4F8EF7)'),
        ('Active Subscribers',sub_count,                                    'linear-gradient(90deg,#34D399,#2DD4BF)'),
        ('Open Messages',     open_msgs,                                    'linear-gradient(90deg,#F59E0B,#EF4444)'),
    ]

    analytics_rows = []
    try:
        from apps.analytics.models import PlayEvent
        total = PlayEvent.objects.using('analytics').count()
        analytics_rows = [
            ('Play Events (MariaDB)', total),
            ('Flagged Tracks',        flagged_count),
        ]
    except Exception:
        pass

    recent_users = User.objects.filter(
        is_staff=False).order_by('-date_joined')[:8]
    top_tracks   = Track.objects.filter(
        is_published=True).order_by('-play_count')[:6]

    return render(request, 'control/dashboard.html', _ctx(
        request, 'dashboard',
        platform_stats=platform_stats,
        analytics_rows=analytics_rows,
        recent_users=recent_users,
        top_tracks_enum=enumerate(top_tracks, 1),
    ))


# ── USERS ─────────────────────────────────────────────────────────────────────

@cp_required
def users_list(request):
    q           = request.GET.get('q', '')
    filter_type = request.GET.get('type', '')
    users = User.objects.all().order_by('-date_joined')
    if q:
        users = users.filter(username__icontains=q) | users.filter(email__icontains=q)
    if filter_type:
        users = users.filter(user_type=filter_type)
    return render(request, 'control/users.html',
                  _ctx(request, 'users', users=users, q=q, filter_type=filter_type))


@cp_required
def toggle_user(request, user_id):
    if not _get_cp_user(request).is_superuser:
        messages.error(request, 'Only superusers can ban/unban users.')
        return redirect('/control/users/')
    user = get_object_or_404(User, id=user_id)
    if user.is_superuser:
        messages.error(request, 'Cannot ban the superuser account.')
        return redirect('/control/users/')
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    action = 'activated' if user.is_active else 'banned'
    messages.success(request, f'{user.username} has been {action}.')
    return redirect('/control/users/')


@cp_required
def create_staff(request):
    """Superuser creates staff accounts and emails credentials."""
    admin_user = _get_cp_user(request)
    if not admin_user.is_superuser:
        messages.error(request, 'Only the superuser can create staff accounts.')
        return redirect('/control/settings/')

    if request.method == 'POST':
        username    = request.POST.get('username', '').strip()
        email       = request.POST.get('email', '').strip()
        role        = request.POST.get('role', 'users')
        is_superuser= request.POST.get('is_superuser') == 'on'
        custom_pw   = request.POST.get('password', '').strip()

        if not username or not email:
            messages.error(request, 'Username and email are required.')
            return redirect('/control/settings/')

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already taken.')
            return redirect('/control/settings/')

        # Use custom password if provided, otherwise auto-generate
        import secrets, string
        password = custom_pw if custom_pw else ''.join(
            secrets.choice(string.ascii_letters + string.digits + '!@#$%^')
            for _ in range(14))

        user = User.objects.create_user(
            username     = username,
            email        = email,
            password     = password,
            is_staff     = True,
            is_superuser = is_superuser,
            user_type    = 'admin',
        )
        # Assign role (stored on CustomUser)
        try:
            user.admin_role = role
            user.save(update_fields=['admin_role'])
        except Exception:
            pass  # admin_role field may not exist yet if migration pending

        # Send credentials by email
        from django.core.mail import send_mail
        from django.conf import settings as djsettings
        role_label = ROLE_LABELS.get(role, role)
        try:
            send_mail(
                subject = 'Your NapsterLegal Admin Account Credentials',
                message = (
                    f'Hello {username},\n\n'
                    f'An admin account has been created for you on NapsterLegal.\n\n'
                    f'Role: {role_label}\n'
                    f'Login URL: http://localhost:8000/control/login/\n'
                    f'Username:  {username}\n'
                    f'Password:  {password}\n\n'
                    f'Please change your password immediately after first login.\n'
                    f'Your role ({role_label}) grants you access to: '
                    f'{", ".join(ROLE_PERMISSIONS.get(role, ["/control/"]))}\n\n'
                    f'NapsterLegal — Control Panel\n'
                    f'This is an automated message. Do not reply.'
                ),
                from_email   = getattr(djsettings, 'DEFAULT_FROM_EMAIL', None),
                recipient_list=[email],
                fail_silently = False,
            )
            messages.success(request,
                f'✅ Account created for {username} ({role_label}). '
                f'Credentials sent to {email}.')
        except Exception as e:
            messages.warning(request,
                f'Account created but email failed: {e}\n'
                f'Manual credentials — {username} / {password}')

    return redirect('/control/settings/')


# ── TRACKS ────────────────────────────────────────────────────────────────────

@cp_required
def tracks_list(request):
    from apps.music.models import Track
    q             = request.GET.get('q', '')
    filter_status = request.GET.get('status', '')
    tracks        = Track.objects.all().select_related(
        'artist', 'genre').order_by('-uploaded_at')

    if q:
        tracks = tracks.filter(title__icontains=q)
    if filter_status == 'live':
        tracks = tracks.filter(is_published=True)
    elif filter_status == 'draft':
        tracks = tracks.filter(is_published=False, acoustid_status__in=['pending','passed',''])
    elif filter_status == 'flagged':
        tracks = tracks.filter(acoustid_status='failed')

    flagged = Track.objects.filter(acoustid_status='failed').count()
    return render(request, 'control/tracks.html',
                  _ctx(request, 'tracks', tracks=tracks,
                       q=q, filter_status=filter_status, flagged=flagged))


@cp_required
def toggle_track(request, track_id):
    from apps.music.models import Track
    track = get_object_or_404(Track, id=track_id)
    if track.acoustid_status == 'failed':
        # Admin manually approving a flagged track clears the flag
        track.acoustid_status = 'passed'
        track.is_published    = True
        track.save(update_fields=['acoustid_status', 'is_published'])
        messages.success(request, f'"{track.title}" approved and published.')
    else:
        track.is_published = not track.is_published
        track.save(update_fields=['is_published'])
        action = 'published' if track.is_published else 'unpublished'
        messages.success(request, f'"{track.title}" {action}.')
    return redirect('/control/tracks/')


# ── ARTISTS ───────────────────────────────────────────────────────────────────

@cp_required
def artists_list(request):
    from apps.accounts.models import ArtistProfile
    tab    = request.GET.get('tab', 'pending')
    counts = {
        'pending':  ArtistProfile.objects.filter(verification_status='pending').count(),
        'verified': ArtistProfile.objects.filter(verification_status='verified').count(),
        'rejected': ArtistProfile.objects.filter(verification_status='rejected').count(),
    }
    artists_qs = ArtistProfile.objects.filter(
        verification_status=tab).select_related('user').order_by('-user__date_joined')
    tabs = [
        ('pending',  'Pending',  counts['pending']),
        ('verified', 'Verified', counts['verified']),
        ('rejected', 'Rejected', counts['rejected']),
    ]
    return render(request, 'control/artists.html',
                  _ctx(request, 'artists', artists=artists_qs,
                       tab=tab, counts=counts, tabs=tabs))


@cp_required
def verify_artist(request, artist_id):
    from apps.accounts.models import ArtistProfile
    artist = get_object_or_404(ArtistProfile, id=artist_id)

    if request.method == 'POST':
        new_status = request.POST.get('verification_status', 'pending')
        note       = request.POST.get('verification_note', '').strip()
        artist.verification_status  = new_status
        artist.verification_note    = note
        artist.save(update_fields=['verification_status', 'verification_note'])

        try:
            from apps.accounts.models import Notification
            if new_status == 'verified':
                Notification.send(
                    recipient   = artist.user,
                    notif_type  = Notification.TYPE_TRACK_APPROVED,
                    title       = 'Artist account verified! 🎉',
                    body        = 'Your artist account is now verified. Tracks publish automatically on clean fingerprint.',
                    link        = '/accounts/dashboard/artist/',
                    sender_name = 'NapsterLegal Admin',
                )
            elif new_status == 'rejected':
                Notification.send(
                    recipient   = artist.user,
                    notif_type  = Notification.TYPE_TRACK_REJECTED,
                    title       = 'Artist verification update',
                    body        = f'Your application was not approved.{" Reason: " + note if note else ""}',
                    link        = '/accounts/contact/',
                    sender_name = 'NapsterLegal Admin',
                )
        except Exception:
            pass

        messages.success(request, f'{artist.stage_name} → {artist.get_verification_status_display()}')
        return redirect('/control/artists/')

    artist_info = [
        ('Username',   artist.user.username,  '#F0F4FF'),
        ('Email',      artist.user.email,     '#94A3B8'),
        ('Stage Name', artist.stage_name,     '#F0F4FF'),
        ('Real Name',  artist.real_name or '⚠ Not provided',
                       '#F0F4FF' if artist.real_name else '#F87171'),
        ('Country',    getattr(artist, 'country', '—') or '—', '#94A3B8'),
        ('Status',     artist.get_verification_status_display(),
                       '#FDE68A' if artist.verification_status == 'pending'
                       else '#6EE7B7' if artist.verification_status == 'verified'
                       else '#FCA5A5'),
        ('Joined',     artist.user.date_joined.strftime('%B %d, %Y'), '#4A5568'),
    ]
    checklist = [
        'Real name has been provided',
        'Work sample URL is valid and opens their music',
        'Artist name on external platform matches stage name',
        'No flagged/duplicate tracks from this artist',
        'Social media presence matches claimed identity',
    ]
    return render(request, 'control/verify_artist.html',
                  _ctx(request, 'artists', artist=artist,
                       artist_info=artist_info, checklist=checklist))


# ── ANALYTICS + LOGS ──────────────────────────────────────────────────────────

@cp_required
def analytics_view(request):
    ctx = {}
    try:
        from apps.analytics.models import PlayEvent
        from django.db.models import Count, Avg
        ctx['total_events']  = PlayEvent.objects.using('analytics').count()
        ctx['avg_listen']    = int(PlayEvent.objects.using('analytics').aggregate(
            a=Avg('listened_duration'))['a'] or 0)
        total  = max(ctx['total_events'], 1)
        compl  = PlayEvent.objects.using('analytics').filter(completed=True).count()
        ctx['completed_rate'] = round(compl / total * 100, 1)
        ctx['device_stats']  = (PlayEvent.objects.using('analytics')
            .values('device_type').annotate(count=Count('id')).order_by('-count'))
        ctx['country_stats'] = (PlayEvent.objects.using('analytics')
            .values('country_code').annotate(count=Count('id')).order_by('-count')[:10])
        try:
            from apps.analytics.models import SearchLog
            ctx['total_searches'] = SearchLog.objects.using('analytics').count()
            ctx['recent_searches']= SearchLog.objects.using('analytics').order_by('-timestamp')[:20]
        except Exception:
            ctx['total_searches'] = 0
            ctx['recent_searches'] = []
    except Exception as e:
        ctx['error'] = str(e)

    return render(request, 'control/analytics.html', _ctx(request, 'analytics', **ctx))


@cp_required
def logs_view(request):
    events = []
    try:
        from apps.analytics.models import PlayEvent
        events = PlayEvent.objects.using('analytics').order_by('-timestamp')[:100]
    except Exception as e:
        messages.warning(request, f'MariaDB unavailable: {e}')
    return render(request, 'control/logs.html', _ctx(request, 'logs', events=events))


# ── MESSAGES ──────────────────────────────────────────────────────────────────

@cp_required
def messages_view(request):
    try:
        from apps.accounts.models import ContactMessage
        contact_msgs = ContactMessage.objects.all().order_by('-created_at')
    except Exception:
        contact_msgs = []
    return render(request, 'control/messages.html',
                  _ctx(request, 'messages', contact_msgs=contact_msgs))


@cp_required
def message_detail(request, msg_id):
    from apps.accounts.models import ContactMessage
    msg = get_object_or_404(ContactMessage, id=msg_id)

    if request.method == 'POST':
        reply = request.POST.get('reply', '').strip()
        if reply:
            from django.utils import timezone
            from django.core.mail import send_mail
            msg.status      = ContactMessage.REPLIED if hasattr(
                ContactMessage, 'REPLIED') else 'replied'
            msg.reply_body  = reply
            msg.replied_at  = timezone.now()
            msg.save()

            # Send email reply
            try:
                send_mail(
                    subject      = f'Re: {msg.subject}',
                    message      = f'Hello {msg.name},\n\n{reply}\n\nNapsterLegal Team',
                    from_email   = None,
                    recipient_list=[msg.email],
                    fail_silently= False,
                )
                messages.success(request, f'Reply sent to {msg.email}.')
            except Exception as e:
                messages.warning(request, f'Reply saved but email error: {e}')

            # In-app notification
            if msg.sender:
                try:
                    from apps.accounts.models import Notification
                    Notification.send(
                        recipient   = msg.sender,
                        notif_type  = Notification.TYPE_ADMIN_REPLY,
                        title       = f'Admin replied to: {msg.subject}',
                        body        = reply,
                        link        = '/accounts/contact/',
                        sender_name = 'NapsterLegal Admin',
                    )
                except Exception:
                    pass

            return redirect('/control/messages/')

    return render(request, 'control/message_detail.html',
                  _ctx(request, 'messages', msg=msg))


# ── SETTINGS ─────────────────────────────────────────────────────────────────

@cp_required
def app_settings(request):
    admin_user = _get_cp_user(request)
    if not admin_user.is_superuser:
        messages.error(request, 'Only the superuser can access settings.')
        return redirect('/control/')

    settings_fields = [
        ('Platform Name',        'site_name',        'NapsterLegal',               'Shown in all emails and page titles'),
        ('Support Email',        'support_email',    'support@napsterlegal.com',   'Outgoing email sender'),
        ('Contact Email',        'contact_email',    'contact@napsterlegal.com',   'Shown on contact page'),
        ('Artist Pool %',        'artist_share',     '40',                         '% of subscription revenue to artists'),
        ('Owner Profit %',       'owner_share',      '35',                         'Platform owner income'),
        ('Production Costs %',   'production_share', '25',                         'Servers, CDN, APIs'),
        ('Free Stream Rate ($)', 'rate_free',        '0.0005',                     'USD per stream (ad-supported)'),
        ('Premium Stream Rate',  'rate_premium',     '0.003',                      'USD per stream (Premium)'),
        ('Pro Stream Rate',      'rate_pro',         '0.005',                      'USD per stream (Pro)'),
        ('Free Audio Quality',   'quality_free',     '128kbps',                    'Bitrate for free users'),
        ('Premium Quality',      'quality_premium',  '320kbps',                    'Bitrate for paid users'),
        ('Pro Quality',          'quality_pro',      'FLAC',                       'Lossless for Listener Pro'),
        ('Max Upload MB',        'max_upload_mb',    '200',                        'Maximum audio file size'),
        ('Review Hold Hours',    'review_hold',      '24',                         'Hours before flagged track hidden'),
        ('Default Language',     'default_language', 'fr',                         'Default for Francophone Africa'),
    ]

    # Revenue simulation
    try:
        from apps.payments.earnings import simulate_earnings
        sim = simulate_earnings(
            monthly_subscribers_premium=50,
            monthly_subscribers_pro=10,
            total_artist_plays=50_000,
            artist_plays=5_000,
        )
    except Exception:
        sim = None

    # Staff accounts managed by superuser
    staff_accounts = User.objects.filter(
        is_staff=True, is_superuser=False).order_by('username')

    return render(request, 'control/settings.html', _ctx(
        request, 'settings',
        settings_fields   = settings_fields,
        revenue_simulation= sim,
        staff_accounts    = staff_accounts,
        role_labels       = ROLE_LABELS,
        role_perms        = ROLE_PERMISSIONS,
    ))


# ── MY SPACE ─────────────────────────────────────────────────────────────────

@cp_required
def admin_my_space(request):
    from apps.music.models import Track
    from django.db.models import Q

    safe_tracks = Track.objects.filter(is_published=True).filter(
        Q(acoustid_status='passed') |
        Q(acoustid_status__isnull=True) |
        Q(acoustid_status='')
    ).order_by('-uploaded_at')[:20]

    liked = []
    admin_user = _get_cp_user(request)
    try:
        from apps.social.models import Like
        liked = Like.objects.filter(user=admin_user).select_related(
            'track', 'track__artist')[:12]
    except Exception:
        pass

    return render(request, 'control/my_space.html',
                  _ctx(request, 'my-space', new_tracks=safe_tracks, liked=liked))
