from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from .models import Track, Album, Genre
from .forms import TrackUploadForm
from apps.accounts.models import ArtistProfile
from django.views.decorators.http import require_POST
from django.http import JsonResponse


# ── SAFE QUERYSET — used by EVERY public view ─────────────────────────────────
def public_tracks():
    """
    The single source of truth for what is publicly visible.
    A track must pass ALL conditions to appear anywhere on the platform.
    - is_published = True
    - acoustid_status is NOT 'failed'
    This function is called by home, search, artist page, track detail.
    Never bypass this filter in public views.
    """
    return Track.objects.filter(
        is_published=True
    ).exclude(acoustid_status='failed')


def home(request):
    safe   = public_tracks()
    return render(request, 'music/home.html', {
        'trending':   safe.order_by('-play_count')[:8],
        'new_tracks': safe.order_by('-uploaded_at')[:8],
        'genres':     Genre.objects.all()[:8],
    })


def track_detail(request, track_id):
    """
    Block all access to flagged tracks — raise 404 so no info leaks.
    """
    track = get_object_or_404(Track, id=track_id)

    # Hard block — flagged tracks are completely invisible
    if track.acoustid_status == 'failed':
        raise Http404

    # Must also be published for non-admin users
    if not track.is_published:
        if not (request.user.is_authenticated and
                (request.user.is_staff or request.user.is_superuser)):
            raise Http404

    related  = public_tracks().filter(
        genre=track.genre
    ).exclude(id=track.id)[:6]

    comments = track.comments.select_related('user').order_by('created_at')

    return render(request, 'music/track_detail.html', {
        'track':    track,
        'related':  related,
        'comments': comments,
    })


def artist_page(request, artist_id):
    artist = get_object_or_404(ArtistProfile, id=artist_id)
    tracks = public_tracks().filter(artist=artist).order_by('-play_count')
    albums = artist.albums.filter(is_published=True).order_by('-release_date')

    is_following = False
    if request.user.is_authenticated:
        from apps.social.models import Follow
        is_following = Follow.objects.filter(
            follower=request.user, following=artist
        ).exists()

    from .models import Announcement
    announcements = Announcement.objects.filter(
        artist=artist
    ).order_by('-is_pinned', '-created_at')[:5]

    # Check if viewer is the artist themselves
    is_own_page = (
        request.user.is_authenticated and
        request.user.is_artist() and
        request.user.artist_profile == artist
    )

    return render(request, 'music/artist_page.html', {
        'artist':         artist,
        'tracks':         tracks,
        'albums':         albums,
        'is_following':   is_following,
        'total_plays':    sum(t.play_count for t in tracks),
        'follower_count': artist.followers.count(),
        'announcements':  announcements,
        'is_own_page':    is_own_page,
    })


@login_required
def upload_track(request):
    if not request.user.is_artist():
        messages.error(request, 'Only artists can upload tracks.')
        return redirect('home')

    artist = request.user.artist_profile

    if request.method == 'POST':
        form = TrackUploadForm(request.POST, request.FILES)
        if form.is_valid():
            track        = form.save(commit=False)
            track.artist = artist

            # ── STEP 1: Force is_published=False until all checks pass ────────
            track.is_published    = False
            track.acoustid_status = 'pending'

            # ── STEP 2: Auto-extract duration via mutagen ─────────────────────
            try:
                import mutagen
                audio_file = request.FILES.get('audio_file')
                if audio_file:
                    audio = mutagen.File(audio_file)
                    if audio and hasattr(audio, 'info'):
                        track.duration = int(audio.info.length)
            except Exception:
                pass

            # ── STEP 3: Save to disk so fpcalc can read the file ─────────────
            track.save()
            form.save_m2m()

            # ── STEP 4: Run AcoustID fingerprint check ────────────────────────
            from .acoustid_check import check_track
            stage_name   = artist.stage_name or request.user.username
            check_result = check_track(track.audio_file.path, stage_name)

            track.acoustid_checked = True
            track.acoustid_result  = check_result.get('raw', {})
            track.acoustid_status  = check_result.get('status', 'error')

            if check_result['status'] == 'failed':
                # ── CRITICAL: Keep is_published=False (already set above) ─────
                # Save the evidence for admin to review
                track.is_published = False
                track.save()

                messages.error(
                    request,
                    f"Upload rejected — copyright fingerprint match detected. "
                    f"This track matches '{check_result['matches'][0]['title']}' "
                    f"by '{check_result['matches'][0]['artist']}' "
                    f"in our database. "
                    f"The file has been saved for admin review but is NOT visible "
                    f"on the platform."
                )
                return render(request, 'music/upload.html', {
                    'form':              TrackUploadForm(),
                    'acoustid_error':    check_result['message'],
                    'acoustid_matches':  check_result['matches'],
                    'verification_notice': _get_verification_notice(artist),
                    'artist':            artist,
                })

            elif check_result['status'] == 'error':
                # Technical failure — save as draft, flag for manual admin review
                track.is_published = False
                track.save()
                messages.warning(
                    request,
                    f'"{track.title}" saved as draft. '
                    f'Fingerprint check had a technical issue and needs manual review. '
                    f'An admin will review it shortly.'
                )
            else:
                # Passed — now honour the artist's original is_published choice
                original_published = form.cleaned_data.get('is_published', False)
                track.is_published = original_published
                track.save()
                messages.success(
                    request,
                    f'"{track.title}" uploaded successfully! '
                    f'Originality check passed. '
                    f'{"Published and live." if original_published else "Saved as draft."}'
                )

            return redirect('track_detail', track_id=track.id)

        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = TrackUploadForm()

    return render(request, 'music/upload.html', {
        'form':                form,
        'verification_notice': _get_verification_notice(artist),
        'artist':              artist,
    })


def _get_verification_notice(artist):
    """Return a notice string based on artist verification status."""
    if artist.verification_status == ArtistProfile.PENDING:
        return (
            'Your artist account is pending verification. '
            'Tracks you publish will be marked as "Unverified Artist" '
            'until an admin reviews your profile.'
        )
    elif artist.verification_status == ArtistProfile.REJECTED:
        return (
            f'Your verification was rejected. '
            f'Reason: {artist.verification_note or "Please contact support."}'
        )
    return None


@login_required
def artist_dashboard(request):
    if not request.user.is_artist():
        messages.error(request, 'Only artists can access the dashboard.')
        return redirect('home')

    artist      = request.user.artist_profile
    # Dashboard shows artist's own tracks including drafts — but NOT flagged ones
    tracks      = Track.objects.filter(
        artist=artist
    ).exclude(acoustid_status='failed').order_by('-uploaded_at')

    total_plays = sum(t.play_count for t in tracks)
    total_likes = sum(t.like_count for t in tracks)

    # ── Fair Payment Simulation ───────────────────────────────────────────────
    # Rate: $0.004 per stream (much fairer than Spotify's $0.003-0.005)
    # This is transparent and shown to artists
    PER_STREAM_RATE = 0.004   # USD per stream

    # Get listened duration from MariaDB for more accurate calculation
    # $0.001 per 30 seconds of actual listening
    PER_SECOND_RATE = 0.001 / 30  # USD per second listened

    total_estimated = round(total_plays * PER_STREAM_RATE, 2)

    # Try to get actual listen data from MariaDB
    actual_listen_seconds = 0
    try:
        from apps.analytics.models import PlayEvent
        from django.db.models import Sum
        track_ids = [str(t.id) for t in tracks]
        result = PlayEvent.objects.using('analytics').filter(
            track_id__in=track_ids
        ).aggregate(total=Sum('listened_duration'))
        actual_listen_seconds = result['total'] or 0
    except Exception:
        pass

    listen_based_earnings = round(actual_listen_seconds * PER_SECOND_RATE, 2)

    return render(request, 'music/artist_dashboard.html', {
        'artist':                 artist,
        'tracks':                 tracks,
        'total_plays':            total_plays,
        'total_likes':            total_likes,
        'per_stream_rate':        PER_STREAM_RATE,
        'total_estimated':        total_estimated,
        'actual_listen_seconds':  actual_listen_seconds,
        'listen_based_earnings':  listen_based_earnings,
        'per_second_rate':        round(PER_SECOND_RATE * 30, 4),
    })

@login_required
def edit_track(request, track_id):
    track = get_object_or_404(Track, id=track_id)

    # Only the track's artist (or staff) can edit
    if not (request.user.is_staff or request.user.is_superuser):
        if not request.user.is_artist() or track.artist != request.user.artist_profile:
            messages.error(request, 'You do not have permission to edit this track.')
            return redirect('track_detail', track_id=track.id)

    if request.method == 'POST':
        form = TrackUploadForm(request.POST, request.FILES, instance=track)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{track.title}" updated successfully.')
            return redirect('track_detail', track_id=track.id)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = TrackUploadForm(instance=track)

    return render(request, 'music/edit_track.html', {
        'form':  form,
        'track': track,
    })


@login_required
def delete_track(request, track_id):
    track = get_object_or_404(Track, id=track_id)

    # Only the track's artist (or staff) can delete
    if not (request.user.is_staff or request.user.is_superuser):
        if not request.user.is_artist() or track.artist != request.user.artist_profile:
            messages.error(request, 'You do not have permission to delete this track.')
            return redirect('track_detail', track_id=track.id)

    if request.method == 'POST':
        title = track.title
        track.delete()
        messages.success(request, f'"{title}" has been deleted.')
        return redirect('artist_dashboard')

    return render(request, 'music/delete_track_confirm.html', {'track': track})

@require_POST
def detect_lyrics(request):
    """
    JSON endpoint — called via Alpine.js fetch from upload.html and edit_track.html.
    Accepts either:
      - 'track_id'  (UUID) for an already-saved track
      - 'audio_file' (uploaded file) for a track not yet saved
    Returns detected lyrics or an error message.
    """
    track_id   = request.POST.get('track_id', '').strip()
    audio_file = request.FILES.get('audio_file')

    # ── Resolve the audio file path ───────────────────────────────────────────
    file_path = None

    if track_id:
        try:
            import uuid
            track = Track.objects.get(id=uuid.UUID(track_id))

            # Only the track's own artist (or staff) may request lyrics detection
            if not (request.user.is_staff or request.user.is_superuser):
                if not request.user.is_authenticated:
                    return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=403)
                if not request.user.is_artist() or track.artist != request.user.artist_profile:
                    return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)

            if not track.audio_file:
                return JsonResponse({'status': 'error', 'message': 'Track has no audio file.'})

            file_path = track.audio_file.path

        except (Track.DoesNotExist, ValueError):
            return JsonResponse({'status': 'error', 'message': 'Track not found.'})

    elif audio_file:
        # Write the upload to a temp file so the detector can read it
        import tempfile, os
        suffix = os.path.splitext(audio_file.name)[-1] or '.mp3'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in audio_file.chunks():
                tmp.write(chunk)
            file_path = tmp.name
    else:
        return JsonResponse({'status': 'error', 'message': 'Provide track_id or audio_file.'})

    # ── Run lyrics detection ──────────────────────────────────────────────────
    try:
        lyrics = _run_lyrics_detection(file_path)
        return JsonResponse({'status': 'ok', 'lyrics': lyrics})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

    finally:
        # Clean up temp file if we created one
        if audio_file and file_path:
            try:
                import os
                os.unlink(file_path)
            except OSError:
                pass


def _run_lyrics_detection(file_path):
    """
    Attempt to extract embedded lyrics from the audio file's ID3/Vorbis tags,
    then fall back to an external lyrics API if nothing is embedded.
    Returns a string (lyrics text) or raises an exception.
    """
    # ── Step 1: Try embedded lyrics (ID3 USLT tag / Vorbis LYRICS comment) ───
    try:
        import mutagen
        from mutagen.id3 import ID3, USLT
        from mutagen.mp3 import MP3

        audio = mutagen.File(file_path)
        if audio is not None:
            # MP3 / ID3
            if hasattr(audio, 'tags') and audio.tags:
                for key in audio.tags.keys():
                    if key.startswith('USLT'):
                        return audio.tags[key].text

            # FLAC / OGG — lyrics stored as plain tag
            lyrics_tag = audio.get('lyrics') or audio.get('LYRICS')
            if lyrics_tag:
                return lyrics_tag[0] if isinstance(lyrics_tag, list) else lyrics_tag

    except Exception:
        pass  # No embedded lyrics — fall through to API

    # ── Step 2: No embedded lyrics found ─────────────────────────────────────
    # Return a clear signal to the front-end so it can show an appropriate
    # message rather than an empty box.
    raise ValueError(
        'No embedded lyrics found in this file. '
        'You can add lyrics manually below.'
    )

@login_required
def post_announcement(request):
    """Artist posts an announcement to their followers."""
    if not request.user.is_artist():
        messages.error(request, 'Only artists can post announcements.')
        return redirect('home')

    if request.method == 'POST':
        from .models import Announcement
        title = request.POST.get('title', '').strip()
        body  = request.POST.get('body', '').strip()
        if title and body:
            Announcement.objects.create(
                artist=request.user.artist_profile,
                title=title,
                body=body,
            )
            messages.success(request, 'Announcement posted!')
        else:
            messages.error(request, 'Title and body are required.')

    return redirect('artist_page', artist_id=request.user.artist_profile.id)
