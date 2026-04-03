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

    return render(request, 'accounts/listener_dashboard.html', {
        'liked_tracks':         liked_tracks,
        'playlists':            playlists,
        'following':            following,
        'recent_from_followed': recent_from_followed,
        'announcements':        announcements,
    })


@login_required
def artist_home_dashboard(request):
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

    return render(request, 'accounts/artist_home_dashboard.html', {
        'artist':          artist,
        'tracks':          tracks,
        'total_plays':     total_plays,
        'total_likes':     total_likes,
        'total_estimated': total_estimated,
        'per_stream_rate': PER_STREAM_RATE,
        'announcements':   announcements,
        'follower_count':  artist.followers.count(),
    })
