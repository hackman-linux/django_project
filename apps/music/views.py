from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Track, Album, Genre
from .forms import TrackUploadForm
from apps.accounts.models import ArtistProfile


def home(request):
    # Only verified artists' tracks on homepage trending/new
    trending   = Track.objects.filter(
        is_published=True,
        artist__verification_status='verified'
    ).order_by('-play_count')[:8]

    # Fall back to all published if no verified artists yet
    if not trending.exists():
        trending = Track.objects.filter(is_published=True).order_by('-play_count')[:8]

    new_tracks = Track.objects.filter(is_published=True).order_by('-uploaded_at')[:8]
    genres     = Genre.objects.all()
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


def _run_acoustid(track, stage_name):
    """Run AcoustID check and update track fields. Returns check_result dict."""
    from .acoustid_check import check_track as acoustid_check
    audio_path   = track.audio_file.path
    check_result = acoustid_check(audio_path, stage_name)
    track.acoustid_checked = True
    track.acoustid_result  = check_result['raw']
    track.acoustid_status  = check_result['status']
    track.save(update_fields=['acoustid_checked', 'acoustid_result', 'acoustid_status'])
    return check_result


@login_required
def upload_track(request):
    if not request.user.is_artist():
        messages.error(request, 'Only artists can upload tracks.')
        return redirect('home')

    artist     = request.user.artist_profile
    all_genres = Genre.objects.all().order_by('name')

    if request.method == 'POST':
        form = TrackUploadForm(request.POST, request.FILES)
        if form.is_valid():
            track        = form.save(commit=False)
            track.artist = artist

            # Auto-extract duration
            try:
                import mutagen
                audio = mutagen.File(track.audio_file)
                if audio and hasattr(audio, 'info'):
                    track.duration = int(audio.info.length)
            except Exception:
                pass

            track.save()
            form.save_m2m()

            # AcoustID check
            check_result = _run_acoustid(track, artist.stage_name or request.user.username)

            if check_result['status'] == 'failed':
                track.audio_file.delete(save=False)
                track.delete()
                messages.error(request, f"Upload rejected: {check_result['message']}")
                return render(request, 'music/upload.html', {
                    'form':             TrackUploadForm(),
                    'all_genres':       all_genres,
                    'acoustid_error':   check_result['message'],
                    'acoustid_matches': check_result['matches'],
                    'artist':           artist,
                })
            elif check_result['status'] == 'error':
                messages.warning(
                    request,
                    f'"{track.title}" uploaded but flagged for manual review. '
                    f'Fingerprint check had a technical issue.'
                )
            else:
                messages.success(
                    request,
                    f'"{track.title}" uploaded successfully! Originality check passed.'
                )

            return redirect('track_detail', track_id=track.id)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = TrackUploadForm()

    verification_notice = None
    if artist.verification_status == ArtistProfile.PENDING:
        verification_notice = (
            'Your artist account is pending verification. Your tracks will be '
            'marked as "Unverified Artist" until an admin reviews your profile.'
        )
    elif artist.verification_status == ArtistProfile.REJECTED:
        verification_notice = (
            f'Your artist account verification was rejected. '
            f'Reason: {artist.verification_note or "Please contact support."}'
        )

    return render(request, 'music/upload.html', {
        'form':                form,
        'all_genres':          all_genres,
        'verification_notice': verification_notice,
        'artist':              artist,
    })


@login_required
def edit_track(request, track_id):
    """Artist edits their own track metadata and optionally replaces the audio."""
    if not request.user.is_artist():
        messages.error(request, 'Only artists can edit tracks.')
        return redirect('home')

    artist = request.user.artist_profile
    track  = get_object_or_404(Track, id=track_id, artist=artist)
    all_genres = Genre.objects.all().order_by('name')

    if request.method == 'POST':
        # Keep old audio if no new file provided
        old_audio = track.audio_file
        form = TrackUploadForm(request.POST, request.FILES, instance=track)

        if form.is_valid():
            updated = form.save(commit=False)

            # If no new audio uploaded, keep the existing one
            if not request.FILES.get('audio_file'):
                updated.audio_file = old_audio
            else:
                # New audio uploaded — re-extract duration and re-run AcoustID
                try:
                    import mutagen
                    audio = mutagen.File(updated.audio_file)
                    if audio and hasattr(audio, 'info'):
                        updated.duration = int(audio.info.length)
                except Exception:
                    pass
                updated.save()
                check_result = _run_acoustid(
                    updated, artist.stage_name or request.user.username)
                if check_result['status'] == 'failed':
                    updated.audio_file.delete(save=False)
                    updated.audio_file = old_audio
                    updated.save()
                    messages.error(request, f"New audio rejected: {check_result['message']}")
                    return render(request, 'music/edit_track.html', {
                        'form': form, 'track': track, 'all_genres': all_genres,
                    })

            updated.save()
            form.save_m2m()
            messages.success(request, f'"{track.title}" updated successfully.')
            return redirect('artist_dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = TrackUploadForm(instance=track)

    return render(request, 'music/edit_track.html', {
        'form':       form,
        'track':      track,
        'all_genres': all_genres,
    })


@login_required
def delete_track(request, track_id):
    """Artist deletes their own track."""
    if not request.user.is_artist():
        messages.error(request, 'Only artists can delete tracks.')
        return redirect('home')

    artist = request.user.artist_profile
    track  = get_object_or_404(Track, id=track_id, artist=artist)

    if request.method == 'POST':
        title = track.title
        # Delete the audio and cover files from disk
        if track.audio_file:
            track.audio_file.delete(save=False)
        if track.cover_image:
            track.cover_image.delete(save=False)
        track.delete()
        messages.success(request, f'"{title}" has been deleted.')
        return redirect('artist_dashboard')

    # If GET request, redirect to dashboard (delete only via POST)
    return redirect('artist_dashboard')


@login_required
def detect_lyrics(request):
    """
    API endpoint — POST an audio file (or track_id for existing track).
    Returns detected lyrics using speech-to-text / lyrics matching.

    Strategy:
    1. Try Vosk (offline, free) for speech recognition on the audio
    2. Fall back to AcoustID match → fetch lyrics from lyrics.ovh API
    3. If neither works → return helpful message

    The artist can Accept or Discard the result before saving.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    import tempfile
    import os

    audio_file = request.FILES.get('audio_file')
    track_id   = request.POST.get('track_id')

    audio_path = None
    temp_path  = None

    try:
        if audio_file:
            # Save uploaded file to temp location
            suffix = os.path.splitext(audio_file.name)[1] or '.mp3'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                for chunk in audio_file.chunks():
                    tmp.write(chunk)
                temp_path = tmp.name
            audio_path = temp_path

        elif track_id:
            # Use existing track's audio file
            try:
                import uuid
                track = Track.objects.get(
                    id=uuid.UUID(track_id),
                    artist=request.user.artist_profile
                )
                audio_path = track.audio_file.path
            except (Track.DoesNotExist, ValueError, AttributeError):
                return JsonResponse({'message': 'Track not found.'}, status=404)

        if not audio_path:
            return JsonResponse({'message': 'No audio file provided.'}, status=400)

        # ── Strategy 1: AcoustID match → lyrics.ovh ──────────────────
        lyrics = _fetch_lyrics_via_acoustid(audio_path)
        if lyrics:
            return JsonResponse({'lyrics': lyrics, 'source': 'acoustid+lyrics.ovh'})

        # ── Strategy 2: No match found ────────────────────────────────
        return JsonResponse({
            'message': (
                'No lyrics detected automatically. This track may be instrumental, '
                'or not yet in the lyrics database. You can add lyrics manually below.'
            )
        })

    except Exception as e:
        return JsonResponse({
            'message': f'Detection error: {str(e)}. Please add lyrics manually.'
        })
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def _fetch_lyrics_via_acoustid(audio_path):
    """
    1. Fingerprint the audio with fpcalc
    2. Look up AcoustID → get artist + title
    3. Fetch lyrics from lyrics.ovh (free, no API key needed)
    Returns lyrics string or None.
    """
    try:
        import subprocess, json, requests

        # Step 1: fingerprint
        result = subprocess.run(
            ['fpcalc', '-json', audio_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None

        data        = json.loads(result.stdout)
        duration    = data['duration']
        fingerprint = data['fingerprint']

        # Step 2: AcoustID lookup
        import acoustid
        from django.conf import settings
        api_key = getattr(settings, 'ACOUSTID_API_KEY',
                          __import__('os').environ.get('ACOUSTID_API_KEY', ''))

        matches = []
        results = acoustid.lookup(api_key, fingerprint, duration, meta='recordings')
        for score, rec_id, title, artist in acoustid.parse_lookup_result(results):
            if score > 0.5 and title and artist:
                matches.append((score, title, artist))

        if not matches:
            return None

        # Take highest confidence match
        matches.sort(reverse=True)
        _, title, artist = matches[0]

        # Step 3: fetch lyrics from lyrics.ovh
        resp = requests.get(
            f'https://api.lyrics.ovh/v1/{artist}/{title}',
            timeout=10
        )
        if resp.status_code == 200:
            ldata = resp.json()
            lyrics = ldata.get('lyrics', '').strip()
            if lyrics:
                # Add header so artist knows the source
                header = f"# {title} — {artist}\n# Lyrics auto-detected via AcoustID + lyrics.ovh\n# Review carefully before saving\n\n"
                return header + lyrics

        return None

    except Exception:
        return None


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
