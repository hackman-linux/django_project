from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET
from django.shortcuts import get_object_or_404
from apps.music.models import Track


def _log_play_event(request, track):
    """Log a play event to MariaDB analytics database."""
    try:
        from apps.analytics.models import PlayEvent
        # Get country from IP (simplified — just store the IP)
        try:
            from ipware import get_client_ip
            ip, _ = get_client_ip(request)
            ip = ip or '0.0.0.0'
        except Exception:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')

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


from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

@require_POST
def log_listen(request):
   
    # Receives actual listen duration from the JS player.
    # Updates the most recent PlayEvent for this track in MariaDB.
    # This data is ADMIN ONLY — never exposed to artists or users.
    try:
        from apps.analytics.models import PlayEvent
        track_id  = request.POST.get('track_id', '')
        duration  = int(request.POST.get('duration', 0))
        completed = request.POST.get('completed', '0') == '1'

        if not track_id:
            from django.http import JsonResponse
            return JsonResponse({'status': 'error', 'msg': 'no track_id'})

        # Update the most recent PlayEvent for this track
        event = PlayEvent.objects.using('analytics').filter(
            track_id=track_id
        ).order_by('-timestamp').first()

        if event:
            event.listened_duration = duration
            event.completed = completed
            event.save(using='analytics', update_fields=['listened_duration', 'completed'])

    except Exception as e:
        print(f"log_listen error: {e}")

    from django.http import JsonResponse
    return JsonResponse({'status': 'ok'})
