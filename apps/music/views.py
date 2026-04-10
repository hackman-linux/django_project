"""
NapsterLegal — Music Views
Includes: AcoustID fingerprint check, duplicate detection,
          genre handling, lyrics detection, rights protection.
"""
import os
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, JsonResponse
from django.db.models import Sum

from .models import Track, Album, Genre
from apps.accounts.models import ArtistProfile

from django.http import JsonResponse
from django.views.decorators.http import require_POST


def public_tracks():
    return Track.objects.filter(
        is_published=True
    ).exclude(acoustid_status='failed').select_related('artist')


# ── RIGHTS CATALOGUE ─────────────────────────────────────────────────────────
LICENSE_INFO = {
    'all_rights': {
        'name':  'All Rights Reserved',
        'short': 'ARR',
        'desc':  'Full copyright. No reproduction without explicit permission.',
        'color': '#EF4444',
    },
    'cc_by': {
        'name':  'Creative Commons CC-BY 4.0',
        'short': 'CC-BY',
        'desc':  'Others may share/adapt with credit. Commercial use allowed.',
        'color': '#4F8EF7',
    },
    'cc_by_nc': {
        'name':  'Creative Commons CC-BY-NC 4.0',
        'short': 'CC-BY-NC',
        'desc':  'Share/adapt with credit. No commercial use.',
        'color': '#F59E0B',
    },
    'cc_by_sa': {
        'name':  'Creative Commons CC-BY-SA 4.0',
        'short': 'CC-BY-SA',
        'desc':  'Share/adapt with credit. Derivatives must use same license.',
        'color': '#8B5CF6',
    },
    'cc_by_nd': {
        'name':  'Creative Commons CC-BY-ND 4.0',
        'short': 'CC-BY-ND',
        'desc':  'Share with credit. No derivatives allowed.',
        'color': '#2DD4BF',
    },
    'public_domain': {
        'name':  'Public Domain (CC0)',
        'short': 'CC0',
        'desc':  'No rights reserved. Free for any use worldwide.',
        'color': '#34D399',
    },
}


def home(request):
    """Landing page."""
    # Admin redirect — but NOT if they're previewing the site
    if (request.user.is_authenticated and
        (request.user.is_staff or request.user.is_superuser) and
        request.GET.get('preview') != '1'):
        return redirect('/control/')

    from apps.music.trending import get_trending_tracks
    safe = public_tracks()
    trending_data = get_trending_tracks(limit=12)
    trending_tracks = [t['track'] for t in trending_data]

    new_from_followed = []
    if request.user.is_authenticated:
        try:
            from apps.social.models import Follow
            followed_ids = Follow.objects.filter(
                follower=request.user).values_list('artist_id', flat=True)
            new_from_followed = list(
                safe.filter(artist__id__in=followed_ids).order_by('-uploaded_at')[:8])
        except Exception:
            pass

    return render(request, 'music/home.html', {
        'trending_tracks':   trending_tracks,
        'new_tracks':        safe.order_by('-uploaded_at')[:12],
        'featured_tracks':   safe.filter(is_featured=True)[:6] if hasattr(Track, 'is_featured') else [],
        'genres':            Genre.objects.all()[:10],
        'new_from_followed': new_from_followed,
        'license_info':      LICENSE_INFO,
    })


def track_detail(request, track_id):
    track    = get_object_or_404(Track, id=track_id, is_published=True)
    related  = public_tracks().filter(genre=track.genre).exclude(id=track.id)[:6]
    comments = track.comments.select_related('user').order_by('created_at')
    return render(request, 'music/track_detail.html', {
        'track':        track,
        'related':      related,
        'comments':     comments,
        'license_info': LICENSE_INFO.get(track.license_type, {}),
    })


def artist_page(request, artist_id):
    artist       = get_object_or_404(ArtistProfile, id=artist_id)
    tracks       = public_tracks().filter(artist=artist).order_by('-uploaded_at')
    albums       = Album.objects.filter(artist=artist, is_published=True)
    announcements = []
    try:
        from apps.music.models import Announcement
        announcements = Announcement.objects.filter(artist=artist).order_by('-created_at')[:5]
    except Exception:
        pass
    is_following = False
    if request.user.is_authenticated:
        try:
            from apps.social.models import Follow
            is_following = Follow.objects.filter(
                follower=request.user, artist=artist).exists()
        except Exception:
            pass
    return render(request, 'music/artist_page.html', {
        'artist':        artist,
        'tracks':        tracks,
        'albums':        albums,
        'announcements': announcements,
        'is_following':  is_following,
        'follower_count':artist.followers.count() if hasattr(artist, 'followers') else 0,
    })


@login_required
def upload_track(request):
    """
    Artist track upload with:
    - AcoustID fingerprint check (duplicate detection)
    - If match found → BLOCKED from publishing, flagged for admin review
    - Genre selection (populated from DB)
    - Lyrics detection (auto-detect language)
    - Full rights/license selection with descriptions
    - Artist identity verification requirement
    """
    if not request.user.is_artist():
        messages.error(request, 'Only verified artists can upload tracks.')
        return redirect('home')

    artist = request.user.artist_profile

    # ── ARTIST VERIFICATION GATE ──────────────────────────────────────────
    if artist.verification_status == 'rejected':
        messages.error(request,
            'Your artist account has been rejected. '
            'Contact support if you believe this is an error.')
        return redirect('artist_home_dashboard')

    # Genres for the dropdown
    genres = Genre.objects.all().order_by('name')

    if request.method == 'POST':
        # ── BASIC FIELD EXTRACTION ────────────────────────────────────────
        title       = request.POST.get('title', '').strip()
        genre_id    = request.POST.get('genre', '')
        license_type= request.POST.get('license_type', 'all_rights')
        lyrics      = request.POST.get('lyrics', '').strip()
        is_explicit = request.POST.get('is_explicit') == 'on'
        bpm_raw     = request.POST.get('bpm', '').strip()
        audio_file  = request.FILES.get('audio_file')
        cover_image = request.FILES.get('cover_image')
        tags_raw    = request.POST.get('tags', '').strip()

        # Validate required fields
        errors = []
        if not title:
            errors.append('Track title is required.')
        if not audio_file:
            errors.append('Audio file is required.')
        if not genre_id:
            errors.append('Please select a genre.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'music/upload.html', {
                'genres':       genres,
                'license_info': LICENSE_INFO,
                'post':         request.POST,
            })

        # ── AUDIO FILE VALIDATION ─────────────────────────────────────────
        allowed_mimes = ['audio/mpeg', 'audio/mp3', 'audio/wav',
                         'audio/flac', 'audio/x-flac', 'audio/ogg']
        allowed_exts  = ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac']
        ext = os.path.splitext(audio_file.name)[1].lower()

        if ext not in allowed_exts:
            messages.error(request,
                f'File type "{ext}" not allowed. Use: {", ".join(allowed_exts)}')
            return render(request, 'music/upload.html', {
                'genres': genres, 'license_info': LICENSE_INFO, 'post': request.POST})

        if audio_file.size > 200 * 1024 * 1024:  # 200MB max
            messages.error(request, 'File too large. Maximum is 200MB.')
            return render(request, 'music/upload.html', {
                'genres': genres, 'license_info': LICENSE_INFO, 'post': request.POST})

        # ── SAVE TRACK (unpublished initially) ────────────────────────────
        genre = Genre.objects.filter(id=genre_id).first()
        bpm   = int(bpm_raw) if bpm_raw.isdigit() else None

        # Auto-detect lyrics language if lyrics provided
        lyrics_language = ''
        if lyrics:
            lyrics_language = _detect_lyrics_language(lyrics)

        track = Track(
            title        = title,
            artist       = artist,
            genre        = genre,
            audio_file   = audio_file,
            cover_image  = cover_image,
            lyrics       = lyrics,
            is_explicit  = is_explicit,
            license_type = license_type,
            bpm          = bpm,
            is_published = False,  # NEVER published until fingerprint passes
            acoustid_status = 'pending',
        )

        # Auto-extract duration
        try:
            import mutagen
            audio = mutagen.File(audio_file)
            if audio and hasattr(audio, 'info'):
                track.duration = int(audio.info.length)
        except Exception:
            pass

        track.save()

        # ── ACOUSTID FINGERPRINT CHECK ────────────────────────────────────
        acoustid_result = _run_acoustid_check(track)

        if acoustid_result['status'] == 'duplicate':
            # CRITICAL: Duplicate found — track stays unpublished, artist flagged
            track.acoustid_status  = 'failed'
            track.acoustid_score   = acoustid_result.get('score', 0)
            track.acoustid_result  = acoustid_result.get('matched_recording', '')
            track.is_published     = False
            track.save()

            # Flag the artist for admin investigation
            _flag_artist_for_investigation(artist, track, acoustid_result)

            messages.warning(request,
                f'⚠️ Your track "{title}" was detected as a potential duplicate '
                f'of an existing recording (confidence: '
                f'{acoustid_result.get("score", 0)*100:.0f}%). '
                f'It will NOT be published until an admin reviews it. '
                f'If this is your original work, the admin will verify and approve it. '
                f'Ref: {track.id}')
            return redirect('artist_home_dashboard')

        elif acoustid_result['status'] == 'passed':
            track.acoustid_status = 'passed'
            track.acoustid_score  = acoustid_result.get('score', 0)
            track.is_published    = True  # Auto-publish on clean pass
            track.save()
            messages.success(request,
                f'✅ "{title}" uploaded and published! Fingerprint verified.')

        elif acoustid_result['status'] == 'error':
            # AcoustID unavailable → hold for manual review
            track.acoustid_status = 'error'
            track.is_published    = False
            track.save()
            messages.info(request,
                f'"{title}" uploaded and is under review. '
                f'Fingerprint check will complete shortly.')

        else:
            # No match found in database (new track)
            track.acoustid_status = 'passed'
            track.is_published    = True
            track.save()
            messages.success(request, f'✅ "{title}" uploaded and published!')

        # ── HANDLE TAGS ───────────────────────────────────────────────────
        if tags_raw:
            from django.utils.text import slugify
            from .models import Tag
            for tag_name in [t.strip() for t in tags_raw.split(',') if t.strip()]:
                tag, _ = Tag.objects.get_or_create(
                    name=tag_name[:50],
                    defaults={'slug': slugify(tag_name)[:50]}
                )
                track.tags.add(tag)

        return redirect('track_detail', track_id=track.id)

    # GET request
    return render(request, 'music/upload.html', {
        'genres':       genres,
        'license_info': LICENSE_INFO,
    })


def _detect_lyrics_language(lyrics_text):
    """
    Simple language detection for lyrics.
    Uses character frequency analysis — no external dependency needed.
    Returns ISO 639-1 language code.
    """
    text = lyrics_text.lower()[:500]

    # French indicators
    fr_words = ['je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
                'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et',
                'est', 'sont', 'avec', 'pour', 'dans', 'sur', 'que', 'qui',
                'pas', 'plus', 'comme', 'tout', 'bien', 'aussi', 'mais']
    # Spanish indicators
    es_words = ['yo', 'tu', 'el', 'ella', 'nosotros', 'ellos', 'el', 'la',
                'los', 'las', 'un', 'una', 'es', 'son', 'con', 'por', 'en',
                'que', 'quien', 'como', 'todo', 'bien', 'pero', 'muy']
    # Portuguese indicators
    pt_words = ['eu', 'tu', 'ele', 'ela', 'nos', 'eles', 'o', 'a', 'os',
                'as', 'um', 'uma', 'de', 'do', 'da', 'e', 'em', 'para',
                'que', 'como', 'muito', 'mais', 'tambem', 'mas']

    words = set(text.split())
    fr_score = len(words & set(fr_words))
    es_score = len(words & set(es_words))
    pt_score = len(words & set(pt_words))

    if fr_score >= 3 and fr_score >= es_score and fr_score >= pt_score:
        return 'fr'
    if es_score >= 3 and es_score > fr_score:
        return 'es'
    if pt_score >= 3 and pt_score > fr_score and pt_score > es_score:
        return 'pt'
    return 'en'


def _run_acoustid_check(track):
    """
    Run AcoustID fingerprint check.
    Returns dict with status: 'passed' | 'duplicate' | 'error' | 'no_match'
    
    DUPLICATE LOGIC:
    - If AcoustID returns a match with score > 0.7 by a DIFFERENT artist → DUPLICATE
    - If match is by the SAME artist → allowed (re-upload of own track)
    - If score < 0.7 → passed (different enough)
    - If AcoustID unavailable → error (held for review)
    """
    try:
        from apps.music.acoustid_check import check_acoustid
        result = check_acoustid(track.audio_file.path)

        if not result or result.get('error'):
            return {'status': 'error', 'message': str(result.get('error', 'AcoustID unavailable'))}

        score    = result.get('score', 0)
        matched  = result.get('artist', '')
        recording_id = result.get('recording_id', '')

        if score > 0.7:
            # Check if match is from same artist
            artist_name = track.artist.stage_name.lower().strip()
            match_name  = matched.lower().strip() if matched else ''

            if match_name and artist_name not in match_name and match_name not in artist_name:
                # Different artist → DUPLICATE
                return {
                    'status': 'duplicate',
                    'score':  score,
                    'matched_recording': recording_id,
                    'matched_artist':    matched,
                }

        return {
            'status': 'passed',
            'score':  score,
            'recording_id': recording_id,
        }

    except ImportError:
        # AcoustID module not available
        return {'status': 'error', 'message': 'AcoustID not configured'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def _flag_artist_for_investigation(artist, track, acoustid_result):
    """
    Flag artist for admin investigation when duplicate is detected.
    Creates a record the admin can see in /control/artists/.
    """
    try:
        note = (
            f"DUPLICATE UPLOAD DETECTED — {track.uploaded_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"Track: {track.title} (ID: {track.id})\n"
            f"AcoustID score: {acoustid_result.get('score', 0)*100:.1f}%\n"
            f"Matched: {acoustid_result.get('matched_artist', 'Unknown')} / "
            f"Recording {acoustid_result.get('matched_recording', '—')}\n"
            f"Action: Track blocked from publishing. Manual review required."
        )
        existing = artist.verification_note or ''
        if 'DUPLICATE' not in existing:
            artist.verification_note = note + ('\n\n' + existing if existing else '')
            artist.save(update_fields=['verification_note'])
    except Exception:
        pass


@login_required
def artist_dashboard(request):
    """Legacy artist dashboard — redirects to new one."""
    return redirect('artist_home_dashboard')

@login_required
def post_announcement(request):
    if not request.user.is_artist():
        return redirect('home')

    artist = request.user.artist_profile

    if request.method == 'POST':
        title    = request.POST.get('title', '').strip()
        body     = request.POST.get('body', '').strip()
        is_pinned = request.POST.get('is_pinned') == 'on'

        if title and body:
            from .models import Announcement
            Announcement.objects.create(
                artist=artist,
                title=title,
                body=body,
                is_pinned=is_pinned,
            )
            messages.success(request, 'Announcement posted!')
            return redirect('artist_dashboard')
        else:
            messages.error(request, 'Title and body are required.')

    return render(request, 'music/post_announcement.html', {'artist': artist})


@require_POST
def detect_lyrics(request):
    """
    Detect language of lyrics text submitted via Alpine.js fetch.
    Called from upload.html and edit_track.html.
    """
    import json
    try:
        body   = json.loads(request.body)
        lyrics = body.get('lyrics', '').strip()
    except (json.JSONDecodeError, AttributeError):
        lyrics = request.POST.get('lyrics', '').strip()

    if not lyrics:
        return JsonResponse({'language': 'unknown', 'confidence': 0})

    language = _detect_lyrics_language(lyrics)
    return JsonResponse({'language': language, 'confidence': 1})