from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Track, Album, Genre
from .forms import TrackUploadForm
from apps.accounts.models import ArtistProfile


def home(request):
    trending   = Track.objects.filter(is_published=True).order_by('-play_count')[:8]
    new_tracks = Track.objects.filter(is_published=True).order_by('-uploaded_at')[:8]
    genres     = Genre.objects.all()[:8]
    return render(request, 'music/home.html', {
        'trending':   trending,
        'new_tracks': new_tracks,
        'genres':     genres,
    })


def track_detail(request, track_id):
    track    = get_object_or_404(Track, id=track_id, is_published=True)
    related  = Track.objects.filter(
        genre=track.genre, is_published=True
    ).exclude(id=track.id)[:6]
    comments = track.comments.select_related('user').order_by('created_at')
    return render(request, 'music/track_detail.html', {
        'track':    track,
        'related':  related,
        'comments': comments,
    })


def artist_page(request, artist_id):
    """Public artist profile page."""
    artist = get_object_or_404(ArtistProfile, id=artist_id)
    tracks = Track.objects.filter(
        artist=artist, is_published=True
    ).order_by('-play_count')
    albums = artist.albums.filter(is_published=True).order_by('-release_date')

    is_following = False
    if request.user.is_authenticated:
        from apps.social.models import Follow
        is_following = Follow.objects.filter(
            follower=request.user, following=artist
        ).exists()

    return render(request, 'music/artist_page.html', {
        'artist':         artist,
        'tracks':         tracks,
        'albums':         albums,
        'is_following':   is_following,
        'total_plays':    sum(t.play_count for t in tracks),
        'follower_count': artist.followers.count(),
    })


@login_required
def upload_track(request):
    if not request.user.is_artist():
        messages.error(request, 'Only artists can upload tracks.')
        return redirect('home')

    if request.method == 'POST':
        form = TrackUploadForm(request.POST, request.FILES)
        if form.is_valid():
            track = form.save(commit=False)
            track.artist = request.user.artist_profile
            try:
                import mutagen
                audio = mutagen.File(track.audio_file)
                if audio and hasattr(audio, 'info'):
                    track.duration = int(audio.info.length)
            except Exception:
                pass
            track.save()
            form.save_m2m()
            messages.success(request, f'"{track.title}" uploaded successfully!')
            return redirect('track_detail', track_id=track.id)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = TrackUploadForm()

    return render(request, 'music/upload.html', {'form': form})


@login_required
def artist_dashboard(request):
    if not request.user.is_artist():
        messages.error(request, 'Only artists can access the dashboard.')
        return redirect('home')

    artist      = request.user.artist_profile
    tracks      = Track.objects.filter(artist=artist).order_by('-uploaded_at')
    total_plays = sum(t.play_count for t in tracks)
    total_likes = sum(t.like_count for t in tracks)

    return render(request, 'music/artist_dashboard.html', {
        'artist':      artist,
        'tracks':      tracks,
        'total_plays': total_plays,
        'total_likes': total_likes,
    })
