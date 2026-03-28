from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from .models import CustomUser, ArtistProfile
from .forms import RegisterForm, LoginForm, ProfileEditForm, ArtistProfileEditForm


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
                return redirect(request.GET.get('next', 'home'))
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
    from apps.social.models import Like
    liked_tracks = Like.objects.filter(
        user=request.user
    ).select_related('track', 'track__artist').order_by('-created_at')[:12]
    playlists = request.user.playlists.filter(
        is_public=True).order_by('-created_at')[:6]
    following = request.user.following.select_related(
        'following').order_by('-created_at')[:12]
    return render(request, 'accounts/profile.html', {
        'profile_user': request.user,
        'liked_tracks': liked_tracks,
        'playlists':    playlists,
        'following':    following,
    })


@login_required
def profile_edit(request):
    """Let any user edit their own profile without touching the admin."""
    user = request.user
    artist_form = None

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=user)
        if user.is_artist():
            artist_form = ArtistProfileEditForm(
                request.POST, instance=user.artist_profile)

        if form.is_valid() and (artist_form is None or artist_form.is_valid()):
            form.save()
            if artist_form:
                ap = artist_form.save(commit=False)
                # Save social links from individual fields
                ap.social_links = {
                    'instagram': request.POST.get('instagram', ''),
                    'twitter':   request.POST.get('twitter', ''),
                    'website':   request.POST.get('website', ''),
                }
                ap.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = ProfileEditForm(instance=user)
        if user.is_artist():
            artist_form = ArtistProfileEditForm(instance=user.artist_profile)

    return render(request, 'accounts/profile_edit.html', {
        'form':        form,
        'artist_form': artist_form,
    })


# ── CUSTOM ADMIN VIEWS ────────────────────────────────────────────────────────

def admin_required(view_func):
    """Decorator: only staff/superuser can access."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, 'Admin access required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_dashboard(request):
    """Custom admin dashboard — overview of the entire platform."""
    from apps.music.models import Track, Genre
    from apps.analytics.models import PlayEvent, SearchLog

    # Platform stats
    total_users   = CustomUser.objects.count()
    total_artists = ArtistProfile.objects.count()
    total_tracks  = Track.objects.filter(is_published=True).count()
    total_plays   = Track.objects.aggregate(
        total=Sum('play_count'))['total'] or 0

    # Recent users
    recent_users  = CustomUser.objects.order_by('-date_joined')[:10]

    # Recent tracks
    recent_tracks = Track.objects.select_related(
        'artist').order_by('-uploaded_at')[:10]

    # Analytics from MariaDB (admin eyes only — raw data never shown to users/artists)
    recent_events   = PlayEvent.objects.using('analytics').order_by('-timestamp')[:20]
    recent_searches = SearchLog.objects.using('analytics').order_by('-timestamp')[:10]

    # Aggregate stats from MariaDB
    from django.db.models import Avg, Count as DCount
    avg_listen = PlayEvent.objects.using('analytics').aggregate(
        avg=Avg('listened_duration'))['avg'] or 0
    completed_count = PlayEvent.objects.using('analytics').filter(
        completed=True).count()
    total_events = PlayEvent.objects.using('analytics').count()
    completion_rate = round(
        (completed_count / total_events * 100) if total_events > 0 else 0, 1)

    # Device breakdown
    device_stats = PlayEvent.objects.using('analytics').values(
        'device_type').annotate(count=DCount('id')).order_by('-count')

    # Top tracks by play count
    top_tracks = Track.objects.filter(
        is_published=True).order_by('-play_count')[:10]

    return render(request, 'admin_panel/dashboard.html', {
        'total_users':       total_users,
        'total_artists':     total_artists,
        'total_tracks':      total_tracks,
        'total_plays':       total_plays,
        'recent_users':      recent_users,
        'recent_tracks':     recent_tracks,
        'recent_events':     recent_events,
        'recent_searches':   recent_searches,
        'top_tracks':        top_tracks,
        'avg_listen':        round(avg_listen, 1),
        'completion_rate':   completion_rate,
        'total_events':      total_events,
        'device_stats':      device_stats,
    })


@admin_required
def admin_users(request):
    """Manage all users."""
    users = CustomUser.objects.order_by('-date_joined')
    return render(request, 'admin_panel/users.html', {'users': users})


@admin_required
def admin_toggle_user(request, user_id):
    """Activate / deactivate a user account."""
    user = get_object_or_404(CustomUser, id=user_id)
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    status = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'User {user.username} {status}.')
    return redirect('admin_users')


@admin_required
def admin_tracks(request):
    """Manage all tracks."""
    from apps.music.models import Track
    tracks = Track.objects.select_related(
        'artist', 'genre').order_by('-uploaded_at')
    return render(request, 'admin_panel/tracks.html', {'tracks': tracks})


@admin_required
def admin_toggle_track(request, track_id):
    """Publish / unpublish a track."""
    from apps.music.models import Track
    track = get_object_or_404(Track, id=track_id)
    track.is_published = not track.is_published
    track.save(update_fields=['is_published'])
    status = 'published' if track.is_published else 'unpublished'
    messages.success(request, f'"{track.title}" {status}.')
    return redirect('admin_tracks')
