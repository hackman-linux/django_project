from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET
from django.shortcuts import get_object_or_404
from apps.music.models import Track


def _log_play_event(request, track):
    """Log a play event to MariaDB analytics database."""
    try:
        from apps.analytics.models import PlayEvent
        # Get country from IP (simplified — just store the IP)
        ip = (request.META.get('HTTP_X_FORWARDED_FOR', '')
              .split(',')[0].strip()
              or request.META.get('REMOTE_ADDR', ''))

        # Detect device type from user agent
        ua = request.META.get('HTTP_USER_AGENT', '').lower()
        if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
            device = 'mobile'
        elif 'tablet' in ua or 'ipad' in ua:
            device = 'tablet'
        else:
            device = 'desktop'

        PlayEvent.objects.using('analytics').create(
            track_id=track.id,
            user_id=request.user.id if request.user.is_authenticated else None,
            session_id=request.session.session_key or '',
            ip_address=ip,
            device_type=device,
            listened_duration=0,   # updated via JS later
            completed=False,
        )
    except Exception as e:
        # Never let analytics break the streaming
        print(f"Analytics log error: {e}")


@require_GET
def stream_track(request, track_id):
    """Stream audio file and log the play event to MariaDB."""
    track = get_object_or_404(Track, id=track_id, is_published=True)

    if not track.audio_file:
        raise Http404("Audio file not found.")

    # Increment play count on PostgreSQL
    Track.objects.filter(id=track_id).update(
        play_count=track.play_count + 1
    )

    # Log to MariaDB analytics
    _log_play_event(request, track)

    # Stream the file
    response = FileResponse(
        track.audio_file.open('rb'),
        content_type='audio/mpeg'
    )
    response['Content-Disposition'] = f'inline; filename="{track.title}.mp3"'
    response['Accept-Ranges'] = 'bytes'
    return response


def track_info(request, track_id):
    """Return track metadata as JSON for the JS player."""
    track = get_object_or_404(Track, id=track_id, is_published=True)
    return JsonResponse({
        'id':         str(track.id),
        'title':      track.title,
        'artist':     str(track.artist),
        'duration':   track.duration,
        'cover':      track.cover_image.url if track.cover_image else '',
        'stream_url': f'/api/stream/{track.id}/',
    })
