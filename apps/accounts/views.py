from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser, ArtistProfile
from .forms import RegisterForm, LoginForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.user_type == CustomUser.ARTIST:
                ArtistProfile.objects.create(
                    user=user, stage_name=user.username)
            login(request, user)
            messages.success(request, f'Welcome to NapsterLegal, {user.username}!')
            return redirect('home')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            if user:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                # Redirect to role-specific dashboard
                next_url = request.GET.get('next', '')
                if next_url:
                    return redirect(next_url)
                if user.is_artist():
                    return redirect('artist_home_dashboard')
                return redirect('listener_dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')


@login_required
def profile_view(request):
    from apps.music.models import Track
    from apps.social.models import Like

    liked_tracks = Like.objects.filter(
        user=request.user
    ).select_related('track', 'track__artist').order_by('-created_at')[:12]

    playlists = request.user.playlists.filter(
        is_public=True
    ).order_by('-created_at')[:6]

    following = request.user.following.select_related(
        'following'
    ).order_by('-created_at')[:12]

    return render(request, 'accounts/profile.html', {
        'profile_user':  request.user,
        'liked_tracks':  liked_tracks,
        'playlists':     playlists,
        'following':     following,
    })


@login_required
def profile_edit(request):
    if request.method == 'POST':
        # Handle basic user fields
        user = request.user
        user.email      = request.POST.get('email', user.email).strip()
        user.first_name = request.POST.get('first_name', user.first_name).strip()
        user.last_name  = request.POST.get('last_name', user.last_name).strip()
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
        user.save()

        # Handle artist profile fields if applicable
        if user.is_artist() and hasattr(user, 'artist_profile'):
            ap = user.artist_profile
            ap.stage_name = request.POST.get('stage_name', ap.stage_name).strip()
            ap.bio        = request.POST.get('bio', ap.bio).strip()
            if 'profile_image' in request.FILES:
                ap.profile_image = request.FILES['profile_image']
            ap.save()

        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')

    return render(request, 'accounts/profile_edit.html', {
        'profile_user': request.user,
        'artist':       getattr(request.user, 'artist_profile', None),
    })


# ── ADMIN VIEWS ───────────────────────────────────────────────────────────────

def _require_admin(request):
    """Returns True if the request should be blocked (not staff/superuser)."""
    return not (request.user.is_authenticated and
                (request.user.is_staff or request.user.is_superuser))


@login_required
def admin_dashboard(request):
    if _require_admin(request):
        messages.error(request, 'Access denied.')
        return redirect('home')

    from apps.music.models import Track
    return render(request, 'admin_panel/dashboard.html', {
        'total_users':   CustomUser.objects.count(),
        'total_tracks':  Track.objects.count(),
        'total_artists': ArtistProfile.objects.count(),
        'flagged_tracks': Track.objects.filter(acoustid_status='failed').count(),
        'pending_artists': ArtistProfile.objects.filter(
            verification_status=ArtistProfile.PENDING
        ).count(),
    })


@login_required
def admin_users(request):
    if _require_admin(request):
        messages.error(request, 'Access denied.')
        return redirect('home')

    users = CustomUser.objects.order_by('-date_joined')
    return render(request, 'admin_panel/users.html', {'users': users})


@login_required
def admin_tracks(request):
    if _require_admin(request):
        messages.error(request, 'Access denied.')
        return redirect('home')

    from apps.music.models import Track
    tracks = Track.objects.select_related('artist').order_by('-uploaded_at')
    return render(request, 'admin_panel/tracks.html', {'tracks': tracks})


@login_required
def admin_artists(request):
    if _require_admin(request):
        messages.error(request, 'Access denied.')
        return redirect('home')

    artists = ArtistProfile.objects.select_related('user').order_by('-user__date_joined')
    return render(request, 'admin_panel/artists.html', {'artists': artists})


@login_required
def admin_verify_artist(request, artist_id):
    if _require_admin(request):
        messages.error(request, 'Access denied.')
        return redirect('home')

    artist = get_object_or_404(ArtistProfile, id=artist_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        note   = request.POST.get('note', '').strip()

        if action == 'approve':
            artist.verification_status = ArtistProfile.VERIFIED
            artist.verification_note   = note
            artist.save()
            messages.success(request, f'{artist.stage_name} approved.')
        elif action == 'reject':
            artist.verification_status = ArtistProfile.REJECTED
            artist.verification_note   = note
            artist.save()
            messages.warning(request, f'{artist.stage_name} rejected.')
        else:
            messages.error(request, 'Unknown action.')

        return redirect('admin_artists')

    return render(request, 'admin_panel/verify_artist.html', {'artist': artist})


@login_required
def admin_toggle_user(request, user_id):
    if _require_admin(request):
        messages.error(request, 'Access denied.')
        return redirect('home')

    if request.method == 'POST':
        user = get_object_or_404(CustomUser, id=user_id)
        if user == request.user:
            messages.error(request, 'You cannot deactivate your own account.')
        else:
            user.is_active = not user.is_active
            user.save()
            state = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'{user.username} {state}.')

    return redirect('admin_users')


@login_required
def admin_toggle_track(request, track_id):
    if _require_admin(request):
        messages.error(request, 'Access denied.')
        return redirect('home')

    if request.method == 'POST':
        from apps.music.models import Track
        track = get_object_or_404(Track, id=track_id)
        track.is_published = not track.is_published
        track.save()
        state = 'published' if track.is_published else 'unpublished'
        messages.success(request, f'"{track.title}" {state}.')

    return redirect('admin_tracks')

@login_required
def listener_dashboard(request):
    # Superusers must use /control/ — not the listener interface
    if request.user.is_superuser or request.user.is_staff:
        return redirect('/control/')
    """Custom post-login dashboard for listeners."""
    from apps.social.models import Like, Follow
    from apps.music.models import Track
    from apps.playlists.models import Playlist

    liked_tracks = Like.objects.filter(
        user=request.user
    ).select_related('track','track__artist').order_by('-created_at')[:12]

    playlists = request.user.playlists.all().order_by('-created_at')

    following = request.user.following.select_related(
        'following').order_by('-created_at')

    # Recent tracks from followed artists
    followed_artist_ids = following.values_list('following_id', flat=True)
    recent_from_followed = Track.objects.filter(
        artist_id__in=followed_artist_ids,
        is_published=True
    ).exclude(acoustid_status='failed').order_by('-uploaded_at')[:8]

    # Announcements from followed artists
    from apps.music.models import Announcement
    announcements = Announcement.objects.filter(
        artist_id__in=followed_artist_ids
    ).select_related('artist').order_by('-created_at')[:10]

    nav_items = [
        ("M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6", "Discover Music",  "/"),
        ("M9 19V6l12-3v13M9 19c0 1.1-1.34 2-3 2s-3-.9-3-2z",          "My Playlists",   "/playlists/"),
        ("M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",               "Search",         "/search/"),
        ("M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z", "My Profile", "/profile/"),
        ("M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z", "Subscription", "/pricing/my-subscription/"),
        ("M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z", "Settings", "/accounts/profile/edit/"),
    ]

    return render(request, 'accounts/listener_dashboard.html', {
        'liked_tracks':         liked_tracks,
        'playlists':            playlists,
        'following':            following,
        'recent_from_followed': recent_from_followed,
        'announcements':        announcements,
        'nav_items':            nav_items,
    })


@login_required  
def artist_home_dashboard(request):
    # Superusers must use /control/ — not artist pages
    if request.user.is_superuser or request.user.is_staff:
        return redirect('/control/')
    """Custom post-login dashboard for artists."""
    if not request.user.is_artist():
        return redirect('listener_dashboard')

    from apps.music.models import Track, Announcement
    artist  = request.user.artist_profile
    tracks  = Track.objects.filter(
        artist=artist
    ).exclude(acoustid_status='failed').order_by('-uploaded_at')

    total_plays = sum(t.play_count for t in tracks)
    total_likes = sum(t.like_count for t in tracks)

    PER_STREAM_RATE = 0.004
    total_estimated = round(total_plays * PER_STREAM_RATE, 2)

    announcements = Announcement.objects.filter(
        artist=artist).order_by('-created_at')[:5]

    # Sidebar links for artist dashboard
    sidebar_links = [
        ('/accounts/dashboard/artist/', 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z', 'Overview', True),
        ('/upload/', 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12', 'Upload Track', False),
        ('/dashboard/', 'M9 19V6l12-3v13M9 19c0 1.1-1.34 2-3 2s-3-.9-3-2z', 'My Tracks', False),
        (f'/artist/{artist.id}/', 'M15 12a3 3 0 11-6 0 3 3 0 016 0M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z', 'Public Profile', False),
        ('/accounts/profile/edit/', 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z', 'Edit Profile', False),
        ('/pricing/my-subscription/', 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z', 'Subscription', False),
    ]

    # Stats for display
    stats = [
        (tracks.count(), 'Tracks', 'linear-gradient(90deg,#4F8EF7,#7C3AED)'),
        (total_plays,    'Total Plays', 'linear-gradient(90deg,#2DD4BF,#4F8EF7)'),
        (total_likes,    'Total Likes', 'linear-gradient(90deg,#F472B6,#8B5CF6)'),
        (f'${total_estimated}', 'Est. Earnings', 'linear-gradient(90deg,#34D399,#2DD4BF)'),
    ]

    # Listen-based earnings from MariaDB
    listen_based_earnings = 0
    try:
        from apps.analytics.models import PlayEvent
        from django.db.models import Sum as DSum
        track_ids = [str(t.id) for t in tracks]
        result = PlayEvent.objects.using('analytics').filter(
            track_id__in=track_ids
        ).aggregate(total=DSum('listened_duration'))
        actual_secs = result['total'] or 0
        listen_based_earnings = round(actual_secs * (0.001/30), 2)
    except Exception:
        pass

    return render(request, 'accounts/artist_home_dashboard.html', {
        'artist':               artist,
        'tracks':               tracks,
        'total_plays':          total_plays,
        'total_likes':          total_likes,
        'total_estimated':      total_estimated,
        'per_stream_rate':      PER_STREAM_RATE,
        'announcements':        announcements,
        'follower_count':       artist.followers.count(),
        'sidebar_links':        sidebar_links,
        'stats':                stats,
        'listen_based_earnings':listen_based_earnings,
    })


@login_required
def settings_view(request):
    """User settings page — profile + app preferences + language."""
    if request.method == 'POST':
        from .forms import ProfileEditForm, ArtistProfileEditForm
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            if request.user.is_artist():
                ap = request.user.artist_profile
                ap.stage_name = request.POST.get('stage_name', ap.stage_name)
                ap.country    = request.POST.get('country', ap.country)
                ap.social_links = {
                    'instagram': request.POST.get('instagram', ''),
                    'twitter':   request.POST.get('twitter', ''),
                    'website':   request.POST.get('website', ''),
                }
                ap.save()
            messages.success(request, 'Settings saved!')
            return redirect('settings')
        else:
            messages.error(request, 'Please fix the errors below.')

    available_languages = [
        ('en', 'English',    '🇬🇧'),
        ('fr', 'Français',   '🇫🇷'),
        ('es', 'Español',    '🇪🇸'),
        ('de', 'Deutsch',    '🇩🇪'),
        ('pt', 'Português',  '🇵🇹'),
    ]

    quality_options = [
        ('auto',    'Auto',    'Best for connection'),
        ('normal',  'Normal',  '128kbps MP3'),
        ('high',    'High',    '320kbps MP3'),
        ('lossless','Lossless','FLAC — Premium'),
    ]

    social_fields = [
        ('Instagram', '@yourhandle'),
        ('Twitter',   '@yourhandle'),
        ('Website',   'https://yoursite.com'),
    ]

    return render(request, 'accounts/settings.html', {
        'available_languages': available_languages,
        'quality_options':     quality_options,
        'social_fields':       social_fields,
    })


@login_required
def settings_view(request):
    """Unified settings page for all user types."""
    if request.method == 'POST':
        from .forms import ProfileEditForm
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            if request.user.is_artist():
                ap = request.user.artist_profile
                ap.stage_name = request.POST.get('stage_name', ap.stage_name)
                ap.country    = request.POST.get('country', ap.country)
                ap.social_links = {
                    'instagram': request.POST.get('instagram', ''),
                    'twitter':   request.POST.get('twitter', ''),
                    'website':   request.POST.get('website', ''),
                }
                ap.save()
            messages.success(request, 'Settings saved successfully!')
            return redirect('settings')
        else:
            messages.error(request, 'Please fix the errors below.')

    available_languages = [
        ('en', 'English',   '🇬🇧'),
        ('fr', 'Français',  '🇫🇷'),
        ('es', 'Español',   '🇪🇸'),
        ('de', 'Deutsch',   '🇩🇪'),
        ('pt', 'Português', '🇵🇹'),
    ]
    quality_options = [
        ('auto',    'Auto',    'Adapts to connection'),
        ('normal',  'Normal',  '128kbps MP3'),
        ('high',    'High',    '320kbps MP3'),
        ('lossless','Lossless','FLAC — Premium only'),
    ]
    return render(request, 'accounts/settings.html', {
        'available_languages': available_languages,
        'quality_options':     quality_options,
    })


def contact_view(request):
    """Contact the admin. Accessible from Settings page."""
    if request.method == 'POST':
        from .models import ContactMessage
        name    = request.POST.get('name', '').strip()
        email   = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        body    = request.POST.get('body', '').strip()

        if name and email and subject and body:
            ContactMessage.objects.create(
                sender  = request.user if request.user.is_authenticated else None,
                name    = name,
                email   = email,
                subject = subject,
                body    = body,
            )
            messages.success(request, 'Message sent! The admin will reply to your email.')
            return redirect('contact')
        else:
            messages.error(request, 'All fields are required.')

    return render(request, 'accounts/contact.html', {
        'prefill_name':  request.user.username if request.user.is_authenticated else '',
        'prefill_email': request.user.email    if request.user.is_authenticated else '',
    })
