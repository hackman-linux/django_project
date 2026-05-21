"""
NapsterLegal — API Views
Handles: streaming, track info, listen logging, offline downloads,
         lyrics language detection.
"""
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
import os

from apps.music.models import Track, OfflineDownload


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _get_client_ip(request):
    try:
        from ipware import get_client_ip
        ip, _ = get_client_ip(request)
        return ip or '0.0.0.0'
    except Exception:
        return (
            request.META.get('HTTP_X_FORWARDED_FOR', '')
            .split(',')[0].strip()
            or request.META.get('REMOTE_ADDR', '0.0.0.0')
        )


def _detect_device(request):
    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    if any(x in ua for x in ['mobile', 'android', 'iphone', 'ipod']):
        return 'mobile'
    elif any(x in ua for x in ['tablet', 'ipad']):
        return 'tablet'
    return 'desktop'


def _log_play_event(request, track):
    """Log a PlayEvent to MariaDB. Admin-only data."""
    try:
        from apps.analytics.models import PlayEvent
        from apps.analytics.geo import get_country_code

        ip           = _get_client_ip(request)
        device       = _detect_device(request)
        country_code = get_country_code(ip)

        PlayEvent.objects.using('analytics').create(
            track_id          = str(track.id),
            user_id           = str(request.user.id) if request.user.is_authenticated else None,
            session_id        = request.session.session_key or '',
            ip_address        = ip,
            country_code      = country_code,
            device_type       = device,
            listened_duration = 0,
            completed         = False,
        )
    except Exception as e:
        print(f"[Analytics] PlayEvent log error: {e}")


# ── STREAM ────────────────────────────────────────────────────────────────────

@require_GET
def stream_track(request, track_id):
    """
    Stream audio file.
    - Blocks flagged tracks (acoustid_status=failed).
    - Serves quality based on subscription tier.
    - Logs PlayEvent to MariaDB.
    """
    track = get_object_or_404(Track, id=track_id, is_published=True)

    if track.acoustid_status == 'failed':
        raise Http404("Track unavailable.")

    if not track.audio_file:
        raise Http404("Audio file not found.")

    # Increment play count atomically
    Track.objects.filter(id=track_id).update(play_count=track.play_count + 1)

    # Log analytics
    _log_play_event(request, track)

    # Determine quality tier
    user_is_premium = (
        request.user.is_authenticated and
        getattr(request.user, 'is_premium', False)
    )
    audio_name  = track.audio_file.name.lower()
    is_lossless = audio_name.endswith('.flac') or audio_name.endswith('.wav')

    if is_lossless and user_is_premium:
        content_type   = 'audio/flac' if audio_name.endswith('.flac') else 'audio/wav'
        quality_header = 'lossless'
    elif is_lossless and not user_is_premium:
        content_type   = 'audio/mpeg'
        quality_header = 'standard-128kbps'
    else:
        content_type   = 'audio/mpeg'
        quality_header = 'hd-320kbps' if user_is_premium else 'standard-128kbps'

    response = FileResponse(
        track.audio_file.open('rb'),
        content_type=content_type,
    )
    response['Content-Disposition'] = f'inline; filename="{track.title}"'
    response['Accept-Ranges']        = 'bytes'
    response['X-Audio-Quality']      = quality_header
    return response


# ── TRACK INFO ────────────────────────────────────────────────────────────────

def track_info(request, track_id):
    """Return track metadata as JSON for the player."""
    track = get_object_or_404(Track, id=track_id, is_published=True)
    if track.acoustid_status == 'failed':
        raise Http404
    return JsonResponse({
        'id':         str(track.id),
        'title':      track.title,
        'artist':     str(track.artist),
        'duration':   track.duration,
        'cover':      track.cover_image.url if track.cover_image else '',
        'stream_url': f'/api/stream/{track.id}/',
        'lyrics':     track.lyrics or '',
        'has_lyrics': bool(track.lyrics and track.lyrics.strip()),
    })


# ── LOG LISTEN ────────────────────────────────────────────────────────────────

@require_POST
def log_listen(request):
    """
    Receives actual listen duration from JS player via sendBeacon.
    Updates the most recent PlayEvent in MariaDB. Admin-only data.
    """
    try:
        from apps.analytics.models import PlayEvent

        track_id  = request.POST.get('track_id', '').strip()
        duration  = int(request.POST.get('duration', 0))
        completed = request.POST.get('completed', '0') == '1'

        if not track_id:
            return JsonResponse({'status': 'error', 'msg': 'no track_id'})

        event = (PlayEvent.objects.using('analytics')
                 .filter(track_id=track_id)
                 .order_by('-timestamp')
                 .first())

        if event:
            event.listened_duration = duration
            event.completed         = completed
            event.save(
                using='analytics',
                update_fields=['listened_duration', 'completed']
            )
    except Exception as e:
        print(f"[Analytics] log_listen error: {e}")

    return JsonResponse({'status': 'ok'})


# ── OFFLINE DOWNLOAD ──────────────────────────────────────────────────────────

@login_required
def download_track(request, track_id):
    """
    Serve track for offline use. Quality depends on subscription tier.

    Free:           blocked (403)
    Premium ($4.99):320kbps MP3, 30 days
    Listener Pro:   FLAC lossless, 30 days
    Artist Pro:     320kbps MP3, 30 days
    Artist Label:   FLAC lossless, 30 days
    """
    track = get_object_or_404(Track, id=track_id, is_published=True)

    if not track.audio_file:
        return JsonResponse({'error': 'No audio file'}, status=404)

    user = request.user

    # Get subscription plan slug
    plan = 'free'
    try:
        active_sub = user.subscriptions.filter(status='active').order_by('-created_at').first()
        if active_sub:
            plan = active_sub.plan.slug
    except Exception:
        plan = getattr(user, 'subscription_plan', 'free')

    quality_map = {
        'free':             ('128kbps', 0),
        'premium_listener': ('320kbps', 30),
        'listener_pro':     ('flac',    30),
        'artist_pro':       ('320kbps', 30),
        'artist_label':     ('flac',    30),
    }

    quality, days = quality_map.get(plan, ('128kbps', 0))

    if days == 0:
        return JsonResponse({
            'error':       'Offline downloads require a Premium or Pro subscription.',
            'upgrade_url': '/pricing/',
        }, status=403)

    # Record download
    expires = timezone.now() + timedelta(days=days)
    OfflineDownload.objects.update_or_create(
        user=user, track=track,
        defaults={
            'quality':       quality,
            'expires_at':    expires,
            'downloaded_at': timezone.now(),
        }
    )

    # Serve file
    response = FileResponse(
        open(track.audio_file.path, 'rb'),
        content_type='audio/mpeg',
        as_attachment=True,
        filename=f"{track.title} — {track.artist}.mp3",
    )
    response['X-Quality']  = quality
    response['X-Expires']  = expires.isoformat()
    response['X-Track-Id'] = str(track.id)
    return response


@login_required
def my_downloads(request):
    """List the current user's active offline downloads as JSON."""
    downloads = (OfflineDownload.objects
                 .filter(user=request.user, expires_at__gt=timezone.now())
                 .select_related('track', 'track__artist'))

    return JsonResponse({
        'downloads': [
            {
                'track_id':   str(d.track.id),
                'title':      d.track.title,
                'artist':     str(d.track.artist),
                'quality':    d.quality,
                'expires_at': d.expires_at.isoformat(),
                'cover':      d.track.cover_image.url if d.track.cover_image else None,
            }
            for d in downloads
        ]
    })


# ── LYRICS LANGUAGE DETECTION ────────────────────────────────────────────────

@require_POST
def detect_lyrics(request):
    """
    Detect language of submitted lyrics text.
    Called from the upload form via AJAX so user sees detected language live.
    Returns ISO 639-1 code + full language name.

    Uses frequency analysis — no external API or library needed.
    Supports: French, Spanish, Portuguese, English.
    """
    text = request.POST.get('lyrics', '').strip()

    if not text:
        return JsonResponse({'language': 'en', 'name': 'English', 'confidence': 0})

    code, name, confidence = _detect_language(text)

    return JsonResponse({
        'language':   code,
        'name':       name,
        'confidence': confidence,
        'message':    f'Detected: {name} ({confidence}% confident)',
    })


def _detect_language(text):
    """
    Frequency-based language detection.
    Returns (code, name, confidence_percent).
    """
    sample = text.lower()[:1000]
    words  = set(sample.split())

    SIGNATURES = {
        'fr': {
            'words': {
                'je','tu','il','elle','nous','vous','ils','elles',
                'le','la','les','un','une','des','du','de','et',
                'est','sont','avec','pour','dans','sur','que','qui',
                'pas','plus','comme','tout','bien','aussi','mais',
                'mon','ma','mes','ton','ta','tes','son','sa','ses',
                'au','aux','ce','cet','cette','ces','moi','toi','lui',
                'ne','se','en','y','dont','où','quand','comment','très',
                'avoir','être','faire','aller','venir','voir','savoir',
            },
            'trigrams': ["les","est","des","que","une","pas","pour","dans"],
            'name': 'French',
        },
        'es': {
            'words': {
                'yo','tu','él','ella','nosotros','vosotros','ellos','ellas',
                'el','la','los','las','un','una','unos','unas',
                'es','son','estar','ser','con','por','en','que',
                'quien','como','todo','bien','pero','muy','también',
                'me','te','le','nos','os','les','mi','mis','su','sus',
                'del','al','lo','ya','si','no','más','menos',
                'hacer','tener','poder','querer','ver','dar','saber',
            },
            'trigrams': ["los","las","que","una","con","por","del"],
            'name': 'Spanish',
        },
        'pt': {
            'words': {
                'eu','tu','ele','ela','nós','vós','eles','elas',
                'o','a','os','as','um','uma','uns','umas',
                'de','do','da','dos','das','em','no','na',
                'que','com','para','por','mas','também','muito',
                'me','te','lhe','nos','se','meu','minha','seu','sua',
                'ao','à','isto','isso','aqui','lá','já','ainda',
                'ser','estar','ter','fazer','ir','ver','dar','poder',
            },
            'trigrams': ["que","com","uma","para","não","dos","das"],
            'name': 'Portuguese',
        },
        'de': {
            'words': {
                'ich','du','er','sie','es','wir','ihr','sie',
                'der','die','das','ein','eine','eines','einem',
                'ist','sind','und','mit','für','auf','in','an',
                'nicht','auch','aber','wenn','dann','noch','schon',
                'mich','dich','ihn','uns','euch','mir','dir','ihm',
                'von','zu','bei','nach','vor','über','unter','durch',
                'haben','sein','werden','können','müssen','sollen',
            },
            'trigrams': ["die","der","und","das","ist","nicht","ein"],
            'name': 'German',
        },
    }

    scores = {}
    for lang, data in SIGNATURES.items():
        word_hits    = len(words & data['words'])
        trigram_hits = sum(1 for t in data['trigrams'] if t in sample)
        scores[lang] = word_hits * 2 + trigram_hits

    if not any(scores.values()):
        return ('en', 'English', 50)

    best_lang = max(scores, key=scores.get)
    best_score = scores[best_lang]
    total      = sum(scores.values()) or 1
    confidence = min(int(best_score / total * 100), 99)

    if confidence < 30:
        return ('en', 'English', 50)

    name = SIGNATURES[best_lang]['name']
    return (best_lang, name, confidence)
