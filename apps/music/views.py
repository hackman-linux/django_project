"""
NapsterLegal — Music Views
Upload, stream, track detail, artist page, trending home page.
"""
import os
from django.shortcuts   import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib     import messages
from django.http        import JsonResponse
from django.db.models   import Q, Sum

from .models  import Track, Album, Genre
from .forms   import TrackUploadForm
from apps.accounts.models import ArtistProfile


# ── RIGHTS CATALOGUE ─────────────────────────────────────────────────────────
LICENSE_INFO = {
    'all_rights':    {'name': 'All Rights Reserved',          'short': 'ARR',     'color': '#EF4444',
                      'desc': 'Full copyright. No use without explicit permission.'},
    'cc_by':         {'name': 'Creative Commons CC-BY 4.0',   'short': 'CC-BY',   'color': '#4F8EF7',
                      'desc': 'Share/adapt with credit. Commercial use allowed.'},
    'cc_by_nc':      {'name': 'Creative Commons CC-BY-NC 4.0','short': 'CC-BY-NC','color': '#F59E0B',
                      'desc': 'Share/adapt with credit. No commercial use.'},
    'cc_by_sa':      {'name': 'Creative Commons CC-BY-SA 4.0','short': 'CC-BY-SA','color': '#8B5CF6',
                      'desc': 'Derivatives must use the same license.'},
    'cc_by_nd':      {'name': 'Creative Commons CC-BY-ND 4.0','short': 'CC-BY-ND','color': '#2DD4BF',
                      'desc': 'Share with credit. No derivatives allowed.'},
    'public_domain': {'name': 'Public Domain (CC0)',           'short': 'CC0',     'color': '#34D399',
                      'desc': 'No rights reserved. Free for any use worldwide.'},
}


# ── HOME ─────────────────────────────────────────────────────────────────────

def home(request):
    """Landing page — trending tracks, new releases, genre grid."""
    # Redirect admin/staff to control panel (unless previewing)
    if (request.user.is_authenticated and
            (request.user.is_staff or request.user.is_superuser) and
            request.GET.get('preview') != '1'):
        return redirect('/control/')

    safe = _public_tracks()

    # Real-time trending — always falls back gracefully
    try:
        from .trending import get_trending_tracks
        _trending_data  = get_trending_tracks(limit=12)
        trending_tracks = [t['track'] for t in _trending_data]
    except Exception:
        trending_tracks = []

    # If still empty, just show newest published tracks
    if not trending_tracks:
        trending_tracks = list(safe.order_by('-play_count')[:12])

    # New releases from followed artists (post-login personalisation)
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
        'genres':            Genre.objects.all()[:10],
        'new_from_followed': new_from_followed,
    })


def _public_tracks():
    """Return only published, non-flagged tracks."""
    return Track.objects.filter(is_published=True).filter(
        Q(acoustid_status='passed') |
        Q(acoustid_status='pending') |
        Q(acoustid_status='') |
        Q(acoustid_status__isnull=True)
    ).select_related('artist', 'genre')


# ── TRACK DETAIL ─────────────────────────────────────────────────────────────

def track_detail(request, track_id):
    """Individual track page."""
    # Artists can preview their own unpublished/flagged tracks
    if (request.user.is_authenticated and
            hasattr(request.user, 'artist_profile')):
        try:
            track = Track.objects.get(
                id=track_id, artist=request.user.artist_profile)
        except Track.DoesNotExist:
            track = get_object_or_404(Track, id=track_id, is_published=True)
    else:
        track = get_object_or_404(Track, id=track_id, is_published=True)

    related  = _public_tracks().filter(genre=track.genre).exclude(id=track.id)[:6]
    comments = track.comments.select_related('user').order_by('created_at')

    return render(request, 'music/track_detail.html', {
        'track':        track,
        'related':      related,
        'comments':     comments,
        'license_info': LICENSE_INFO.get(track.license_type, {}),
    })


# ── ARTIST PAGE ──────────────────────────────────────────────────────────────

def artist_page(request, artist_id):
    artist        = get_object_or_404(ArtistProfile, id=artist_id)
    tracks        = _public_tracks().filter(artist=artist).order_by('-uploaded_at')
    albums        = Album.objects.filter(artist=artist, is_published=True)
    announcements = []
    try:
        from apps.music.models import Announcement
        announcements = Announcement.objects.filter(
            artist=artist).order_by('-created_at')[:5]
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

    follower_count = 0
    try:
        follower_count = artist.followers.count()
    except Exception:
        pass

    return render(request, 'music/artist_page.html', {
        'artist':        artist,
        'tracks':        tracks,
        'albums':        albums,
        'announcements': announcements,
        'is_following':  is_following,
        'follower_count':follower_count,
    })


# ── UPLOAD ───────────────────────────────────────────────────────────────────

@login_required
def upload_track(request):
    """
    Artist track upload.
    Steps:
      1. Validate file type + size
      2. Save track as unpublished
      3. Auto-extract duration (mutagen)
      4. Run AcoustID fingerprint check
      5. If duplicate   → keep unpublished, flag artist for admin
      6. If clean/error → publish automatically
      7. Handle tags
    """
    # Only artists can upload
    if not request.user.is_artist():
        messages.error(request, 'Only artists can upload tracks.')
        return redirect('home')

    artist = request.user.artist_profile

    # Rejected artists cannot upload
    if artist.verification_status == 'rejected':
        messages.error(request,
            'Your artist account has been rejected. '
            'Contact support if you believe this is an error.')
        return redirect('artist_home_dashboard')

    genres = Genre.objects.all().order_by('name')

    if request.method != 'POST':
        # GET — show empty form
        return render(request, 'music/upload.html', {
            'genres':       genres,
            'license_info': LICENSE_INFO,
            'form':         TrackUploadForm(),
        })

    # ── POST — process upload ─────────────────────────────────────────────
    form = TrackUploadForm(request.POST, request.FILES)

    if not form.is_valid():
        for field, errs in form.errors.items():
            for e in errs:
                messages.error(request, f'{field}: {e}' if field != '__all__' else e)
        return render(request, 'music/upload.html', {
            'genres':       genres,
            'license_info': LICENSE_INFO,
            'form':         form,
        })

    # ── Build track object (don't save yet) ──────────────────────────────
    track              = form.save(commit=False)
    track.artist       = artist
    track.is_published = False          # never published until fingerprint passes
    track.acoustid_status = 'pending'

    # Auto-detect lyrics language
    if track.lyrics:
        track.lyrics_language = _detect_lyrics_language(track.lyrics)

    # Auto-extract duration with mutagen
    audio_file = form.cleaned_data['audio_file']
    try:
        import mutagen
        tmp = mutagen.File(audio_file)
        if tmp and hasattr(tmp, 'info'):
            track.duration = int(tmp.info.length)
        audio_file.seek(0)          # rewind after mutagen reads it
    except Exception:
        pass

    track.save()
    form.save_m2m()

    # ── Handle tags ───────────────────────────────────────────────────────
    tags_raw = request.POST.get('tags', '').strip()
    if tags_raw:
        from django.utils.text import slugify
        try:
            from .models import Tag
            for tag_name in [t.strip() for t in tags_raw.split(',') if t.strip()]:
                tag, _ = Tag.objects.get_or_create(
                    name=tag_name[:50],
                    defaults={'slug': slugify(tag_name)[:50]}
                )
                track.tags.add(tag)
        except Exception:
            pass

    # ── AcoustID fingerprint check ────────────────────────────────────────
    acoustid_result = _run_acoustid_check(track)

    if acoustid_result['status'] == 'duplicate':
        track.acoustid_status = 'failed'
        track.acoustid_score  = acoustid_result.get('score', 0)
        track.acoustid_result = acoustid_result.get('matched_recording', '')
        track.is_published    = False
        track.save(update_fields=['acoustid_status', 'acoustid_score',
                                   'acoustid_result', 'is_published'])

        _flag_artist_for_investigation(artist, track, acoustid_result)

        messages.warning(request,
            f'⚠️ "{track.title}" matched an existing recording '
            f'({acoustid_result.get("score", 0)*100:.0f}% confidence). '
            f'It will NOT be published until an admin reviews it. '
            f'If this is your original work, the admin will verify and approve it. '
            f'Reference: {track.id}')
        return redirect('artist_home_dashboard')

    elif acoustid_result['status'] == 'error':
        # fpcalc not installed / API key missing → hold for review, don't block
        track.acoustid_status = 'error'
        track.is_published    = False
        track.save(update_fields=['acoustid_status', 'is_published'])
        messages.info(request,
            f'"{track.title}" has been uploaded and is under review. '
            f'It will appear publicly once verified.')

    else:
        # passed or no_match → auto-publish
        track.acoustid_status = 'passed'
        track.acoustid_score  = acoustid_result.get('score', 0)
        track.is_published    = True
        track.save(update_fields=['acoustid_status', 'acoustid_score', 'is_published'])

        # Notify followers
        try:
            from apps.accounts.models import Notification
            from apps.social.models   import Follow
            for follow in Follow.objects.filter(artist=artist).select_related('follower')[:500]:
                Notification.send(
                    recipient   = follow.follower,
                    notif_type  = Notification.TYPE_ARTIST_POST,
                    title       = f'New track by {artist.stage_name}: {track.title}',
                    body        = f'{artist.stage_name} just released a new track.',
                    link        = f'/track/{track.id}/',
                    sender_name = artist.stage_name,
                )
        except Exception:
            pass

        messages.success(request,
            f'✅ "{track.title}" uploaded and published! '
            f'{"Fingerprint verified." if acoustid_result["status"] == "passed" else ""}')

    return redirect('track_detail', track_id=track.id)


# ── UPLOAD HELPERS ────────────────────────────────────────────────────────────

def _run_acoustid_check(track):
    """
    Run AcoustID fingerprint check.
    Returns dict with status: 'passed' | 'duplicate' | 'error' | 'no_match'
    """
    try:
        from .acoustid_check import check_acoustid
        result = check_acoustid(track.audio_file.path)

        if not result or result.get('status') == 'error':
            return {'status': 'error',
                    'message': result.get('error', 'AcoustID unavailable')}

        score   = result.get('score', 0)
        matched = result.get('artist', '')
        rec_id  = result.get('recording_id', '')

        if score > 0.7:
            artist_name = track.artist.stage_name.lower().strip()
            match_name  = matched.lower().strip()
            # Allow if it's the same artist re-uploading their own track
            if match_name and artist_name not in match_name and match_name not in artist_name:
                return {
                    'status':             'duplicate',
                    'score':              score,
                    'matched_recording':  rec_id,
                    'matched_artist':     matched,
                }

        return {'status': 'passed', 'score': score, 'recording_id': rec_id}

    except ImportError:
        return {'status': 'error', 'message': 'AcoustID module not installed'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def _flag_artist_for_investigation(artist, track, acoustid_result):
    """Update artist's verification_note with duplicate detection info."""
    try:
        note = (
            f'DUPLICATE UPLOAD DETECTED — {track.uploaded_at.strftime("%Y-%m-%d %H:%M")}\n'
            f'Track: {track.title} (ID: {track.id})\n'
            f'AcoustID score: {acoustid_result.get("score", 0)*100:.1f}%\n'
            f'Matched: {acoustid_result.get("matched_artist", "Unknown")} / '
            f'Recording {acoustid_result.get("matched_recording", "—")}\n'
            f'Action: Track blocked. Manual review required.'
        )
        existing = artist.verification_note or ''
        if 'DUPLICATE' not in existing:
            artist.verification_note = note + ('\n\n' + existing if existing else '')
            artist.save(update_fields=['verification_note'])
    except Exception:
        pass


def _detect_lyrics_language(lyrics_text):
    """
    Frequency-based language detection for lyrics.
    Returns ISO 639-1 code. No external API needed.
    """
    sample = lyrics_text.lower()[:800]
    words  = set(sample.split())

    FR = {'je','tu','il','elle','nous','vous','ils','elles','le','la','les','un','une',
          'des','du','de','et','est','sont','avec','pour','dans','sur','que','qui',
          'pas','plus','comme','tout','bien','aussi','mais','mon','ma','son','sa',
          'au','aux','ce','cette','ne','se','en','y','très','avoir','être','faire'}
    ES = {'yo','él','ella','nosotros','ellos','el','la','los','las','un','una',
          'es','son','con','por','en','que','quien','como','todo','bien','pero',
          'muy','también','me','te','le','nos','mi','su','del','al','ya','si','no'}
    PT = {'eu','ele','ela','nós','eles','elas','o','a','os','as','um','uma','de',
          'do','da','dos','das','em','no','na','que','com','para','por','mas',
          'muito','também','me','te','lhe','meu','minha','seu','sua','não','já'}
    DE = {'ich','du','er','sie','es','wir','ihr','der','die','das','ein','eine',
          'ist','sind','und','mit','für','auf','in','nicht','auch','aber','wenn',
          'dann','noch','von','zu','bei','nach','über','haben','sein','werden'}

    scores = {
        'fr': len(words & FR),
        'es': len(words & ES),
        'pt': len(words & PT),
        'de': len(words & DE),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] >= 3 else 'en'


# ── ARTIST DASHBOARD (legacy redirect) ───────────────────────────────────────

@login_required
def artist_dashboard(request):
    return redirect('artist_home_dashboard')


# ── ANNOUNCEMENT ─────────────────────────────────────────────────────────────

@login_required
def post_announcement(request):
    if not request.user.is_artist():
        messages.error(request, 'Only artists can post announcements.')
        return redirect('home')
    artist = request.user.artist_profile

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        body  = request.POST.get('body',  '').strip()
        if title and body:
            try:
                from .models import Announcement
                ann = Announcement.objects.create(
                    artist=artist, title=title, body=body)
                # Notify followers
                try:
                    from apps.accounts.models import Notification
                    from apps.social.models   import Follow
                    for follow in Follow.objects.filter(
                            artist=artist).select_related('follower')[:500]:
                        Notification.send(
                            recipient   = follow.follower,
                            notif_type  = Notification.TYPE_ARTIST_POST,
                            title       = f'{artist.stage_name}: {title}',
                            body        = body[:200],
                            link        = f'/artist/{artist.id}/',
                            sender_name = artist.stage_name,
                        )
                except Exception:
                    pass
                messages.success(request, 'Announcement posted!')
            except Exception as e:
                messages.error(request, f'Error: {e}')
        else:
            messages.error(request, 'Title and body are required.')
    return redirect('artist_home_dashboard')
