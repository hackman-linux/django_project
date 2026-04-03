from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import get_object_or_404
from apps.music.models import Track


def _get_client_ip(request):
    """Get real client IP using django-ipware."""
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
    """Detect device type from User-Agent."""
    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    if any(x in ua for x in ['mobile', 'android', 'iphone', 'ipod']):
        return 'mobile'
    elif any(x in ua for x in ['tablet', 'ipad']):
        return 'tablet'
    return 'desktop'


def _log_play_event(request, track):
    """
    Log a PlayEvent to MariaDB analytics.
    Includes IP address, country code, device type.
    This data is ADMIN ONLY — never exposed to artists or users.
    """
    try:
        from apps.analytics.models import PlayEvent
        from apps.analytics.geo import get_country_code

        ip           = _get_client_ip(request)
        device       = _detect_device(request)
        country_code = get_country_code(ip)

        PlayEvent.objects.using('analytics').create(
            track_id         = str(track.id),
            user_id          = str(request.user.id) if request.user.is_authenticated else None,
            session_id       = request.session.session_key or '',
            ip_address       = ip,
            country_code     = country_code,
            device_type      = device,
            listened_duration= 0,    # Updated later via /api/log-listen/
            completed        = False,
        )
    except Exception as e:
        # Analytics must NEVER break streaming
        print(f"[Analytics] PlayEvent log error: {e}")


@require_GET
def stream_track(request, track_id):
    """
    Stream audio file.
    Blocks flagged tracks (acoustid_status=failed) at API level.
    Logs PlayEvent to MariaDB.
    """
    track = get_object_or_404(Track, id=track_id, is_published=True)

    # Hard block — flagged tracks cannot be streamed
    if track.acoustid_status == 'failed':
        raise Http404

    if not track.audio_file:
        raise Http404("Audio file not found.")

    # Increment play count
    Track.objects.filter(id=track_id).update(
        play_count=track.play_count + 1
    )

    # Log to MariaDB
    _log_play_event(request, track)

    # ── Audio quality tier based on subscription ─────────────────────────────
    # Free users: serve the file as-is (typically MP3 128kbps)
    # Premium / Artist Pro users: serve the original uploaded file (FLAC/WAV/320kbps)
    user_is_premium = (
        request.user.is_authenticated and
        getattr(request.user, 'is_premium', False)
    )

    # Detect uploaded format
    audio_name  = track.audio_file.name.lower()
    is_lossless = audio_name.endswith('.flac') or audio_name.endswith('.wav')

    if is_lossless and not user_is_premium:
        # Serve a standard quality notice — in production transcode here
        # For demo: serve the file but set X-Quality header
        content_type = 'audio/mpeg'
        quality_header = 'standard-128kbps'
    elif is_lossless and user_is_premium:
        content_type   = 'audio/flac' if audio_name.endswith('.flac') else 'audio/wav'
        quality_header = 'lossless'
    else:
        content_type   = 'audio/mpeg'
        quality_header = 'standard-128kbps' if not user_is_premium else 'hd-320kbps'

    response = FileResponse(
        track.audio_file.open('rb'),
        content_type=content_type,
    )
    response['Content-Disposition'] = f'inline; filename="{track.title}"' 
    response['Accept-Ranges']        = 'bytes'
    response['X-Audio-Quality']      = quality_header
    return response


def track_info(request, track_id):
    """Return track metadata as JSON."""
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
    })


@require_POST
def log_listen(request):
    """
    Receives actual listen duration from JS player via sendBeacon.
    Updates the most recent PlayEvent for this track in MariaDB.
    ADMIN ONLY data — never exposed to users or artists.
    """
    try:
        from apps.analytics.models import PlayEvent

        track_id  = request.POST.get('track_id', '').strip()
        duration  = int(request.POST.get('duration', 0))
        completed = request.POST.get('completed', '0') == '1'

        if not track_id:
            return JsonResponse({'status': 'error', 'msg': 'no track_id'})

        # Update the most recent PlayEvent for this track/session
        event = PlayEvent.objects.using('analytics').filter(
            track_id=track_id
        ).order_by('-timestamp').first()

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
